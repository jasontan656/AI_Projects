#!/usr/bin/env python3
"""
Kobe Backend Service
FastAPI 后端服务主入口
统一管理日志、API路由、业务逻辑
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.timing import add_timing_middleware
from dotenv import load_dotenv
from SharedUtility.RichLogger.logger import RichLoggerManager
from SharedUtility.RichLogger.trace import ensure_trace_id, get_progress_reporter

# Windows 环境下强制使用 UTF-8 编码，避免 emoji 等特殊字符导致日志输出失败
if sys.platform == 'win32':
    # 设置标准输出和错误输出为 UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    # 设置环境变量（对子进程生效）
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 确保使用支持子进程的 Proactor 事件循环（避免 asyncio.create_subprocess_* 在 Windows 上报 NotImplementedError）
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

# 加载环境变量
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# 初始化全局日志系统（控制台提升到 DEBUG，文件已默认 DEBUG）
logger = RichLoggerManager.bootstrap(console_level=logging.DEBUG)

# 定义生命周期事件处理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    logger.info("Kobe Backend API 启动")
    
    yield
    
    # 关闭事件
    logger.info("Kobe Backend API 关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Kobe Backend API",
    description="AI驱动的后端服务，支持聊天、工具调用、数据管理",
    version="2.0.0",
    lifespan=lifespan
)

# 配置 CORS（允许前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加性能监控中间件
add_timing_middleware(app, record=lambda msg: logger.debug(msg))

# Trace-Id 中间件：为每个请求注入/传播 trace id，并记录请求起止
@app.middleware("http")
async def trace_id_middleware(request, call_next):
    incoming = request.headers.get("X-Trace-Id") or request.headers.get("X-Request-Id")
    trace_id = ensure_trace_id(incoming)
    reporter = get_progress_reporter("http")
    reporter.on_request_start(request.method, request.url.path)
    try:
        response = await call_next(request)
        reporter.on_request_end(request.method, request.url.path, response.status_code)
        response.headers["X-Trace-Id"] = trace_id
        return response
    except Exception as e:
        reporter.on_error(str(e))
        raise

# 导入并注册路由
from api.chat_langchain import router as chat_langchain_router
from api.bridge_logger import router as bridge_logger_router
from TelegramBot.webhook import router as telegram_webhook_router

app.include_router(chat_langchain_router, prefix="/api", tags=["聊天"])
app.include_router(bridge_logger_router, prefix="/api", tags=["桥接日志"])
app.include_router(telegram_webhook_router, prefix="/telegram", tags=["Telegram Bot"])

# MCP HTTP 集成版已移除：本项目仅保留两个 stdio 版本（Cursor/Codex 客户端各自启动）


@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "service": "Kobe Backend API",
        "status": "running",
        "version": "2.0.0",
        "features": {
            "chat": True,
            "telegram_bot": True,
            "mcp_server": True,
            "mcp_transport": "RMCP (POST /mcp + GET /mcp/stream)",
            "mcp_endpoints": {"rpc": "POST /mcp", "stream": "GET /mcp/stream"},
            "documentation": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    # Windows环境下禁用reload以避免进程爆炸
    # 如需开发模式，请手动重启服务或使用 --reload 参数单独运行
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # 禁用自动重载避免Windows下进程问题
        log_level="debug",
        log_config=None
    )
