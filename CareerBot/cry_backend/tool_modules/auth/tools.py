"""
Auth module tool interface for LLM function calling.
Exposes auth module as a self-contained tool with multiple actions.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Dict, List

from shared_utilities.response import create_error_response
from hub.logger import info
from shared_utilities.time import Time
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username

from .exceptions import (
    DependencyError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidInputError,
    UserAlreadyExistsError,
)


# Supported actions within auth tool
AUTH_ACTIONS = [
    "auth_login",
    "auth_register",
    "oauth_google_url",
    "oauth_google_callback",
    "oauth_facebook_url",
    "oauth_facebook_callback",
    "reset_step1",
    "reset_step2",
    "auth_logout",
]


def _run_sync(result: Any) -> Any:
    """Resolve coroutine results in a fail-fast manner."""
    if not inspect.iscoroutine(result):
        return result

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(result)

    raise RuntimeError("Auth router returned coroutine under an active event loop")


def _map_exception(exc: Exception) -> Dict[str, Any]:
    if isinstance(exc, InvalidInputError):
        return create_error_response(str(exc), error_type="INVALID_INPUT")
    if isinstance(exc, InvalidCredentialsError):
        return create_error_response(str(exc), error_type="UNAUTHORIZED")
    if isinstance(exc, (UserAlreadyExistsError, EmailAlreadyRegisteredError)):
        return create_error_response(str(exc), error_type="CONFLICT")
    if isinstance(exc, DependencyError):
        return create_error_response(str(exc), error_type="DEPENDENCY_ERROR")
    raise exc


def auth_tool_handler(
    action: str,
    params: Dict[str, Any],
    user_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Auth tool handler for LLM function calling.

    Args:
        action: The auth action to perform (e.g., "auth_login", "auth_register")
        params: Action-specific parameters (e.g., {"auth_username": "...", "password": "..."})
        user_context: User context with user_id, session_id, authorization, etc.

    Returns:
        Standardized result from auth module
    """
    info("auth.tool_called", action=action, params_keys=sorted(params.keys()))

    if action not in AUTH_ACTIONS:
        return create_error_response(f"Unknown auth action: {action}", error_type="STEP_NOT_FOUND")

    try:
        user_id = ensure_timestamp_uuidv4(user_context.get("user_id"), field_name="user_id")
    except ValueError as exc:
        return create_error_response(str(exc), error_type="INVALID_INPUT")

    try:
        auth_username = normalize_auth_username(
            params.get("auth_username") or user_context.get("auth_username")
        )
    except ValueError as exc:
        return create_error_response(str(exc), error_type="INVALID_INPUT")

    request_id = params.get("request_id")
    if request_id:
        try:
            request_id = ensure_timestamp_uuidv4(request_id, field_name="request_id")
        except ValueError as exc:
            return create_error_response(str(exc), error_type="INVALID_INPUT")
    else:
        request_id = Time.timestamp()

    envelope = {
        "user": {
            "id": user_id,
            "auth_username": auth_username,
            "authorization": user_context.get("authorization"),
        },
        "payload": {
            "route": {
                "path": ["auth", action],
            },
            "data": {**params, "user_id": user_id, "auth_username": auth_username, "request_id": request_id},
        },
        "meta": {
            "session_id": user_context.get("session_id"),
            "request_id": request_id,
        },
    }

    from .router import router

    try:
        result = router.route(envelope)
    except (
        InvalidInputError,
        InvalidCredentialsError,
        UserAlreadyExistsError,
        EmailAlreadyRegisteredError,
        DependencyError,
    ) as exc:
        return _map_exception(exc)

    return _run_sync(result)


# Tool metadata for registration
AUTH_TOOL_SPEC = {
    "name": "auth",
    "description": (
        "Authentication and authorization module. Handles user login, registration, "
        "OAuth (Google, Facebook), password reset, and logout operations."
    ),
    "actions": AUTH_ACTIONS,
    "handler": auth_tool_handler,
}


__all__ = ["auth_tool_handler", "AUTH_TOOL_SPEC", "AUTH_ACTIONS"]




