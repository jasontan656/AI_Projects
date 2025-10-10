from __future__ import annotations

# Facebook OAuth 自包含模块
# - 提供 URL 生成/回调处理（Envelope 适配）
# - 内联 HTTP 交互（不再依赖 oauth_utils.py）
# - 统一 user_id-first 与登录历史写入（provider=facebook）

import secrets
import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from shared_utilities.response import create_success_response
from shared_utilities.time import Time

import os
from shared_utilities.mango_db.mongodb_connector import DatabaseOperations
from .tokens import generate_token_pair
from .email_register import (
    resolve_user_id_by_auth_username,
    create_user_for_oauth,
    link_oauth_to_existing_email,
)
from pydantic import BaseModel, ConfigDict
class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    auth_username: str
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
# UserResponse(user_id/auth_username/access_token/refresh_token)
# OAuth 登录成功返回模型，供门面封装


def _db() -> DatabaseOperations:
    return DatabaseOperations()
    # _db() 返回数据库操作对象，用于写入登录历史与状态


# ======== Pydantic 请求模型 ========
class FacebookOAuthUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Optional[str] = None
    # FacebookOAuthUrlRequest(state) 封装 URL 生成请求字段


class FacebookOAuthCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    state: Optional[str] = None
    expected_state: Optional[str] = None
    # FacebookOAuthCallbackRequest(code/state/expected_state) 封装回调参数


# ======== 核心领域函数 ========
def get_facebook_auth_url(state: Optional[str] = None) -> str:
    """
    生成 Facebook OAuth 授权 URL。
    - 输入: state（可选）用于 CSRF 防护
    - 输出: 可直接跳转的授权链接
    """
    actual_state = state or secrets.token_urlsafe(32)

    auth_endpoint = "https://www.facebook.com/v18.0/dialog/oauth"
    scope = "email,public_profile"
    from urllib.parse import urlencode
    params = {
        "client_id": os.getenv("FACEBOOK_CLIENT_ID", ""),
        "redirect_uri": os.getenv("OAUTH_REDIRECT_URI", ""),
        "response_type": "code",
        "scope": scope,
        "state": actual_state,
    }
    query = urlencode(params)
    return f"{auth_endpoint}?{query}"
    # get_facebook_auth_url(state)->url 构造授权链接返回给前端


def _exchange_code_for_token(code: str) -> Dict[str, Any]:
    token_endpoint = "https://graph.facebook.com/v18.0/oauth/access_token"
    params = {
        "client_id": os.getenv("FACEBOOK_CLIENT_ID", ""),
        "client_secret": os.getenv("FACEBOOK_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv("OAUTH_REDIRECT_URI", ""),
        "code": code,
    }
    with httpx.Client(timeout=20.0) as client:
        r = client.get(token_endpoint, params=params)
    # httpx.get(token_endpoint, params) 以查询参数换取 token
    r.raise_for_status()
    return r.json()
    # 返回 token JSON


def _get_user_info(access_token: str) -> Dict[str, Any]:
    info_endpoint = "https://graph.facebook.com/me"
    params = {"fields": "id,name,email", "access_token": access_token}
    with httpx.Client(timeout=20.0) as client:
        r = client.get(info_endpoint, params=params)
    # httpx.get(info_endpoint, params) 请求用户信息端点
    r.raise_for_status()
    return r.json()
    # 返回用户信息字典


def login_with_facebook(code: str, state: Optional[str], expected_state: Optional[str]) -> UserResponse:
    """
    完成 Facebook OAuth 登录流程：code→token→userinfo→user落库→生成 token pair。
    """
    if expected_state and (expected_state != (state or "")):
        raise ValueError("Invalid state parameter")

    token_data = _exchange_code_for_token(code)
    access_token = token_data.get("access_token")

    user_info = _get_user_info(access_token)
    facebook_id = user_info.get("id")
    email = (user_info.get("email") or "").strip().lower()

    user_id = resolve_user_id_by_auth_username(email) or create_user_for_oauth(email)
    try:
        link_oauth_to_existing_email(email, "facebook", facebook_id)
    except ValueError:
        pass

    tokens = generate_token_pair(user_id, email)
    return UserResponse(
        user_id=user_id,
        auth_username=email,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


# ======== Envelope 适配 Handler ========
def _get_envelope_data(envelope: Dict[str, Any]) -> Dict[str, Any]:
    payload = envelope.get("payload") or {}
    return (payload.get("data") or {}) if isinstance(payload, dict) else {}


def handle_oauth_facebook_url_step(envelope: Dict[str, Any]) -> Dict[str, Any]:
    data = _get_envelope_data(envelope)
    req = FacebookOAuthUrlRequest(**data)
    auth_url = get_facebook_auth_url(req.state)
    return {
        "success": True,
        "message": "Facebook OAuth URL generated",
        "data": {"auth_url": auth_url, "provider": "facebook"},
    }


def handle_oauth_facebook_callback_step(envelope: Dict[str, Any]) -> UserResponse:
    data = _get_envelope_data(envelope)
    req = FacebookOAuthCallbackRequest(**data)

    result = login_with_facebook(req.code, req.state, req.expected_state)

    meta = envelope.get("meta") or {}
    ip = meta.get("ip")
    ua = meta.get("user_agent")
    history_item = {
        "ts": Time.timestamp(),
        "ip": ip,
        "user_agent": ua,
        "success": True,
        "auth_username": result.auth_username,
        "provider": "facebook",
    }
    _db().update(
        "user_status",
        {"user_id": result.user_id},
        {
            "$setOnInsert": {"user_id": result.user_id},
            "$push": {"login_history.history": history_item},
        },
    )
    return create_success_response(
        data={
            "user_id": result.user_id,
            "auth_username": result.auth_username,
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "token_type": result.token_type,
        }
    )


# ======== Step 规范 ========
FACEBOOK_OAUTH_STEP_SPECS = {
    "flow_id": "oauth_facebook_authentication",
    "name": "Facebook OAuth authentication flow (single-step entries)",
    "description": "Generate Facebook OAuth URL and handle callback (user_id-first)",
    "modules": ["auth"],
    "steps": [
        {
            "step_id": "oauth_facebook_url",
            "module": "auth",
            "handler": "cry_backend.tool_modules.auth.oauth_facebook.handle_oauth_facebook_url_step",
            "required_fields": ["payload"],
            "output_fields": ["success", "message", "data.auth_url", "data.provider"],
        },
        {
            "step_id": "oauth_facebook_callback",
            "module": "auth",
            "handler": "cry_backend.tool_modules.auth.oauth_facebook.handle_oauth_facebook_callback_step",
            "required_fields": ["payload"],
            "output_fields": ["user_id", "auth_username", "access_token", "refresh_token", "token_type"],
        },
    ],
}


__all__ = [
    "get_facebook_auth_url",
    "login_with_facebook",
    "handle_oauth_facebook_url_step",
    "handle_oauth_facebook_callback_step",
    "FACEBOOK_OAUTH_STEP_SPECS",
]


