#!/usr/bin/env python3
"""
快速设置 Telegram Webhook
使用方法：python TelegramBot/setup_webhook.py
"""

import asyncio
import sys
from pathlib import Path

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from TelegramBot.services.telegram_service import get_telegram_service
from TelegramBot.config import get_config
from SharedUtility.RichLogger.logger import RichLoggerManager

logger = RichLoggerManager.get_logger(__name__)


async def main():
    """设置 Webhook"""
    try:
        config = get_config()
        
        # 验证配置
        if not config.telegram_bot_token or config.telegram_bot_token == "你的机器人token":
            logger.error("请先在 .env 中配置 TELEGRAM_BOT_TOKEN")
            return False
        
        if not config.telegram_webhook_url:
            logger.error("请先在 .env 中配置 TELEGRAM_WEBHOOK_URL（ngrok 地址）")
            return False
        
        logger.info("=" * 60)
        logger.info("Telegram Bot Webhook 设置工具")
        logger.info("=" * 60)
        
        # 获取机器人信息
        telegram_service = get_telegram_service()
        bot_info = await telegram_service.get_me()
        
        logger.info(f"机器人名称: {bot_info.get('first_name')}")
        logger.info(f"机器人用户名: @{bot_info.get('username')}")
        logger.info(f"机器人 ID: {bot_info.get('id')}")
        logger.info("-" * 60)
        
        # 设置 Webhook
        webhook_url = f"{config.telegram_webhook_url}/telegram/webhook"
        logger.info(f"Webhook URL: {webhook_url}")
        
        success = await telegram_service.set_webhook(
            webhook_url=webhook_url,
            secret_token=config.telegram_webhook_secret
        )
        
        if success:
            logger.info("✓ Webhook 设置成功！")
            logger.info("-" * 60)
            logger.info("下一步：")
            logger.info("1. 在 Telegram 中找到你的机器人")
            logger.info("2. 发送任意消息测试")
            logger.info("3. 或将机器人添加到群组并 @提及测试")
            return True
        else:
            logger.error("✗ Webhook 设置失败")
            return False
        
    except Exception as e:
        logger.error(f"设置失败: {str(e)}", exc_info=True)
        return False
    finally:
        # 清理资源
        if telegram_service:
            await telegram_service.close()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

