"""
Telegram Bot 数据模型
使用 Pydantic v2 定义 Telegram API 消息结构
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class TelegramUser(BaseModel):
    """Telegram 用户模型"""
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None


class TelegramChat(BaseModel):
    """Telegram 聊天模型"""
    id: int
    type: str  # "private", "group", "supergroup", "channel"
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class TelegramMessageEntity(BaseModel):
    """消息实体（提及、标签等）"""
    type: str  # "mention", "hashtag", "bot_command", etc.
    offset: int
    length: int
    url: Optional[str] = None
    user: Optional[TelegramUser] = None


class TelegramMessage(BaseModel):
    """Telegram 消息模型"""
    message_id: int
    from_user: Optional[TelegramUser] = Field(None, alias="from")
    chat: TelegramChat
    date: int
    text: Optional[str] = None
    entities: Optional[List[TelegramMessageEntity]] = None
    reply_to_message: Optional["TelegramMessage"] = None
    
    model_config = {"populate_by_name": True}
    
    def is_private_chat(self) -> bool:
        """判断是否为私聊"""
        return self.chat.type == "private"
    
    def is_group_chat(self) -> bool:
        """判断是否为群组"""
        return self.chat.type in ["group", "supergroup"]
    
    def mentions_bot(self, bot_username: str) -> bool:
        """判断是否提及机器人"""
        if not self.entities:
            return False
        
        # 检查 @mention
        for entity in self.entities:
            if entity.type == "mention" and self.text:
                start = entity.offset
                end = start + entity.length
                mention = self.text[start:end]
                if mention.lower() == f"@{bot_username.lower()}":
                    return True
        
        return False
    
    def contains_keywords(self, keywords: List[str]) -> bool:
        """判断消息是否包含关键词"""
        if not self.text or not keywords:
            return False
        
        text_lower = self.text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)


class TelegramUpdate(BaseModel):
    """Telegram Webhook 更新模型"""
    update_id: int
    message: Optional[TelegramMessage] = None
    edited_message: Optional[TelegramMessage] = None
    channel_post: Optional[TelegramMessage] = None
    edited_channel_post: Optional[TelegramMessage] = None
    
    def get_message(self) -> Optional[TelegramMessage]:
        """获取消息对象（优先取 message，其次 edited_message）"""
        return self.message or self.edited_message


class SendMessageRequest(BaseModel):
    """发送消息请求模型"""
    chat_id: int
    text: str
    reply_to_message_id: Optional[int] = None
    parse_mode: Optional[str] = "Markdown"  # "Markdown" or "HTML"

