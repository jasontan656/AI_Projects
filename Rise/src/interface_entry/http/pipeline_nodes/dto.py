from __future__ import annotations

"""Pydantic DTOs for pipeline node endpoints."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PipelineNodeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    allowLLM: bool
    systemPrompt: str
    createdAt: datetime
    pipelineId: Optional[str] = Field(default=None, min_length=1)
    status: str = Field(default="draft", pattern=r"^(draft|published)$")
    strategy: Dict[str, Any] = Field(default_factory=dict)


class PipelineNodeUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    allowLLM: Optional[bool] = None
    systemPrompt: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern=r"^(draft|published)$")
    pipelineId: Optional[str] = Field(default=None, min_length=1)
    strategy: Optional[Dict[str, Any]] = None


class PipelineNodeSnapshot(BaseModel):
    id: str
    name: str
    allowLLM: bool
    systemPrompt: str
    pipelineId: Optional[str] = None
    status: str
    strategy: Dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime
    clientCreatedAt: Optional[datetime] = None
    updatedAt: datetime
    version: int
    updatedBy: Optional[str] = None


class PipelineNodeResponse(PipelineNodeSnapshot):
    latestSnapshot: PipelineNodeSnapshot


class PipelineNodeListResponse(BaseModel):
    page: int
    pageSize: int
    total: int
    items: list[PipelineNodeResponse]
