"""Aiogram bootstrap orchestration."""

from __future__ import annotations

import logging
import os
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode

from project_utility.context import ContextBridge

from foundational_service.bootstrap.state import (
    BootstrapState,
    get_bootstrap_state,
    resolve_repo_root,
    set_bootstrap_context,
    set_bootstrap_state,
)
from foundational_service.diagnostics.metrics import default_metrics_state
from foundational_service.integrations.memory_loader import behavior_asset_guard
from foundational_service.policy.runtime import RuntimePolicyError, load_runtime_policy

__all__ = ["bootstrap_aiogram", "BootstrapState", "get_bootstrap_state", "resolve_repo_root"]


logger = logging.getLogger("foundational_service.bootstrap.aiogram")


def bootstrap_aiogram(
    *,
    repo_root: Path | str,
    redis_url: Optional[str] = None,
    runtime_policy_path: Optional[Path | str] = None,
    attach_handlers: bool = True,
) -> Dict[str, Any]:
    """Initialise aiogram dispatcher, runtime policy, and telemetry context."""

    root_path = Path(repo_root).resolve()
    request_id = ContextBridge.request_id()
    timeline: list[Dict[str, Any]] = []

    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("bootstrap_refused_missing_token")
    secret = (os.getenv("TELEGRAM_BOT_SECRETS") or "").strip()
    timeline.append({"stage": "env_load", "status": "ok", "has_secret": bool(secret)})

    default_policy_path = root_path / "config" / "runtime_policy.json"
    if runtime_policy_path is not None:
        policy_path = Path(runtime_policy_path)
    else:
        policy_path = default_policy_path
    policy_path_exists = policy_path.exists()

    try:
        policy_raw = load_runtime_policy(root_path, runtime_policy_path)
    except RuntimePolicyError as exc:
        timeline.append({"stage": "policy_load", "status": "error", "error": str(exc)})
        raise
    else:
        source_payload: Dict[str, Any]
        if runtime_policy_path is not None:
            source_payload = {"source": "override", "path": str(policy_path)}
        elif policy_path_exists:
            source_payload = {"source": "filesystem", "path": str(policy_path)}
        else:
            source_payload = {"source": "embedded_defaults"}

        timeline.append({"stage": "policy_load", "status": "ok", **source_payload})

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
    dispatcher = Dispatcher()
    setattr(dispatcher, "bot", bot)
    setattr(bot, "dispatcher", dispatcher)

    router: Optional[Any] = None
    if attach_handlers:
        try:
            message_module = import_module("interface_entry.telegram.handlers")
            router = getattr(message_module, "router", None)
            if router is None:
                raise AttributeError("interface_entry.telegram.handlers.router 缺失")
            timeline.append(
                {
                    "stage": "router_attach",
                    "status": "deferred",
                    "router": getattr(router, "name", "unknown"),
                    "reason": "runtime_attach",
                }
            )
        except Exception as exc:  # pragma: no cover - import failures should abort startup
            timeline.append({"stage": "router_attach", "status": "error", "error": str(exc)})
            raise
    else:
        timeline.append({"stage": "router_attach", "status": "skipped"})

    metrics_state = default_metrics_state()
    dispatcher.workflow_data.setdefault("metrics", metrics_state)
    dispatcher.workflow_data["runtime_policy"] = dict(policy_raw)
    if redis_url:
        dispatcher.workflow_data["redis_url"] = redis_url

    asset_guard_report = behavior_asset_guard(root_path)
    timeline.append({"stage": "asset_guard", "status": asset_guard_report.get("status", "ok")})

    state = BootstrapState(
        bot=bot,
        dispatcher=dispatcher,
        router=dispatcher,
        repo_root=root_path,
        redis_url=redis_url,
    )
    set_bootstrap_state(state)
    set_bootstrap_context(
        {
            "policy": dict(policy_raw),
            "metrics": metrics_state,
            "asset_guard": asset_guard_report,
            "timeline": list(timeline),
            "redis": {"url": redis_url, "mode": "redis" if redis_url else "memory"},
            "request_id": request_id,
        }
    )

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
        "router": getattr(router, "name", "unknown") if router is not None else None,
    }
