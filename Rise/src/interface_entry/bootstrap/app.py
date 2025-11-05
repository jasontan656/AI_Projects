from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import shutil
from contextlib import asynccontextmanager, suppress
from time import perf_counter
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from aiohttp.client_exceptions import ClientConnectorError, ClientOSError
from business_logic import KnowledgeSnapshotOrchestrator
from business_service import KnowledgeSnapshotService
from foundational_service.bootstrap.webhook import behavior_webhook_startup
from foundational_service.contracts.registry import BehaviorContract, behavior_top_entry
from project_utility.context import ContextBridge
from project_utility.config.paths import get_log_root, get_repo_root
from project_utility.logging import configure_logging
from aiogram.exceptions import TelegramRetryAfter

from interface_entry.config.manifest_loader import load_doc_context, load_top_entry_manifest
from interface_entry.http.dependencies import application_lifespan
from interface_entry.http.errors import http_exception_handler, unhandled_exception_handler
from interface_entry.http.middleware import FastAPIRequestIDMiddleware, LoggingMiddleware
from interface_entry.http.pipeline_nodes import get_router as get_pipeline_node_router
from interface_entry.http.prompts import get_router as get_prompt_router
from interface_entry.middleware.signature import SignatureVerifyMiddleware
from interface_entry.telegram.runtime import bootstrap_aiogram_service, get_bootstrap_metadata
from interface_entry.telegram.routes import register_routes

from dotenv import load_dotenv  # type: ignore[import]


REPO_ROOT = get_repo_root()

load_dotenv(dotenv_path=str(REPO_ROOT / ".env"))


log = logging.getLogger("interface_entry.app")

REPO_ROOT = get_repo_root()
load_dotenv(dotenv_path=str(REPO_ROOT / ".env"))

WEBHOOK_PATH = "/telegram/webhook"
TOP_ENTRY_MANIFEST = load_top_entry_manifest()
DOC_CONTEXT = load_doc_context()
DOC_ID = DOC_CONTEXT["doc_id"]
DOC_COMMIT = DOC_CONTEXT["doc_commit"]


class TelegramWebhookUnavailableError(RuntimeError):
    """Raised when Telegram webhook cannot be reached during startup."""


def _sanitize_endpoint(raw: str) -> str:
    if "@" in raw:
        return raw.split("@", 1)[1]
    return raw


def _release_logging_handlers() -> None:
    logging.shutdown()
    logger_names = [None, *list(logging.root.manager.loggerDict.keys())]
    for name in logger_names:
        logger = logging.getLogger(name) if name else logging.getLogger()
        for handler in list(logger.handlers):
            with suppress(Exception):
                handler.flush()
            with suppress(Exception):
                handler.close()
            logger.removeHandler(handler)


def _perform_clean_startup() -> None:
    _release_logging_handlers()
    configure_logging()
    log.info("startup.clean.begin")
    issues: List[str] = []

    directories = {
        "logs": get_log_root(),
        "runtime_state": REPO_ROOT / "openai_agents" / "agent_contract" / "runtime_state",
    }
    for label, target in directories.items():
        try:
            log.info(
                "startup.clean.segment.begin",
                extra={"segment": label, "path": str(target)},
            )
            if target.exists():
                log.info(
                    "startup.clean.segment.removing",
                    extra={"segment": label, "path": str(target)},
                )
                shutil.rmtree(target)
                log.info(
                    "startup.clean.segment.removed",
                    extra={"segment": label, "path": str(target)},
                )
            target.mkdir(parents=True, exist_ok=True)
            log.info(
                "startup.clean.segment.ready",
                extra={"segment": label, "path": str(target)},
            )
        except Exception as exc:  # pragma: no cover - surface filesystem failures immediately
            issues.append(f"{label}: {exc}")
            log.error(
                "startup.clean.segment_failed",
                extra={"segment": label, "error": repr(exc)},
            )

    def _execute(label: str, func: Callable[[], None]) -> None:
        try:
            log.info("startup.clean.segment.begin", extra={"segment": label})
            func()
            log.info("startup.clean.segment.ready", extra={"segment": label})
        except Exception as exc:  # pragma: no cover - propagate external service errors
            issues.append(f"{label}: {exc}")
            log.error(
                "startup.clean.segment_failed",
                extra={"segment": label, "error": repr(exc)},
            )

    _execute("redis", _purge_redis_store)
    _execute("mongodb", _purge_mongo_store)

    final_status = "ok" if not issues else "failed"
    log.info("startup.clean.status", extra={"status": final_status, "issues": issues})

    if issues:
        raise RuntimeError("startup_clean_failed: " + "; ".join(issues))

    log.info("startup.clean.complete")


def _purge_redis_store() -> None:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL not configured")

    from redis import Redis  # type: ignore[import]

    redis_client = Redis.from_url(redis_url)
    redis_client.flushall()
    log.info("startup.clean.redis", extra={"endpoint": _sanitize_endpoint(redis_url)})


def _purge_mongo_store() -> None:
    mongo_uri = os.getenv("MONGODB_URI")
    mongo_db = os.getenv("MONGODB_DATABASE")
    if not mongo_uri or not mongo_db:
        missing = "MONGODB_URI" if not mongo_uri else "MONGODB_DATABASE"
        raise RuntimeError(f"{missing} not configured")

    from pymongo import MongoClient  # type: ignore[import]

    client = MongoClient(mongo_uri)
    try:
        db = client[mongo_db]
        collections: List[str] = db.list_collection_names()
        for collection_name in collections:
            db[collection_name].delete_many({})
        log.info(
            "startup.clean.mongodb",
            extra={
                "endpoint": _sanitize_endpoint(mongo_uri),
                "database": mongo_db,
                "collections": collections,
            },
        )
    finally:
        with suppress(Exception):
            client.close()


def _env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        if name == "TELEGRAM_BOT_TOKEN":
            raise RuntimeError("bootstrap_refused_missing_token")
        raise RuntimeError(f"missing required environment variable: {name}")
    return value or ""


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Rise Telegram Bridge", version="1.0.0")
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_middleware(FastAPIRequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SignatureVerifyMiddleware, webhook_path=WEBHOOK_PATH)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    token = _env("TELEGRAM_BOT_TOKEN")
    webhook_secret = _env("TELEGRAM_BOT_SECRETS")
    public_url = _env("WEB_HOOK")
    redis_url = os.getenv("REDIS_URL")
    if not public_url.lower().startswith("https://"):
        log.error("startup.insecure_webhook", extra={"public_url": public_url})
        raise RuntimeError("bootstrap_refused_insecure_webhook")

    def _log_startup_step(step: str, description: str, **metadata: Any) -> None:
        log.info("startup.step", extra={"step": step, "description": description, **metadata})

    _log_startup_step(
        "bootstrap_aiogram.start",
        "Initialising aiogram bootstrap sequence",
    )

    bootstrap_state = bootstrap_aiogram_service(
        api_token=token,
        webhook_url=WEBHOOK_PATH,
        redis_url=redis_url,
        fastapi_app=None,
    )
    _log_startup_step(
        "bootstrap_aiogram.complete",
        "Aiogram bootstrap finished",
        router=bootstrap_state.router.name,
    )
    metadata = get_bootstrap_metadata()
    policy: Dict[str, Any] = metadata["policy"]
    metrics_state: Dict[str, Any] = metadata["metrics"]
    telemetry = metadata["telemetry"]
    bootstrap_redis_runtime: Dict[str, Any] = metadata.get("redis", {}) or {}
    redis_runtime: Dict[str, Any] = dict(bootstrap_redis_runtime)
    redis_active = bool(redis_runtime.get("available"))

    contract = BehaviorContract()
    top_entry_validation = behavior_top_entry(TOP_ENTRY_MANIFEST, app=app)
    app.state.top_entry_manifest = top_entry_validation

    def configure_policy(policy_obj: dict[str, object]) -> None:
        app.state.runtime_policy = policy_obj

    setattr(app, "configure_policy", configure_policy)
    _log_startup_step("behavior_contract.apply", "Applying behavior contract")
    contract.apply_contract(app)
    app.state.doc_context = {"doc_id": DOC_ID, "doc_commit": DOC_COMMIT}
    app.state.runtime_policy = policy
    app.state.bootstrap_metrics = metrics_state
    app.state.webhook_secret = webhook_secret
    app.state.public_url = public_url
    app.state.telegram = bootstrap_state
    app.state.telegram_metrics = metrics_state
    app.state.asset_guard = metadata.get("asset_guard")
    app.state.redis_runtime = redis_runtime

    redis_primary_hint = bool(redis_url)
    _log_startup_step("memory_loader.start", "Loading KnowledgeBase snapshot")
    knowledge_service = KnowledgeSnapshotService(
        base_path=REPO_ROOT / "KnowledgeBase",
        org_index_path=REPO_ROOT / "KnowledgeBase" / "KnowledgeBase_index.yaml",
        redis_url=redis_url,
        redis_prefix="rise:kb",
        redis_primary=redis_primary_hint,
        redis_metadata=redis_runtime,
    )
    knowledge_orchestrator = KnowledgeSnapshotOrchestrator(knowledge_service)
    snapshot_state = knowledge_orchestrator.load()
    app.state.knowledge_snapshot_orchestrator = knowledge_orchestrator

    def _legacy_refresh(reason: str = "manual") -> Dict[str, Any]:
        refreshed_state = knowledge_orchestrator.refresh(reason)
        return refreshed_state.to_legacy_dict()

    app.state.memory_loader = {"refresh": _legacy_refresh}
    app.state.memory_snapshot_obj = snapshot_state.snapshot
    app.state.memory_snapshot = snapshot_state.snapshot_dict
    app.state.memory_snapshot_status = snapshot_state.status
    app.state.memory_snapshot_telemetry = snapshot_state.telemetry
    app.state.memory_snapshot_health = snapshot_state.health
    app.state.memory_snapshot_missing_agencies = list(snapshot_state.missing_agencies)
    loader_metadata = dict(snapshot_state.metadata)
    app.state.memory_loader_metadata = loader_metadata
    latest_redis_runtime = loader_metadata.get("redis", {})
    if isinstance(latest_redis_runtime, dict):
        redis_runtime = latest_redis_runtime
        redis_active = bool(redis_runtime.get("available"))
        app.state.redis_runtime = redis_runtime
    else:
        redis_active = bool(redis_runtime.get("available"))
    app.state.memory_backend = redis_runtime
    _log_startup_step(
        "memory_loader.complete",
        "KnowledgeBase snapshot ready",
        status=snapshot_state.status,
        redis_primary=redis_active,
    )

    def refresh_memory_snapshot(refresh_reason: str = "manual") -> Dict[str, Any]:
        refreshed_state = knowledge_orchestrator.refresh(refresh_reason)
        app.state.memory_snapshot_obj = refreshed_state.snapshot
        app.state.memory_snapshot = refreshed_state.snapshot_dict
        app.state.memory_snapshot_status = refreshed_state.status
        app.state.memory_snapshot_telemetry = refreshed_state.telemetry
        app.state.memory_snapshot_health = refreshed_state.health
        app.state.memory_snapshot_missing_agencies = list(refreshed_state.missing_agencies)
        app.state.memory_loader_metadata = dict(refreshed_state.metadata)
        app.state.memory_backend = refreshed_state.metadata.get("redis", {})
        return refreshed_state.to_legacy_dict()

    app.state.memory_snapshot_refresh = refresh_memory_snapshot

    _log_startup_step("register_routes", "Registering Telegram routes")
    register_routes(app, bootstrap_state.dispatcher, WEBHOOK_PATH, policy, webhook_secret)
    app.include_router(get_pipeline_node_router())
    app.include_router(get_prompt_router())

    _log_startup_step(
        "bootstrap.complete",
        "bootstrap_aiogram_service completed",
        redis_enabled=redis_active,
        router=bootstrap_state.router.name,
    )

    async def _prompt_yes_no(question: str, *, timeout: float = 30.0, default: bool = True) -> bool:
        loop = asyncio.get_running_loop()
        default_hint = "Y/n" if default else "y/N"
        prompt_text = f"{question} [{default_hint}] "

        def _ask() -> str:
            try:
                return input(prompt_text)
            except EOFError:
                return ""

        try:
            raw = await asyncio.wait_for(loop.run_in_executor(None, _ask), timeout)
        except asyncio.TimeoutError:
            _log_startup_step(
                "telegram_backlog.prompt_timeout",
                "Backlog prompt timed out, using default",
                default_selected=default,
                timeout_seconds=timeout,
            )
            return default

        normalized = (raw or "").strip().lower()
        if not normalized:
            _log_startup_step(
                "telegram_backlog.prompt_default",
                "Backlog prompt empty input, using default",
                default_selected=default,
            )
            return default
        if normalized in {"y", "yes", "是", "1", "true", "start"}:
            return True
        if normalized in {"n", "no", "否", "0", "false", "drop"}:
            return False
        _log_startup_step(
            "telegram_backlog.prompt_unknown",
            "Backlog prompt received unrecognized input, using default",
            input_value=normalized,
            default_selected=default,
        )
        return default

    async def _verify_telegram_connectivity() -> None:
        target_host = os.getenv("TELEGRAM_API_HOST", "api.telegram.org")
        target_port = int(os.getenv("TELEGRAM_API_PORT", "443"))
        timeout_seconds = max(1.0, float(os.getenv("TELEGRAM_PRECHECK_TIMEOUT", "3")))
        _log_startup_step(
            "telegram_precheck.start",
            "Probing outbound connectivity to Telegram API",
            host=target_host,
            port=target_port,
            timeout_seconds=timeout_seconds,
        )
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(target_host, target_port),
                timeout=timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover - network failures depend on env
            log.error(
                "startup.telegram_precheck.failed",
                extra={
                    "host": target_host,
                    "port": target_port,
                    "timeout_seconds": timeout_seconds,
                    "public_url": public_url,
                    "hint": "确保部署环境允许访问 api.telegram.org:443，必要时配置代理或开通出站白名单。",
                    "error": repr(exc),
                },
            )
            raise RuntimeError("telegram_network_precheck_failed") from exc
        else:
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
            _log_startup_step(
                "telegram_precheck.ok",
                "Telegram API connectivity verified",
                host=target_host,
                port=target_port,
                timeout_seconds=timeout_seconds,
            )

    async def _handle_pending_updates() -> Dict[str, Any]:
        max_attempts = max(1, int(os.getenv("TELEGRAM_WEBHOOK_MAX_ATTEMPTS", "5")))
        base_delay = max(0.1, float(os.getenv("TELEGRAM_WEBHOOK_RETRY_DELAY", "0.5")))
        request_timeout = max(1.0, float(os.getenv("TELEGRAM_WEBHOOK_TIMEOUT", "10")))

        delay = base_delay
        attempt_used = 0
        webhook_info = None
        last_exc: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                webhook_info = await bootstrap_state.bot.get_webhook_info(request_timeout=request_timeout)
                attempt_used = attempt
                break
            except TelegramRetryAfter as exc:
                wait_for = max(float(exc.retry_after), delay)
                log.warning(
                    "startup.telegram_backlog.retry_after",
                    extra={"attempt": attempt, "retry_in": wait_for, "error": str(exc)},
                )
                await asyncio.sleep(wait_for)
                last_exc = exc
            except (ClientConnectorError, ClientOSError, asyncio.TimeoutError) as exc:
                log.warning(
                    "startup.telegram_backlog.retry",
                    extra={"attempt": attempt, "backoff": delay, "error": repr(exc)},
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10.0)
                last_exc = exc
            except Exception as exc:
                log.error(
                    "startup.telegram_backlog.unexpected_error",
                    extra={"attempt": attempt, "error": repr(exc)},
                )
                last_exc = exc
                break

        if webhook_info is None:
            log.error(
                "startup.telegram_backlog.unreachable",
                extra={
                    "attempts": max_attempts,
                    "error": repr(last_exc) if last_exc else "unknown",
                    "public_url": public_url,
                    "hint": "Confirm outbound network access to api.telegram.org or start ngrok with WEB_HOOK.",
                },
            )
            message = (
                "Unable to reach Telegram webhook after "
                f"{max_attempts} attempts. Ensure the server can access api.telegram.org "
                "and that WEB_HOOK/ngrok URL is reachable."
            )
            raise TelegramWebhookUnavailableError(message) from last_exc
        if last_exc is not None and attempt_used > 1:
            log.info(
                "startup.telegram_backlog.recovered",
                extra={"attempts": attempt_used},
            )
        _log_startup_step(
            "telegram_backlog.check_begin",
            "Checking Telegram backlog",
            webhook_url=getattr(webhook_info, "url", ""),
        )
        pending = getattr(webhook_info, "pending_update_count", 0)
        if not pending:
            _log_startup_step("telegram_backlog.empty", "No Telegram backlog detected")
            return {"pending_updates": 0, "drop_pending": False}

        log.warning(
            "startup.telegram_backlog.detected",
            extra={
                "pending_updates": pending,
                "last_error_date": getattr(webhook_info, "last_error_date", None),
                "last_error_message": getattr(webhook_info, "last_error_message", ""),
            },
        )
        decision = await _prompt_yes_no(
            f"检测到 Telegram 积压消息 {pending} 条，是否继续处理？",
            timeout=30.0,
            default=True,
        )
        decision_label = "keep" if decision else "drop"
        drop_pending = False
        if not decision:
            try:
                await bootstrap_state.bot.delete_webhook(drop_pending_updates=True)
                _log_startup_step(
                    "telegram_backlog.drop",
                    "Dropped pending Telegram updates",
                    pending_updates=pending,
                )
                drop_pending = True
            except Exception as exc:  # pragma: no cover - surface caller-facing failures
                log.error(
                    "startup.telegram_backlog.drop_failed",
                    extra={"error": str(exc), "pending_updates": pending},
                )
                raise
        else:
            _log_startup_step(
                "telegram_backlog.keep",
                "Keeping pending Telegram updates",
                pending_updates=pending,
            )
        _log_startup_step(
            "telegram_backlog.check_end",
            "Backlog inspection finished",
            decision=decision_label,
            pending_updates=pending,
        )
        return {"pending_updates": pending, "drop_pending": drop_pending}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async with application_lifespan():
            await _verify_telegram_connectivity()
            _log_startup_step("telegram_backlog.check", "Begin backlog inspection")
            backlog_meta = await _handle_pending_updates()
            _log_startup_step(
                "behavior_webhook_startup.invoke",
                "Registering webhook with Telegram",
            )
            startup_meta = await behavior_webhook_startup(
                bootstrap_state.bot,
                f"{public_url.rstrip('/')}{WEBHOOK_PATH}",
                webhook_secret,
                drop_pending_updates=bool(backlog_meta.get("drop_pending")),
            )
            for prompt in startup_meta.get("prompt_events", []):
                log.warning(
                    "webhook.prompt.retry",
                    extra={
                        "prompt_id": prompt.get("prompt_id"),
                        "prompt_text": prompt.get("prompt_text", ""),
                        "request_id": ContextBridge.request_id(),
                        "retry": prompt.get("prompt_variables", {}).get("retry"),
                    },
                )
            _log_startup_step(
                "startup.complete",
                "Application ready",
                router=bootstrap_state.router.name,
                stages=startup_meta.get("telemetry", {}).get("stages", []),
                bootstrapped_request_id=telemetry.get("request_id"),
            )

            try:
                yield
            finally:
                state = getattr(app.state, "telegram", None)
                if state:
                    await state.bot.session.close()
                log.info("shutdown.complete")

    app.router.lifespan_context = lifespan

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        state = getattr(app.state, "telegram", None)
        return {
            "status": "ok",
            "router": getattr(state.router, "name", "pending") if state else "pending",
        }

    @app.get("/internal/memory_health")
    async def memory_health() -> Dict[str, Any]:
        snapshot = getattr(app.state, "memory_snapshot", {})
        status = getattr(app.state, "memory_snapshot_status", "unknown")
        telemetry_state = getattr(app.state, "memory_snapshot_telemetry", {})
        health = getattr(app.state, "memory_snapshot_health", {})
        missing = getattr(app.state, "memory_snapshot_missing_agencies", [])
        metadata = getattr(app.state, "memory_loader_metadata", {})
        checksum_status = (
            telemetry_state.get("checksum_status")
            or health.get("checksum_status")
            or snapshot.get("stats", {}).get("checksum_status")
        )
        return {
            "status": status,
            "snapshot_version": snapshot.get("snapshot_version"),
            "snapshot_checksum": snapshot.get("checksum"),
            "checksum_status": checksum_status,
            "stats": snapshot.get("stats", {}),
            "health": health,
            "missing_agencies": missing,
            "telemetry": telemetry_state,
            "metadata": metadata,
        }

    return app


CLI_DESCRIPTION = "Rise Telegram service"

app: FastAPI | None = None


def configure_arg_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--clean",
        action="store_true",
        help="启动前清空日志、runtime_state 目录，并重置 Redis 与 MongoDB 数据库",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="绑定主机地址 (默认 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="监听端口 (默认 8000)",
    )


def handle_cli(args: argparse.Namespace) -> None:
    global app  # type: ignore[assignment]
    try:
        if getattr(args, "clean", False):
            _perform_clean_startup()
            app = create_app()
        else:
            app = create_app()
    except TelegramWebhookUnavailableError as exc:
        log.critical("Startup aborted: %s", exc)
        raise

    import uvicorn

    uvicorn.run(
        app,
        host=getattr(args, "host", "0.0.0.0"),
        port=getattr(args, "port", int(os.getenv("PORT", "8000"))),
        log_config=None,
    )


try:
    app = create_app()
except TelegramWebhookUnavailableError as exc:
    log.critical("Startup aborted: %s", exc)
    raise
