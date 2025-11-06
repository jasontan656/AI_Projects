from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, Field

__all__ = [
    "WorkflowRequest",
    "WorkflowResponse",
]


class WorkflowRequest(BaseModel):
    name: str = Field(..., description="流程名称")
    description: str = Field("", description="流程描述")
    stageIds: Optional[Sequence[str]] = Field(default=None, description="阶段 ID 顺序列表")
    metadata: Optional[Mapping[str, Any]] = Field(default=None, description="自定义元数据")


class WorkflowResponse(BaseModel):
    id: str = Field(..., alias="workflowId")
    name: str
    description: str
    stageIds: Sequence[str] = Field(default_factory=list)
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    version: int
    updatedAt: Any
    updatedBy: Optional[str] = None

    class Config:
        populate_by_name = True
