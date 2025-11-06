from __future__ import annotations

from typing import Any, Mapping, Optional

from pydantic import BaseModel, Field

__all__ = [
    "ToolRequest",
    "ToolResponse",
]


class ToolRequest(BaseModel):
    name: str = Field(..., description="工具名称")
    description: str = Field("", description="工具说明")
    promptSnippet: str = Field("", description="将嵌入到提示词中的片段")
    metadata: Optional[Mapping[str, Any]] = Field(default=None, description="自定义扩展字段")


class ToolResponse(BaseModel):
    id: str = Field(..., alias="toolId")
    name: str
    description: str
    promptSnippet: str
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    version: int
    updatedAt: Any
    updatedBy: Optional[str] = None

    class Config:
        populate_by_name = True
