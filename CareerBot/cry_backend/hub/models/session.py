from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from shared_utilities.time import Time


class ConversationSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="UUID of the conversation session")
    user_id: str = Field(..., description="Canonical user identifier")
    session_id: Optional[str] = Field(default=None, description="Client/session id if provided")
    context_ref: Optional[str] = Field(default=None, description="MongoDB key to memory context")
    last_step_id: Optional[str] = Field(default=None, description="Last processed step id")
    created_at: "datetime" = Field(default_factory=Time.now)
    updated_at: "datetime" = Field(default_factory=Time.now)


__all__ = ["ConversationSession"]
