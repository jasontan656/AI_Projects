# 标准登录模块
# 实现用户名/密码登录逻辑

from shared_utilities.mango_db.mongodb_connector import DatabaseOperations
from shared_utilities.time import Time
from typing import Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
# 本模块内置密码校验（自包含，不依赖外部 hashing.py）
import bcrypt

def _verify_password(password: str, hashed: str) -> bool:
    # bcrypt.checkpw() 对比明文密码与哈希
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
from pydantic import BaseModel, Field, ConfigDict
from shared_utilities.validator import normalize_auth_username, ensure_password_strength
from .tokens import generate_token_pair
from .exceptions import InvalidCredentialsError, InvalidInputError
class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    auth_username: str
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
# UserResponse(user_id/auth_username/access_token/refresh_token)
# 登录成功返回模型，供门面封装


def _db() -> DatabaseOperations:
    return DatabaseOperations()


# ======== Normalizers & Validators (constitution-compliant) ========
def _normalize_username(username: str) -> str:
    # Use centralized username normalization; do not force email format
    return normalize_auth_username(username)

def _validate_password(password: str) -> str:
    try:
        return ensure_password_strength(password, field_name="password")
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc


# ======== Request models (for strong field skeleton) ========
class EmailLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    auth_username: str = Field(..., description="登录邮箱或用户名（邮箱优先）")
    password: str = Field(..., description="明文密码")

# 专用线程池：仅用于 CPU 密集的 bcrypt 校验，避免与 IO 竞争
_CPU_CORES = max(1, (os.cpu_count() or 4))
# 硬编码 bcrypt 专用线程池规模（与 CPU 关联），自包含不读取外部配置
_BCRYPT_EXECUTOR = ThreadPoolExecutor(max_workers=min(max(4, _CPU_CORES), 32))



def _resolve_user_id_by_auth_username(auth_username: str) -> str:
    doc = _db().find("auth_login_index", {"auth_username": auth_username}, {"user_id": 1, "_id": 0})
    if not doc:
        raise InvalidCredentialsError("邮箱或密码错误")
    return doc[0]["user_id"]


def login_user_sync(auth_username: str, password: str) -> UserResponse:
    """
    执行用户标准登录流程（异步版）
    """
    # 归一化与强校验
    req = EmailLoginRequest(auth_username=auth_username, password=password)
    normalized_username = _normalize_username(req.auth_username)
    validated_password = _validate_password(req.password)

    # 一次聚合查询：映射表匹配 → $lookup 关联 user_status → 投影热字段
    pipeline = [
        {"$match": {"auth_username": normalized_username}},
        {"$lookup": {"from": "user_status", "localField": "user_id", "foreignField": "user_id", "as": "status"}},
        {"$unwind": "$status"},
        {"$project": {"user_id": 1, "auth_user_password": "$status.auth_user_password", "auth": "$status.auth"}}
    ]
    agg = DatabaseOperations().aggregate("auth_login_index", pipeline)
    if not agg:
        raise InvalidCredentialsError("用户名或密码错误")
    row = agg[0]
    user_id = row.get("user_id")
    stored_hashed_password = row.get("auth_user_password")
    # 在专用线程池中执行 bcrypt 校验，避免阻塞
    is_password_valid = _BCRYPT_EXECUTOR.submit(_verify_password, validated_password, stored_hashed_password).result()
    if not is_password_valid:
        raise InvalidCredentialsError("用户名或密码错误")

    tokens = generate_token_pair(user_id, normalized_username)
    return UserResponse(
        user_id=user_id,
        auth_username=((row.get("auth") or {}).get("auth_username") or normalized_username),
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="Bearer"
    )


async def login_user_async(auth_username: str, password: str) -> UserResponse:
    """
    异步版登录：将数据库读操作放入线程池，避免阻塞事件循环。
    """
    # 归一化与强校验
    req = EmailLoginRequest(auth_username=auth_username, password=password)
    normalized_username = _normalize_username(req.auth_username)
    validated_password = _validate_password(req.password)

    # 解析 user_id
    pipeline = [
        {"$match": {"auth_username": normalized_username}},
        {"$lookup": {"from": "user_status", "localField": "user_id", "foreignField": "user_id", "as": "status"}},
        {"$unwind": "$status"},
        {"$project": {"user_id": 1, "auth_user_password": "$status.auth_user_password", "auth": "$status.auth"}}
    ]
    agg = await DatabaseOperations().a_aggregate("auth_login_index", pipeline)
    if not agg:
        raise InvalidCredentialsError("用户名或密码错误")
    row = agg[0]
    user_id = row.get("user_id")
    stored_hashed_password = row.get("auth_user_password")
    is_password_valid = await asyncio.get_event_loop().run_in_executor(
        _BCRYPT_EXECUTOR,
        _verify_password,
        validated_password,
        stored_hashed_password,
    )
    if not is_password_valid:
        raise InvalidCredentialsError("用户名或密码错误")

    tokens = await asyncio.to_thread(generate_token_pair, user_id, normalized_username)
    return UserResponse(
        user_id=user_id,
        auth_username=((row.get("auth") or {}).get("auth_username") or normalized_username),
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="Bearer"
    )


# ======== Envelope adapter (extracts payload.data) ========
def _get_envelope_data(envelope: Dict[str, Any]) -> Dict[str, Any]:
    payload = envelope.get("payload") or {}
    data = (payload.get("data") or {}) if isinstance(payload, dict) else {}
    return data


def handle_login_step(envelope: Dict[str, Any]) -> UserResponse:
    """
    Envelope handler for email+password login.
    Expects payload.data to contain {auth_username, password}.
    """
    data = _get_envelope_data(envelope)
    req = EmailLoginRequest(**data)
    result = login_user_sync(req.auth_username, req.password)

    # 记录登录历史（ip/ua 来源 meta，可选）
    meta = envelope.get("meta") or {}
    ip = meta.get("ip")
    ua = meta.get("user_agent")
    history_item = {
        "ts": Time.timestamp(),
        "ip": ip,
        "user_agent": ua,
        "success": True,
        "auth_username": result.auth_username,
        "provider": "emaillogin",
    }
    _db().update(
        "user_status",
        {"user_id": result.user_id},
        {"$setOnInsert": {"user_id": result.user_id}, "$push": {"login_history.history": history_item}},
    )

    return result


# ======== Step specifications (for module-local router) ========
EMAIL_LOGIN_STEP_SPECS = {
    "flow_id": "auth_login_flow",
    "name": "User email/password login flow",
    "description": "Single-step login using email (auth_username) and password",
    "modules": ["auth"],
    "steps": [
        {
            "step_id": "auth_login",
            "module": "auth",
            "handler": "cry_backend.tool_modules.auth.email_login.handle_login_step",
            "required_fields": ["payload"],
            "output_fields": ["user_id", "auth_username", "access_token", "refresh_token", "token_type"],
        }
    ],
}
