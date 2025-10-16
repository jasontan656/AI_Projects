"""
MongoDB数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """聊天消息基础模型"""
    message_id: int
    chat_id: int
    user_id: int
    text: str
    timestamp: datetime
    platform: str  # "telegram", "wechat", etc.
    metadata: Optional[Dict[str, Any]] = None


class UserProfile(BaseModel):
    """用户画像模型"""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tags: List[str] = []
    profile_data: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class GroupProfile(BaseModel):
    """群组画像模型"""
    chat_id: int
    group_name: Optional[str] = None
    member_count: int = 0
    tags: List[str] = []
    profile_data: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class KnowledgeGap(BaseModel):
    """知识缺口记录模型"""
    question: str
    user_id: int
    chat_id: int
    context: Dict[str, Any]
    status: str = "pending"  # pending, reviewed, resolved
    created_at: datetime

