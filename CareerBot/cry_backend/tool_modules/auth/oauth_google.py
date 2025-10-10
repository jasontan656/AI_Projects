from __future__ import annotations

# Google OAuth 自包含模块
# - 提供 URL 生成/回调处理（Envelope 适配）
# - 内联 HTTP 交互（不再依赖 oauth_utils.py）
# - 统一 user_id-first 与登录历史写入（provider=google）

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
class GoogleOAuthUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Optional[str] = None
    # GoogleOAuthUrlRequest(state) 封装 URL 生成请求字段


class GoogleOAuthCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    state: Optional[str] = None
    expected_state: Optional[str] = None
    # GoogleOAuthCallbackRequest(code/state/expected_state) 封装回调参数


# ======== 核心领域函数（供服务层与 Envelope Handler 复用） ========
def get_google_auth_url(state: Optional[str] = None) -> str:
    """
    生成 Google OAuth 授权 URL。
    - 输入: state（可选）用于 CSRF 防护
    - 输出: 可直接跳转的授权链接
    """
    # state = state or secrets.token_urlsafe(32) 若未提供则生成随机串
    actual_state = state or secrets.token_urlsafe(32)

    # Google 授权端点与 scope
    auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    scope = "openid email profile"

    # 组装查询参数并编码
    from urllib.parse import urlencode
    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "redirect_uri": os.getenv("OAUTH_REDIRECT_URI", ""),
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "state": actual_state,
    }
    query = urlencode(params)
    url = f"{auth_endpoint}?{query}"
    return url
    # get_google_auth_url(state)->url 构造授权链接返回给前端


def _exchange_code_for_token(code: str) -> Dict[str, Any]:
    """
    使用授权码换取访问令牌（Google）。
    - 输入: code 授权码
    - 输出: token 响应字典（access_token/refresh_token 等）
    """
    token_endpoint = "https://oauth2.googleapis.com/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv("OAUTH_REDIRECT_URI", ""),
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    with httpx.Client(timeout=20.0) as client:
        resp = client.post(token_endpoint, data=data, headers=headers)
    # httpx.post(token_endpoint,data,headers) 发送表单请求
    resp.raise_for_status()
    return resp.json()
    # 返回 token JSON 用于后续获取用户信息


def _get_user_info(access_token: str) -> Dict[str, Any]:
    """
    使用 access_token 获取 Google 用户信息（id/email/name）。
    """
    info_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=20.0) as client:
        r = client.get(info_endpoint, headers=headers)
    # httpx.get(info_endpoint, headers) 请求用户信息端点
    r.raise_for_status()
    return r.json()
    # 返回用户信息字典供解析


def login_with_google(code: str, state: Optional[str], expected_state: Optional[str]) -> UserResponse:
    """
    完成 Google OAuth 登录流程：code→token→userinfo→user落库→生成 token pair。
    - 输入: 授权码 code、回调 state、预期 expected_state
    - 输出: UserResponse（包含 access_token/refresh_token）
    """
    # 校验 state（若提供 expected_state）
    if expected_state and (expected_state != (state or "")):
        raise ValueError("Invalid state parameter")
    # _exchange_code_for_token(code) 请求 Google 令牌端点换取 token
    token_data = _exchange_code_for_token(code)
    access_token = token_data.get("access_token")

    # _get_user_info(access_token) 读取用户信息
    user_info = _get_user_info(access_token)
    google_id = user_info.get("id")
    email = (user_info.get("email") or "").strip().lower()

    # 解析/创建 user_id，并尝试绑定 google_id → user_status.oauth_google_id
    user_id = resolve_user_id_by_auth_username(email) or create_user_for_oauth(email)
    try:
        link_oauth_to_existing_email(email, "google", google_id)
    except ValueError:
        # 邮箱不存在或更新失败时静默（首次创建路径已覆盖）
        pass

    # 生成访问令牌与刷新令牌
    tokens = generate_token_pair(user_id, email)

    return UserResponse(
        user_id=user_id,
        auth_username=email,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )
    # 返回 UserResponse 供上层包装/透传


# ======== Envelope 适配 Handler（供 router 调用） ========
def _get_envelope_data(envelope: Dict[str, Any]) -> Dict[str, Any]:
    payload = envelope.get("payload") or {}
    return (payload.get("data") or {}) if isinstance(payload, dict) else {}
    # _get_envelope_data(envelope) 提取 payload.data 字段


def handle_oauth_google_url_step(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成授权 URL 的单步处理器。
    - 入参: envelope.payload.data.state（可选）
    - 出参: 标准字典 {success, message, data:{auth_url, provider}}
    """
    data = _get_envelope_data(envelope)
    req = GoogleOAuthUrlRequest(**data)
    auth_url = get_google_auth_url(req.state)
    return {
        "success": True,
        "message": "Google OAuth URL generated",
        "data": {"auth_url": auth_url, "provider": "google"},
    }
    # 返回标准结构，供 auth_route 直接透传


def handle_oauth_google_callback_step(envelope: Dict[str, Any]) -> UserResponse:
    """
    处理授权回调的单步处理器。
    - 入参: envelope.payload.data.{code,state,expected_state}
    - 出参: UserResponse（auth_route 会包装为标准响应）
    """
    data = _get_envelope_data(envelope)
    req = GoogleOAuthCallbackRequest(**data)

    # 执行登录主流程
    result = login_with_google(req.code, req.state, req.expected_state)

    # 记录登录历史（provider=google）
    meta = envelope.get("meta") or {}
    ip = meta.get("ip")
    ua = meta.get("user_agent")
    history_item = {
        "ts": Time.timestamp(),
        "ip": ip,
        "user_agent": ua,
        "success": True,
        "auth_username": result.auth_username,
        "provider": "google",
    }
    _db().update(
        "user_status",
        {"user_id": result.user_id},
        {
            "$setOnInsert": {"user_id": result.user_id},
            "$push": {"login_history.history": history_item},
        },
    )
    # update('user_status',{user_id},{setOnInsert, $push login_history}) 写入登录历史

    return create_success_response(
        data={
            "user_id": result.user_id,
            "auth_username": result.auth_username,
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "token_type": result.token_type,
        }
    )


# ======== Step 规范（供 applications.auth.router 动态注册） ========
GOOGLE_OAUTH_STEP_SPECS = {
    "flow_id": "oauth_google_authentication",
    "name": "Google OAuth authentication flow (single-step entries)",
    "description": "Generate Google OAuth URL and handle callback (user_id-first)",
    "modules": ["auth"],
    "steps": [
        {
            "step_id": "oauth_google_url",
            "module": "auth",
            "handler": "cry_backend.tool_modules.auth.oauth_google.handle_oauth_google_url_step",
            "required_fields": ["payload"],
            "output_fields": ["success", "message", "data.auth_url", "data.provider"],
        },
        {
            "step_id": "oauth_google_callback",
            "module": "auth",
            "handler": "cry_backend.tool_modules.auth.oauth_google.handle_oauth_google_callback_step",
            "required_fields": ["payload"],
            "output_fields": ["user_id", "auth_username", "access_token", "refresh_token", "token_type"],
        },
    ],
}


__all__ = [
    # 领域函数
    "get_google_auth_url",
    "login_with_google",
    # Envelope handler
    "handle_oauth_google_url_step",
    "handle_oauth_google_callback_step",
    # Step 规范
    "GOOGLE_OAUTH_STEP_SPECS",
]


