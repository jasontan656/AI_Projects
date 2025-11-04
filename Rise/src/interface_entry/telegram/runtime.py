"""
Runtime bootstrap for the Telegram channel.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI

from foundational_service.bootstrap.aiogram import (
    BootstrapState,
    bootstrap_aiogram,
    get_bootstrap_state,
)
from interface_entry.telegram import handlers as message_handlers
from interface_entry.telegram.routes import register_routes
from project_utility.config.paths import get_repo_root
from project_utility.context import ContextBridge

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
    bootstrap_info = bootstrap_aiogram(
        repo_root=get_repo_root(),
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
        parent_router = getattr(message_handlers.router, "parent_router", None)
        if parent_router is not None and parent_router is not dispatcher:
            try:
                sub_routers = getattr(parent_router, "sub_routers", [])
                if message_handlers.router in sub_routers:
                    sub_routers.remove(message_handlers.router)
            except Exception:  # pragma: no cover
                pass
            setattr(message_handlers.router, "_parent_router", None)

        if message_handlers.router is router:
            log.error(
                "bootstrap.router_legacy_reference",
                extra={"request_id": telemetry.get("request_id"), "router": getattr(router, "name", "unknown")},
            )
            raise RuntimeError("bootstrap_refused_self_reference_router")

        already_attached = message_handlers.router.parent_router is dispatcher
        if not already_attached:
            router.include_router(message_handlers.router)
            log.debug(
                "bootstrap.router_attached",
                extra={"request_id": telemetry.get("request_id")},
            )
        else:
            log.debug(
                "bootstrap.router_cached",
                extra={"request_id": telemetry.get("request_id")},
            )
        dispatcher.workflow_data["message_router_attached"] = True
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
