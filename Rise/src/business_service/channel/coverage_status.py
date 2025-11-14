from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

from motor.motor_asyncio import AsyncIOMotorCollection
from redis.asyncio import Redis

from foundational_service.telemetry.coverage_recorder import (
    CoverageTestEventRecorder,
    get_coverage_test_event_recorder,
)


@dataclass(slots=True)
class WorkflowCoverageStatus:
    workflow_id: str
    status: str
    updated_at: datetime
    scenarios: Sequence[str]
    mode: str = "webhook"
    last_run_id: Optional[str] = None
    last_error: Optional[str] = None
    actor_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflowId": self.workflow_id,
            "status": self.status,
            "updatedAt": self.updated_at.isoformat(),
            "scenarios": list(self.scenarios),
            "mode": self.mode,
            "lastRunId": self.last_run_id,
            "lastError": self.last_error,
            "actorId": self.actor_id,
        }


class CoverageStatusService:
    """Persist coverage state to Redis (current view) and Mongo (history)."""

    def __init__(
        self,
        *,
        redis_client: Redis,
        history_collection: Optional[AsyncIOMotorCollection],
        ttl_seconds: int = 86400,
        event_recorder: Optional[CoverageTestEventRecorder] = None,
    ) -> None:
        self._redis = redis_client
        self._history = history_collection
        self._ttl_seconds = ttl_seconds
        self._event_recorder = event_recorder or get_coverage_test_event_recorder()

    async def get_status(self, workflow_id: str) -> WorkflowCoverageStatus:
        payload = await self._redis.get(self._redis_key(workflow_id))
        if payload:
            return self._from_payload(workflow_id, json.loads(payload))
        return WorkflowCoverageStatus(
            workflow_id=workflow_id,
            status="unknown",
            updated_at=datetime.now(timezone.utc),
            scenarios=[],
        )

    async def mark_status(
        self,
        workflow_id: str,
        *,
        status: str,
        scenarios: Sequence[str],
        mode: str,
        actor_id: Optional[str] = None,
        last_run_id: Optional[str] = None,
        last_error: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> WorkflowCoverageStatus:
        now = datetime.now(timezone.utc)
        payload = {
            "status": status,
            "scenarios": list(scenarios),
            "mode": mode,
            "actorId": actor_id,
            "lastRunId": last_run_id,
            "lastError": last_error,
            "updatedAt": now.isoformat(),
            "metadata": dict(metadata or {}),
        }
        await self._redis.set(
            self._redis_key(workflow_id),
            json.dumps(payload, ensure_ascii=False),
            ex=self._ttl_seconds,
        )
        if self._history is not None:
            history_record = dict(payload)
            history_record["workflowId"] = workflow_id
            await self._history.insert_one(history_record)
        if self._event_recorder is not None and status.lower() not in {"pending"}:
            await self._event_recorder.record_completion(
                workflow_id,
                status=status,
                scenarios=scenarios,
                mode=mode,
                actor_id=actor_id,
                last_run_id=last_run_id,
                last_error=last_error,
                metadata=dict(metadata or {}),
            )
        return self._from_payload(workflow_id, payload)

    def _redis_key(self, workflow_id: str) -> str:
        return f"rise:coverage:workflow:{workflow_id}"

    @staticmethod
    def _from_payload(workflow_id: str, payload: Mapping[str, Any]) -> WorkflowCoverageStatus:
        updated_at_raw = payload.get("updatedAt")
        updated_at = (
            datetime.fromisoformat(updated_at_raw) if isinstance(updated_at_raw, str) else datetime.now(timezone.utc)
        )
        return WorkflowCoverageStatus(
            workflow_id=workflow_id,
            status=str(payload.get("status", "unknown")),
            updated_at=updated_at,
            scenarios=list(payload.get("scenarios", [])),
            mode=str(payload.get("mode", "webhook")),
            last_run_id=payload.get("lastRunId"),
            last_error=payload.get("lastError"),
            actor_id=payload.get("actorId"),
        )


__all__ = ["CoverageStatusService", "WorkflowCoverageStatus"]
