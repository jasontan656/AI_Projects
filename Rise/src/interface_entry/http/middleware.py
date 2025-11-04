"""HTTP middleware for interface entry layer."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from project_utility.context import ContextBridge


class FastAPIRequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        ContextBridge.set_request_id(request.headers.get("x-request-id"))
        response = await call_next(request)
        return response


_logger = logging.getLogger("interface_entry.http.middleware")


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
            _logger.info(
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


__all__ = ["FastAPIRequestIDMiddleware", "LoggingMiddleware"]
