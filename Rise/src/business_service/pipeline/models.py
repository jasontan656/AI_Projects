from __future__ import annotations

"""Domain models for pipeline node storage."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional
from uuid import uuid4


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class PipelineNode:
    node_id: str
    name: str
    allow_llm: bool
    system_prompt: str
    status: str = "draft"
    pipeline_id: Optional[str] = None
    strategy: Mapping[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
    client_created_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    def to_document(self) -> MutableMapping[str, Any]:
        return {
            "node_id": self.node_id,
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "status": self.status,
            "allow_llm": self.allow_llm,
            "system_prompt": self.system_prompt,
            "strategy": dict(self.strategy) if self.strategy else {},
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "client_created_at": self.client_created_at,
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "PipelineNode":
        return cls(
            node_id=str(doc["node_id"]),
            pipeline_id=doc.get("pipeline_id"),
            name=str(doc["name"]),
            status=str(doc.get("status", "draft")),
            allow_llm=bool(doc.get("allow_llm", True)),
            system_prompt=str(doc.get("system_prompt", "")),
            strategy=doc.get("strategy") or {},
            version=int(doc.get("version", 1)),
            created_at=doc.get("created_at") or _now_utc(),
            updated_at=doc.get("updated_at") or _now_utc(),
            client_created_at=doc.get("client_created_at"),
            updated_by=doc.get("updated_by"),
        )

    @classmethod
    def new(
        cls,
        *,
        name: str,
        allow_llm: bool,
        system_prompt: str,
        status: str = "draft",
        pipeline_id: Optional[str] = None,
        strategy: Optional[Mapping[str, Any]] = None,
        client_created_at: Optional[datetime] = None,
        actor: Optional[str] = None,
    ) -> "PipelineNode":
        now = _now_utc()
        return cls(
            node_id=str(uuid4()),
            name=name,
            allow_llm=allow_llm,
            system_prompt=system_prompt,
            status=status or "draft",
            pipeline_id=pipeline_id,
            strategy=strategy or {},
            version=1,
            created_at=now,
            updated_at=now,
            client_created_at=client_created_at,
            updated_by=actor,
        )
