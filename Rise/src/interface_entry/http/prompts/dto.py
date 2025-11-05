from __future__ import annotations

"""Pydantic DTOs for prompt management endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PromptPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    markdown: str = Field(..., min_length=1)


class PromptUpdatePayload(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    markdown: Optional[str] = Field(default=None, min_length=1)


class PromptResponse(BaseModel):
    id: str = Field(serialization_alias="id")
    name: str
    markdown: str
    createdAt: datetime
    updatedAt: datetime
    version: int
    updatedBy: Optional[str] = None


class PromptListResponse(BaseModel):
    page: int
    pageSize: int
    total: int
    items: list[PromptResponse]
