"""HTTP middleware for interface entry layer."""

from __future__ import annotations

from time import perf_counter
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from project_utility.context import ContextBridge
from project_utility.telemetry import emit as telemetry_emit


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
            signature_reason = getattr(request.state, "signature_reason", None)
            reject_reason = getattr(request.state, "reject_reason", None)
            reject_detail = getattr(request.state, "reject_detail", None)
            payload = {
                "status_code": status_code,
                "latency_ms": latency_ms,
                "signature_status": signature_status,
            }
            if signature_reason:
                payload["signature_reason"] = signature_reason
            if reject_reason:
                payload["reject_reason"] = reject_reason
            if reject_detail:
                payload["reject_detail"] = reject_detail
            telemetry_emit(
                "http.request",
                level="info",
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                payload=payload,
            )


__all__ = ["FastAPIRequestIDMiddleware", "LoggingMiddleware"]
