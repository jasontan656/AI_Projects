from __future__ import annotations

"""Conversation domain business services."""

from business_service.conversation.models import ConversationServiceResult
from business_service.conversation.primitives import AdapterBuilder, AgentDelegator
from business_service.conversation.service import (
    TelegramConversationService,
    behavior_telegram_inbound,
    behavior_telegram_outbound,
    set_behavior_hooks,
)

__all__ = [
    "AdapterBuilder",
    "AgentDelegator",
    "ConversationServiceResult",
    "behavior_telegram_inbound",
    "behavior_telegram_outbound",
    "set_behavior_hooks",
    "TelegramConversationService",
]
