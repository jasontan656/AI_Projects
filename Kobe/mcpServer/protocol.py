"""
MCP JSON-RPC 协议处理器

负责 JSON-RPC 2.0 消息的解析、校验、分发与响应构建。
"""
from __future__ import annotations  # 使用内置 future 特性延迟注解解析；避免循环引用
import logging  # 使用标准库模块 logging 导入日志 API；随后记录协议处理过程
from typing import Any, Callable, Coroutine  # 使用标准库模块 typing 导入类型标注；随后提升可读性
from .models import (  # 使用同项目模块导入协议模型；随后用于请求与响应校验
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    ErrorCode,
)

logger = logging.getLogger(__name__)  # 调用标准库函数 logging.getLogger 获取当前模块记录器；用于输出日志


class MCPProtocolHandler:  # 定义类 MCPProtocolHandler；封装 JSON-RPC 协议处理逻辑【协议（Protocol）/ 处理器（Handler）】
    """MCP JSON-RPC 2.0 协议处理器"""
    
    def __init__(self):  # 定义初始化方法；构造处理器实例【初始化（Init）】
        self._methods: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}  # 使用字典存储方法名到处理函数的映射；支持动态注册
    
    def register_method(  # 定义方法 register_method；注册 MCP 方法处理器【注册（Registration）/ 路由（Routing）】
        self,
        name: str,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """注册 MCP 方法处理器
        
        Args:
            name: 方法名，如 'tools/list'、'tools/call'
            handler: 异步处理函数，接收 params 返回 result
        """
        self._methods[name] = handler  # 在字典 _methods 上添加键值对；关联方法名与处理函数
        logger.info(f"注册 MCP 方法: {name}")  # 在 logger 上调用 info 记录注册事件；便于追踪
    
    async def handle_request(self, request_data: dict[str, Any]) -> JSONRPCResponse:  # 定义异步方法 handle_request；处理单个 JSON-RPC 请求【请求处理（Request Handling）/ 异步（Async）】
        """处理 JSON-RPC 2.0 请求
        
        Args:
            request_data: 原始请求字典
            
        Returns:
            JSON-RPC 响应对象
        """
        # 步骤 1: 解析请求
        try:  # 尝试解析请求数据；若失败进入异常分支【异常处理（Exception Handling）】
            request = JSONRPCRequest(**request_data)  # 使用 Pydantic 模型解析请求；校验字段类型与必填项
        except Exception as parse_error:  # 捕获解析异常；条件成立进入分支【异常处理（Exception Handling）】
            logger.error(f"请求解析失败: {parse_error}")  # 在 logger 上调用 error 记录解析错误；包含异常信息
            return JSONRPCResponse(  # 返回错误响应；符合 JSON-RPC 2.0 规范
                jsonrpc="2.0",
                id=request_data.get("id"),  # 在字典 request_data 上调用 get 提取 ID；可能为空
                error=JSONRPCError(  # 构造错误对象；描述解析失败
                    code=ErrorCode.PARSE_ERROR,
                    message="请求解析失败",
                    data=str(parse_error),
                ),
            )
        
        # 步骤 2: 查找方法
        method_name = request.method  # 从请求对象提取方法名；用于路由查找
        if method_name not in self._methods:  # 判断方法名是否已注册；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
            logger.warning(f"方法未找到: {method_name}")  # 在 logger 上调用 warning 记录未知方法；提示调用方
            return JSONRPCResponse(  # 返回错误响应；符合 JSON-RPC 2.0 规范
                jsonrpc="2.0",
                id=request.id,
                error=JSONRPCError(  # 构造错误对象；描述方法未找到
                    code=ErrorCode.METHOD_NOT_FOUND,
                    message=f"方法未找到: {method_name}",
                ),
            )
        
        # 步骤 3: 执行方法
        handler = self._methods[method_name]  # 从字典 _methods 提取处理函数；根据方法名查找
        try:  # 尝试执行处理函数；若失败进入异常分支【异常处理（Exception Handling）】
            params = request.params or {}  # 提取请求参数；缺省使用空字典
            result = await handler(**params)  # 调用异步处理函数；展开参数字典并 await 等待结果
            logger.debug(f"方法执行成功: {method_name}")  # 在 logger 上调用 debug 记录成功；便于调试
            return JSONRPCResponse(  # 返回成功响应；包含执行结果
                jsonrpc="2.0",
                id=request.id,
                result=result,
            )
        except TypeError as param_error:  # 捕获参数类型错误；条件成立进入分支【异常处理（Exception Handling）】
            logger.error(f"参数错误 [{method_name}]: {param_error}")  # 在 logger 上调用 error 记录参数错误；包含方法名
            return JSONRPCResponse(  # 返回错误响应；符合 JSON-RPC 2.0 规范
                jsonrpc="2.0",
                id=request.id,
                error=JSONRPCError(  # 构造错误对象；描述参数错误
                    code=ErrorCode.INVALID_PARAMS,
                    message="参数类型或格式错误",
                    data=str(param_error),
                ),
            )
        except Exception as internal_error:  # 捕获其他内部异常；条件成立进入分支【异常处理（Exception Handling）】
            logger.exception(f"方法执行失败 [{method_name}]")  # 在 logger 上调用 exception 记录堆栈；保留完整上下文
            return JSONRPCResponse(  # 返回错误响应；符合 JSON-RPC 2.0 规范
                jsonrpc="2.0",
                id=request.id,
                error=JSONRPCError(  # 构造错误对象；描述内部错误
                    code=ErrorCode.INTERNAL_ERROR,
                    message="内部服务错误",
                    data=str(internal_error),
                ),
            )

