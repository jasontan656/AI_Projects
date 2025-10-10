from __future__ import annotations
# from __future__ import annotations 启用前置注解
# 便于类型提示前置引用

from typing import Any, Dict, Generic, Optional, TypeVar, List
import inspect
# typing 导入 Any/Dict/Generic/Optional/TypeVar
# 用于类型注解与泛型模型

from pydantic import BaseModel, Field, ValidationError, field_validator
# pydantic 导入 BaseModel/Field/ValidationError
# 用于数据模型与错误处理
from pydantic import ConfigDict
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username
# ConfigDict 用于设置 extra=forbid

from .router import router
from shared_utilities.response import (
    create_success_response as _shared_create_success_response,
    create_error_response as _shared_create_error_response,
)
# 从 applications.mbti.router 导入 router 实例

T = TypeVar("T", bound=BaseModel)
# T = 泛型边界为 BaseModel
# 用于 StandardResponse[T]


class StandardResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    # StandardResponse 拒绝未知字段
    success: bool
    # success: 处理是否成功
    message: Optional[str] = None
    # message: 可选提示信息
    data: Optional[T] = None
    # data: 可选数据负载
    error: Optional[str] = None
    # error: 可选错误信息
    error_type: Optional[str] = None
    # error_type: 可选错误类型


class UserNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # UserNode 拒绝未知字段
    id: Optional[str] = None
    # UserNode.id
    auth_username: Optional[str] = None
    # UserNode.auth_username 顶层用户ID
    authorization: Optional[str] = None
    # UserNode.authorization 认证头
    profile: Optional[Dict[str, Any]] = None
    # UserNode.profile 用户资料
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
    # RouteNode: nested routing path definition
    path: List[str]


class MbtiPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # MbtiPayload 拒绝未知字段
    module: str = Field(default="mbti")
    # MbtiPayload.module 固定为 "mbti"
    route: RouteNode
    # MbtiPayload.route 嵌套路由路径
    data: Dict[str, Any] = Field(default_factory=dict)
    # MbtiPayload.data 允许嵌套的数据字典


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Envelope 拒绝未知字段
    user: Optional[UserNode] = None
    # Envelope.user 顶层用户节点
    payload: MbtiPayload
    # Envelope.payload 业务载荷
    meta: Optional[Dict[str, Any]] = None
    # Envelope.meta 元信息

    def unwrap(self) -> Dict[str, Any]:
        data = self.payload.data or {}
        # Envelope.unwrap() 返回 payload.data
        return data
        # 返回 dict 供后续步骤使用


def create_success_response(data: Any = None, message: str = "ok") -> Dict[str, Any]:
    response: Dict[str, Any] = {"success": True, "message": message}
    # create_success_response(data/message)
    # 构建标准成功响应字典
    if data is not None:
        response["data"] = data
        # 若 data 存在，附加 data 字段
    return response
    # 返回成功响应字典


def create_error_response(error: str, error_type: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response: Dict[str, Any] = {"success": False, "error": error, "error_type": error_type}
    # create_error_response(error/error_type/details)
    # 构建标准错误响应字典
    if details:
        response["details"] = details
        # 若 details 存在，附加 details 字段
    return response
    # 返回错误响应字典


def _parse(envelope_like: Dict[str, Any]) -> Envelope:
    # _parse(envelope_like) 解析顶层 Envelope
    try:
        return Envelope(**envelope_like)
        # Envelope(**envelope_like) -> Envelope
    except ValidationError as ve:
        raise ValueError(f"invalid envelope: {ve}")
        # 验证失败抛 ValueError 显示细节


def _err(error: str, error_type: str) -> Dict[str, Any]:
    # _err(error/error_type) 错误包装
    return create_error_response(error=error, error_type=error_type)
    # 返回错误结构供调用方使用


def _run_async(awaitable_obj: Any) -> Any:
    # _run_async(awaitable_obj) 同步等待协程
    import asyncio
    # 导入 asyncio 创建事件循环
    if not inspect.iscoroutine(awaitable_obj):
        return awaitable_obj
        # 非协程直接返回原值
    loop = asyncio.new_event_loop()
    # loop = 新事件循环对象
    try:
        asyncio.set_event_loop(loop)
        # 设置当前线程事件循环
        return loop.run_until_complete(awaitable_obj)
        # 同步等待协程完成并返回
    finally:
        try:
            loop.close()
            # 关闭事件循环释放资源
        except (RuntimeError, ValueError, OSError):
            pass
            # 忽略关闭异常确保稳定性


def mbti_route(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Facade entry: Envelope validation + flow_router dispatch
    """
    # mbti_route(payload) 门面主入口
    try:
        env = _parse(payload)
        # Strict skeleton: require payload.route.path
        route_path: List[str] = (env.payload.route.path if env.payload and env.payload.route else [])
        if not route_path or not all(isinstance(seg, str) and seg for seg in route_path):
            return _err("payload.route.path is required", "INVALID_INPUT")

        # Pass-through full envelope to module router
        result = router.route(env.model_dump())
        # result = 调用模块内 router.route 进行分发
        if isinstance(result, dict) and (result.get("success") is not None):
            return result
            # 若包含 success 字段，直接透传
        return create_success_response(data=result)
        # 否则包装为标准成功响应
    except ValidationError as ve:
        return _err(f"invalid envelope: {ve}", "INVALID_INPUT")
        # Pydantic 验证异常，返回输入错误
    except (RuntimeError, ValueError, KeyError):
        return _err("Internal error", "INTERNAL_ERROR")
        # 其它异常，返回统一未知错误


__all__ = [
    "StandardResponse",
    "UserNode",
    "MbtiPayload",
    "Envelope",
    "mbti_route",
]
# __all__ 导出门面符号与入口


# Override local helpers with shared single-point implementations to enforce consistency
create_success_response = _shared_create_success_response  # type: ignore
create_error_response = _shared_create_error_response  # type: ignore


