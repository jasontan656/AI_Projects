from __future__ import annotations

from shared_utilities.time import Time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ToolInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="UUID of the tool invocation")
    user_id: str
    session_id: Optional[str] = None
    module: str = Field(..., description="Module name e.g. auth, mbti")
    route_path: List[str] = Field(default_factory=list)
    input_summary: Dict[str, Any] = Field(default_factory=dict)
    output_summary: Dict[str, Any] = Field(default_factory=dict)
    next_step: Optional[str] = None
    form_schema: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    status: str = Field(..., description="success|error")
    created_at: "datetime" = Field(default_factory=Time.now)


__all__ = ["ToolInvocation"]

