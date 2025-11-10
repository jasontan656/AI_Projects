"""Webhook signature verification middleware."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from foundational_service.contracts import toolcalls
from project_utility.context import ContextBridge
from project_utility.telemetry import emit as telemetry_emit

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
        request_id = ContextBridge.request_id()
        if request.url.path != self._webhook_path:
            return await call_next(request)

        secret = getattr(request.app.state, "webhook_secret", "")
        if not secret:
            log.error("webhook.secret_missing")
            request.state.signature_status = "error"
            request.state.signature_reason = "secret_missing"
            telemetry_emit(
                "telegram.signature",
                level="error",
                request_id=request_id,
                payload={
                    "status": "error",
                    "reason": "secret_missing",
                    "path": request.url.path,
                },
            )
            raise HTTPException(status_code=500, detail="webhook_secret_unset")

        metrics_state = getattr(request.app.state, "telegram_metrics", None)
        request.state.signature_status = "pending"
        request.state.signature_reason = "pending"
        try:
            toolcalls.call_verify_signature(request.headers, secret)
        except HTTPException as exc:
            request.state.signature_status = "rejected"
            request.state.signature_reason = "mismatch"
            request.state.reject_reason = "signature_mismatch"
            if metrics_state is not None:
                metrics_state["webhook_signature_failures"] = metrics_state.get("webhook_signature_failures", 0) + 1
            log.warning(
                "webhook.signature_mismatch",
                extra={
                    "request_id": request_id,
                    "signature_status": "rejected",
                },
            )
            telemetry_emit(
                "telegram.signature",
                level="warning",
                request_id=request_id,
                payload={
                    "status": "rejected",
                    "reason": "mismatch",
                    "path": request.url.path,
                    "header_present": bool(request.headers.get(self._header_name)),
                },
            )
            raise exc

        request.state.signature_status = "accepted"
        request.state.signature_reason = "accepted"
        return await call_next(request)


__all__ = ["SignatureVerifyMiddleware"]
