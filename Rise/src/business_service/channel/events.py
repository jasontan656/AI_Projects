"""Backwards-compatible exports for channel binding event DTOs."""
from __future__ import annotations

from foundational_service.contracts.channel_events import (  # noqa: F401
    CHANNEL_BINDING_HEALTH_TOPIC,
    CHANNEL_BINDING_TOPIC,
    ChannelBindingEvent,
    ChannelBindingHealthEvent,
)

__all__ = [
    "CHANNEL_BINDING_TOPIC",
    "CHANNEL_BINDING_HEALTH_TOPIC",
    "ChannelBindingEvent",
    "ChannelBindingHealthEvent",
]
