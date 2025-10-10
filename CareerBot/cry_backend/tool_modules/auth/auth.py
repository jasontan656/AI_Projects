from __future__ import annotations

from typing import Any, Dict, Generic, Optional, Type, TypeVar, Callable

from pydantic import BaseModel, Field, ValidationError, field_validator, ConfigDict

from shared_utilities.response import create_error_response, create_success_response
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str
# RefreshTokenRequest(refresh_token)
# 入参校验模型，确保存在 refresh_token 字段
# 返回值用于 _call_with_request_model 的数据解析

class UserProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    email: str
    auth_username: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
# UserProfileResponse(user_id/email/auth_username/...)
# 出参模型，用于 _wrap_and_validate 的数据契约校验

class LogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: bool
    message: str
# LogoutResponse(success/message)
# 出参模型，登出结果的标准结构

# Removed dependency on legacy auth_middleware per facade design
# Email registration moved to its own module entry and flows; facade should not import domain functions/models

from .router import router
from .tokens import verify_access_token, refresh_access_token, revoke_session
from .exceptions import (
    InvalidCredentialsError,
    InvalidInputError,
    UserAlreadyExistsError,
    EmailAlreadyRegisteredError,
)


class AuthenticatedUserModel (BaseModel) :
    model_config = ConfigDict(extra="forbid")
    user_id: str
    auth_username: str

    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")

    @field_validator("auth_username", mode="before")
    def _validate_auth_username(cls, value: str | None) -> str:
        return normalize_auth_username(value)

AuthenticatedUser = AuthenticatedUserModel

T = TypeVar ("T", bound=BaseModel)

class StandardResponse (BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    success : bool
    message : Optional[str] = None
    data : Optional[T] = None
    error : Optional[str] = None
    error_type : Optional[str] = None

class UserNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Optional[str] = None
    # UserNode.id
    auth_username: Optional[str] = None
    # UserNode.auth_username 顶层用户ID，用于关联与限速
    authorization: Optional[str] = None
    # UserNode.authorization 顶层认证头，格式如 "Bearer xxx"
    profile: Optional[Dict[str,Any]] = None
    # UserNode.profile 可选用户资料，不做强校验
    @field_validator("id")
    def _validate_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return ensure_timestamp_uuidv4(value, field_name="user.id")

    @field_validator("auth_username", mode="before")
    def _validate_auth_username(cls, value: Optional[str]) -> Optional[str]:
        return normalize_auth_username(value)

class RouteNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: list[str]


class AuthPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    module: str = Field(default="auth")
    # AuthPayload.module 固定 'auth'，用于路由
    route: RouteNode
    # AuthPayload.route 嵌套路由路径
    data: Dict[str, Any] = Field(default_factory=dict)
    # AuthPayload.data 业务字段容器


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user: Optional[UserNode] = None
    # Envelope.user 顶层用户节点，可空
    payload: AuthPayload
    # Envelope.payload 业务载荷，包含 data
    meta: Optional[Dict[str,Any]] = None
    # Envelope.meta 元信息（客户端、IP等）

    def unwrap(self) -> Dict[str,Any]:
        data = self.payload.data or {}
        # Envelope.unwrap() 返回 payload.data 供领域模型校验
        return data

def _extract_token(envelope: Envelope) -> Optional[str]:
    auth = None
    if envelope.user and envelope.user.authorization:
        auth = envelope.user.authorization
        # 从 Envelope.user.authorization 读取认证头
    if auth and auth.startswith("Bearer"):
        return auth[7:]
        # 去除前缀 'Bearer '
    return auth

def _parse(envelope_like:Dict[str,Any]) -> Envelope:
    # _parse(envelope_like) 解析顶层嵌套结构为 Envelope
    try:
        return Envelope(**envelope_like)
    except ValidationError as ve:
        raise InvalidInputError(f"invalid envelope: {ve}")

def _ok(
    data: Optional[BaseModel] = None, message: Optional[str] = None
) -> Dict[str, Any]:
    return create_success_response(
        data=data.model_dump() if isinstance(data, BaseModel) else data,
        message=message or "ok",
    )

def _err(error: str, error_type: str) -> Dict[str, Any]:
    return create_error_response(error=error, error_type=error_type)

def _wrap_and_validate(
    raw_result: Dict[str,Any],
    data_model: Optional[type[T]] = None
) -> Dict[str,Any]:

    """
    Validate outgoing result contract and coerce into StandardResponse[T] when T is provided.
    """
    try:
        success = bool(raw_result.get("success"))
        message = raw_result.get("message")
        error = raw_result.get("error")
        error_type = raw_result.get("error_type")
        data_payload = raw_result.get("data")

        typed_data: Optional[T] = None
        if data_model is not None and data_payload is not None:
            typed_data = data_model(**data_payload)

        wrapper = StandardResponse[T](
            success=success,
            message=message,
            data=typed_data,
            error=error,
            error_type=error_type,
        )

        result = wrapper.model_dump()
        # 当未提供数据模型时，透传原始 data 载荷
        if data_model is None and data_payload is not None:
            result["data"] = data_payload
        elif typed_data is not None:
            result["data"] = typed_data.model_dump()
        return result
    except ValidationError as ve:
         return _err(f"Response contract validation failed: {ve}", "RESPONSE_CONTRACT_ERROR")



def _call_with_request_model(
    envelope_like: Dict[str,Any],
    request_model: Type[BaseModel],
    service_fn:Callable[Dict[str,Any],Any],
    response_data_model: Optional [Type[T]] = None
) -> Dict[str,Any]:
    """
    Generic facade entry: validate input using request_model, invoke service, validate output.
    """
    try:
        env = _parse(envelope_like)
        # _parse(envelope_like) -> Envelope，对顶层结构做骨架校验
        body = env.unwrap()
        # Envelope.unwrap() 返回 payload.data
        request_obj = request_model(**body)
        # request_model(**body) 对领域数据做字段校验
        raw_result = service_fn(body)
        # service_fn(body) 仅传递解析后的领域数据给下游
        return _wrap_and_validate(raw_result,response_data_model)


    except (InvalidInputError, EmailAlreadyRegisteredError, UserAlreadyExistsError) as be:  #潜在问题
        return _wrap_and_validate(_err(str(be), "INVALID_INPUT"))
    except InvalidCredentialsError as ice:
        return _wrap_and_validate(_err(str(ice), "INVALID_CREDENTIALS"))
# ------------------------------
# Authentication helpers
# ------------------------------


def extract_current_user(envelope_like: Dict[str,Any]) -> Optional[AuthenticatedUserModel]:
    """
    Facade-level user extraction with contract validation and DB align check.
    """
    try:
        env = _parse(envelope_like)
        token = _extract_token(env)
        if not token:
            return None
        payload = verify_access_token(token)
        user_id = payload.get("user_id")
        username = payload.get("auth_username")
        token_type = payload.get("type")
        if not user_id or not username or token_type !="access_token":
            return None
        return AuthenticatedUserModel(user_id=user_id,auth_username=username)
    except ValueError:
        return None


# ------------------------------
# Facade public API（Skeleton validation + Router）
# ------------------------------

def auth_route(payload: Dict[str, Any]) -> Dict[str, Any]:
    """统一入口：Envelope 骨架校验后，内部路由到子模块。"""
    try:
        env = _parse(payload)  # Envelope 骨架校验
        # 必须提供 payload.route.path
        route = (env.payload.route if env and env.payload else None)
        if route is None or not isinstance(route.path, list) or not route.path:
            return _err("payload.route.path is required", "INVALID_INPUT")
        result = router.route(env.model_dump())
        # 规范化简单字典/模型为标准响应
        if isinstance(result, dict) and result.get("success") is not None:
            return result
        return _ok(data=result if isinstance(result, BaseModel) else None)
    except ValidationError as ve:
        return _err(f"invalid envelope: {ve}", "INVALID_INPUT")

def auth_login(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Nested routing
    class _Req(BaseModel):
        auth_username: str
        password: str
    env = _parse(payload)
    body = env.unwrap()
    _Req(**body)
    routed_env = env.model_dump()
    routed_env["payload"]["route"] = {"path": ["auth", "auth_login"]}
    result = router.route(routed_env)
    if isinstance(result, dict) and result.get("success") is not None:
        return result
    return _ok(data=result if isinstance(result, BaseModel) else None)

def auth_oauth_google_url(payload: Dict[str, Any]) -> Dict[str, Any]:
    class _Req(BaseModel):
        state: Optional[str] = None
    env = _parse(payload)
    body = env.unwrap()
    _Req(**body)
    routed_env = env.model_dump()
    routed_env["payload"]["route"] = {"path": ["auth", "oauth_google_url"]}
    return router.route(routed_env)

def auth_oauth_google_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
    class _Req(BaseModel):
        code: str
        state: Optional[str] = None
        expected_state: Optional[str] = None
    env = _parse(payload)
    body = env.unwrap()
    _Req(**body)
    routed_env = env.model_dump()
    routed_env["payload"]["route"] = {"path": ["auth", "oauth_google_callback"]}
    result = router.route(routed_env)
    if isinstance(result, dict) and result.get("success") is not None:
        return result
    return _ok(data=result if isinstance(result, BaseModel) else None)

def auth_oauth_facebook_url(payload: Dict[str, Any]) -> Dict[str, Any]:
    class _Req(BaseModel):
        state: Optional[str] = None
    env = _parse(payload)
    body = env.unwrap()
    _Req(**body)
    routed_env = env.model_dump()
    routed_env["payload"]["route"] = {"path": ["auth", "oauth_facebook_url"]}
    return router.route(routed_env)
def auth_oauth_facebook_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
    class _Req(BaseModel):
        code: str
        state: Optional[str] = None
        expected_state: Optional[str] = None
    env = _parse(payload)
    body = env.unwrap()
    _Req(**body)
    routed_env = env.model_dump()
    routed_env["payload"]["route"] = {"path": ["auth", "oauth_facebook_callback"]}
    result = router.route(routed_env)
    if isinstance(result, dict) and result.get("success") is not None:
        return result
    return _ok(data=result if isinstance(result, BaseModel) else None)

# removed: password reset endpoints; use module flows instead

def auth_get_profile(payload: Dict[str, Any]) -> Dict[str, Any]:
    # 当前未实现：返回标准未实现错误
    return _err("Not implemented", "NOT_FOUND")

def auth_update_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    # 当前未实现：返回标准未实现错误
    return _err("Not implemented", "NOT_FOUND")

def auth_refresh_token(payload: Dict[str, Any]) -> Dict[str, Any]:
    # 兼容旧名：与 auth_refresh_access_token 一致
    return _call_with_request_model(
        payload,
        RefreshTokenRequest,
        lambda body: create_success_response(data=refresh_access_token(body.get("refresh_token"))),
        response_data_model=None,
    )

def auth_refresh_access_token(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _call_with_request_model(
        payload,
        RefreshTokenRequest,
        lambda body: create_success_response(data=refresh_access_token(body.get("refresh_token"))),
        response_data_model=None,
    )

def auth_logout(payload: Dict[str, Any]) -> Dict[str, Any]:
    env = _parse(payload)
    routed_env = env.model_dump()
    routed_env["payload"]["route"] = {"path": ["auth", "auth_logout"]}
    routed_env["payload"]["data"] = {}
    result = router.route(routed_env)
    if isinstance(result, dict) and result.get("success") is not None:
        return result
    return _ok(data=None)

def auth_prompt_login(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _err("Not implemented", "NOT_FOUND")


__all__ = [
    # Models
    "AuthenticatedUser", "AuthenticatedUserModel", "StandardResponse",
    # Auth helpers
    "extract_current_user",
    # Facade endpoints
    "auth_route",
    "auth_login",
    "auth_oauth_google_url", "auth_oauth_google_callback",
    "auth_oauth_facebook_url", "auth_oauth_facebook_callback",
    "auth_get_profile", "auth_update_settings",
    "auth_refresh_token", "auth_refresh_access_token",
    "auth_logout", "auth_prompt_login",
]

