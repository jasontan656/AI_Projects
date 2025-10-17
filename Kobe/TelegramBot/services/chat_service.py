"""
聊天服务
对接 LangChain 提供智能对话能力
使用 Redis 存储临时上下文（重启即清空）
"""

import logging
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.messages import HumanMessage, AIMessage, SystemMessage
import redis.asyncio as redis

from TelegramBot.config import get_config
from SharedUtility.RichLogger.logger import RichLoggerManager

# 确保全局日志已初始化
RichLoggerManager.bootstrap()
logger = logging.getLogger(__name__)


class ChatService:
    """聊天服务类 - 提供 LangChain 驱动的智能对话"""
    
    def __init__(self):
        """初始化聊天服务"""
        self.config = get_config()
        
        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=self.config.openai_model,
            temperature=0.7,
            streaming=False  # Telegram 使用简单模式，不需要流式
        )
        
        # Redis 客户端（用于临时上下文存储）
        self.redis_client: Optional[redis.Redis] = None
        
        # Prompt 模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个友好、专业的 AI 助手。你在 Telegram 中与用户对话。

对话规则：
1. 保持友好、自然的对话风格
2. 回复简洁明了，避免过长的消息
3. 如果不知道答案，诚实地说明
4. 使用用户的语言回复
5. 在群组中被提及时，直接回复相关内容，无需重复用户的问题

当前环境：Telegram {chat_type}
"""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}")
        ])
        
        logger.info("ChatService 初始化完成")
    
    async def initialize_redis(self):
        """初始化 Redis 连接（异步）"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis 连接已建立（用于上下文存储）")
    
    async def close_redis(self):
        """关闭 Redis 连接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis 连接已关闭")
    
    async def get_chat_context(
        self, 
        bot_id: int,
        chat_id: int, 
        user_id: int, 
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        从 Redis 获取临时上下文（最近几轮对话）
        
        Args:
            bot_id: 机器人 ID
            chat_id: 聊天 ID
            user_id: 用户 ID
            limit: 最多获取轮数（每轮包含用户消息和机器人回复）
            
        Returns:
            上下文列表 [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        await self.initialize_redis()
        
        # Redis key: 每个对话的上下文
        key = f"telegram:context:{bot_id}:{chat_id}:{user_id}"
        
        # 获取最近的消息（Redis List 结构）
        # 每个元素是 JSON 字符串：{"role": "user/assistant", "content": "..."}
        messages_json = await self.redis_client.lrange(key, -limit*2, -1)
        
        if not messages_json:
            return []
        
        # 解析 JSON
        import json
        context = []
        for msg_json in messages_json:
            try:
                context.append(json.loads(msg_json))
            except Exception:
                pass
        
        return context
    
    async def save_chat_context(
        self,
        bot_id: int,
        chat_id: int,
        user_id: int,
        user_message: str,
        bot_reply: str
    ):
        """
        保存对话上下文到 Redis（临时存储）
        
        Args:
            bot_id: 机器人 ID
            chat_id: 聊天 ID
            user_id: 用户 ID
            user_message: 用户消息
            bot_reply: 机器人回复
        """
        await self.initialize_redis()
        
        import json
        
        key = f"telegram:context:{bot_id}:{chat_id}:{user_id}"
        
        # 添加用户消息
        user_msg = json.dumps({"role": "user", "content": user_message}, ensure_ascii=False)
        await self.redis_client.rpush(key, user_msg)
        
        # 添加机器人回复
        bot_msg = json.dumps({"role": "assistant", "content": bot_reply}, ensure_ascii=False)
        await self.redis_client.rpush(key, bot_msg)
        
        # 设置过期时间：1小时（电脑关机或重启后自动清空）
        await self.redis_client.expire(key, 3600)
        
        # 保留最近 10 轮对话（20条消息）
        await self.redis_client.ltrim(key, -20, -1)
        
        logger.debug(f"已保存上下文到 Redis: chat_id={chat_id}, user_id={user_id}")
    
    async def chat(
        self,
        bot_id: int,
        message: str,
        chat_id: int,
        user_id: int,
        username: Optional[str] = None,
        chat_type: str = "private"
    ) -> str:
        """
        处理聊天消息，返回 AI 回复
        
        Args:
            bot_id: 机器人 ID
            message: 用户消息
            chat_id: 聊天 ID
            user_id: 用户 ID
            username: 用户名（可选）
            chat_type: 聊天类型（private/group）
            
        Returns:
            AI 回复内容
        """
        try:
            logger.info(f"收到消息: bot_id={bot_id}, chat_id={chat_id}, user_id={user_id}, type={chat_type}")
            
            # 从 Redis 获取临时上下文（最近 5 轮）
            context_data = await self.get_chat_context(bot_id, chat_id, user_id, limit=5)
            
            # 构建 LangChain 消息历史
            chat_history = []
            for ctx in context_data:
                if ctx.get("role") == "user":
                    chat_history.append(HumanMessage(content=ctx.get("content", "")))
                elif ctx.get("role") == "assistant":
                    chat_history.append(AIMessage(content=ctx.get("content", "")))
            
            # 构建 Prompt
            formatted_prompt = self.prompt.format_messages(
                chat_type=chat_type,
                chat_history=chat_history,
                input=message
            )
            
            # 调用 LLM
            logger.debug("正在调用 LLM...")
            response = await self.llm.ainvoke(formatted_prompt)
            reply = response.content
            
            logger.info(f"LLM 回复生成完成: {len(reply)} 字符")
            
            # 保存上下文到 Redis（临时存储，重启清空）
            await self.save_chat_context(
                bot_id=bot_id,
                chat_id=chat_id,
                user_id=user_id,
                user_message=message,
                bot_reply=reply
            )
            
            return reply
            
        except Exception as e:
            logger.error(f"聊天服务错误: {str(e)}", exc_info=True)
            return "抱歉，我现在无法回复。请稍后再试。"


# 全局单例
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """获取聊天服务单例"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
