"""
Telegram Bot Webhook 路由
FastAPI 路由定义，接收 Telegram Webhook 请求
支持多机器人动态路由
"""

import logging
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Path
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from TelegramBot.models import TelegramUpdate
from TelegramBot.config import get_config
from TelegramBot.handlers.message_handler import create_message_handler
from TelegramBot.services.telegram_service import create_telegram_service
from SharedUtility.RichLogger.logger import RichLoggerManager

# 确保全局日志已初始化
RichLoggerManager.bootstrap()
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook/{bot_name}")
async def telegram_webhook(
    bot_name: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Telegram Webhook 端点（支持多机器人）
    
    Args:
        bot_name: 机器人标识名（从路由路径提取）
        
    接收来自 Telegram 的更新并异步处理
    """
    try:
        config = get_config()
        
        # 根据 bot_name 获取机器人配置
        bot_instance = config.get_bot_by_name(bot_name)
        if not bot_instance:
            logger.warning(f"未找到机器人配置: {bot_name}")
            raise HTTPException(status_code=404, detail=f"Bot '{bot_name}' not found")
        
        # 验证请求（可选：检查 X-Telegram-Bot-Api-Secret-Token）
        if config.telegram_webhook_secret:
            secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret_token != config.telegram_webhook_secret:
                logger.warning(f"Webhook 密钥验证失败: bot={bot_name}")
                raise HTTPException(status_code=403, detail="Invalid secret token")
        
        # 解析请求体
        body = await request.json()
        
        # 验证并解析为 TelegramUpdate 对象
        try:
            update = TelegramUpdate(**body)
        except ValidationError as e:
            logger.error(f"消息格式验证失败: {e}")
            return JSONResponse({"ok": False, "error": "Invalid update format"}, status_code=400)
        
        logger.info(f"收到 Webhook 更新: bot={bot_name}, update_id={update.update_id}")
        
        # 为该机器人创建专用的消息处理器
        handler = create_message_handler(bot_instance.token)
        logger.info(f"消息处理器已创建: bot={bot_name}")
        
        # 包装异步任务以捕获异常
        async def process_with_error_handling():
            try:
                logger.info(f"开始处理消息: update_id={update.update_id}")
                result = await handler.handle_update(update)
                logger.info(f"消息处理完成: update_id={update.update_id}, result={result}")
            except Exception as e:
                logger.error(f"消息处理异常: {str(e)}", exc_info=True)
        
        # 异步处理消息（不阻塞响应）
        background_tasks.add_task(process_with_error_handling)
        
        # 立即返回 200 OK
        return JSONResponse({"ok": True})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook 处理异常: {str(e)}", exc_info=True)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/setup-webhook/{bot_name}")
async def setup_webhook(bot_name: str):
    """
    设置 Webhook（支持多机器人）
    
    Args:
        bot_name: 机器人标识名
    """
    try:
        config = get_config()
        
        # 获取机器人配置
        bot_instance = config.get_bot_by_name(bot_name)
        if not bot_instance:
            raise HTTPException(
                status_code=404,
                detail=f"Bot '{bot_name}' not found in configuration"
            )
        
        if not config.telegram_webhook_url:
            raise HTTPException(
                status_code=400,
                detail="TELEGRAM_WEBHOOK_URL not configured in .env"
            )
        
        telegram_service = create_telegram_service(bot_instance.token)
        
        # 构建完整的 Webhook URL
        full_webhook_url = f"{config.telegram_webhook_url}{bot_instance.webhook_path}"
        
        # 设置 Webhook
        success = await telegram_service.set_webhook(
            webhook_url=full_webhook_url,
            secret_token=config.telegram_webhook_secret
        )
        
        if success:
            return {
                "ok": True,
                "message": f"Webhook 设置成功: {bot_name}",
                "bot_name": bot_name,
                "webhook_url": full_webhook_url
            }
        else:
            raise HTTPException(status_code=500, detail="Webhook 设置失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置 Webhook 异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/setup-all-webhooks")
async def setup_all_webhooks():
    """
    一键设置所有机器人的 Webhook
    """
    try:
        config = get_config()
        bots = config.get_bots()
        
        if not config.telegram_webhook_url:
            raise HTTPException(
                status_code=400,
                detail="TELEGRAM_WEBHOOK_URL not configured in .env"
            )
        
        results = []
        
        for bot_instance in bots:
            try:
                telegram_service = create_telegram_service(bot_instance.token)
                full_webhook_url = f"{config.telegram_webhook_url}{bot_instance.webhook_path}"
                
                success = await telegram_service.set_webhook(
                    webhook_url=full_webhook_url,
                    secret_token=config.telegram_webhook_secret
                )
                
                results.append({
                    "bot_name": bot_instance.name,
                    "success": success,
                    "webhook_url": full_webhook_url
                })
                
            except Exception as e:
                results.append({
                    "bot_name": bot_instance.name,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "ok": True,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量设置 Webhook 异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete-webhook/{bot_name}")
async def delete_webhook(bot_name: str):
    """
    删除 Webhook（支持多机器人）
    
    Args:
        bot_name: 机器人标识名
    """
    try:
        config = get_config()
        
        bot_instance = config.get_bot_by_name(bot_name)
        if not bot_instance:
            raise HTTPException(
                status_code=404,
                detail=f"Bot '{bot_name}' not found"
            )
        
        telegram_service = create_telegram_service(bot_instance.token)
        
        success = await telegram_service.delete_webhook()
        
        if success:
            return {"ok": True, "message": f"Webhook 已删除: {bot_name}"}
        else:
            raise HTTPException(status_code=500, detail="删除 Webhook 失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除 Webhook 异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{bot_name}")
async def bot_status(bot_name: str):
    """
    获取机器人状态（支持多机器人）
    
    Args:
        bot_name: 机器人标识名
    """
    try:
        config = get_config()
        
        bot_instance = config.get_bot_by_name(bot_name)
        if not bot_instance:
            raise HTTPException(
                status_code=404,
                detail=f"Bot '{bot_name}' not found"
            )
        
        telegram_service = create_telegram_service(bot_instance.token)
        bot_info = await telegram_service.get_me()
        
        return {
            "ok": True,
            "bot": {
                "name": bot_name,
                "id": bot_info.get("id"),
                "username": bot_info.get("username"),
                "first_name": bot_info.get("first_name")
            },
            "config": {
                "webhook_path": bot_instance.webhook_path,
                "webhook_url": f"{config.telegram_webhook_url}{bot_instance.webhook_path}" if config.telegram_webhook_url else None,
                "group_debounce_seconds": config.telegram_group_debounce_seconds,
                "mode": "私聊立即回复 | 群组被@立即回复 | 群组未@防抖回复"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取状态异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list-bots")
async def list_bots():
    """
    列出所有配置的机器人
    """
    try:
        config = get_config()
        bots = config.get_bots()
        
        return {
            "ok": True,
            "count": len(bots),
            "bots": [
                {
                    "name": bot.name,
                    "webhook_path": bot.webhook_path,
                    "token_preview": bot.token[:10] + "..." if bot.token else None
                }
                for bot in bots
            ]
        }
        
    except Exception as e:
        logger.error(f"列出机器人异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
