"""
MBTI module tool interface for LLM function calling.
Exposes MBTI module as a self-contained tool with multiple test steps.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Dict, List

from shared_utilities.time import Time
from hub.logger import info
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username
from shared_utilities.response import create_error_response
from .errors import MBTIConfigurationError, MBTIStepStateError, MBTIDatabaseError


# Supported actions within mbti tool
MBTI_ACTIONS = [
    "mbti_step1",
    "mbti_step2",
    "mbti_step3",
    "mbti_step4",
    "mbti_step5",
]


def _run_sync(result: Any) -> Any:
    if not inspect.iscoroutine(result):
        return result
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(result)
    raise RuntimeError("MBTI router returned coroutine under an active event loop")


def mbti_tool_handler(
    action: str,
    params: Dict[str, Any],
    user_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    MBTI tool handler for LLM function calling.

    Args:
        action: The MBTI test step to perform (e.g., "mbti_step1", "mbti_step2")
        params: Step-specific parameters (e.g., {"answers": {...}})
        user_context: User context with user_id, session_id, authorization, etc.

    Returns:
        Standardized result from MBTI module
    """
    info("mbti.tool_called", action=action, params_keys=sorted(params.keys()))

    if action not in MBTI_ACTIONS:
        return create_error_response(f"Unknown MBTI action: {action}", error_type="STEP_NOT_FOUND")

    try:
        user_candidate = params.get("user_id") or user_context.get("user_id")
        user_id = ensure_timestamp_uuidv4(user_candidate, field_name="user_id")
    except ValueError as exc:
        return create_error_response(str(exc), error_type="INVALID_INPUT")

    try:
        auth_username = normalize_auth_username(
            params.get("auth_username") or user_context.get("auth_username")
        )
    except ValueError as exc:
        return create_error_response(str(exc), error_type="INVALID_INPUT")

    request_id_candidate = params.get("request_id")
    if request_id_candidate is None:
        request_id = Time.timestamp()
    else:
        try:
            request_id = ensure_timestamp_uuidv4(str(request_id_candidate), field_name="request_id")
        except ValueError as exc:
            return create_error_response(str(exc), error_type="INVALID_INPUT")

    enriched_params = {**params, "user_id": user_id, "auth_username": auth_username, "request_id": request_id}
    if "flow_id" not in enriched_params:
        enriched_params["flow_id"] = "mbti_personality_test"

    envelope = {
        "user": {
            "id": user_id,
            "auth_username": auth_username,
            "authorization": user_context.get("authorization"),
        },
        "payload": {
            "route": {
                "path": ["mbti", action],
            },
            "data": enriched_params,
        },
        "meta": {
            "session_id": user_context.get("session_id"),
            "request_id": request_id,
        },
    }

    from .router import router

    try:
        result = router.route(envelope)
        return _run_sync(result)
    except MBTIStepStateError as exc:
        return create_error_response(str(exc), error_type="CONFLICT")
    except MBTIConfigurationError as exc:
        return create_error_response(str(exc), error_type="DEPENDENCY_ERROR")
    except MBTIDatabaseError as exc:
        return create_error_response(str(exc), error_type="DEPENDENCY_ERROR")
    except ValueError as exc:
        return create_error_response(str(exc), error_type="INVALID_INPUT")


# Tool metadata for registration
MBTI_TOOL_SPEC = {
    "name": "mbti",
    "description": (
        "MBTI personality test module. Provides a complete multi-step testing process "
        "including questionnaires, scoring, verification, and final report generation."
    ),
    "actions": MBTI_ACTIONS,
    "handler": mbti_tool_handler,
}


__all__ = ["mbti_tool_handler", "MBTI_TOOL_SPEC", "MBTI_ACTIONS"]
