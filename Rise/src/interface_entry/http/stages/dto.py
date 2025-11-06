from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, Field

__all__ = [
    "StageRequest",
    "StageResponse",
]


class StageRequest(BaseModel):
    name: str = Field(..., description="阶段名称")
    promptTemplate: str = Field(..., description="阶段提示词模板")
    description: str = Field("", description="阶段描述")
    toolIds: Optional[Sequence[str]] = Field(default=None, description="引用的工具 ID 列表")
    metadata: Optional[Mapping[str, Any]] = Field(default=None, description="自定义元数据")


class StageResponse(BaseModel):
    id: str = Field(..., alias="stageId")
    name: str
    description: str
    promptTemplate: str
    toolIds: Sequence[str] = Field(default_factory=list)
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    version: int
    updatedAt: Any
    updatedBy: Optional[str] = None

    class Config:
        populate_by_name = True
