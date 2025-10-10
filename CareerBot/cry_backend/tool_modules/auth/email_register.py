from __future__ import annotations
from typing import Dict, Any, Optional, List
import time, random
from pydantic import BaseModel, field_validator, ConfigDict
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username, ensure_email, ensure_password_strength

from shared_utilities.mango_db.mongodb_connector import DatabaseOperations
from shared_utilities.time import Time
from shared_utilities.mail.verification_code import send_verification_email

# 本模块内置密码哈希（自包含，不依赖外部 hashing.py）
import bcrypt

def _hash_password(password: str) -> str:
    """
    使用 bcrypt 对密码进行不可逆哈希。
    - 输入: 明文密码字符串
    - 输出: 哈希后的字符串，持久化到 user_status.auth_user_password
    """
    pw_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode('utf-8')
from .tokens import generate_token_pair
from .exceptions import (
    InvalidInputError, UserAlreadyExistsError, EmailAlreadyRegisteredError
)

# ======== Pydantic models（email registration only）========

class EmailUserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str
    test_user: bool = False
    # UserRegisterRequest 定义注册字段
    # 用于单步注册/测试直通


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    auth_username: str
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    # UserResponse 定义注册成功返回结构（auth_username-first）


class EmailSendVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    test_user: bool = False
    # SendVerificationRequest 定义发送验证码入参


class EmailSendVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    message: str
    user_id: Optional[str] = None
    # SendVerificationResponse 定义发送验证码出参（结构化回传 user_id）


class EmailVerifyCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    auth_username: str = ""
    email: str
    code: str
    # VerifyCodeRequest 校验包含 user_id/email/code
    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")

    @field_validator("auth_username", mode="before")
    def _validate_auth_username(cls, value: str | None) -> str:
        return normalize_auth_username(value)



class EmailVerifyCodeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    message: str
    user_exists: bool
    is_oauth_user: bool
    # VerifyCodeResponse 返回用户存在与是否OAuth-only


class EmailSetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    auth_username: str = ""
    email: str
    password: str
    # SetPasswordRequest 设置密码入参（带 user_id）
    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")

    @field_validator("auth_username", mode="before")
    def _validate_auth_username(cls, value: str | None) -> str:
        return normalize_auth_username(value)



class EmailSetPasswordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    message: str
    user_id: Optional[str] = None
    # SetPasswordResponse 设置密码出参


# ======== Inline validators（replacing validators.py）========


def _validate_password(password: str) -> str:
    try:
        return ensure_password_strength(password, field_name="password")
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc
    # _validate_password(password) 验证密码长度


# ======== Normalizers ========

def _normalize_email(email: str) -> str:
    try:
        return ensure_email(email, field_name="email")
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc
    # _normalize_email(email) 统一处理


def _normalize_auth_username_value(auth_username: str) -> str:
    try:
        return normalize_auth_username(auth_username)
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc


# ======== DB helpers（user_id-first）========

def _db() -> DatabaseOperations:
    return DatabaseOperations()
    # _db() 返回数据库操作实例


def _ensure_user_status_doc(user_id: str, email: str) -> None:
    # 确保 user_status 文档存在，并写入 auth.auth_username 与 email 映射基础
    normalized_email = _normalize_email(email)
    _db().update(
        "user_status",
        {"user_id": user_id},
        {
            "$setOnInsert": {"user_id": user_id},
            "$set": {"auth.auth_username": normalized_email}
        },
    )
    # update("user_status", {user_id}, {...}) 保证文档存在


def _write_auth_login_index(auth_username: str, user_id: str) -> None:
    # 维护 auth_login_index 映射（auth_username -> user_id）
    normalized_auth_username = _normalize_auth_username_value(auth_username)
    existing = _db().find("auth_login_index", {"auth_username": normalized_auth_username}, {"user_id": 1, "_id": 0})
    if existing and existing[0].get("user_id") and existing[0]["user_id"] != user_id:
        # 已被其他 user_id 占用，属于冲突
        raise EmailAlreadyRegisteredError("邮箱已被绑定到其他账户")
    _db().update(
        "auth_login_index",
        {"auth_username": normalized_auth_username},
        {"$setOnInsert": {"auth_username": normalized_auth_username}, "$set": {"user_id": user_id}},
    )
    # update("auth_login_index", {auth_username}, {$set: {user_id}})


def resolve_user_id_by_auth_username(auth_username: str) -> Optional[str]:
    normalized_auth_username = _normalize_auth_username_value(auth_username)
    doc = _db().find("auth_login_index", {"auth_username": normalized_auth_username}, {"user_id": 1, "_id": 0})
    # find("auth_login_index", {auth_username}) 返回user_id
    if not doc:
        return None
    return doc[0].get("user_id")
    # 返回解析出的user_id


def create_user_for_oauth(email: str) -> str:
    """为OAuth首次登录创建用户（user_id-first）"""
    normalized_email = _normalize_email(email)
    user_id = Time.timestamp()
    dummy_password = _hash_password(__import__('secrets').token_urlsafe(32))
    _create_user_profile_and_status(user_id=user_id, primary_email=normalized_email, hashed_password=dummy_password)
    return user_id
    # 创建档案/状态/登录索引并返回user_id


def _get_user_by_id(user_id: str) -> dict:
    users = _db().find("user_profiles", {"user_id": user_id}, {"user_id": 1, "profile": 1, "_id": 0})
    return users[0] if users else {}
    # find("user_profiles", {user_id}) 返回用户画像


def _user_exists_by_id(user_id: str) -> bool:
    return bool(_get_user_by_id(user_id))
    # _user_exists_by_id(user_id) 判断画像是否已建立


def _check_user_is_oauth_only_by_id(user_id: str) -> bool:
    status = _db().find("user_status", {"user_id": user_id}, {"auth_user_password": 1, "_id": 0})
    if not status:
        return True
    hashed = status[0].get("auth_user_password", "")
    return not hashed or len(hashed) < 10
    # 无密码或异常视为OAuth-only


def _create_user_profile_and_status(user_id: str, primary_email: str, hashed_password: str) -> None:
    # 写入画像（profile.email 与未来扩展 email_1...）
    normalized_email = _normalize_email(primary_email)
    _db().insert("user_profiles", {"user_id": user_id, "profile": {"email": normalized_email}})
    # 写入/补齐状态（auth_user_password 与 auth.auth_username），首次用 upsert 避免重复键
    _db().update(
        "user_status",
        {"user_id": user_id},
        {"$setOnInsert": {"user_id": user_id}, "$set": {"auth_user_password": hashed_password, "auth.auth_username": normalized_email}}
    )
    # 写入登录索引
    _write_auth_login_index(normalized_email, user_id)
    # 插入画像/状态/索引，完成用户创建


def _set_user_password_by_user_id(user_id: str, hashed_password: str) -> None:
    _db().update("user_status", {"user_id": user_id}, {"auth_user_password": hashed_password})
    # update("user_status", {user_id}, {auth__user_password}) 更新状态密码


# ======== Module-scoped creator for email registration ========
def email_register_create_user(auth_username: str, primary_email: str, hashed_password: str) -> str:
    """
    email_register_create_user 创建用户（邮箱注册专用）。

    - 生成 user_id
    - 插入 user_profiles 与 user_status
    - 写入 auth_login_index(auth_username -> user_id)
    返回 user_id
    """
    normalized_email = _normalize_email(primary_email)
    # _normalize_email(primary_email) 归一化邮箱
    user_id = Time.timestamp()
    # Time.timestamp() 生成全局唯一 user_id
    _create_user_profile_and_status(user_id=user_id, primary_email=normalized_email, hashed_password=hashed_password)
    # _create_user_profile_and_status(...) 写入画像/状态并建立索引
    return user_id
    # 返回创建好的 user_id


# ======== OAuth linking helper（migrated from repository.py）========
def link_oauth_to_existing_email(email: str, provider: str, oauth_id: str) -> None:
    """
    将OAuth账户绑定到现有邮箱用户（user_id-first）。

    行为：
    - 通过邮箱在 user_profiles 中解析 user_id
    - 在 user_status 中写入 oauth_{provider}_id 字段（带归档）
    - 邮箱不存在时抛出 ValueError
    """
    normalized_email = _normalize_email(email)
    # _normalize_email(email) 入参邮箱归一化

    users = _db().find("user_profiles", {"profile.email": normalized_email}, {"user_id": 1, "_id": 0})
    # find("user_profiles", {profile.email}, {user_id}) 解析 user_id
    if not users:
        raise ValueError(f"邮箱 {email} 不存在，无法绑定OAuth账户")
    # 邮箱不存在 → 抛出错误

    user_id = users[0]["user_id"]
    # 取回 user_id 作为后续更新键

    oauth_field = f"oauth_{provider}_id"
    # 计算需要更新的字段名 oauth_provider_id

    update_doc = {oauth_field: oauth_id}
    # 组装更新字典 {oauth_xxx_id: oauth_id}

    result = _db().update("user_status", {"user_id": user_id}, update_doc)
    # update("user_status", {user_id}, update_doc) 带归档更新
    if hasattr(result, "matched_count") and result.matched_count == 0:
        raise ValueError(f"用户 {user_id} OAuth绑定更新失败")
    # 若未匹配到文档，抛出错误（保持与旧实现一致）

# ======== Verification history（persisted under user_status by user_id）========

def _push_verification_history(user_id: str, email: str, code: str, created_ts: float, is_test_user: bool) -> None:
    _ensure_user_status_doc(user_id, email)
    normalized_email = _normalize_email(email)
    _db().update(
        "user_status",
        {"user_id": user_id},
        {"$push": {"email_verification.history": {"email": normalized_email, "code": code, "created_at": created_ts, "used": False, "test_user": is_test_user}}},
    )
    # 将验证码历史追加到 user_status.email_verification.history 数组


def _find_latest_verification(user_id: str) -> Optional[dict]:
    docs = _db().find("user_status", {"user_id": user_id}, {"email_verification": 1, "_id": 0})
    if not docs:
        return None
    history: List[dict] = (docs[0].get("email_verification", {}) or {}).get("history", [])
    return history[-1] if history else None
    # 读取最近一次验证码记录


# 内部工具：按邮箱查找 user_status（支持未注册用户）
def _get_user_status_by_email(email: str) -> Optional[dict]:
    normalized_email = _normalize_email(email)
    # _normalize_email(email) 将邮箱转小写去空格
    docs = _db().find(
        "user_status",
        {"auth.auth_username": normalized_email},
        {"user_id": 1, "email_verification": 1, "_id": 0},
    )
    # _db().find('user_status', {auth.auth_username}, {fields}) 查询状态
    return docs[0] if docs else None
    # 返回首条文档，含 user_id 与 email_verification


def _mark_verification_used(user_id: str, code: str) -> None:
    _db().update(
        "user_status",
        {"user_id": user_id, "email_verification.history.code": code},
        {"$set": {"email_verification.history.$.used": True}},
    )
    # 标记验证码已使用


# ======== Domain functions（used by services and flows）========

async def send_verification_code_to_email(request: EmailSendVerificationRequest) -> EmailSendVerificationResponse:
    email = _normalize_email(request.email)
    test_user = request.test_user
    # 校验邮箱格式

    # 优先复用已存在邮箱的 user_id；否则从状态中查找；仍无则分配
    existing_user_id = resolve_user_id_by_auth_username(email)
    # resolve_user_id_by_auth_username(email) 登录索引查 user_id
    if not existing_user_id:
        status_doc = _get_user_status_by_email(email)
        # _get_user_status_by_email(email) 状态集合查 user_id
        existing_user_id = (status_doc or {}).get("user_id")
        # 从状态文档取出 user_id（可能为 None）
    user_id = existing_user_id or Time.timestamp()
    # Time.timestamp() 生成新 user_id 作为顶层键（在 time.py 中保证唯一）

    # 生成验证码：测试用户固定 123456，否则随机 6 位
    code = "123456" if test_user else "".join(str(random.randint(0, 9)) for _ in range(6))
    created_ts = time.time()
    # time.time() 生成当前秒级时间戳

    # 发送速率限制：同一 user_id 30 秒内仅可生成一次
    latest = _find_latest_verification(user_id)
    # _find_latest_verification(user_id) 获取最近验证码
    if latest and (created_ts - float(latest.get("created_at", 0)) < 30):
        # 与上次创建间隔不足 30 秒，拒绝
        return EmailSendVerificationResponse(success=False, message="请求过于频繁，请在30秒后重试", user_id=user_id)
        # 返回失败并附带 user_id 供前端沿用

    _push_verification_history(user_id=user_id, email=email, code=code, created_ts=created_ts, is_test_user=test_user)
    # 写入验证码历史（user_status），确保 user_status 文档存在

    ok = await send_verification_email(to=email, code=code, is_test_user=test_user)
    # 发送邮件验证码
    if ok:
        msg = "测试验证码已发送：123456" if test_user else "验证码已发送到您的邮箱"
        return EmailSendVerificationResponse(success=True, message=msg, user_id=user_id)
        # 返回消息中附带 user_id，供前端携带进入下一步
    else:
        return EmailSendVerificationResponse(success=False, message="验证码发送失败，请稍后重试")
    # 返回发送结果


def verify_email_code(request: EmailVerifyCodeRequest) -> EmailVerifyCodeResponse:
    user_id = request.user_id
    email = _normalize_email(request.email)
    code = request.code
    # 校验邮箱格式

    # 检查错误尝试锁定状态：5次错误锁定5分钟
    status_docs = _db().find("user_status", {"user_id": user_id}, {"email_verification": 1, "_id": 0})
    # _db().find('user_status', {user_id}, {email_verification}) 读取状态文档
    email_verif = (status_docs[0].get("email_verification", {}) if status_docs else {}) or {}
    # 取出 email_verification 对象
    failed_attempts = (email_verif.get("failed_attempts") or {})
    # 取出 failed_attempts 结构（count/lock_until）
    lock_until = float(failed_attempts.get("lock_until") or 0)
    # 读取锁定截止时间戳（秒）
    now_ts = time.time()
    # 当前秒级时间戳
    if lock_until and now_ts < lock_until:
        # 仍在锁定窗口，拒绝校验
        return EmailVerifyCodeResponse(success=False, message="尝试过多，请稍后再试", user_exists=False, is_oauth_user=False)
        # 提示 5 分钟后再尝试

    latest = _find_latest_verification(user_id)
    # 读取最近验证码记录
    if not latest or latest.get("used"):
        return EmailVerifyCodeResponse(success=False, message="验证码无效", user_exists=False, is_oauth_user=False)

    if latest.get("email") != email:
        return EmailVerifyCodeResponse(success=False, message="邮箱不匹配", user_exists=False, is_oauth_user=False)
    # 校验邮箱匹配

    if time.time() - float(latest["created_at"]) > 300:
        return EmailVerifyCodeResponse(success=False, message="验证码已过期", user_exists=False, is_oauth_user=False)
    # 过期校验 5 分钟

    if latest["code"] != code:
        # 记录错误次数，达5次锁定5分钟
        current_count = int((failed_attempts.get("count") or 0)) + 1
        # 错误计数 +1
        update_doc = {"$set": {"email_verification.failed_attempts.count": current_count}}
        # 组装更新文档：写入最新错误次数
        if current_count >= 5:
            update_doc["$set"]["email_verification.failed_attempts.lock_until"] = now_ts + 300
            # 达到阈值：设置锁定截止时间 now+300 秒
        _db().update("user_status", {"user_id": user_id}, update_doc)
        # _db().update('user_status', {user_id}, update_doc) 写入 DB
        return EmailVerifyCodeResponse(success=False, message="验证码错误", user_exists=False, is_oauth_user=False)
    # 比对验证码

    _mark_verification_used(user_id, code)
    # 标记为已使用

    # 成功后清理失败状态（计数与锁定）
    _db().update(
        "user_status",
        {"user_id": user_id},
        {"$set": {"email_verification.failed_attempts.count": 0, "email_verification.failed_attempts.lock_until": 0}},
    )
    # _db().update('user_status', {user_id}, {$set:{count:0, lock_until:0}})

    user_exists = _user_exists_by_id(user_id)
    if not user_exists:
        return EmailVerifyCodeResponse(success=True, message="邮箱验证成功，您可以设置密码完成注册", user_exists=False, is_oauth_user=False)
    is_oauth_only = _check_user_is_oauth_only_by_id(user_id)
    if is_oauth_only:
        return EmailVerifyCodeResponse(success=True, message="您已通过第三方登录，请设置密码启用邮箱登录", user_exists=True, is_oauth_user=True)
    else:
        return EmailVerifyCodeResponse(success=True, message="邮箱验证成功，账户已完整注册", user_exists=True, is_oauth_user=False)
    # 返回校验结果


def set_user_password_after_verification(request: EmailSetPasswordRequest) -> EmailSetPasswordResponse:
    user_id = request.user_id
    email = _normalize_email(request.email)
    password = request.password
    password = _validate_password(password)
    # 字段校验

    hashed = _hash_password(password)
    # 计算密码哈希

    exists = _user_exists_by_id(user_id)
    if not exists:
        _create_user_profile_and_status(user_id=user_id, primary_email=email, hashed_password=hashed)
        # 创建画像/状态/登录索引
        return EmailSetPasswordResponse(success=True, message="注册成功！您可以使用邮箱和密码登录", user_id=user_id)

    # 已存在用户：仅允许 OAuth-only 在注册流程中补齐密码
    if _check_user_is_oauth_only_by_id(user_id):
        _set_user_password_by_user_id(user_id, hashed)
        return EmailSetPasswordResponse(success=True, message="密码设置成功！现在您可以使用邮箱密码登录", user_id=user_id)

    # 已存在且已设置密码的用户修改密码应走 reset_password 流程
    raise EmailAlreadyRegisteredError("邮箱已存在且已设置密码，请使用忘记密码重置")


def register_user(request: EmailUserRegisterRequest) -> UserResponse:
    email = _normalize_email(request.email); password = request.password; test_user = request.test_user
    auth_username = email  # 初始登录名等于注册邮箱（后续可独立变更）
    password = _validate_password(password)
    # 字段校验

    if not test_user:
        raise InvalidInputError("请先通过验证码验证流程完成注册")
    # 非测试模式禁止单步注册

    # 寻找该邮箱是否已绑定 user_id
    existing_user_id = resolve_user_id_by_auth_username(email)
    hashed = _hash_password(password)
    if existing_user_id:
        # 已存在：允许 OAuth-only 用户补齐密码；否则视为已注册
        if _check_user_is_oauth_only_by_id(existing_user_id):
            _set_user_password_by_user_id(existing_user_id, hashed)
            user_id = existing_user_id
        else:
            raise UserAlreadyExistsError("邮箱已存在")
    else:
        # 不存在：创建新用户
        user_id = Time.timestamp()
        _create_user_profile_and_status(user_id=user_id, primary_email=email, hashed_password=hashed)
    # 根据存在性与OAuth-only决定创建或补齐

    # 使用 auth_username 生成令牌（与 email 解耦，不使用 profile）
    token_pair = generate_token_pair(user_id, auth_username)
    # 生成令牌对

    return UserResponse(
        user_id=user_id,
        auth_username=auth_username,
        access_token=token_pair["access_token"],
        refresh_token=token_pair["refresh_token"],
    )
    # 返回注册成功响应


# ======== Envelope 适配器（从顶层嵌套结构提取 data）========

def _get_envelope_data(envelope: Dict[str, Any]) -> Dict[str, Any]:
    payload = envelope.get("payload") or {}
    # envelope.get('payload') 取出嵌套 payload
    data = (payload.get("data") or {}) if isinstance(payload, dict) else {}
    # payload.get('data') 取出 data 字典
    return data
    # 返回 data 作为领域模型入参


def handle_register_step1(envelope: Dict[str, Any]):
    data = _get_envelope_data(envelope)
    # _get_envelope_data(envelope) 取出 data
    req = EmailSendVerificationRequest(**data)
    # EmailSendVerificationRequest(**data) 构造请求对象
    return send_verification_code_to_email(req)
    # 调用发送验证码并返回响应协程/结果


def handle_register_step2(envelope: Dict[str, Any]):
    data = dict(_get_envelope_data(envelope))
    # 拷贝 data，避免原始对象被修改
    user = envelope.get("user") or {}
    # envelope.get('user') 取出顶层用户节点
    if isinstance(user, dict) and user.get("id"):
        data["user_id"] = user.get("id")
        # 将顶层 user.id 写回 data['user_id']
    req = EmailVerifyCodeRequest(**data)
    # EmailVerifyCodeRequest(**data) 构造请求对象
    return verify_email_code(req)
    # 调用验证码校验并返回结果


def handle_register_step3(envelope: Dict[str, Any]):
    data = dict(_get_envelope_data(envelope))
    # 拷贝 data，避免原始对象被修改
    user = envelope.get("user") or {}
    # envelope.get('user') 取出顶层用户节点
    if isinstance(user, dict) and user.get("id"):
        data["user_id"] = user.get("id")
        # 将顶层 user.id 写回 data['user_id']
    req = EmailSetPasswordRequest(**data)
    # EmailSetPasswordRequest(**data) 构造请求对象
    return set_user_password_after_verification(req)
    # 调用设置密码并返回结果


def handle_single_step_register(envelope: Dict[str, Any]):
    data = _get_envelope_data(envelope)
    # _get_envelope_data(envelope) 取出 data
    req = EmailUserRegisterRequest(**data)
    # EmailUserRegisterRequest(**data) 构造请求对象
    return register_user(req)
    # 调用单步注册并返回结果


# ======== Step 规范描述（供 router 读取）========
EMAIL_REGISTER_STEP_SPECS = {
    "flow_id": "user_registration",
    "name": "User email verification registration flow",
    "description": "Complete flow to register user via email verification code (user_id-first)",
    "modules": ["auth"],
    "steps": [
        {
            "step_id": "register_step1",
            "module": "auth",
            "handler": "cry_backend.tool_modules.auth.email_register.handle_register_step1",
            "required_fields": ["payload"],
            "output_fields": ["success", "message", "user_id"],
            "next_step": "register_step2"
        },
        {
            "step_id": "register_step2",
            "module": "auth",
            "handler": "cry_backend.tool_modules.auth.email_register.handle_register_step2",
            "required_fields": ["payload"],
            "output_fields": ["success", "message", "user_exists", "is_oauth_user"],
            "previous_step": "register_step1",
            "next_step": "register_step3"
        },
        {
            "step_id": "register_step3",
            "module": "auth",
            "handler": "cry_backend.tool_modules.auth.email_register.handle_register_step3",
            "required_fields": ["payload"],
            "output_fields": ["success", "message", "user_id"],
            "previous_step": "register_step2"
        }
    ]
}


