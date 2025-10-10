from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

import bcrypt
from pydantic import BaseModel, ConfigDict, ValidationError
from pymongo.errors import PyMongoError

from shared_utilities.mail.SendMail import send_email
from shared_utilities.mail.verification_code import get_test_verification_code
from shared_utilities.mango_db.mongodb_connector import DatabaseOperations
from shared_utilities.response import create_error_response, create_success_response
from shared_utilities.validator import ensure_password_strength, normalize_auth_username

DEPENDENCY_ERRORS: tuple[type[BaseException], ...] = (OSError, RuntimeError, ValueError)
try:
    from aiosmtplib.errors import SMTPException  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    SMTPException = None  # type: ignore[assignment]
else:
    DEPENDENCY_ERRORS = DEPENDENCY_ERRORS + (SMTPException,)


from .exceptions import DependencyError, InvalidInputError


def _hash_password(password: str) -> str:
    """Hash password using bcrypt with a generated salt."""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")


# ======== Inline validators（replacing validators.py）========

# 内联校验函数（替代 validators 与 email_verification 依赖）

def _normalize_auth_username(auth_username: str) -> str:

    try:

        return normalize_auth_username(auth_username)

    except ValueError as exc:

        raise InvalidInputError(str(exc)) from exc



def _validate_password(password: str) -> str:

    try:

        return ensure_password_strength(password, field_name="password")

    except ValueError as exc:

        raise InvalidInputError(str(exc)) from exc



def _db() -> DatabaseOperations:

    return DatabaseOperations()



def _check_user_exists_by_auth_username(auth_username: str) -> bool:

    # 通过 auth_login_index 解析 user_id，再确认 user_profiles 是否存在

    normalized = _normalize_auth_username(auth_username)

    idx = _db().find("auth_login_index", {"auth_username": normalized}, {"user_id": 1, "_id": 0})

    if not idx:

        return False

    uid = idx[0]["user_id"]

    prof = _db().find("user_profiles", {"user_id": uid}, {"_id": 1})

    return bool(prof)



# 密码重置验证码缓存存储

# 使用内存字典模拟缓存，键为邮箱，值为 (验证码, 时间戳) 元组

# 与注册验证码分离，避免混淆

_reset_codes: Dict[str, Tuple[str, float]] = {}

# _reset_codes[user_id] = (code, created_at)



# 每用户发送频控：30秒内仅可发送一次

_last_send_ts: Dict[str, float] = {}

# _last_send_ts[user_id] = last_sent_ts



# 错误尝试锁定：5次错误锁定5分钟

_failed_attempts: Dict[str, Tuple[int, float]] = {}

# _failed_attempts[user_id] = (count, lock_until_ts)



# 密码重置验证码有效期（秒）

RESET_CODE_EXPIRY = 300  # 5分钟（全站统一）





# ======== Pydantic models（reset password only）========



class ResetSendCodeRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    auth_username: str

    test_user: bool = False

    # ResetSendCodeRequest(**{auth_username,test_user})





class ResetSendCodeResponse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    success: bool

    message: str

    user_id: Optional[str] = None

    code: Optional[str] = None

    # ResetSendCodeResponse 返回结构（结构化 user_id）





class ResetPasswordRequestModel(BaseModel):

    model_config = ConfigDict(extra="forbid")

    auth_username: str

    code: str

    new_password: str

    confirm_new_password: str

    # ResetPasswordRequestModel(**{auth_username,code,new_password,confirm_new_password})





class ResetPasswordResponse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    success: bool

    message: str

    # ResetPasswordResponse 返回结构





async def send_reset_code(auth_username: str, is_test_user: bool = False) -> bool:

    """

    normalized_auth_username = _normalize_auth_username(auth_username)

    发送密码重置验证码



    生成6位数字验证码，组织邮件正文，

    通过 send_email 发送或直接返回（测试）。

    将验证码与时间戳写入缓存。

    测试用户与直接返回为不同用途：

    - 测试用户: 前端人工测试无邮箱时使用

    - 直接返回: 自动化脚本直取真实验证码



    参数:

        auth_username: 登录名（通常为邮箱）

        is_test_user: 测试用户标识，为True时生成固定验证码，默认False



    返回:

        bool: 发送成功返回True，否则返回False

    """

    normalized_auth_username = _normalize_auth_username(auth_username)

    # _check_user_exists_by_auth_username(normalized_auth_username)

    # 若索引或画像不存在，直接返回 False

    if not _check_user_exists_by_auth_username(normalized_auth_username):

        return False

    

    # 生成验证码（两种路径）：

    # True: 直接返回随机验证码，跳过发信

    # False: 生成随机验证码并发送邮件

    if is_test_user is True:

        # get_test_verification_code() → code

        # 用于自动化测试直接取用

        code = get_test_verification_code()

    else:

        # ''.join(randint) 生成6位数字验证码 → code

        code = ''.join(str(__import__('random').randint(0,9)) for _ in range(6))



    # current_time = time.time() 生成秒级时间戳

    current_time = time.time()



    # 解析 user_id 与邮箱，用于缓存与发信

    idx = _db().find("auth_login_index", {"auth_username": normalized_auth_username}, {"user_id": 1, "_id": 0})

    user_id = idx[0]["user_id"]

    prof = _db().find("user_profiles", {"user_id": user_id}, {"profile": 1, "_id": 0})

    target_email = (prof[0].get("profile") or {}).get("email") if prof else None

    if not target_email:

        return False



    # 发送速率限制：同一 user_id 30 秒内仅可发送一次（读DB最近一条历史）

    docs = _db().find("user_status", {"user_id": user_id}, {"email_verification": 1, "_id": 0})

    history = ((docs[0].get("email_verification") or {}).get("history") or []) if docs else []

    last = history[-1] if history else None

    if (not is_test_user) and last and (current_time - float(last.get("created_at") or 0)) < 30:

        return False

    # 将验证码写入 user_status.email_verification.history

    _db().update(

        "user_status",

        {"user_id": user_id},

        {

            "$setOnInsert": {"user_id": user_id},

            "$push": {

                "email_verification.history": {

                    "email": target_email,

                    "code": code,

                    "created_at": current_time,

                    "used": False,

                    "test_user": bool(is_test_user)

                }

            }

        }

    )



    # 组装邮件主题与正文（生产）

    subject = "Password reset code - reset your account password"

    if is_test_user:

        body = (

            f"Your password reset code is: {code}\n"

            "This is a test reset code. The code is valid for 5 minutes.\n"

            "Note: This is development test mode.\n"

            "If you did not request a password reset, please ignore this email."

        )

    else:

        body = (

            f"Your password reset code is: {code}\n"

            "The code is valid for 5 minutes. Please use it promptly."

        )



    try:

        if is_test_user:

            return True

        # 发送邮件改为异步线程池封装，避免阻塞事件循环

        return await asyncio.to_thread(send_email, target_email, subject, body, "plain")

    except DEPENDENCY_ERRORS as exc:

        raise DependencyError("Failed to dispatch password reset code") from exc







def verify_reset_code(auth_username: str, code: str) -> bool:

    """

    验证密码重置验证码



    从密码重置缓存中获取存储的验证码，检查验证码是否正确且未过期。

    验证成功后保留验证码，供后续重置密码步骤使用。



    参数:

        auth_username: 登录名（通常为邮箱）

        code: 用户输入的验证码字符串



    返回:

        bool: 验证成功返回True，否则返回False

    """

    normalized_auth_username = _normalize_auth_username(auth_username)

    # 检查邮箱是否在密码重置验证码缓存中

    idx = _db().find("auth_login_index", {"auth_username": normalized_auth_username}, {"user_id": 1, "_id": 0})

    if not idx:

        return False

    user_id = idx[0]["user_id"]



    # 读取失败计数与锁定窗口（DB）

    doc = _db().find("user_status", {"user_id": user_id}, {"email_verification": 1, "_id": 0})

    email_verif = (doc[0].get("email_verification", {}) if doc else {}) or {}

    failed = (email_verif.get("failed_attempts") or {})

    lock_until = float(failed.get("lock_until") or 0)

    now = time.time()

    if lock_until and now < lock_until:

        return False



    history = (email_verif.get("history") or [])

    latest = history[-1] if history else None

    if not latest or latest.get("used"):

        return False

    if now - float(latest.get("created_at") or 0) > RESET_CODE_EXPIRY:

        return False

    if str(code) != str(latest.get("code") or ""):

        new_count = int(failed.get("count") or 0) + 1

        update_doc = {"$set": {"email_verification.failed_attempts.count": new_count}}

        if new_count >= 5:

            update_doc["$set"]["email_verification.failed_attempts.lock_until"] = now + 300

        _db().update("user_status", {"user_id": user_id}, update_doc)

        return False



    # 成功：标记 used=true，清零失败计数

    _db().update(

        "user_status",

        {"user_id": user_id, "email_verification.history.code": str(code)},

        {"$set": {"email_verification.history.$.used": True, "email_verification.failed_attempts.count": 0, "email_verification.failed_attempts.lock_until": 0}}

    )

    return True





def reset_password(auth_username: str, code: str, new_password: str) -> bool:

    """

    重置用户密码



    一次性验证重置验证码并更新用户密码。

    验证成功后从缓存中清除验证码，完成密码重置流程。



    参数:

        auth_username: 登录名（通常为邮箱）

        code: 验证码字符串

        new_password: 新密码字符串



    返回:

        bool: 重置成功返回True，否则返回False



    异常:

        InvalidInputError: 邮箱格式或密码格式不正确

    """

    normalized_auth_username = _normalize_auth_username(auth_username)

    

    # 调用 validate_password 函数验证新密码格式

    new_password = _validate_password(new_password)



    # 注意：验证码已在 verify_reset_code 中验证并置为 used，这里仅执行密码更新

    idx = _db().find("auth_login_index", {"auth_username": normalized_auth_username}, {"user_id": 1, "_id": 0})

    if not idx:

        return False

    user_id = idx[0]["user_id"]

    # 调用 hash_password 函数对新密码进行加密处理

    # 传入原始新密码字符串，得到加密后的密码哈希

    # 结果赋值给 hashed_new_password 变量

    hashed_new_password = _hash_password(new_password)



    try:

        _db().update("user_status", {"user_id": user_id}, {"$set": {"auth_user_password": hashed_new_password}})

    except PyMongoError as exc:

        raise DependencyError("Failed to update user password") from exc

    return True





def cleanup_expired_reset_codes() -> None:

    """

    清理过期的密码重置验证码



    基于DB的过期清理可由后台任务实现；

    当前校验流程已按时间戳判定，无需额外操作。

    """

    # 获取当前时间戳

    current_time = time.time()



    # 创建需要删除的邮箱列表

    expired_users = []



    # 遍历密码重置验证码缓存字典

    for uid, (code, timestamp) in _reset_codes.items():

        # 检查验证码是否过期

        if current_time - timestamp > RESET_CODE_EXPIRY:

            expired_users.append(uid)



    # 从缓存中移除所有过期的验证码

    for uid in expired_users:

        del _reset_codes[uid]





# ======== Envelope 适配器（从嵌套结构提取 data）========



def _get_envelope_data(envelope: Dict[str, Any]) -> Dict[str, Any]:

    if not isinstance(envelope, dict):

        raise InvalidInputError("Envelope must be an object")



    user_section = envelope.get("user")

    if not isinstance(user_section, dict):

        raise InvalidInputError("Envelope.user must be an object")



    meta_section = envelope.get("meta")

    if not isinstance(meta_section, dict):

        raise InvalidInputError("Envelope.meta must be an object")



    payload = envelope.get("payload")

    if not isinstance(payload, dict):

        raise InvalidInputError("Envelope.payload must be an object")



    data = payload.get("data")

    if not isinstance(data, dict):

        raise InvalidInputError("Envelope.payload.data must be an object")

    return data





async def handle_reset_step1(envelope: Dict[str, Any]) -> Dict[str, Any]:

    try:

        data = _get_envelope_data(envelope)

    except InvalidInputError as exc:

        return create_error_response(str(exc), error_type="INVALID_INPUT")



    try:

        req = ResetSendCodeRequest.model_validate(data)

    except ValidationError as exc:

        return create_error_response(

            "Invalid payload for reset_step1",

            error_type="INVALID_INPUT",

            details={"errors": exc.errors()},

        )



    try:

        normalized_username = _normalize_auth_username(req.auth_username)

    except InvalidInputError as exc:

        return create_error_response(str(exc), error_type="INVALID_INPUT")



    try:

        send_success = await send_reset_code(normalized_username, is_test_user=req.test_user)

    except DependencyError as exc:

        return create_error_response(str(exc), error_type="DEPENDENCY_ERROR")



    if not send_success:

        return create_error_response(

            "Unable to send password reset code",

            error_type="INVALID_INPUT",

        )



    idx = _db().find(

        "auth_login_index",

        {"auth_username": normalized_username},

        {"user_id": 1, "_id": 0},

    )

    user_id = idx[0]["user_id"] if idx else None

    code_field = get_test_verification_code() if req.test_user else None



    response_payload: Dict[str, Any] = {}

    if user_id is not None:

        response_payload["user_id"] = user_id

    if code_field is not None:

        response_payload["code"] = code_field



    message = (

        "Password reset code generated for test user"

        if req.test_user

        else "Password reset code dispatched"

    )

    return create_success_response(data=response_payload or None, message=message)



def handle_reset_step2(envelope: Dict[str, Any]) -> Dict[str, Any]:

    try:

        data = _get_envelope_data(envelope)

    except InvalidInputError as exc:

        return create_error_response(str(exc), error_type="INVALID_INPUT")



    try:

        req = ResetPasswordRequestModel.model_validate(data)

    except ValidationError as exc:

        return create_error_response(

            "Invalid payload for reset_step2",

            error_type="INVALID_INPUT",

            details={"errors": exc.errors()},

        )



    if req.new_password != req.confirm_new_password:

        return create_error_response(

            "new_password and confirm_new_password must match",

            error_type="INVALID_INPUT",

        )



    if not verify_reset_code(req.auth_username, req.code):

        return create_error_response(

            "Verification code is invalid or expired",

            error_type="INVALID_INPUT",

        )



    try:

        reset_ok = reset_password(req.auth_username, req.code, req.new_password)

    except InvalidInputError as exc:

        return create_error_response(str(exc), error_type="INVALID_INPUT")

    except DependencyError as exc:

        return create_error_response(str(exc), error_type="DEPENDENCY_ERROR")



    if not reset_ok:

        return create_error_response(

            "Unable to reset password for provided auth_username",

            error_type="NOT_FOUND",

        )



    return create_success_response(message="Password reset successfully")





# ======== Step 规范描述（供注册器读取，不做直接注册）========

RESET_PASSWORD_STEP_SPECS: Dict[str, Any] = {

    "flow_id": "password_reset",

    "name": "Password reset flow",

    "description": "Reset user password via email verification code",

    "modules": ["auth"],

    "steps": [

        {

            "step_id": "reset_step1",

            "module": "auth",

            "handler": "cry_backend.tool_modules.auth.reset_password.handle_reset_step1",

            "required_fields": ["payload"],

            "output_fields": ["success", "message", "user_id", "code"],

            "next_step": "reset_step2"

        },

        {

            "step_id": "reset_step2",

            "module": "auth",

            "handler": "cry_backend.tool_modules.auth.reset_password.handle_reset_step2",

            "required_fields": ["payload"],

            "output_fields": ["success", "message"],

            "previous_step": "reset_step1"

        }

    ]

}









