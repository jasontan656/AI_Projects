from __future__ import annotations

"""HTTP exception handlers producing standard API envelopes."""

from typing import Any, Mapping

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from interface_entry.http.responses import ApiError, ApiMeta, ApiResponse
from project_utility.context import ContextBridge


def _extract_error(detail: Any, default_code: str = "UNKNOWN_ERROR") -> ApiError:
    if isinstance(detail, Mapping):
        code = str(detail.get("code") or default_code)
        message = str(detail.get("message") or detail.get("detail") or "An error occurred")
        return ApiError(code=code, message=message)
    if isinstance(detail, str):
        return ApiError(code=default_code, message=detail)
    return ApiError(code=default_code, message=str(detail))


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = ContextBridge.request_id()
    error = _extract_error(exc.detail, default_code="HTTP_ERROR")
    payload = ApiResponse[dict[str, Any]](
        data=None,
        meta=ApiMeta(requestId=request_id),  # type: ignore[arg-type]
        errors=[error],
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(by_alias=True),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = ContextBridge.request_id()
    payload = ApiResponse[dict[str, Any]](
        data=None,
        meta=ApiMeta(requestId=request_id),  # type: ignore[arg-type]
        errors=[
            ApiError(code="INTERNAL_ERROR", message="Unexpected server error"),
        ],
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload.model_dump(by_alias=True),
    )

