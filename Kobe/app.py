"""
Kobe Telegram service entrypoint aligned with 02.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import perf_counter
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from Contracts.behavior_contract import (
    BehaviorContract,
    behavior_memory_loader,
    behavior_top_entry,
    behavior_webhook_startup,
)
from Contracts import toolcalls
from core.context import ContextBridge

DOC_ID = "02"
DOC_COMMIT = "28a8d3a"

try:  # pragma: no cover - optional依赖
    from dotenv import load_dotenv  # type: ignore[import]
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]


if load_dotenv is not None:
    try:
        load_dotenv(dotenv_path=str(Path(__file__).resolve().parent / ".env"))
    except Exception:  # pragma: no cover
        pass


class _DocContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.doc_id = DOC_ID
        record.doc_commit = DOC_COMMIT
        return True


_root_logger = logging.getLogger()
if not any(isinstance(f, _DocContextFilter) for f in _root_logger.filters):
    _root_logger.addFilter(_DocContextFilter())


try:
    from rich.logging import RichHandler  # type: ignore[import]
    from rich.console import Console  # type: ignore[import]
    from rich.panel import Panel  # type: ignore[import]
    from rich.text import Text  # type: ignore[import]
except ImportError:  # pragma: no cover - rich optional
    RichHandler = None  # type: ignore[assignment]
    Console = None  # type: ignore[assignment]
    Panel = None  # type: ignore[assignment]
    Text = None  # type: ignore[assignment]


class _RichAlertHandler(logging.Handler):
    """Render warning/error 日志为 Rich 面板，便于运营聚焦异常。"""

    def __init__(self, console: Console) -> None:  # type: ignore[type-arg]
        super().__init__(level=logging.WARNING)
        self._console = console

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            metadata_lines: List[str] = []
            for key in ("request_id", "convo_id", "chat_id", "error", "status_code"):
                value = getattr(record, key, None)
                if value not in (None, "", []):
                    metadata_lines.append(f"{key}: {value}")
            body_parts = metadata_lines + [message]
            if Text is not None and Panel is not None:
                body = Text("\n".join(body_parts))
                border_style = "yellow" if record.levelno == logging.WARNING else "red"
                title = f"{record.levelname} · {record.name}"
                panel = Panel(body, title=title, border_style=border_style, expand=False)
                self._console.print(panel)
            else:  # pragma: no cover - 理论上不会出现，保持安全兜底
                border = "WARNING" if record.levelno == logging.WARNING else "ERROR"
                formatted = " | ".join(body_parts)
                self._console.print(f"[{border}]{record.levelname} {record.name}[/] {formatted}")
        except Exception:
            self.handleError(record)


def _configure_logging() -> None:
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    console_handlers: List[logging.Handler] = []
    if Console is not None:
        console = Console(force_terminal=True, width=120, highlight=False, markup=True)
        if Panel is not None and Text is not None:
            alert_handler = _RichAlertHandler(console)
            alert_handler.setLevel(logging.WARNING)
            alert_handler.setFormatter(logging.Formatter("%(message)s"))
            console_handlers.append(alert_handler)
        elif RichHandler is not None:
            rich_handler = RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_path=False,
                enable_link_path=False,
                console=console,
            )
            rich_handler.setLevel(logging.WARNING)
            rich_handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
            console_handlers.append(rich_handler)
        else:  # pragma: no cover - 理论兜底
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.WARNING)
            stream_handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
            console_handlers.append(stream_handler)
    else:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.WARNING)
        stream_handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        console_handlers.append(stream_handler)

    file_formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    root_file_handler = RotatingFileHandler(
        log_dir / "root.debug.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    root_file_handler.setLevel(logging.DEBUG)
    root_file_handler.setFormatter(file_formatter)

    combined_handlers: List[logging.Handler] = [root_file_handler, *console_handlers]

    basic_config_kwargs: Dict[str, Any] = {
        "level": logging.DEBUG,
        "force": True,
        "handlers": combined_handlers,
    }
    logging.basicConfig(**basic_config_kwargs)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        if isinstance(handler, RotatingFileHandler):
            handler.setLevel(logging.DEBUG)
    if not any(isinstance(f, _DocContextFilter) for f in root.filters):
        root.addFilter(_DocContextFilter())

    component_logs = {
        "kobe.app": "kobe.app.debug.log",
        "TelegramBot.routes": "telegram.routes.debug.log",
        "TelegramBot.handlers": "telegram.handlers.debug.log",
        "Contracts.behavior_contract": "contracts.behavior.debug.log",
        "uvicorn.error": "uvicorn.error.debug.log",
        "uvicorn.access": "uvicorn.access.debug.log",
        "aiogram": "aiogram.debug.log",
    }

    for logger_name, file_name in component_logs.items():
        logger_obj = logging.getLogger(logger_name)
        target_path = log_dir / file_name
        existing_handler = None
        for handler in logger_obj.handlers:
            if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == target_path:
                existing_handler = handler
                break
        if existing_handler is None:
            file_handler = RotatingFileHandler(
                target_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            logger_obj.addHandler(file_handler)
        else:
            existing_handler.setLevel(logging.DEBUG)
            existing_handler.setFormatter(file_formatter)
        logger_obj.setLevel(logging.DEBUG)
        logger_obj.propagate = True


_configure_logging()


class FastAPIRequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        ContextBridge.set_request_id(request.headers.get("x-request-id"))
        response = await call_next(request)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            latency_ms = round((perf_counter() - start) * 1000, 3)
            request_id = ContextBridge.request_id()
            status_code = getattr(response, "status_code", 500)
            signature_status = getattr(request.state, "signature_status", "unknown")
            log.info(
                "webhook.request",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "latency_ms": latency_ms,
                    "status_code": status_code,
                    "signature_status": signature_status,
                },
            )


class SignatureVerifyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, *, webhook_path: str, header_name: str = "X-Telegram-Bot-Api-Secret-Token") -> None:
        super().__init__(app)
        self._webhook_path = webhook_path
        self._header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path != self._webhook_path:
            return await call_next(request)

        secret = getattr(request.app.state, "webhook_secret", "")
        if not secret:
            log.error("webhook.secret_missing")
            raise HTTPException(status_code=500, detail="webhook_secret_unset")

        request_id = ContextBridge.request_id()
        metrics_state = getattr(request.app.state, "telegram_metrics", None)
        request.state.signature_status = "pending"
        try:
            toolcalls.call_verify_signature(request.headers, secret)
        except HTTPException as exc:
            request.state.signature_status = "rejected"
            if metrics_state is not None:
                metrics_state["webhook_signature_failures"] = metrics_state.get("webhook_signature_failures", 0) + 1
            prompt_text = None
            try:
                from core.prompt_registry import PROMPT_REGISTRY

                prompt_text = PROMPT_REGISTRY.render("webhook_signature_fail", request_id=request_id)
            except Exception:  # pragma: no cover - optional registry
                prompt_text = None
            log.warning(
                "webhook.signature_mismatch",
                extra={
                    "request_id": request_id,
                    "signature_status": "rejected",
                    "prompt_id": "webhook_signature_fail",
                    "prompt_text": prompt_text or "",
                },
            )
            raise exc

        request.state.signature_status = "accepted"
        return await call_next(request)


log = logging.getLogger("kobe.app")

REPO_ROOT = Path(__file__).resolve().parent
TOP_ENTRY_MANIFEST_PATH = REPO_ROOT / "WorkPlan" / "top_entry_manifest.json"
WEBHOOK_PATH = "/telegram/webhook"
try:
    TOP_ENTRY_MANIFEST = json.loads(TOP_ENTRY_MANIFEST_PATH.read_text(encoding="utf-8"))
except FileNotFoundError:
    TOP_ENTRY_MANIFEST = {
        "doc_id": DOC_ID,
        "version": "v1.1.0",
        "app_py": "{REPO_ROOT}/app.py",
        "infra": ["{REPO_ROOT}/infra/fastapi_app.py"],
        "core": [
            "{REPO_ROOT}/core/schema.py",
            "{REPO_ROOT}/core/adapters.py",
            "{REPO_ROOT}/core/context.py"
        ],
        "telegrambot": [
            "{REPO_ROOT}/TelegramBot/runtime.py",
            "{REPO_ROOT}/TelegramBot/routes.py",
            "{REPO_ROOT}/TelegramBot/handlers/message.py",
            "{REPO_ROOT}/TelegramBot/adapters/telegram.py"
        ],
    }


def _env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        if name == "TELEGRAM_BOT_TOKEN":
            raise RuntimeError("bootstrap_refused_missing_token")
        raise RuntimeError(f"missing required environment variable: {name}")
    return value or ""


def create_app() -> FastAPI:
    app = FastAPI(title="Kobe Telegram Bridge", version="1.0.0")
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

    from TelegramBot.runtime import bootstrap_aiogram_service, get_bootstrap_metadata
    from TelegramBot.routes import register_routes

    bootstrap_state = bootstrap_aiogram_service(
        api_token=token,
        webhook_url=WEBHOOK_PATH,
        redis_url=redis_url,
        fastapi_app=None,
    )
    metadata = get_bootstrap_metadata()
    policy: Dict[str, Any] = metadata["policy"]
    metrics_state: Dict[str, Any] = metadata["metrics"]
    telemetry = metadata["telemetry"]
    redis_runtime: Dict[str, Any] = metadata.get("redis", {}) or {}
    redis_active = bool(redis_runtime.get("available"))

    contract = BehaviorContract()
    top_entry_validation = behavior_top_entry(TOP_ENTRY_MANIFEST, app=app)
    app.state.top_entry_manifest = top_entry_validation

    def configure_policy(policy_obj: dict[str, object]) -> None:
        app.state.runtime_policy = policy_obj

    setattr(app, "configure_policy", configure_policy)
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

    memory_loader_result = behavior_memory_loader(
        base_path=REPO_ROOT / "KnowledgeBase",
        org_index_path=REPO_ROOT / "KnowledgeBase_index.yaml",
        redis_url=redis_url,
        redis_primary=redis_active,
        redis_metadata=redis_runtime,
    )
    app.state.memory_loader = memory_loader_result.get("loader")
    app.state.memory_snapshot_obj = memory_loader_result["snapshot"]
    app.state.memory_snapshot = memory_loader_result["snapshot_dict"]
    app.state.memory_snapshot_status = memory_loader_result["status"]
    app.state.memory_snapshot_telemetry = memory_loader_result["telemetry"]
    app.state.memory_snapshot_health = memory_loader_result["health"]
    app.state.memory_snapshot_missing_agencies = memory_loader_result["missing_agencies"]
    app.state.memory_loader_metadata = memory_loader_result.get("metadata", {})
    app.state.memory_backend = memory_loader_result.get("metadata", {}).get("redis", {})

    def refresh_memory_snapshot(refresh_reason: str = "manual") -> Dict[str, Any]:
        refresh_result = memory_loader_result["refresh"](refresh_reason)
        app.state.memory_snapshot_obj = refresh_result["snapshot"]
        app.state.memory_snapshot = refresh_result["snapshot_dict"]
        app.state.memory_snapshot_status = refresh_result["status"]
        app.state.memory_snapshot_telemetry = refresh_result["telemetry"]
        app.state.memory_snapshot_health = refresh_result["health"]
        app.state.memory_snapshot_missing_agencies = refresh_result["missing_agencies"]
        app.state.memory_loader_metadata = refresh_result.get("metadata", {})
        app.state.memory_backend = refresh_result.get("metadata", {}).get("redis", {})
        return refresh_result

    app.state.memory_snapshot_refresh = refresh_memory_snapshot

    register_routes(app, bootstrap_state.dispatcher, WEBHOOK_PATH, policy, webhook_secret)

    @app.on_event("startup")
    async def on_startup() -> None:
        startup_meta = await behavior_webhook_startup(
            bootstrap_state.bot,
            f"{public_url.rstrip('/')}{WEBHOOK_PATH}",
            webhook_secret,
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
        log.info(
            "startup.complete",
            extra={
                "router": bootstrap_state.router.name,
                "stages": startup_meta.get("telemetry", {}).get("stages", []),
                "bootstrapped_request_id": telemetry.get("request_id"),
            },
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        state = getattr(app.state, "telegram", None)
        if state:
            await state.bot.session.close()
        log.info("shutdown.complete")

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


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

