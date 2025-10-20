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
from fastapi import FastAPI
from dotenv import load_dotenv
from SharedUtility.RichLogger.logger import RichLoggerManager
from SharedUtility.RichLogger.trace import ensure_trace_id, get_progress_reporter
from telegram import Bot



# 加载环境变量
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# 初始化全局日志系统（控制台提升到 DEBUG，文件已默认 DEBUG）
logger = RichLoggerManager.bootstrap(console_level=logging.DEBUG)


# 创建 FastAPI 应用
app = FastAPI(
    title="Kobe Backend API",
    description="AI驱动的后端服务，支持聊天、工具调用、数据管理",
    version="2.0.0",
)

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

async def setupTelegram4WaysVisaBot():
    telegramVisaBotToken = os.environ["telegramVisaBotToken"]
    telegramVisaBotSecrets = os.environ["telegramVisaBotSecrets"]
    public_url = os.environ["ngrokPublicUrl"]
    telegramVisaBotWebhookUrl = f"{public_url.rstrip('/')}/telegram/webhook"
    await Bot(token=telegramVisaBotToken).set_webhook(
        url=telegramVisaBotWebhookUrl,
        secret_token=telegramVisaBotSecrets,
        allowed_updates=["message"],
        drop_pending_updates=True,        
    )
    




if __name__ == "__main__":
    asyncio.run(setupTelegram4WaysVisaBot())
    import uvicorn   

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False, 
        log_level="debug",
        log_config=None
    )
