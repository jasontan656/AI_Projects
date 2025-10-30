"""
Runtime bootstrap for the Telegram channel.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from Contracts.behavior_contract import BootstrapState, behavior_bootstrap, get_bootstrap_state
from TelegramBot.handlers import message as message_handlers
from TelegramBot.routes import register_routes
from core.context import ContextBridge

log = logging.getLogger(__name__)


_BOOTSTRAP_STATE: BootstrapState | None = None
_BOOTSTRAP_METADATA: dict[str, Any] | None = None
_BOUND_APPS: set[int] = set()


def bootstrap_aiogram_service(
    api_token: str,
    webhook_url: str,
    redis_url: str | None = None,
    fastapi_app: FastAPI | None = None,
) -> BootstrapState:
    global _BOOTSTRAP_STATE, _BOOTSTRAP_METADATA, _BOUND_APPS
    ContextBridge.set_request_id()
    bootstrap_info = behavior_bootstrap(
        repo_root=Path(__file__).resolve().parents[1],
        redis_url=redis_url,
    )
    state: BootstrapState = get_bootstrap_state()
    policy: Dict[str, Any] = bootstrap_info["policy"]
    telemetry: Dict[str, Any] = bootstrap_info["telemetry"]

    dispatcher = state.dispatcher
    router = state.router

    bot_token = getattr(state.bot, "token", api_token)
    if bot_token != api_token:
        log.warning(
            "bootstrap.token_mismatch",
            extra={"expected": "***", "actual": "***"},
        )

    if not dispatcher.workflow_data.get("message_router_attached"):
        router.include_router(message_handlers.router)
        dispatcher.workflow_data["message_router_attached"] = True
        log.debug(
            "bootstrap.router_attached",
            extra={"request_id": telemetry.get("request_id")},
        )
    else:
        log.debug(
            "bootstrap.router_cached",
            extra={"request_id": telemetry.get("request_id")},
        )

    metrics_state = dispatcher.workflow_data.setdefault(
        "metrics",
        {
            "telegram_updates_total": 0,
            "telegram_inbound_total": 0,
            "telegram_ignored_total": 0,
            "telegram_streaming_failures": 0,
            "telegram_placeholder_latency_sum": 0.0,
            "telegram_placeholder_latency_count": 0,
            "webhook_signature_failures": 0,
            "webhook_rtt_ms_sum": 0.0,
            "webhook_rtt_ms_count": 0,
        },
    )

    _BOOTSTRAP_STATE = state
    _BOOTSTRAP_METADATA = {
        "telemetry": telemetry,
        "policy": policy,
        "metrics": metrics_state,
    }

    log.info(
        "bootstrap.success",
        extra={
            "request_id": telemetry.get("request_id"),
            "router": router.name,
            "policy_seed": policy.get("determinism", {}).get("seed"),
            "memory_only_mode": policy.get("runtime_flags", {}).get("memory_only_mode"),
            "stages": telemetry.get("stages", []),
        },
    )

    if fastapi_app is not None:
        fastapi_app.state.runtime_policy = policy
        fastapi_app.state.bootstrap_metrics = metrics_state
        app_key = id(fastapi_app)
        if app_key not in _BOUND_APPS:
            secret = getattr(fastapi_app.state, "webhook_secret", "")
            register_routes(fastapi_app, dispatcher, webhook_url, policy, secret)
            _BOUND_APPS.add(app_key)
    return state


def get_bootstrap_metadata() -> Dict[str, Any]:
    if _BOOTSTRAP_METADATA is None:
        raise RuntimeError("bootstrap metadata not initialized")
    return _BOOTSTRAP_METADATA


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        ContextBridge.set_request_id(request.headers.get("x-request-id"))
        response = await call_next(request)
        return response

