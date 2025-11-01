"""Contracts/behavior_contract.py

根据 Kobe WorkPlan 文档（尤其是 04、16、17、18、24）实现启动契约、知识库加载、
Webhook 校验以及 AgentsBridge 流程。
"""
from __future__ import annotations

import json
import logging
import os
import asyncio
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Literal,
    TYPE_CHECKING,
)

import yaml
from fastapi import HTTPException
from starlette import status

from SharedUtility.core.adapters import build_core_schema
from SharedUtility.core.context import ContextBridge
from SharedUtility.core.schema import SchemaValidationError
from SharedUtility.Contracts.toolcalls import LayoutMismatch, call_compare_tree, call_scan_tree
from OpenaiAgents.UnifiedCS import AgentsBridge as UnifiedAgentsBridge

if TYPE_CHECKING:  # pragma: no cover
    from aiogram import Router

try:  # pragma: no cover - redis 为可选依赖
    import redis  # type: ignore[import]
    from redis.exceptions import RedisError  # type: ignore[import]
except Exception:  # pragma: no cover - redis 缺失时不可用
    redis = None  # type: ignore[assignment]

    class RedisError(Exception):  # type: ignore[misc,override]
        """占位异常：当 redis 未安装时使用。"""
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode


logger = logging.getLogger("kobe.contract")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class BootstrapState:
    """保存 aiogram 组件，供运行期复用。"""

    bot: Any
    dispatcher: Any
    router: Any
    repo_root: Path
    redis_url: Optional[str] = None


_BOOTSTRAP_STATE: Optional[BootstrapState] = None
_BOOTSTRAP_CONTEXT: Dict[str, Any] = {}
_AGENTS_BRIDGE: Optional["AgentsBridge"] = None


class TopLevelAgency(TypedDict):
    key: str
    name: str
    path: str
    keywords: list[str]


class ServiceIndexEntry(TypedDict):
    service_id: str
    name: str
    path: str
    overview: str
    scenarios: list[str]
    required_docs: list[str]
    summary_text: str
    keywords: list[str]


class TokensBudget(TypedDict):
    per_call_max_tokens: int
    per_flow_max_tokens: int
    summary_threshold_tokens: int


class AgentRequest(TypedDict, total=False):
    prompt: str
    convo_id: str
    language: str
    intent_hint: str
    attachments: list[str]
    kb_scope: list[str]
    tokens_budget: TokensBudget
    system_tags: list[str]


class ServiceMatch(TypedDict):
    agency_id: str
    agency_name: str
    service_id: str
    service_name: str
    service_payload: Dict[str, Any]
    overview: str
    scenarios: list[str]
    required_docs: list[str]
    summary_text: str
    confidence: float


def _default_metrics_state() -> Dict[str, Any]:
    return {
        "telegram_updates_total": 0,
        "telegram_inbound_total": 0,
        "telegram_ignored_total": 0,
        "telegram_streaming_failures": 0,
        "telegram_placeholder_latency_sum": 0.0,
        "telegram_placeholder_latency_count": 0,
        "webhook_signature_failures": 0,
        "webhook_rtt_ms_sum": 0.0,
        "webhook_rtt_ms_count": 0,
        "last_webhook_latency_ms": 0.0,
    }


def behavior_bootstrap(
    *,
    repo_root: Path | str,
    redis_url: Optional[str] = None,
    runtime_policy_path: Optional[Path | str] = None,
    attach_handlers: bool = True,
) -> Dict[str, Any]:
    """初始化 aiogram Bot/Dispatcher/Router，加载运行策略并记录遥测。"""

    root_path = Path(repo_root).resolve()
    request_id = ContextBridge.request_id()
    timeline: list[Dict[str, Any]] = []

    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("bootstrap_refused_missing_token")
    secret = (os.getenv("TELEGRAM_BOT_SECRETS") or "").strip()
    timeline.append(
        {
            "stage": "env_load",
            "status": "ok",
            "has_secret": bool(secret),
        }
    )

    config_root = root_path / "SharedUtility" / "Config"
    policy_file = Path(runtime_policy_path) if runtime_policy_path else config_root / "runtime_policy.json"
    try:
        policy_raw = json.loads(policy_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - 配置缺失时直接拒绝
        timeline.append({"stage": "policy_load", "status": "error", "error": str(exc)})
        raise
    except json.JSONDecodeError as exc:  # pragma: no cover
        timeline.append({"stage": "policy_load", "status": "error", "error": str(exc)})
        raise RuntimeError(f"runtime_policy_invalid_json: {exc}") from exc
    else:
        timeline.append({"stage": "policy_load", "status": "ok", "path": str(policy_file)})

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
    dispatcher = Dispatcher()
    setattr(dispatcher, "bot", bot)
    setattr(bot, "dispatcher", dispatcher)
    router: Any = None
    if attach_handlers:
        try:
            message_module = import_module("TelegramAPI.handlers.message")
            router = getattr(message_module, "router", None)
            if router is None:
                raise AttributeError("TelegramAPI.handlers.message.router 缺失")
            dispatcher.include_router(router)
            dispatcher.workflow_data["message_router_attached"] = True
            timeline.append(
                {
                    "stage": "router_attach",
                    "status": "ok",
                    "router": getattr(router, "name", "unknown"),
                }
            )
        except Exception as exc:  # pragma: no cover - 导入失败属于启动错误
            timeline.append({"stage": "router_attach", "status": "error", "error": str(exc)})
            raise
    else:
        timeline.append({"stage": "router_attach", "status": "skipped"})

    metrics_state = _default_metrics_state()
    dispatcher.workflow_data.setdefault("metrics", metrics_state)
    dispatcher.workflow_data["runtime_policy"] = dict(policy_raw)
    if redis_url:
        dispatcher.workflow_data["redis_url"] = redis_url

    asset_guard_report = behavior_asset_guard(root_path)
    timeline.append({"stage": "asset_guard", "status": asset_guard_report.get("status", "ok")})

    global _BOOTSTRAP_STATE, _BOOTSTRAP_CONTEXT
    router_ref = router if router is not None else getattr(dispatcher, "router", None)
    _BOOTSTRAP_STATE = BootstrapState(
        bot=bot,
        dispatcher=dispatcher,
        router=router_ref or dispatcher,
        repo_root=root_path,
        redis_url=redis_url,
    )
    _BOOTSTRAP_CONTEXT = {
        "policy": dict(policy_raw),
        "metrics": metrics_state,
        "asset_guard": asset_guard_report,
        "timeline": list(timeline),
        "redis": {"url": redis_url, "mode": "redis" if redis_url else "memory"},
        "request_id": request_id,
    }

    telemetry = {
        "request_id": request_id,
        "stages": list(timeline),
        "redis": {"url": redis_url, "mode": "redis" if redis_url else "memory"},
    }

    return {
        "policy": dict(policy_raw),
        "telemetry": telemetry,
        "timeline": list(timeline),
        "asset_guard": asset_guard_report,
        "redis": {"url": redis_url, "mode": "redis" if redis_url else "memory"},
    }


def get_bootstrap_state() -> BootstrapState:
    if _BOOTSTRAP_STATE is None:
        raise RuntimeError("bootstrap_state 未初始化，请先调用 behavior_bootstrap")
    return _BOOTSTRAP_STATE


def _resolve_repo_root() -> Path:
    if _BOOTSTRAP_STATE is not None:
        return _BOOTSTRAP_STATE.repo_root
    # 当前文件位于 SharedUtility/Contracts，需要向上两级才是仓库根目录
    return Path(__file__).resolve().parents[2]


def _ensure_agents_bridge(repo_root: Optional[Path | str] = None) -> "AgentsBridge":
    global _AGENTS_BRIDGE
    if _AGENTS_BRIDGE is not None:
        return _AGENTS_BRIDGE
    repo_root_path = Path(repo_root).resolve() if repo_root is not None else _resolve_repo_root()
    kb_root = repo_root_path / "KnowledgeBase"
    if not kb_root.exists():
        raise FileNotFoundError(f"knowledge base root missing: {kb_root}")
    try:
        _AGENTS_BRIDGE = AgentsBridge(knowledge_base_root=kb_root)
    except Exception as exc:  # pragma: no cover - 初始化失败需立即显式上报
        logger.exception(
            "agents_bridge.bootstrap_failed",
            extra={"repo_root": str(repo_root_path), "knowledge_base_root": str(kb_root), "error": str(exc)},
        )
        raise
    return _AGENTS_BRIDGE


async def behavior_agents_bridge(
    agent_request: Mapping[str, Any],
    *,
    repo_root: Optional[Path | str] = None,
) -> Dict[str, Any]:
    bridge = _ensure_agents_bridge(repo_root)
    request_id = str(agent_request.get("request_id") or ContextBridge.request_id())
    payload = dict(agent_request)
    payload.setdefault("request_id", request_id)
    payload.setdefault("convo_id", payload.get("convo_id") or request_id)
    try:
        result = await bridge.dispatch(payload, request_id=request_id)
    except Exception as exc:  # pragma: no cover - 将异常暴露给调用方
        logger.exception("agents_bridge.dispatch_failed", extra={"request_id": request_id, "error": str(exc)})
        raise

    telemetry = dict(result.telemetry)
    telemetry.setdefault("request_id", request_id)
    debug_nodes_payload = []
    for node in getattr(result, "debug_nodes", []) or []:
        to_payload = getattr(node, "to_payload", None)
        if callable(to_payload):
            debug_nodes_payload.append(to_payload())
        else:
            debug_nodes_payload.append(
                {
                    "name": getattr(node, "name", ""),
                    "model": getattr(node, "model", ""),
                    "prompt": getattr(node, "prompt", ""),
                    "input_text": getattr(node, "input_text", ""),
                    "output_text": getattr(node, "output_text", ""),
                    "latency_ms": getattr(node, "latency_ms", 0.0),
                    "tokens": dict(getattr(node, "tokens", {}) or {}),
                    "metadata": dict(getattr(node, "metadata", {}) or {}),
                    "status": getattr(node, "status", ""),
                    "extras": dict(getattr(node, "extras", {}) or {}),
                }
            )
    return {
        "agent_bridge_result": {
            "mode": result.mode,
            "chunks": list(result.chunks),
            "tokens_usage": result.tokens_usage,
            "telemetry": telemetry,
            "debug_nodes": debug_nodes_payload,
        },
        "telemetry": telemetry,
        "debug_nodes": debug_nodes_payload,
    }


def _extract_telegram_message(update: Mapping[str, Any]) -> Tuple[Optional[Mapping[str, Any]], str]:
    for key in (
        "message",
    ):
        message_obj = update.get(key)
        if message_obj is None:
            continue
        if isinstance(message_obj, Mapping):
            return _prune_none_mapping(message_obj), key
        if hasattr(message_obj, "model_dump"):
            payload = getattr(message_obj, "model_dump")()
            if isinstance(payload, Mapping):
                return _prune_none_mapping(payload), key
    return None, "unknown"


def _compose_telegram_update(source: Mapping[str, Any], message_payload: Mapping[str, Any]) -> Dict[str, Any]:
    message_data = _prune_none_mapping(message_payload)
    reply_payload = message_data.get("reply_to_message")
    if reply_payload is None or not isinstance(reply_payload, Mapping):
        message_data.pop("reply_to_message", None)
    if "reply_to_message" not in message_data:
        message_data["reply_to_message"] = {}
    update_id = source.get("update_id")
    composed: Dict[str, Any] = {"message": message_data}
    if update_id is not None:
        composed["update_id"] = update_id
    return composed


def _prune_none_mapping(value: Mapping[str, Any]) -> Dict[str, Any]:
    pruned: Dict[str, Any] = {}
    for key, item in value.items():
        if item is None:
            continue
        if isinstance(item, Mapping):
            pruned[key] = _prune_none_mapping(item)
        elif isinstance(item, list):
            pruned_list = [_prune_none_mapping(elem) if isinstance(elem, Mapping) else elem for elem in item if elem is not None]
            pruned[key] = pruned_list
        else:
            pruned[key] = item
    return pruned


def behavior_core_envelope(update: Mapping[str, Any], *, channel: str = "telegram") -> Dict[str, Any]:
    """包装 core.adapters.build_core_schema，供路由层直接调用。"""
    if channel != "telegram":
        return build_core_schema(dict(update), channel=channel)

    message_payload, update_type = _extract_telegram_message(update)
    if message_payload is None:
        raise UnsupportedUpdateError(update_type)
    normalized_update = _compose_telegram_update(update, message_payload)
    return build_core_schema(normalized_update, channel=channel)


def behavior_telegram_inbound(
    update: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    message, update_type = _extract_telegram_message(update)
    request_id = ContextBridge.request_id()

    telemetry = {
        "request_id": request_id,
        "update_type": update_type,
        "chat_id": message.get("chat", {}).get("id") if message else None,
    }

    if message is None:
        return {
            "response_status": "ignored",
            "telemetry": telemetry,
            "error_hint": "unsupported_update_type",
            "logging": {
                "event": "telegram.update.ignored",
                "reason": "unsupported_update_type",
            },
        }

    text = (message.get("text") or message.get("caption") or "").strip()
    if not text:
        return {
            "response_status": "ignored",
            "telemetry": telemetry,
            "error_hint": "empty_message",
            "logging": {
                "event": "telegram.update.ignored",
                "reason": "empty_message",
                "chat_id": message.get("chat", {}).get("id"),
            },
        }

    try:
        normalized_update = _compose_telegram_update(update, message)
        core_bundle = build_core_schema(normalized_update, channel="telegram")
    except SchemaValidationError as exc:
        return {
            "response_status": "ignored",
            "telemetry": telemetry,
            "error_hint": str(exc),
            "logging": {
                "event": "telegram.update.schema_violation",
                "error": str(exc),
                "chat_id": message.get("chat", {}).get("id"),
            },
            "prompt_id": "core_schema_violation",
            "prompt_variables": {"error": str(exc)},
        }

    core_envelope = dict(core_bundle.get("core_envelope", {}))
    telemetry.update(core_bundle.get("telemetry", {}))
    metadata = core_envelope.get("metadata", {})
    ext_flags = core_envelope.get("ext_flags", {})
    payload = core_envelope.get("payload", {})

    agent_request = {
        "prompt": payload.get("user_message", ""),
        "convo_id": metadata.get("convo_id", ""),
        "language": metadata.get("language", "zh-CN"),
        "intent_hint": ext_flags.get("intent_hint", ""),
        "kb_scope": ext_flags.get("kb_scope", []),
        "system_tags": payload.get("system_tags", []),
        "request_id": request_id,
        "tokens_usage": payload.get("token_usage"),
    }

    logging_payload = {
        "event": "telegram.update.accepted",
        "chat_id": metadata.get("chat_id"),
        "convo_id": agent_request.get("convo_id"),
        "intent_hint": agent_request.get("intent_hint"),
    }

    return {
        "response_status": "handled",
        "core_envelope": core_envelope,
        "envelope": core_envelope,
        "agent_request": agent_request,
        "telemetry": telemetry,
        "logging": logging_payload,
        "policy_snapshot": {"tokens_budget": policy.get("tokens_budget", {})},
    }


def behavior_telegram_outbound(chunks: Sequence[str], policy: Mapping[str, Any]) -> Dict[str, Any]:
    sanitized = [str(chunk).strip() for chunk in chunks if str(chunk).strip()]
    if not sanitized:
        sanitized = [""]
    total_chars = sum(len(chunk) for chunk in sanitized)
    chunk_metrics = [
        {"chunk_index": index, "char_count": len(chunk), "planned_delay_ms": 1500.0}
        for index, chunk in enumerate(sanitized)
    ]
    return {
        "text": "\n\n".join(sanitized),
        "chunks": sanitized,
        "placeholder": "处理中…",
        "edits": [],
        "metrics": {"chunk_metrics": chunk_metrics, "total_chars": total_chars},
    }


def load_top_index(index_path: Path) -> list[TopLevelAgency]:
    data: Mapping[str, Any] = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    agencies: list[TopLevelAgency] = []
    for item in data.get("agencies", []):
        if not isinstance(item, Mapping):
            continue
        agency_id = str(item.get("agency_id") or item.get("id") or "").lower()
        agencies.append(
            {
                "key": agency_id,
                "name": str(item.get("name") or item.get("agency_name") or agency_id),
                "path": str(item.get("path") or ""),
                "keywords": [str(k).lower() for k in item.get("keywords", [])],
            }
        )
    return agencies






class AgentsBridge(UnifiedAgentsBridge):
    """Compatibility shim delegating to UnifiedCS AgentsBridge."""
    pass





class PromptRegistry(TypedDict):
    categories: list[str]
    mapping: Dict[str, list[str]]


PROMPT_REGISTRY: PromptRegistry = {
    "categories": [
        "system",
        "triage",
        "summarize",
        "compose",
        "clarify",
        "toolcall",
        "refusal",
        "welcome",
        "help",
        "rate_limit",
        "ops_alert",
        "dev_alert",
    ],
    "mapping": {
        "system": ["agent_triage_system"],
        "triage": ["agent_triage_system"],
        "summarize": ["telegram_history_summarize"],
        "compose": [
            "agency_compose_body",
            "agency_compose_header",
            "agent_consult_compose",
            "agent_plan_executor",
            "pricing_summary",
        ],
        "clarify": ["telegram_user_clarify"],
        "toolcall": ["telegram_toolcall_error"],
        "refusal": ["agent_refusal_policy", "core_schema_violation"],
        "welcome": ["telegram_welcome"],
        "help": ["telegram_prompt_missing"],
        "rate_limit": ["budget_alert"],
        "ops_alert": [
            "agency_pricing_alert",
            "aiogram_bootstrap_alert",
            "aiogram_bootstrap_status",
            "asset_cleanup_summary",
            "asset_guard_violation",
            "kb_index_missing_agency",
            "kb_index_ready",
            "kb_pipeline_failed",
            "kb_pipeline_success",
            "memory_checksum_mismatch",
            "memory_loader_alert",
            "memory_snapshot_ready",
            "plan_autodiscovery_status",
            "pricing_error",
            "telegram_streaming_error",
            "webhook_register_retry",
            "webhook_signature_fail",
        ],
        "dev_alert": [
            "core_envelope_attachment",
            "core_envelope_gap",
            "core_schema_alert",
            "core_schema_violation",
            "entry_layout_violation",
            "entry_missing_file",
            "kb_routing_conflict",
            "layout_missing_dir",
            "layout_owner_mismatch",
            "plan_alignment_gap",
            "plan_scope_ack",
            "selector_match_debug",
            "slot_missing",
            "slot_validation_error",
        ],
    },
}


def validate_prompt_registry(registry: PromptRegistry) -> bool:
    return all(category in registry["mapping"] for category in registry["categories"])


class BehaviorContract:
    """应用启动期统一注入 Prompts Registry 等契约配置。"""

    def __init__(self, registry: Optional[PromptRegistry] = None) -> None:
        self._registry = registry or PROMPT_REGISTRY

    def apply_contract(self, app: Any) -> None:
        if not validate_prompt_registry(self._registry):
            raise ValueError("prompt_registry_incomplete")
        if not hasattr(app, "state"):
            raise AttributeError("FastAPI app 缺少 state 属性")
        app.state.prompt_registry = self._registry  # type: ignore[attr-defined]
        logger.debug(
            "behavior_contract.applied",
            extra={"categories": len(self._registry["categories"])},
        )


class UnsupportedUpdateError(Exception):
    def __init__(self, update_type: str) -> None:
        self.update_type = update_type
        super().__init__(f"unsupported update type: {update_type}")


def behavior_asset_guard(repo_root: Path) -> Dict[str, Any]:
    """检查关键资产（目录/配置/索引），返回状态与提示事件。"""

    root = Path(repo_root).resolve()
    required_dirs = ["Config", "Contracts", "core", "TelegramAPI", "KnowledgeBase"]
    required_files = [
        ("SharedUtility/Config/runtime_policy.json", "runtime_policy"),
        ("SharedUtility/Config/prompts.zh-CN.yaml", "prompts_zh"),
        ("SharedUtility/Config/prompts.en-US.yaml", "prompts_en"),
        ("KnowledgeBase/KnowledgeBase_index.yaml", "kb_index"),
    ]

    missing_dirs = [name for name in required_dirs if not (root / name).exists()]
    missing_files = [path for path, _ in required_files if not (root / path).exists()]

    prompt_events: list[Dict[str, Any]] = []
    for missing in missing_dirs:
        prompt_events.append(
            {
                "prompt_id": "asset_guard_violation",
                "prompt_variables": {"component": missing, "kind": "directory"},
            }
        )
    for missing in missing_files:
        prompt_events.append(
            {
                "prompt_id": "asset_guard_violation",
                "prompt_variables": {"component": missing, "kind": "file"},
            }
        )

    status: Literal["ok", "violation"] = "ok" if not (missing_dirs or missing_files) else "violation"
    report = {
        "status": status,
        "checked_at": _utc_now().isoformat(),
        "missing_dirs": missing_dirs,
        "missing_files": missing_files,
        "prompt_events": prompt_events,
    }
    return report


class MemorySnapshot(TypedDict):
    org_metadata: Mapping[str, Any]
    routing_table: list[Any]
    agencies: Mapping[str, Any]
    created_at: str
    checksum: str
    missing_agencies: list[str]


class MemoryLoaderResult(TypedDict):
    snapshot: MemorySnapshot
    snapshot_dict: MemorySnapshot
    status: Literal["ready", "memory_only"]
    telemetry: Dict[str, Any]
    health: Dict[str, Any]
    missing_agencies: list[str]
    refresh: Callable[[str], Dict[str, Any]]
    loader: Dict[str, Callable[[str], Dict[str, Any]]]
    metadata: Dict[str, Any]


def behavior_memory_loader(
    *,
    base_path: Path,
    org_index_path: Path,
    agencies: Optional[Iterable[str]] = None,
    redis_url: Optional[str] = None,
    redis_prefix: str = "kobe:kb",
    redis_primary: Optional[bool] = None,
    redis_metadata: Optional[Mapping[str, Any]] = None,
) -> MemoryLoaderResult:
    repo_base = Path(base_path).resolve()
    org_index_file = Path(org_index_path).resolve()
    telemetry: dict[str, Any] = {"stages": []}

    if not org_index_file.exists():
        raise FileNotFoundError(f"org index missing: {org_index_file}")

    resolved_redis_url = redis_url or os.getenv("REDIS_URL") or ""

    def _load_snapshot() -> Tuple[MemorySnapshot, list[str]]:
        snapshot: MemorySnapshot = {
            "org_metadata": {},
            "routing_table": [],
            "agencies": {},
            "created_at": datetime.utcnow().isoformat(),
            "checksum": "",
            "missing_agencies": [],
        }
        missing_agencies: list[str] = []

        org_payload = yaml.safe_load(org_index_file.read_text(encoding="utf-8")) or {}
        snapshot["org_metadata"] = org_payload.get("org_metadata", {})
        snapshot["routing_table"] = org_payload.get("routing_table", [])

        requested_agencies = list(agencies or [])
        if not requested_agencies:
            requested_agencies = [
                str(entry.get("agency_id"))
                for entry in org_payload.get("agencies", [])
                if isinstance(entry, Mapping)
            ]

        agencies_payload: Dict[str, Any] = {}
        digest = sha256(org_index_file.read_bytes())
        for agency_id in filter(None, requested_agencies):
            agency_path = (repo_base / agency_id) / f"{agency_id}_index.yaml"
            if not agency_path.exists():
                missing_agencies.append(agency_id)
                continue
            payload = yaml.safe_load(agency_path.read_text(encoding="utf-8")) or {}
            agencies_payload[agency_id] = payload
            digest.update(agency_path.read_bytes())
        snapshot["agencies"] = agencies_payload
        snapshot["missing_agencies"] = list(missing_agencies)
        snapshot["checksum"] = f"sha256::{digest.hexdigest()}"
        return snapshot, missing_agencies

    def _sync_to_redis(snapshot: Mapping[str, Any], *, reason: str) -> Dict[str, Any]:
        stage: Dict[str, Any] = {"stage": "redis_sync", "reason": reason, "status": "skipped"}
        if not resolved_redis_url:
            return stage

        stage["redis_url"] = resolved_redis_url
        if redis is None:
            stage.update(status="redis_unavailable", error="redis_dependency_missing")
            return stage

        client = None
        try:
            client = redis.Redis.from_url(  # type: ignore[attr-defined]
                resolved_redis_url,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
            )
            client.ping()
            payload = json.dumps(snapshot, ensure_ascii=False)
            cached_at = datetime.utcnow().isoformat()
            snapshot_key = f"{redis_prefix}:snapshot"
            metadata_key = f"{redis_prefix}:metadata"
            client.set(snapshot_key, payload)
            client.hset(
                metadata_key,
                mapping={
                    "updated_at": cached_at,
                    "reason": reason,
                    "checksum": snapshot.get("checksum", ""),
                    "missing_agencies": json.dumps(snapshot.get("missing_agencies", []), ensure_ascii=False),
                },
            )
            stage.update(status="ready", snapshot_key=snapshot_key, metadata_key=metadata_key, cached_at=cached_at)
        except RedisError as exc:  # type: ignore[misc]
            stage.update(status="redis_unavailable", error=str(exc))
        except Exception as exc:  # pragma: no cover
            stage.update(status="redis_unavailable", error=str(exc))
        finally:
            if client is not None:
                try:
                    client.close()  # type: ignore[attr-defined]
                except Exception:
                    pass
        return stage

    snapshot_dict, missing = _load_snapshot()
    telemetry["stages"].append({"stage": "initial_load", "status": "attention" if missing else "ready", "missing_agencies": list(missing)})
    redis_stage = _sync_to_redis(snapshot_dict, reason="initial_load")
    telemetry["stages"].append(redis_stage)

    status: Literal["ready", "memory_only"] = "ready"
    if missing or redis_stage.get("status") not in {"ready", "skipped"}:
        status = "memory_only"

    health = {
        "missing_agencies": missing,
        "redis_status": redis_stage.get("status", "skipped"),
        "redis_error": redis_stage.get("error", ""),
    }

    redis_details: Dict[str, Any] = {
        "backend": "redis" if redis_stage.get("status") == "ready" else "memory",
        "primary": "redis" if redis_primary else "memory",
        **{key: value for key, value in redis_stage.items() if key not in {"stage", "reason", "status"}},
    }
    if redis_metadata:
        redis_details["metadata"] = dict(redis_metadata)
    metadata = {"redis": redis_details}

    def _refresh(reason: str = "manual") -> Dict[str, Any]:
        refreshed_snapshot, refreshed_missing = _load_snapshot()
        refresh_stage = _sync_to_redis(refreshed_snapshot, reason=reason)
        refresh_status: Literal["ready", "memory_only"] = "ready"
        if refreshed_missing or refresh_stage.get("status") not in {"ready", "skipped"}:
            refresh_status = "memory_only"
        refresh_health = {
            "missing_agencies": refreshed_missing,
            "redis_status": refresh_stage.get("status", "skipped"),
            "redis_error": refresh_stage.get("error", ""),
        }
        refresh_details: Dict[str, Any] = {
            "backend": "redis" if refresh_stage.get("status") == "ready" else "memory",
            "primary": "redis" if redis_primary else "memory",
            **{key: value for key, value in refresh_stage.items() if key not in {"stage", "reason", "status"}},
        }
        if redis_metadata:
            refresh_details["metadata"] = dict(redis_metadata)
        return {
            "snapshot": refreshed_snapshot,
            "snapshot_dict": refreshed_snapshot,
            "status": refresh_status,
            "telemetry": {"stages": [refresh_stage]},
            "health": refresh_health,
            "missing_agencies": refreshed_missing,
            "metadata": {"redis": refresh_details},
        }

    return {
        "snapshot": snapshot_dict,
        "snapshot_dict": snapshot_dict,
        "status": status,
        "telemetry": telemetry,
        "health": health,
        "missing_agencies": missing,
        "refresh": _refresh,
        "loader": {"refresh": _refresh},
        "metadata": metadata,
    }


def behavior_kb_pipeline(
    *,
    config: Mapping[str, Any],
    repo_root: Path | str,
) -> Dict[str, Any]:
    """CI 使用的知识库管道校验：检查必备工具及目录是否就绪。"""
    started = datetime.utcnow()
    issues: list[str] = []
    tools = config.get("required_tools", [])
    for tool in tools:
        if not shutil.which(str(tool)):
            issues.append(f"required tool missing: {tool}")

    kb_root = Path(repo_root).resolve() / "KnowledgeBase"
    if not kb_root.exists():
        issues.append(f"knowledge base root missing: {kb_root}")

    snapshot_template = (
        config.get("publish_targets", {}).get("snapshot_path")
        if isinstance(config.get("publish_targets"), Mapping)
        else None
    )

    status: Literal["success", "failed"] = "success" if not issues else "failed"
    duration_ms = (datetime.utcnow() - started).total_seconds() * 1000

    report = {
        "status": status,
        "issues": issues,
        "snapshot_path": snapshot_template or "",
        "approvals": config.get("approvals", {}),
        "duration_ms": duration_ms,
    }
    return {"kb_pipeline_report": report}


class ProjectLayout(TypedDict):
    app_py: str
    infra: list[str]
    core: list[str]
    telegrambot: list[str]


class TopEntryManifest(TypedDict):
    app_py: str
    directories: list[str]


def behavior_top_entry(layout: ProjectLayout, app: Optional[Any] = None) -> TopEntryManifest:
    manifest: TopEntryManifest = {"app_py": layout["app_py"], "directories": ["infra", "core", "TelegramAPI"]}
    if app is not None and hasattr(app, "state"):
        app.state.top_entry_manifest = manifest  # type: ignore[attr-defined]
    return manifest


def call_verify_layout(manifest: TopEntryManifest) -> bool:
    required = [manifest["app_py"], *manifest["directories"]]
    return all(Path(item).exists() for item in required)


def call_register_channel(app: Any, module: str) -> None:
    __import__(module)


def behavior_layout_guard(repo_root: Path | str, expected_tree: str, ownership: Mapping[str, Any]) -> Dict[str, Any]:
    """对比仓库目录结构，不一致时抛出 LayoutMismatch。"""
    root = Path(repo_root).resolve()
    actual_tree = call_scan_tree(root)
    diff = call_compare_tree(expected_tree, actual_tree)
    report = {
        "tree": actual_tree,
        "expected": expected_tree,
        "ownership": dict(ownership),
        "status": "clean" if not diff else "violation",
        "diff": diff,
    }
    if diff:
        raise LayoutMismatch(
            diff,
            prompt_id="layout_missing_dir",
            prompt_variables={"diff": diff},
            layout_report=report,
        )
    return report


class WebhookResponse(TypedDict, total=False):
    status: Literal["accepted", "rejected"]
    request_id: str
    telemetry: Dict[str, Any]


async def behavior_webhook_startup(
    bot: Any,
    webhook_url: str,
    secret: str,
    *,
    retries: int = 2,
    drop_pending_updates: bool = False,
    max_connections: Optional[int] = None,
) -> Dict[str, Any]:
    """注册 Telegram Webhook，失败时重试并记录遥测。"""
    if not webhook_url.startswith("https://"):
        raise RuntimeError("webhook_url_must_be_https")
    if not secret:
        raise RuntimeError("webhook_secret_missing")

    stages: list[Dict[str, Any]] = []
    prompt_events: list[Dict[str, Any]] = []
    attempt = 0

    while attempt < max(1, retries):
        attempt += 1
        stage = {"stage": "register_webhook", "attempt": attempt, "url": webhook_url}
        try:
            result = await call_register_webhook(
                bot,
                webhook_url,
                secret,
                drop_pending_updates=drop_pending_updates,
                max_connections=max_connections,
            )
        except Exception as exc:  # pragma: no cover - 链路异常直接重试/终止
            stage.update(status="error", error=str(exc))
            stages.append(stage)
            if attempt >= retries:
                prompt_events.append(
                    {
                        "prompt_id": "aiogram_bootstrap_alert",
                        "prompt_variables": {"step": "set_webhook", "retry": attempt, "error": str(exc)},
                    }
                )
                raise RuntimeError("webhook_register_failed") from exc
            await asyncio.sleep(1.0)
            continue

        status_flag = result.get("status", "ok")
        stage.update(status=status_flag)
        stages.append(stage)
        if status_flag == "ok":
            break
        if attempt >= retries:
            prompt_events.append(
                {
                    "prompt_id": "aiogram_bootstrap_alert",
                    "prompt_variables": {"step": "set_webhook", "retry": attempt, "error": "registration_failed"},
                }
            )
            raise RuntimeError("webhook_register_failed")
        await asyncio.sleep(1.0)

    telemetry = {
        "stages": stages,
        "attempts": attempt,
    }
    if prompt_events:
        telemetry["prompt_events"] = prompt_events
    return {"status": "ok", "telemetry": telemetry, "prompt_events": prompt_events}


def behavior_webhook_request(
    headers: Mapping[str, str],
    secret: str,
    dispatcher: Any,
) -> WebhookResponse:
    request_id = headers.get("X-Request-ID") or ContextBridge.request_id()
    signature_ok = call_verify_signature(headers, secret)
    metrics_store: Dict[str, Any] = {}
    workflow = getattr(dispatcher, "workflow_data", None)
    if isinstance(workflow, dict):
        metrics_store = workflow.setdefault("metrics", _default_metrics_state())
    if not signature_ok:
        if metrics_store is not None:
            metrics_store["webhook_signature_failures"] = metrics_store.get("webhook_signature_failures", 0) + 1
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid webhook signature")
    return {
        "status": "accepted",
        "request_id": request_id,
        "telemetry": {"signature_status": "accepted"},
    }


def call_verify_signature(headers: Mapping[str, str], secret: str) -> bool:
    expected = (secret or "").strip()
    provided = (headers.get("X-Telegram-Bot-Api-Secret-Token") or "").strip()
    return bool(expected) and provided == expected


async def call_register_webhook(
    bot: Any,
    url: str,
    secret: str,
    *,
    drop_pending_updates: bool = False,
    max_connections: Optional[int] = None,
) -> Dict[str, Any]:
    if bot is None or not hasattr(bot, "set_webhook"):
        raise RuntimeError("bot_object_invalid")
    kwargs: Dict[str, Any] = {"url": url, "secret_token": secret, "drop_pending_updates": drop_pending_updates}
    if max_connections is not None:
        kwargs["max_connections"] = max_connections
    result = await bot.set_webhook(**kwargs)
    status_flag = "ok" if bool(result) else "retry"
    return {
        "status": status_flag,
        "webhook_url": url,
        "attempts": 1,
        "drop_pending_updates": drop_pending_updates,
        "max_connections": max_connections,
    }


__all__ = [
    "BootstrapState",
    "AgentsBridge",
    "AgentRequest",
    "BehaviorContract",
    "behavior_asset_guard",
    "behavior_agents_bridge",
    "behavior_bootstrap",
    "behavior_core_envelope",
    "behavior_layout_guard",
    "behavior_kb_pipeline",
    "behavior_telegram_inbound",
    "behavior_telegram_outbound",
    "get_bootstrap_state",
    "SchemaValidationError",
    "PROMPT_REGISTRY",
    "ServiceIndexEntry",
    "ServiceMatch",
    "TopEntryManifest",
    "behavior_memory_loader",
    "behavior_top_entry",
    "behavior_webhook_request",
    "behavior_webhook_startup",
    "load_service_index",
    "load_top_index",
    "validate_prompt_registry",
    "UnsupportedUpdateError",
]

