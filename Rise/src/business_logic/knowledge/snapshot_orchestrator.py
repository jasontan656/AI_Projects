from __future__ import annotations

"""Knowledge snapshot orchestration for the Business Logic layer."""

from dataclasses import dataclass
from typing import Any, Mapping

from business_logic.knowledge.models import KnowledgeSnapshotState
from business_service.knowledge import KnowledgeSnapshotService
from business_service.knowledge.models import SnapshotResult


@dataclass(slots=True)
class KnowledgeSnapshotOrchestrator:
    service: KnowledgeSnapshotService

    def load(self) -> KnowledgeSnapshotState:
        """Load the knowledge snapshot via the Business Service."""
        result = self.service.load()
        return self._to_state(result)

    def refresh(self, reason: str = "manual") -> KnowledgeSnapshotState:
        """Refresh the knowledge snapshot and return the new state."""
        result = self.service.refresh(reason)
        return self._to_state(result)

    @staticmethod
    def _to_state(result: SnapshotResult) -> KnowledgeSnapshotState:
        health_mapping: Mapping[str, Any] = {
            "missing_agencies": list(result.health.missing_agencies),
            "redis_status": result.health.redis_status,
            "redis_error": result.health.redis_error,
        }
        return KnowledgeSnapshotState(
            snapshot=result.snapshot,
            snapshot_dict=result.snapshot_dict,
            status=result.status,
            telemetry=result.telemetry,
            health=health_mapping,
            missing_agencies=list(result.missing_agencies),
            metadata=result.metadata,
        )


__all__ = ["KnowledgeSnapshotOrchestrator"]
