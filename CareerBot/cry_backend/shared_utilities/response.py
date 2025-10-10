from __future__ import annotations

from typing import Any, Dict, Optional


def create_success_response(data: Any = None, message: str = "ok") -> Dict[str, Any]:
    response: Dict[str, Any] = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    return response


def create_error_response(
    error: str,
    error_type: str = "INTERNAL_ERROR",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response: Dict[str, Any] = {"success": False, "error": error, "error_type": error_type}
    if details:
        response["details"] = details
    return response


__all__ = ["create_success_response", "create_error_response"]

