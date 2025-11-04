from __future__ import annotations

"""Typed models for knowledge snapshot orchestration."""

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping


@dataclass(slots=True)
class KnowledgeSnapshotState:
    snapshot: Mapping[str, Any]
    snapshot_dict: Mapping[str, Any]
    status: str
    telemetry: Mapping[str, Any]
    health: Mapping[str, Any]
    missing_agencies: list[str] = field(default_factory=list)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_legacy_dict(self) -> MutableMapping[str, Any]:
        return {
            "snapshot": self.snapshot,
            "snapshot_dict": self.snapshot_dict,
            "status": self.status,
            "telemetry": self.telemetry,
            "health": self.health,
            "missing_agencies": list(self.missing_agencies),
            "metadata": dict(self.metadata),
        }


__all__ = ["KnowledgeSnapshotState"]
