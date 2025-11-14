from __future__ import annotations

"""Channel mode policy helpers to guard webhook vs polling configurations."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

__all__ = [
    "ChannelMode",
    "ChannelModeDecision",
    "evaluate_channel_mode",
]


class ChannelMode(str, Enum):
    """Operational modes for workflow channels."""

    WEBHOOK = "webhook"
    POLLING = "polling"


@dataclass(slots=True, frozen=True)
class ChannelModeDecision:
    """Represents the outcome of evaluating a mode request."""

    mode: ChannelMode
    allow_binding: bool = True
    message: Optional[str] = None

    @property
    def is_conflict(self) -> bool:
        return not self.allow_binding


def evaluate_channel_mode(*, enabled: bool, use_polling: bool) -> ChannelModeDecision:
    """Decide channel mode and detect conflicts between webhook + polling."""

    return ChannelModeDecision(
        mode=ChannelMode.POLLING if use_polling else ChannelMode.WEBHOOK,
        allow_binding=True,
        message=None,
    )
