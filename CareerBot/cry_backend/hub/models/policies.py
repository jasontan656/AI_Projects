from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MemoryRetentionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: Literal["MongoDB"] = Field(default="MongoDB")
    key_format: str = Field(default="{user_id}:{session_id}")
    ttl_hours: int = Field(default=24, ge=1)


__all__ = ["MemoryRetentionPolicy"]

