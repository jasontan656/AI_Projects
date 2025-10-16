"""
MCP JSON-RPC 2.0 协议模型定义

符合 MCP 规范的请求与响应数据结构，基于 Pydantic v2 提供校验与序列化。
"""
from __future__ import annotations  # 使用内置 future 特性延迟注解解析；避免循环引用
from typing import Any, Literal, Optional  # 使用标准库模块 typing 导入类型标注；随后提升可读性
from pydantic import BaseModel, Field  # 使用依赖库类 BaseModel 与 Field；构建数据模型与字段约束


class JSONRPCRequest(BaseModel):  # 定义类 JSONRPCRequest；封装 JSON-RPC 2.0 请求结构【协议（Protocol）/ 请求（Request）】
    """JSON-RPC 2.0 请求模型"""
    jsonrpc: Literal["2.0"] = Field(default="2.0", description="JSON-RPC 协议版本，固定为 2.0")  # 使用 Field 约束协议版本；保证兼容性
    id: Optional[str | int] = Field(default=None, description="请求唯一标识符，用于匹配响应")  # 使用 Field 标注请求 ID；支持字符串或整数
    method: str = Field(..., description="调用的 MCP 方法名，如 tools/list、tools/call")  # 使用 Field 标注方法名；必填参数
    params: Optional[dict[str, Any]] = Field(default=None, description="方法参数对象，可选")  # 使用 Field 标注参数字典；允许为空


class JSONRPCError(BaseModel):  # 定义类 JSONRPCError；封装 JSON-RPC 2.0 错误对象【协议（Protocol）/ 错误（Error）】
    """JSON-RPC 2.0 错误对象"""
    code: int = Field(..., description="错误码，标准错误码范围 -32768 到 -32000")  # 使用 Field 标注错误码；整数类型
    message: str = Field(..., description="错误描述信息")  # 使用 Field 标注错误信息；人类可读
    data: Optional[Any] = Field(default=None, description="附加错误数据，可选")  # 使用 Field 标注扩展数据；灵活承载上下文


class JSONRPCResponse(BaseModel):  # 定义类 JSONRPCResponse；封装 JSON-RPC 2.0 响应结构【协议（Protocol）/ 响应（Response）】
    """JSON-RPC 2.0 响应模型"""
    jsonrpc: Literal["2.0"] = Field(default="2.0", description="JSON-RPC 协议版本")  # 使用 Field 约束协议版本；与请求对齐
    id: Optional[str | int] = Field(default=None, description="与请求 ID 对应")  # 使用 Field 标注响应 ID；用于请求匹配
    result: Optional[Any] = Field(default=None, description="方法执行结果，成功时返回")  # 使用 Field 标注结果字段；互斥于 error
    error: Optional[JSONRPCError] = Field(default=None, description="错误对象，失败时返回")  # 使用 Field 标注错误对象；互斥于 result


class Tool(BaseModel):  # 定义类 Tool；封装 MCP 工具描述结构【工具（Tool）/ 元数据（Metadata）】
    """MCP 工具描述模型"""
    name: str = Field(..., description="工具唯一标识名称")  # 使用 Field 标注工具名；必填且唯一
    description: str = Field(..., description="工具功能描述")  # 使用 Field 标注功能说明；帮助 Agent 选择
    input_schema: dict[str, Any] = Field(..., description="JSON Schema 描述的输入参数结构")  # 使用 Field 标注输入模式；遵循 JSON Schema 规范


class ToolListResult(BaseModel):  # 定义类 ToolListResult；封装工具列表响应结构【工具（Tool）/ 响应（Response）】
    """tools/list 方法返回结构"""
    tools: list[Tool] = Field(default_factory=list, description="可用工具列表")  # 使用 Field 标注工具数组；默认空列表


class ToolCallParams(BaseModel):  # 定义类 ToolCallParams；封装工具调用请求参数【工具（Tool）/ 请求（Request）】
    """tools/call 方法请求参数"""
    name: str = Field(..., description="要调用的工具名称")  # 使用 Field 标注工具名；必填参数
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具输入参数")  # 使用 Field 标注参数字典；默认空字典


class ToolCallResult(BaseModel):  # 定义类 ToolCallResult；封装工具调用响应结构【工具（Tool）/ 响应（Response）】
    """tools/call 方法返回结构"""
    content: list[dict[str, Any]] = Field(default_factory=list, description="工具执行结果内容数组")  # 使用 Field 标注结果数组；可包含多条内容
    is_error: bool = Field(default=False, description="是否执行失败")  # 使用 Field 标注错误标志；默认成功


# 标准 JSON-RPC 错误码常量
class ErrorCode:  # 定义类 ErrorCode；集中管理协议错误码【常量（Constants）/ 协议（Protocol）】
    """JSON-RPC 2.0 标准错误码"""
    PARSE_ERROR = -32700  # 解析错误：无效 JSON
    INVALID_REQUEST = -32600  # 无效请求：不符合协议格式
    METHOD_NOT_FOUND = -32601  # 方法未找到：未注册的方法名
    INVALID_PARAMS = -32602  # 无效参数：参数类型或格式错误
    INTERNAL_ERROR = -32603  # 内部错误：服务器端异常

