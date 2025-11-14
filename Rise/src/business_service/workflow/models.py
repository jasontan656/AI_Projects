from __future__ import annotations

"""Workflow domain models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional, Sequence
from uuid import uuid4

__all__ = [
    "ToolDefinition",
    "StageDefinition",
    "WorkflowDefinition",
    "PromptBinding",
    "WorkflowPublishRecord",
]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ToolDefinition:
    tool_id: str
    name: str
    description: str
    prompt_snippet: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
    updated_by: Optional[str] = None

    def to_document(self) -> MutableMapping[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "prompt_snippet": self.prompt_snippet,
            "metadata": dict(self.metadata),
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "ToolDefinition":
        return cls(
            tool_id=str(doc["tool_id"]),
            name=str(doc.get("name", "")),
            description=str(doc.get("description", "")),
            prompt_snippet=str(doc.get("prompt_snippet", "")),
            metadata=dict(doc.get("metadata") or {}),
            version=int(doc.get("version", 1)),
            created_at=doc.get("created_at") or _now_utc(),
            updated_at=doc.get("updated_at") or _now_utc(),
            updated_by=doc.get("updated_by"),
        )

    @classmethod
    def new(
        cls,
        *,
        name: str,
        description: str,
        prompt_snippet: str,
        metadata: Optional[Mapping[str, Any]] = None,
        actor: Optional[str] = None,
    ) -> "ToolDefinition":
        now = _now_utc()
        return cls(
            tool_id=str(uuid4()),
            name=name,
            description=description,
            prompt_snippet=prompt_snippet,
            metadata=dict(metadata or {}),
            updated_by=actor,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class StageDefinition:
    stage_id: str
    name: str
    prompt_template: str
    description: str = ""
    tool_ids: Sequence[str] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
    updated_by: Optional[str] = None

    def to_document(self) -> MutableMapping[str, Any]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "description": self.description,
            "prompt_template": self.prompt_template,
            "tool_ids": list(self.tool_ids),
            "metadata": dict(self.metadata),
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "StageDefinition":
        return cls(
            stage_id=str(doc["stage_id"]),
            name=str(doc.get("name", "")),
            description=str(doc.get("description", "")),
            prompt_template=str(doc.get("prompt_template", "")),
            tool_ids=tuple(str(t) for t in (doc.get("tool_ids") or [])),
            metadata=dict(doc.get("metadata") or {}),
            version=int(doc.get("version", 1)),
            created_at=doc.get("created_at") or _now_utc(),
            updated_at=doc.get("updated_at") or _now_utc(),
            updated_by=doc.get("updated_by"),
        )

    @classmethod
    def new(
        cls,
        *,
        name: str,
        prompt_template: str,
        description: str = "",
        tool_ids: Optional[Sequence[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        actor: Optional[str] = None,
    ) -> "StageDefinition":
        now = _now_utc()
        return cls(
            stage_id=str(uuid4()),
            name=name,
            description=description,
            prompt_template=prompt_template,
            tool_ids=tuple(tool_ids or []),
            metadata=dict(metadata or {}),
            updated_by=actor,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    description: str = ""
    stage_ids: Sequence[str] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    node_sequence: Sequence[str] = field(default_factory=tuple)
    prompt_bindings: Sequence[PromptBinding] = field(default_factory=tuple)
    strategy: Mapping[str, Any] = field(default_factory=dict)
    status: str = "draft"
    version: int = 1
    published_version: int = 0
    pending_changes: bool = True
    publish_history: Sequence[WorkflowPublishRecord] = field(default_factory=tuple)
    history_checksum: str = ""
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
    updated_by: Optional[str] = None

    def to_document(self) -> MutableMapping[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "stage_ids": list(self.stage_ids),
            "metadata": dict(self.metadata),
            "node_sequence": list(self.node_sequence),
            "prompt_bindings": [binding.to_document() for binding in self.prompt_bindings],
            "strategy": dict(self.strategy),
            "status": self.status,
            "version": self.version,
            "published_version": self.published_version,
            "pending_changes": self.pending_changes,
            "publish_history": [record.to_document() for record in self.publish_history],
            "history_checksum": self.history_checksum,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "WorkflowDefinition":
        return cls(
            workflow_id=str(doc["workflow_id"]),
            name=str(doc.get("name", "")),
            description=str(doc.get("description", "")),
            stage_ids=tuple(str(s) for s in (doc.get("stage_ids") or [])),
            metadata=dict(doc.get("metadata") or {}),
            node_sequence=tuple(str(node) for node in (doc.get("node_sequence") or [])),
            prompt_bindings=tuple(
                PromptBinding.from_document(item) for item in (doc.get("prompt_bindings") or [])
            ),
            strategy=dict(doc.get("strategy") or {}),
            status=str(doc.get("status", "draft")),
            version=int(doc.get("version", 1)),
            published_version=int(doc.get("published_version", doc.get("publishedVersion", 0) or 0)),
            pending_changes=bool(doc.get("pending_changes", doc.get("pendingChanges", True))),
            publish_history=tuple(
                WorkflowPublishRecord.from_document(item)
                for item in (doc.get("publish_history") or doc.get("publishHistory") or [])
            ),
            history_checksum=str(doc.get("history_checksum") or doc.get("historyChecksum") or ""),
            created_at=doc.get("created_at") or _now_utc(),
            updated_at=doc.get("updated_at") or _now_utc(),
            updated_by=doc.get("updated_by"),
        )

    @classmethod
    def new(
        cls,
        *,
        name: str,
        description: str = "",
        stage_ids: Optional[Sequence[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        node_sequence: Optional[Sequence[str]] = None,
        prompt_bindings: Optional[Sequence[PromptBinding]] = None,
        strategy: Optional[Mapping[str, Any]] = None,
        status: str = "draft",
        actor: Optional[str] = None,
        pending_changes: bool = True,
    ) -> "WorkflowDefinition":
        now = _now_utc()
        return cls(
            workflow_id=str(uuid4()),
            name=name,
            description=description,
            stage_ids=tuple(stage_ids or []),
            metadata=dict(metadata or {}),
            node_sequence=tuple(node_sequence or []),
            prompt_bindings=tuple(prompt_bindings or ()),
            strategy=dict(strategy or {}),
            status=status,
            published_version=0,
            pending_changes=pending_changes,
            history_checksum="",
            updated_by=actor,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class PromptBinding:
    node_id: str
    prompt_id: str

    def to_document(self) -> Mapping[str, Any]:
        return {"node_id": self.node_id, "prompt_id": self.prompt_id}

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "PromptBinding":
        return cls(node_id=str(doc.get("node_id", "")), prompt_id=str(doc.get("prompt_id", "")))


@dataclass(slots=True)
class WorkflowPublishRecord:
    version: int
    action: str
    actor: Optional[str]
    comment: Optional[str]
    timestamp: datetime
    snapshot: Mapping[str, Any]
    diff: Mapping[str, Any] = field(default_factory=dict)

    def to_document(self) -> Mapping[str, Any]:
        return {
            "version": self.version,
            "action": self.action,
            "actor": self.actor,
            "comment": self.comment,
            "timestamp": self.timestamp,
            "snapshot": dict(self.snapshot),
            "diff": dict(self.diff),
        }

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "WorkflowPublishRecord":
        return cls(
            version=int(doc.get("version", 0)),
            action=str(doc.get("action", "")),
            actor=doc.get("actor"),
            comment=doc.get("comment"),
            timestamp=doc.get("timestamp") or _now_utc(),
            snapshot=dict(doc.get("snapshot") or {}),
            diff=dict(doc.get("diff") or {}),
        )
