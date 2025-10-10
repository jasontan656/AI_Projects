from __future__ import annotations
from typing import Dict, Any, Optional
import time

from shared_utilities.mango_db.mongodb_connector import DatabaseOperations
from shared_utilities.response import create_error_response
from .tokens import verify_access_token, revoke_session


def _db() -> DatabaseOperations:
    return DatabaseOperations()
# _db() 返回数据库操作实例
# 用于写入登录历史审计与状态更新


def _get_envelope_token(envelope: Dict[str, Any]) -> Optional[str]:
    user = envelope.get("user") or {}
    if isinstance(user, dict):
        auth = user.get("authorization")
        if isinstance(auth, str) and auth.startswith("Bearer "):
            return auth[7:]
        return auth
    return None
# _get_envelope_token(envelope)
# 从 envelope.user.authorization 解析 Bearer 令牌
# 返回去除前缀后的 token 字符串或 None



def handle_logout_step(envelope: Dict[str, Any]) -> Dict[str, Any]:
    token = _get_envelope_token(envelope)
    if not token:
        return create_error_response("Authentication required to logout", error_type="UNAUTHORIZED")
    # Validate access token integrity
    try:
        payload = verify_access_token(token)
    except (ValueError, KeyError, RuntimeError) as exc:
        message = str(exc) if isinstance(exc, Exception) else ""
        if message and "Session revoked" in message:
            return {"success": True, "message": "Logout successful"}
        if message and "expired" in message.lower():
            return create_error_response("Token has expired", error_type="UNAUTHORIZED")
        return create_error_response("Invalid token", error_type="UNAUTHORIZED")

    if payload.get("type") != "access_token":
        return create_error_response("Token is not an access token", error_type="INVALID_INPUT")

    sid = payload.get("sid")
    if not sid:
        return create_error_response("Session id missing in token", error_type="NOT_FOUND")

    ok = revoke_session(sid)
    if not ok:
        return create_error_response("Logout operation failed", error_type="DEPENDENCY_ERROR")

    # Record logout attempt without failing user experience
    try:
        user_id = payload.get("user_id")
        auth_username = payload.get("auth_username")
        history_item = {
            "ts": time.time(),
            "ip": (envelope.get("meta") or {}).get("ip"),
            "user_agent": (envelope.get("meta") or {}).get("user_agent"),
            "success": True,
            "auth_username": auth_username,
            "provider": "system",
            "action": "logout",
        }
        _db().update(
            "user_status",
            {"user_id": user_id},
            {
                "$setOnInsert": {"user_id": user_id},
                "$push": {"login_history.history": history_item},
            },
        )
    except (RuntimeError, OSError, ValueError):
        pass

    return {"success": True, "message": "Logout successful"}



LOGOUT_STEP_SPECS: Dict[str, Any] = {
    "flow_id": "auth_session_management",
    "name": "Auth logout flow",
    "description": "Revoke current session and record audit",
    "modules": ["auth"],
    "steps": [
        {
            "step_id": "auth_logout",
            "module": "auth",
            "handler": "cry_backend.tool_modules.auth.logout.handle_logout_step",
            "required_fields": ["payload"],
            "output_fields": ["success", "message"],
        }
    ],
}


