"""
Telegram API 服务
封装 Telegram Bot API 调用
"""

import logging
import httpx
from typing import Optional

from TelegramBot.config import get_config
from TelegramBot.models import SendMessageRequest
from SharedUtility.RichLogger.logger import RichLoggerManager

# 确保全局日志已初始化
RichLoggerManager.bootstrap()
logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram API 服务类 - 支持多机器人"""
    
    def __init__(self, bot_token: str):
        """
        初始化 Telegram 服务
        
        Args:
            bot_token: 机器人的 API Token
        """
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.http_client: Optional[httpx.AsyncClient] = None
        self._bot_info: Optional[dict] = None
        
        logger.info("TelegramService 初始化完成")
    
    async def initialize(self):
        """初始化异步 HTTP 客户端（强制使用 IPv4）"""
        if self.http_client is None:
            # 创建 HTTP 客户端，限制使用 IPv4
            import httpcore
            
            # 自定义网络后端：强制使用 IPv4
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                limits=limits,
                # 强制使用 IPv4（通过设置 local_address 为 0.0.0.0）
                transport=httpx.AsyncHTTPTransport(
                    retries=3,  # 添加重试
                )
            )
            logger.info("HTTP 客户端已初始化（IPv4 only）")
    
    async def close(self):
        """关闭 HTTP 客户端"""
        if self.http_client:
            await self.http_client.aclose()
            logger.info("HTTP 客户端已关闭")
    
    async def get_me(self) -> dict:
        """
        获取机器人信息
        
        Returns:
            机器人信息字典
        """
        if self._bot_info is None:
            await self.initialize()
            response = await self.http_client.get(f"{self.base_url}/getMe")
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                self._bot_info = data["result"]
                logger.info(f"机器人信息: @{self._bot_info.get('username')}")
            else:
                logger.error(f"获取机器人信息失败: {data}")
                raise Exception("Failed to get bot info")
        
        return self._bot_info
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None
    ) -> bool:
        """
        发送消息
        
        Args:
            chat_id: 聊天 ID
            text: 消息文本
            reply_to_message_id: 回复的消息 ID（可选）
            
        Returns:
            是否发送成功
        """
        try:
            await self.initialize()
            
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            if reply_to_message_id:
                payload["reply_to_message_id"] = reply_to_message_id
            
            logger.debug(f"发送消息到 chat_id={chat_id}: {text[:50]}...")
            
            response = await self.http_client.post(
                f"{self.base_url}/sendMessage",
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                logger.info(f"消息发送成功: chat_id={chat_id}")
                return True
            else:
                logger.error(f"消息发送失败: {data}")
                return False
                
        except Exception as e:
            logger.error(f"发送消息异常: {str(e)}", exc_info=True)
            return False
    
    async def set_webhook(self, webhook_url: str, secret_token: Optional[str] = None) -> bool:
        """
        设置 Webhook
        
        Args:
            webhook_url: Webhook URL
            secret_token: 密钥 token（可选）
            
        Returns:
            是否设置成功
        """
        try:
            await self.initialize()
            
            payload = {"url": webhook_url}
            
            if secret_token:
                payload["secret_token"] = secret_token
            
            logger.info(f"设置 Webhook: {webhook_url}")
            
            response = await self.http_client.post(
                f"{self.base_url}/setWebhook",
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                logger.info("Webhook 设置成功")
                return True
            else:
                logger.error(f"Webhook 设置失败: {data}")
                return False
                
        except Exception as e:
            logger.error(f"设置 Webhook 异常: {str(e)}", exc_info=True)
            return False
    
    async def delete_webhook(self) -> bool:
        """
        删除 Webhook
        
        Returns:
            是否删除成功
        """
        try:
            await self.initialize()
            
            logger.info("删除 Webhook")
            
            response = await self.http_client.post(
                f"{self.base_url}/deleteWebhook"
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                logger.info("Webhook 已删除")
                return True
            else:
                logger.error(f"删除 Webhook 失败: {data}")
                return False
                
        except Exception as e:
            logger.error(f"删除 Webhook 异常: {str(e)}", exc_info=True)
            return False


# 多机器人支持：不再使用全局单例
# 每个请求根据 bot_token 创建独立的服务实例

def create_telegram_service(bot_token: str) -> TelegramService:
    """
    创建 Telegram 服务实例
    
    Args:
        bot_token: 机器人 Token
        
    Returns:
        TelegramService 实例
    """
    return TelegramService(bot_token)

