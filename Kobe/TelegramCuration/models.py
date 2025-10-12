from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    message_id: str
    chat_id: str
    sender: str
    text: str | None = None
    created_at: datetime
    reply_to: str | None = None
    media: list[str] | None = None
    reactions: list[str] | None = None
    forwards: int = 0
    is_pinned: bool = False
    is_service: bool = False


class NormalizedMessage(BaseModel):
    message_id: str
    text_clean: Optional[str] = None
    entities: List[str] = []
    urls: List[str] = []
    hashtags: List[str] = []
    mentions: List[str] = []
    created_at: datetime


class Thread(BaseModel):
    thread_id: str
    message_ids: List[str]
    representative: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    topic: Optional[str] = None
    participants: List[str] = []
    turns: int = 0
    coherence_score: float = 0.0


class KnowledgeSlice(BaseModel):
    slice_id: str
    title: str
    summary: str
    tags: List[str] = []
    sources: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    lifecycle: str = "draft"  # draft/published/deprecated
    owner: Optional[str] = None
    score: float = 0.0
    freshness: Optional[int] = None


class QAPair(BaseModel):
    question: str
    answers: List[str] = []
    evidence_ids: List[str] = []
    confidence: float = 0.0


class QueryRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: dict = {}


class QueryResponse(BaseModel):
    hits: List[dict] = []
    latency_ms: int = 0

