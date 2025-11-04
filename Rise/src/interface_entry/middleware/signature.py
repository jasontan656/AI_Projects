"""Webhook signature verification middleware."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from foundational_service.contracts import toolcalls
from foundational_service.contracts.prompt_registry import PROMPT_REGISTRY
from project_utility.context import ContextBridge

log = logging.getLogger("interface_entry.middleware.signature")


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
            prompt_text = ""
            try:  # pragma: no cover - optional prompt rendering
                prompt_text = PROMPT_REGISTRY.render("webhook_signature_fail", request_id=request_id)
            except Exception:
                prompt_text = ""
            log.warning(
                "webhook.signature_mismatch",
                extra={
                    "request_id": request_id,
                    "signature_status": "rejected",
                    "prompt_id": "webhook_signature_fail",
                    "prompt_text": prompt_text,
                },
            )
            raise exc

        request.state.signature_status = "accepted"
        return await call_next(request)


__all__ = ["SignatureVerifyMiddleware"]
