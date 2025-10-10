# 登录令牌生成模块
# 使用 JWT 生成和管理用户登录后的访问令牌（支持会话/轮换/保活）

import os
import jwt
from datetime import timedelta
from typing import Dict, Any, Optional

from pymongo.errors import PyMongoError
from shared_utilities.time import Time
from shared_utilities.mango_db.mongodb_connector import DatabaseOperations
from .exceptions import DependencyError


REFRESH_TTL_DAYS_DEFAULT = 7
ACCESS_TTL_MIN_DEFAULT = 15
SESSION_MAX_AGE_DAYS_DEFAULT = 30


def _get_current_token_epoch() -> int:
    """Read current token epoch from DB (system-wide revocation version)."""
    try:
        db = DatabaseOperations().db
        doc = db["system_settings"].find_one({"_id": "auth"})
    except PyMongoError as exc:
        raise DependencyError("Failed to read auth token epoch") from exc

    if isinstance(doc, dict):
        return int(doc.get("token_epoch", 0))
    return 0
# _get_current_token_epoch()
# 无参函数，读取系统级撤销版本号
# 返回 int 值，低于该值的 token 视为已撤销


def _secret() -> str:
    return os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
# _secret()
# 无参函数，读取 JWT 密钥字符串
# 返回密钥，用于 jwt.encode/jwt.decode


def _sessions_col():
    return DatabaseOperations().db["auth_sessions"]
# _sessions_col()
# 无参函数，返回会话集合对象
# 供后续 create/revoke/refresh 操作使用


def _new_id() -> str:
    return Time.timestamp()
# _new_id()
# 无参函数，生成随机 jti/sid
# 返回 32位十六进制字符串


def create_session(user_id: str, ua: Optional[str] = None, ip: Optional[str] = None) -> Dict[str, Any]:
    now = Time.now()
    sid = _new_id()
    refresh_jti = _new_id()
    rot = 0
    max_age_at = now + timedelta(days=SESSION_MAX_AGE_DAYS_DEFAULT)
    doc = {
        "sid": sid,
        "user_id": user_id,
        "refresh_jti": refresh_jti,
        "rot": rot,
        "revoked": False,
        "created_at": now.timestamp(),
        "last_activity_at": now.timestamp(),
        "max_age_at": max_age_at.timestamp(),
        "ua": ua or "",
        "ip": ip or "",
    }
    res = _sessions_col().insert_one(doc)
    if not getattr(res, "acknowledged", False):
        raise ValueError("Failed to create session")
    return doc
# create_session(user_id, ua, ip)
# 写入会话文档，生成 sid/refresh_jti 等
# 返回会话文档，供 token_pair 生成使用


def revoke_session(sid: str) -> bool:
    res = _sessions_col().update_one({"sid": sid}, {"$set": {"revoked": True}})
    # 仅当找到对应会话文档时返回 True；已撤销但匹配到文档也视为 True（幂等）
    return bool(getattr(res, "acknowledged", False) and getattr(res, "matched_count", 0) >= 1)
# revoke_session(sid)
# 将会话标记为撤销
# 返回布尔值表示更新是否成功


def revoke_all_sessions(user_id: str) -> int:
    res = _sessions_col().update_many({"user_id": user_id}, {"$set": {"revoked": True}})
    return int(getattr(res, "modified_count", 0) or 0)
# revoke_all_sessions(user_id)
# 撤销该用户所有会话
# 返回修改的会话数量


def _ensure_session_for_refresh(sid: str) -> Dict[str, Any]:
    sess = _sessions_col().find_one({"sid": sid})
    if not sess:
        raise ValueError("Session not found")
    if bool(sess.get("revoked")):
        raise ValueError("Session revoked")
    now_ts = Time.now().timestamp()
    if now_ts > float(sess.get("max_age_at", 0.0)):
        raise ValueError("Session over max age")
    return sess
# _ensure_session_for_refresh(sid)
# 读取并校验会话合法性（存在/未撤销/未超龄）
# 返回会话文档，非法抛出 ValueError


def _touch_activity(sid: str) -> None:
    _sessions_col().update_one({"sid": sid}, {"$set": {"last_activity_at": Time.now().timestamp()}})
# _touch_activity(sid)
# 更新会话活跃时间戳
# 无返回，用于滑动保活统计


def _encode(payload: Dict[str, Any]) -> str:
    return jwt.encode(payload, _secret(), algorithm="HS256")
# _encode(payload)
# 使用 HS256 对载荷进行签名
# 返回 JWT 字符串


def _decode(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
# _decode(token)
# 解码并校验签名/有效期
# 返回载荷或抛出 ValueError


def generate_access_token(user_id: str, auth_username: str, sid: str, expires_minutes: int = ACCESS_TTL_MIN_DEFAULT) -> str:
    now = Time.now()
    exp = now + timedelta(minutes=expires_minutes)
    to_encode = {
        "user_id": user_id,
        "auth_username": auth_username,
        "sid": sid,
        "jti": _new_id(),
        "type": "access_token",
        "iat": now.timestamp(),
        "exp": exp.timestamp(),
        "token_epoch": _get_current_token_epoch(),
    }
    return _encode(to_encode)
# generate_access_token(user_id, auth_username, sid, expires_minutes)
# 构造访问令牌载荷并签名
# 返回 access_token 字符串


def generate_refresh_token(user_id: str, auth_username: str, sid: str, refresh_jti: str, rot: int, expires_days: int = REFRESH_TTL_DAYS_DEFAULT, max_age_at: Optional[float] = None) -> str:
    now = Time.now()
    exp = now + timedelta(days=expires_days)
    to_encode = {
        "user_id": user_id,
        "auth_username": auth_username,
        "sid": sid,
        "jti": refresh_jti,
        "rot": rot,
        "type": "refresh_token",
        "iat": now.timestamp(),
        "exp": exp.timestamp(),
        "max_age_at": max_age_at,
        "token_epoch": _get_current_token_epoch(),
    }
    return _encode(to_encode)
# generate_refresh_token(user_id, auth_username, sid, refresh_jti, rot, expires_days, max_age_at)
# 构造刷新令牌载荷并签名
# 返回 refresh_token 字符串


def generate_token_pair(user_id: str, auth_username: str, ua: Optional[str] = None, ip: Optional[str] = None) -> Dict[str, str]:
    sess = create_session(user_id, ua, ip)
    sid = sess["sid"]
    access_token = generate_access_token(user_id, auth_username, sid)
    refresh_token = generate_refresh_token(user_id, auth_username, sid, sess["refresh_jti"], sess["rot"], max_age_at=sess["max_age_at"])
    return {"access_token": access_token, "refresh_token": refresh_token}
# generate_token_pair(user_id, auth_username, ua, ip)
# 创建会话并签发 access/refresh 令牌
# 返回包含两个令牌的字典


def verify_access_token(token: str) -> Dict[str, Any]:
    payload = _decode(token)
    if payload.get("type") != "access_token":
        raise ValueError("Token is not an access token")
    if int(payload.get("token_epoch", 0)) < _get_current_token_epoch():
        raise ValueError("Token revoked")
    sid = payload.get("sid")
    if sid:
        sess = _sessions_col().find_one({"sid": sid}, {"revoked": 1})
        if sess and bool(sess.get("revoked")):
            raise ValueError("Session revoked")
    return payload
# verify_access_token(token)
# 解码并校验类型/epoch/会话撤销
# 返回载荷字典，非法抛出 ValueError


def refresh_access_token(refresh_token: str) -> Dict[str, str]:
    payload = _decode(refresh_token)
    if payload.get("type") != "refresh_token":
        raise ValueError("Token is not a refresh token")
    if int(payload.get("token_epoch", 0)) < _get_current_token_epoch():
        raise ValueError("Token revoked")

    sid = payload.get("sid")
    jti = payload.get("jti")
    rot = int(payload.get("rot", 0))
    user_id = payload.get("user_id")
    auth_username = payload.get("auth_username")

    sess = _ensure_session_for_refresh(sid)
    if jti != sess.get("refresh_jti"):
        revoke_session(sid)
        raise ValueError("Refresh token reuse detected")

    new_refresh_jti = _new_id()
    new_rot = rot + 1
    _sessions_col().update_one({"sid": sid}, {"$set": {"refresh_jti": new_refresh_jti, "rot": new_rot}})

    _touch_activity(sid)

    new_access = generate_access_token(user_id, auth_username, sid)
    new_refresh = generate_refresh_token(user_id, auth_username, sid, new_refresh_jti, new_rot, max_age_at=sess.get("max_age_at"))
    return {"access_token": new_access, "refresh_token": new_refresh}
# refresh_access_token(refresh_token)
# 校验 refresh 类型与 epoch，检测 jti 复用，轮换 jti/rot，更新活跃时间
# 返回新的 access/refresh 令牌对








