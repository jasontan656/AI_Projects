"""
消息处理器
处理 Telegram 消息并决定如何响应
支持群组消息防抖（Debouncing）机制
"""

import logging
import asyncio
from typing import Optional, Dict
import redis.asyncio as redis

from TelegramBot.models import TelegramMessage, TelegramUpdate
from TelegramBot.config import get_config, BotInstance
from TelegramBot.services.chat_service import get_chat_service
from TelegramBot.services.telegram_service import TelegramService, create_telegram_service
from SharedUtility.RichLogger.logger import RichLoggerManager

# 确保全局日志已初始化
RichLoggerManager.bootstrap()
logger = logging.getLogger(__name__)


class MessageHandler:
    """消息处理器类 - 支持群组消息防抖和多机器人"""
    
    def __init__(self, bot_token: str):
        """
        初始化消息处理器
        
        Args:
            bot_token: 机器人的 API Token
        """
        self.config = get_config()
        self.bot_token = bot_token
        self.chat_service = get_chat_service()
        self.telegram_service = create_telegram_service(bot_token)
        self.redis_client: Optional[redis.Redis] = None
        self._bot_username: Optional[str] = None
        self._bot_id: Optional[int] = None  # 存储机器人 ID
        
        # 存储待处理的延迟任务 {key: asyncio.Task}
        self.pending_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info(f"MessageHandler 初始化完成: token={bot_token[:10]}...")
    
    async def initialize(self):
        """初始化异步资源（仅首次调用时执行）"""
        # 初始化 Redis 连接
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis 连接已建立")
            
            # 仅在首次初始化时获取机器人信息（避免重复调用 API）
            try:
                bot_info = await self.telegram_service.get_me()
                self._bot_username = bot_info.get("username", "")
                self._bot_id = bot_info.get("id")
                logger.info(f"机器人信息已缓存: @{self._bot_username} (ID: {self._bot_id})")
            except Exception as e:
                logger.error(f"获取机器人信息失败: {e}")
                # 设置默认值，避免阻塞
                self._bot_username = "unknown"
                self._bot_id = 0
    
    async def close(self):
        """关闭资源"""
        # 取消所有待处理的任务
        for task in self.pending_tasks.values():
            if not task.done():
                task.cancel()
        
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis 连接已关闭")
    
    async def check_rate_limit(self, user_id: int, chat_type: str) -> bool:
        """
        检查速率限制
        
        Args:
            user_id: 用户 ID
            chat_type: 聊天类型
            
        Returns:
            是否超过限制（True = 超限，False = 未超限）
        """
        await self.initialize()
        
        # 根据聊天类型选择限制
        if chat_type == "private":
            limit = self.config.telegram_user_rate_limit
        else:
            limit = self.config.telegram_group_rate_limit
        
        # 速率限制键：包含 bot_id 以支持多机器人
        key = f"telegram:rate_limit:{self._bot_id}:{user_id}"
        
        # 使用 Redis INCR 和 EXPIRE 实现滑动窗口
        current = await self.redis_client.incr(key)
        
        if current == 1:
            # 首次请求，设置过期时间
            await self.redis_client.expire(key, 60)  # 1 分钟窗口
        
        if current > limit:
            logger.warning(f"用户 {user_id} 超过速率限制: {current}/{limit}")
            return True
        
        return False
    
    def clean_message_text(self, message: TelegramMessage) -> str:
        """
        清理消息文本（移除 @提及）
        
        Args:
            message: Telegram 消息
            
        Returns:
            清理后的文本
        """
        text = message.text or ""
        
        # 移除 @bot_username
        if self._bot_username:
            text = text.replace(f"@{self._bot_username}", "").strip()
        
        return text
    
    async def handle_private_message(self, message: TelegramMessage) -> bool:
        """
        处理私聊消息 - 立即回复
        
        Args:
            message: Telegram 消息
            
        Returns:
            是否处理成功
        """
        try:
            user_id = message.from_user.id
            chat_id = message.chat.id
            
            # 检查速率限制
            if await self.check_rate_limit(user_id, "private"):
                await self.telegram_service.send_message(
                    chat_id=chat_id,
                    text="您的消息太频繁了，请稍后再试。",
                    reply_to_message_id=message.message_id
                )
                return False
            
            message_text = self.clean_message_text(message)
            
            if not message_text:
                return False
            
            logger.info(f"处理私聊消息: user={message.from_user.username or user_id}")
            
            # 调用聊天服务生成回复
            reply = await self.chat_service.chat(
                bot_id=self._bot_id,
                message=message_text,
                chat_id=chat_id,
                user_id=user_id,
                username=message.from_user.username,
                chat_type="private"
            )
            
            # 发送回复
            success = await self.telegram_service.send_message(
                chat_id=chat_id,
                text=reply,
                reply_to_message_id=message.message_id
            )
            
            if success:
                logger.info(f"私聊回复已发送: user_id={user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"处理私聊消息异常: {str(e)}", exc_info=True)
            return False
    
    async def handle_group_message_immediate(self, message: TelegramMessage) -> bool:
        """
        处理群组消息 - 立即回复（被 @ 时）
        
        Args:
            message: Telegram 消息
            
        Returns:
            是否处理成功
        """
        try:
            user_id = message.from_user.id
            chat_id = message.chat.id
            
            # 检查速率限制
            if await self.check_rate_limit(user_id, "group"):
                await self.telegram_service.send_message(
                    chat_id=chat_id,
                    text="您的消息太频繁了，请稍后再试。",
                    reply_to_message_id=message.message_id
                )
                return False
            
            message_text = self.clean_message_text(message)
            
            if not message_text:
                return False
            
            logger.info(
                f"处理群组消息（被@）: chat_id={chat_id}, "
                f"user={message.from_user.username or user_id}"
            )
            
            # 调用聊天服务生成回复
            reply = await self.chat_service.chat(
                bot_id=self._bot_id,
                message=message_text,
                chat_id=chat_id,
                user_id=user_id,
                username=message.from_user.username,
                chat_type="group"
            )
            
            # 发送回复
            success = await self.telegram_service.send_message(
                chat_id=chat_id,
                text=reply,
                reply_to_message_id=message.message_id
            )
            
            if success:
                logger.info(f"群组回复已发送（立即）: chat_id={chat_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"处理群组消息异常: {str(e)}", exc_info=True)
            return False
    
    async def handle_group_message_debounced(self, message: TelegramMessage) -> bool:
        """
        处理群组消息 - 防抖模式（未被 @ 时）
        将消息加入队列，15秒后聚合回复
        
        Args:
            message: Telegram 消息
            
        Returns:
            是否处理成功
        """
        try:
            await self.initialize()
            
            user_id = message.from_user.id
            chat_id = message.chat.id
            message_text = self.clean_message_text(message)
            
            if not message_text:
                return False
            
            # Redis key: 包含 bot_id 以支持多机器人
            redis_key = f"telegram:debounce:{self._bot_id}:{chat_id}:{user_id}"
            task_key = f"{self._bot_id}:{chat_id}:{user_id}"
            
            # 1. 将消息追加到 Redis 列表
            await self.redis_client.rpush(redis_key, message_text)
            await self.redis_client.expire(redis_key, 30)  # 30秒过期（保险）
            
            message_count = await self.redis_client.llen(redis_key)
            
            logger.debug(
                f"群组消息加入队列: chat_id={chat_id}, user={user_id}, "
                f"queue_size={message_count}"
            )
            
            # 2. 取消之前的延迟任务（如果存在）
            if task_key in self.pending_tasks:
                old_task = self.pending_tasks[task_key]
                if not old_task.done():
                    old_task.cancel()
                    logger.debug(f"已取消旧的延迟任务: {task_key}")
            
            # 3. 创建新的延迟任务
            delay = self.config.telegram_group_debounce_seconds
            task = asyncio.create_task(
                self._delayed_group_reply(
                    chat_id=chat_id,
                    user_id=user_id,
                    username=message.from_user.username,
                    reply_to_message_id=message.message_id,
                    delay=delay
                )
            )
            self.pending_tasks[task_key] = task
            
            logger.info(
                f"群组防抖任务已创建: chat_id={chat_id}, "
                f"user={user_id}, delay={delay}s"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"处理群组防抖消息异常: {str(e)}", exc_info=True)
            return False
    
    async def _delayed_group_reply(
        self,
        chat_id: int,
        user_id: int,
        username: Optional[str],
        reply_to_message_id: int,
        delay: int
    ):
        """
        延迟回复任务（内部方法）
        
        Args:
            chat_id: 聊天 ID
            user_id: 用户 ID
            username: 用户名
            reply_to_message_id: 回复的消息 ID
            delay: 延迟时间（秒）
        """
        try:
            # 等待延迟时间
            await asyncio.sleep(delay)
            
            # Redis key 需要包含 bot_id
            bot_id = self._bot_id
            redis_key = f"telegram:debounce:{bot_id}:{chat_id}:{user_id}"
            task_key = f"{bot_id}:{chat_id}:{user_id}"
            
            # 获取所有聚合的消息
            messages = await self.redis_client.lrange(redis_key, 0, -1)
            
            if not messages:
                logger.warning(f"延迟任务执行时消息队列为空: {task_key}")
                return
            
            # 聚合消息
            combined_message = "\n".join(messages)
            message_count = len(messages)
            
            logger.info(
                f"开始处理聚合消息: chat_id={chat_id}, user={user_id}, "
                f"message_count={message_count}"
            )
            
            # 检查速率限制
            if await self.check_rate_limit(user_id, "group"):
                await self.telegram_service.send_message(
                    chat_id=chat_id,
                    text="您的消息太频繁了，请稍后再试。",
                    reply_to_message_id=reply_to_message_id
                )
                return
            
            # 调用聊天服务生成回复
            reply = await self.chat_service.chat(
                bot_id=bot_id,
                message=combined_message,
                chat_id=chat_id,
                user_id=user_id,
                username=username,
                chat_type="group"
            )
            
            # 发送回复
            success = await self.telegram_service.send_message(
                chat_id=chat_id,
                text=reply,
                reply_to_message_id=reply_to_message_id
            )
            
            if success:
                logger.info(
                    f"群组聚合回复已发送: chat_id={chat_id}, "
                    f"聚合了 {message_count} 条消息"
                )
            
            # 清理 Redis
            await self.redis_client.delete(redis_key)
            
            # 清理任务记录
            if task_key in self.pending_tasks:
                del self.pending_tasks[task_key]
            
        except asyncio.CancelledError:
            logger.debug(f"延迟任务被取消: chat_id={chat_id}, user={user_id}")
            # 任务被取消是正常情况（用户继续发消息）
        except Exception as e:
            logger.error(f"延迟回复任务异常: {str(e)}", exc_info=True)
    
    async def handle_message(self, message: TelegramMessage) -> bool:
        """
        处理单条消息（主入口）
        
        逻辑：
        1. 私聊 -> 立即回复
        2. 群组被 @ -> 立即回复
        3. 群组未被 @ -> 15秒防抖
        
        Args:
            message: Telegram 消息
            
        Returns:
            是否处理成功
        """
        try:
            await self.initialize()
            
            # 忽略没有文本的消息
            if not message.text:
                logger.debug("跳过消息: 无文本内容")
                return False
            
            # 私聊：立即回复
            if message.is_private_chat():
                return await self.handle_private_message(message)
            
            # 群组：检查是否被 @
            if message.is_group_chat():
                is_mentioned = message.mentions_bot(self._bot_username)
                
                if is_mentioned:
                    # 被 @ 时：立即回复
                    return await self.handle_group_message_immediate(message)
                else:
                    # 未被 @ 时：15秒防抖
                    return await self.handle_group_message_debounced(message)
            
            return False
            
        except Exception as e:
            logger.error(f"处理消息异常: {str(e)}", exc_info=True)
            return False
    
    async def handle_update(self, update: TelegramUpdate) -> bool:
        """
        处理 Telegram Update
        
        Args:
            update: Telegram 更新对象
            
        Returns:
            是否处理成功
        """
        message = update.get_message()
        
        if message:
            return await self.handle_message(message)
        
        logger.debug(f"跳过更新: update_id={update.update_id}, 无消息对象")
        return False


# 多机器人支持：不再使用全局单例
# 每个请求根据 bot_token 创建独立的处理器实例

def create_message_handler(bot_token: str) -> MessageHandler:
    """
    创建消息处理器实例
    
    Args:
        bot_token: 机器人 Token
        
    Returns:
        MessageHandler 实例
    """
    return MessageHandler(bot_token)
