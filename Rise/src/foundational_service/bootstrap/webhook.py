"""Webhook utilities for foundational services."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Mapping, Optional, TypedDict

from fastapi import HTTPException
from starlette import status

from project_utility.context import ContextBridge

from foundational_service.contracts.toolcalls import call_verify_signature
from foundational_service.diagnostics.metrics import default_metrics_state

__all__ = [
    "WebhookResponse",
    "behavior_webhook_request",
    "behavior_webhook_startup",
    "call_register_webhook",
]


class WebhookResponse(TypedDict, total=False):
    status: str
    request_id: str
    telemetry: Dict[str, Any]


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
        metrics_store = workflow.setdefault("metrics", default_metrics_state())
    if not signature_ok:
        if metrics_store is not None:
            metrics_store["webhook_signature_failures"] = metrics_store.get("webhook_signature_failures", 0) + 1
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid webhook signature")
    return {
        "status": "accepted",
        "request_id": request_id,
        "telemetry": {"signature_status": "accepted"},
    }


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


async def behavior_webhook_startup(
    bot: Any,
    webhook_url: str,
    secret: str,
    *,
    retries: int = 2,
    drop_pending_updates: bool = False,
    max_connections: Optional[int] = None,
) -> Dict[str, Any]:
    """Register Telegram webhook with retry telemetry."""

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
        except Exception as exc:  # pragma: no cover - escalate pipeline errors for retry/abort
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

    return {
        "status": "ok",
        "stages": stages,
        "prompt_events": prompt_events,
        "request_id": ContextBridge.request_id(),
        "telemetry": {"stages": stages, "prompt_events": prompt_events},
    }
