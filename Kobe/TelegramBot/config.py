"""
Telegram Bot 配置管理
基于 Pydantic v2 Settings 实现类型安全的配置加载
支持多机器人场景
"""

import os
import json
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotInstance(BaseModel):
    """单个机器人实例配置"""
    name: str  # 机器人标识名（用于路由路径）
    token: str  # Bot Token
    webhook_path: str  # Webhook 路径（如 /telegram/bot1/webhook）
    

class TelegramBotConfig(BaseSettings):
    """Telegram Bot 配置类 - 支持多机器人"""
    
    model_config = SettingsConfigDict(
        env_file=".env",  # 使用相对路径，从项目根目录查找
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # 单机器人配置（向后兼容）
    telegram_bot_token: Optional[str] = Field(
        None,
        description="Telegram Bot API Token（单机器人模式）",
        alias="TELEGRAM_BOT_TOKEN"
    )
    
    # 多机器人配置（JSON格式）
    telegram_bots_json: Optional[str] = Field(
        None,
        description="多机器人配置（JSON数组）",
        alias="TELEGRAM_BOTS_JSON"
    )
    
    # Webhook 配置
    telegram_webhook_url: Optional[str] = Field(
        None,
        description="Webhook 公网 URL（ngrok/Cloudflare Tunnel 等）",
        alias="TELEGRAM_WEBHOOK_URL"
    )
    
    telegram_webhook_secret: Optional[str] = Field(
        None,
        description="Webhook 密钥（用于验证请求来源）",
        alias="TELEGRAM_WEBHOOK_SECRET"
    )
    
    # 群组消息处理配置
    telegram_group_debounce_seconds: int = Field(
        15,
        description="群组消息防抖延迟（秒）- 用户停止发送消息后等待的时间",
        alias="TELEGRAM_GROUP_DEBOUNCE_SECONDS"
    )
    
    # 速率限制
    telegram_user_rate_limit: int = Field(
        10,
        description="用户消息速率限制（条/分钟）",
        alias="TELEGRAM_USER_RATE_LIMIT"
    )
    
    telegram_group_rate_limit: int = Field(
        20,
        description="群组消息速率限制（条/分钟）",
        alias="TELEGRAM_GROUP_RATE_LIMIT"
    )
    
    # LLM 配置
    openai_model: str = Field(
        "gpt-4o-mini",
        description="OpenAI 模型名称",
        alias="OPENAI_MODEL"
    )
    
    # Redis 配置（用于速率限制、防抖队列、临时上下文存储）
    redis_url: str = Field(
        "redis://localhost:6379/0",
        alias="REDIS_URL"
    )
    
    def get_bots(self) -> List[BotInstance]:
        """
        获取所有机器人实例配置
        
        优先使用 TELEGRAM_BOTS_JSON，如果不存在则使用单机器人配置
        
        Returns:
            机器人实例列表
        """
        # 方式 1：多机器人 JSON 配置
        if self.telegram_bots_json:
            try:
                # 去除首尾空格和可能的 BOM
                json_str = self.telegram_bots_json.strip()
                if json_str.startswith('\ufeff'):  # 移除 UTF-8 BOM
                    json_str = json_str[1:]
                
                bots_data = json.loads(json_str)
                return [BotInstance(**bot) for bot in bots_data]
            except json.JSONDecodeError as e:
                # 打印详细错误信息用于调试
                import logging
                logging.error(f"JSON 解析失败: {e}")
                logging.error(f"JSON 内容 (前100字符): {repr(self.telegram_bots_json[:100])}")
                raise ValueError(f"TELEGRAM_BOTS_JSON 格式错误: {e}")
            except Exception as e:
                raise ValueError(f"TELEGRAM_BOTS_JSON 配置错误: {e}")
        
        # 方式 2：单机器人配置（向后兼容）
        if self.telegram_bot_token:
            return [
                BotInstance(
                    name="default",
                    token=self.telegram_bot_token,
                    webhook_path="/telegram/webhook"
                )
            ]
        
        raise ValueError("未配置机器人：请设置 TELEGRAM_BOT_TOKEN 或 TELEGRAM_BOTS_JSON")
    
    def get_bot_by_name(self, name: str) -> Optional[BotInstance]:
        """根据名称获取机器人配置"""
        bots = self.get_bots()
        for bot in bots:
            if bot.name == name:
                return bot
        return None
    
    def get_bot_by_token(self, token: str) -> Optional[BotInstance]:
        """根据 token 获取机器人配置"""
        bots = self.get_bots()
        for bot in bots:
            if bot.token == token:
                return bot
        return None


# 全局配置实例
_config: Optional[TelegramBotConfig] = None


def get_config() -> TelegramBotConfig:
    """获取全局配置实例（单例模式）"""
    global _config
    if _config is None:
        _config = TelegramBotConfig()
    return _config

