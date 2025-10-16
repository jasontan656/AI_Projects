"""
MCP Server 鉴权与会话管理

支持 Bearer Token 鉴权与基于 X-Agent-Id 的会话隔离。
"""
from __future__ import annotations  # 使用内置 future 特性延迟注解解析；避免循环引用
import os  # 使用标准库模块 os 访问环境变量；随后读取配置
import logging  # 使用标准库模块 logging 导入日志 API；随后记录鉴权事件
from typing import Optional  # 使用标准库模块 typing 导入类型标注；随后提升可读性
from fastapi import Request, HTTPException  # 使用依赖库 fastapi 导入请求与异常类；随后处理鉴权逻辑
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # 使用依赖库 fastapi.security 导入鉴权方案；随后提取 Bearer Token
from starlette.middleware.base import BaseHTTPMiddleware  # 使用依赖库 starlette.middleware 导入中间件基类；随后实现鉴权中间件
from starlette.responses import JSONResponse  # 使用依赖库 starlette.responses 导入响应类；随后返回错误

logger = logging.getLogger(__name__)  # 调用标准库函数 logging.getLogger 获取当前模块记录器；用于输出日志

# 从环境变量读取配置
MCP_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"  # 读取鉴权开关环境变量；默认关闭
MCP_BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN")  # 读取 Bearer Token 环境变量；用于校验请求
BYPASS_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}  # 定义绕过鉴权的路径集合；允许公开访问

# HTTPBearer 实例
bearer_scheme = HTTPBearer(auto_error=False)  # 创建 Bearer Token 鉴权方案实例；禁用自动错误


def verify_token(token: str) -> bool:  # 定义函数 verify_token；校验 Bearer Token【鉴权（Authentication）/ 校验（Validation）】
    """校验 Bearer Token
    
    Args:
        token: 待校验的 Token
        
    Returns:
        是否有效
    """
    if not MCP_AUTH_ENABLED:  # 判断鉴权是否启用；条件不成立进入分支【条件分支（Branch）】
        return True  # 直接返回成功；鉴权关闭时允许所有请求
    
    if not MCP_BEARER_TOKEN:  # 判断是否配置 Token；条件不成立进入分支【条件分支（Branch）/ 校验（Validation）】
        logger.warning("MCP_BEARER_TOKEN 未配置，但鉴权已启用")  # 在 logger 上调用 warning 记录警告；提示配置错误
        return False  # 返回失败；拒绝请求
    
    return token == MCP_BEARER_TOKEN  # 比较 Token 是否匹配；返回比较结果


def extract_agent_id(request: Request) -> str:  # 定义函数 extract_agent_id；提取 Agent ID【会话（Session）/ 提取（Extract）】
    """从请求头提取 Agent ID
    
    Args:
        request: FastAPI 请求对象
        
    Returns:
        Agent ID，默认为 "default"
    """
    return request.headers.get("X-Agent-Id", "default")  # 从请求头提取 X-Agent-Id；缺省使用默认值


class AuthMiddleware(BaseHTTPMiddleware):  # 定义类 AuthMiddleware；实现鉴权中间件【中间件（Middleware）/ 鉴权（Authentication）】
    """鉴权中间件，校验 Bearer Token"""
    
    async def dispatch(self, request: Request, call_next):  # 定义异步方法 dispatch；处理每个请求【异步（Async）/ 中间件（Middleware）】
        """处理请求
        
        Args:
            request: FastAPI 请求对象
            call_next: 调用下一个中间件或路由处理器
            
        Returns:
            响应对象
        """
        # 步骤 1: 检查是否需要鉴权
        if not MCP_AUTH_ENABLED:  # 判断鉴权是否启用；条件不成立进入分支【条件分支（Branch）】
            return await call_next(request)  # 直接调用下一个处理器；跳过鉴权
        
        # 步骤 2: 检查是否为绕过路径
        if request.url.path in BYPASS_PATHS:  # 判断路径是否在绕过列表中；条件成立进入分支【条件分支（Branch）】
            return await call_next(request)  # 直接调用下一个处理器；允许公开访问
        
        # 步骤 3: 提取 Bearer Token
        authorization = request.headers.get("Authorization")  # 从请求头提取 Authorization 字段；用于鉴权
        if not authorization:  # 判断是否缺少 Authorization 头；条件成立进入分支【条件分支（Branch）/ 校验（Validation）】
            logger.warning(f"缺少 Authorization 头: {request.url.path}")  # 在 logger 上调用 warning 记录警告；包含路径
            return JSONResponse(  # 返回错误响应；符合 HTTP 401 规范
                status_code=401,
                content={"error": "缺少 Authorization 头"},
            )
        
        # 步骤 4: 解析 Bearer Token
        if not authorization.startswith("Bearer "):  # 判断格式是否正确；条件不成立进入分支【条件分支（Branch）/ 校验（Validation）】
            logger.warning(f"Authorization 格式错误: {request.url.path}")  # 在 logger 上调用 warning 记录警告；包含路径
            return JSONResponse(  # 返回错误响应；符合 HTTP 401 规范
                status_code=401,
                content={"error": "Authorization 格式错误，应为 'Bearer <token>'"},
            )
        
        token = authorization[7:]  # 提取 Token 字符串；去除 "Bearer " 前缀
        
        # 步骤 5: 校验 Token
        if not verify_token(token):  # 判断 Token 是否有效；条件不成立进入分支【条件分支（Branch）/ 校验（Validation）】
            logger.warning(f"Token 校验失败: {request.url.path}")  # 在 logger 上调用 warning 记录警告；包含路径
            return JSONResponse(  # 返回错误响应；符合 HTTP 403 规范
                status_code=403,
                content={"error": "Token 无效"},
            )
        
        # 步骤 6: Token 有效，继续处理
        agent_id = extract_agent_id(request)  # 提取 Agent ID；用于会话隔离
        logger.info(f"鉴权成功: agent_id={agent_id}, path={request.url.path}")  # 在 logger 上调用 info 记录成功；包含 Agent ID 与路径
        
        # 将 Agent ID 存入请求状态，供后续处理器使用
        request.state.agent_id = agent_id  # 在请求状态对象设置 agent_id 属性；供路由访问
        
        return await call_next(request)  # 调用下一个处理器；继续处理请求


class SessionManager:  # 定义类 SessionManager；管理客户端会话【会话管理（Session Management）/ 管理器（Manager）】
    """会话管理器，按 Agent ID 隔离"""
    
    def __init__(self):  # 定义初始化方法；构造会话管理器实例【初始化（Init）】
        self._sessions: dict[str, dict] = {}  # 使用字典存储会话数据；键为 Agent ID
    
    def get_session(self, agent_id: str) -> dict:  # 定义方法 get_session；获取或创建会话【会话（Session）/ 查询（Query）】
        """获取或创建会话
        
        Args:
            agent_id: Agent 标识符
            
        Returns:
            会话数据字典
        """
        if agent_id not in self._sessions:  # 判断会话是否存在；条件不成立进入分支【条件分支（Branch）】
            self._sessions[agent_id] = {  # 创建新会话；初始化数据字典
                "agent_id": agent_id,
                "request_count": 0,
                "created_at": None,  # TODO: 添加时间戳
            }
            logger.info(f"创建新会话: agent_id={agent_id}")  # 在 logger 上调用 info 记录创建事件；包含 Agent ID
        
        self._sessions[agent_id]["request_count"] += 1  # 增加请求计数；用于统计
        return self._sessions[agent_id]  # 返回会话数据字典；供调用方使用
    
    def remove_session(self, agent_id: str):  # 定义方法 remove_session；删除会话【会话（Session）/ 清理（Cleanup）】
        """删除会话
        
        Args:
            agent_id: Agent 标识符
        """
        if agent_id in self._sessions:  # 判断会话是否存在；条件成立进入分支【条件分支（Branch）】
            del self._sessions[agent_id]  # 从字典删除会话；释放资源
            logger.info(f"删除会话: agent_id={agent_id}")  # 在 logger 上调用 info 记录删除事件；包含 Agent ID
    
    def list_sessions(self) -> list[dict]:  # 定义方法 list_sessions；列出所有会话【会话（Session）/ 查询（Query）】
        """列出所有活跃会话"""
        return list(self._sessions.values())  # 返回会话数据列表；用于监控


# 全局会话管理器实例
session_manager = SessionManager()  # 实例化会话管理器；全局单例

