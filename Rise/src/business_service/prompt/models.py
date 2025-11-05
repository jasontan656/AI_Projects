from __future__ import annotations

"""Domain models for prompt management."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from uuid import uuid4


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Prompt:
    prompt_id: str
    name: str
    markdown: str
    version: int = 1
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
    updated_by: Optional[str] = None

    def to_document(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "name": self.name,
            "markdown": self.markdown,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "Prompt":
        return cls(
            prompt_id=str(doc["prompt_id"]),
            name=str(doc.get("name", "")),
            markdown=str(doc.get("markdown", "")),
            version=int(doc.get("version", 1)),
            created_at=_ensure_datetime(doc.get("created_at") or _now_utc()),
            updated_at=_ensure_datetime(doc.get("updated_at") or _now_utc()),
            updated_by=doc.get("updated_by"),
        )

    @classmethod
    def new(
        cls,
        *,
        name: str,
        markdown: str,
        actor: Optional[str],
    ) -> "Prompt":
        now = _now_utc()
        return cls(
            prompt_id=str(uuid4()),
            name=name,
            markdown=markdown,
            version=1,
            created_at=now,
            updated_at=now,
            updated_by=actor,
        )


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


__all__ = ["Prompt", "_now_utc"]
