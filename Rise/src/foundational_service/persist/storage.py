from __future__ import annotations

"""Mongo-backed idempotent storage helpers for task execution results."""

from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from .task_envelope import TaskEnvelope

__all__ = ["WorkflowRunStorage"]


class WorkflowRunStorage:
    def __init__(self, database: Database, *, collection_name: str = "workflow_runs") -> None:
        self._collection = database[collection_name]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index([("idempotency_key", ASCENDING)], unique=True, name="uniq_run_idempo")
        self._collection.create_index([("task_id", ASCENDING)], unique=True, name="uniq_run_task")
        self._collection.create_index(
            [("workflow_id", ASCENDING), ("updated_at", DESCENDING)],
            name="workflow_recent_idx",
        )

    def upsert_result(
        self,
        *,
        envelope: TaskEnvelope,
        result: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:
        now = datetime.now(timezone.utc)
        workflow_id = envelope.payload.get("workflowId")
        document: MutableMapping[str, Any] = {
            "task_id": envelope.task_id,
            "workflow_id": workflow_id,
            "status": envelope.status.value,
            "result": dict(result),
            "error": envelope.error,
            "updated_at": now,
            "created_at": envelope.created_at,
        }
        document["idempotency_key"] = envelope.context.get("idempotencyKey", envelope.task_id)
        document["payload_snapshot"] = self._build_payload_snapshot(envelope)
        document["context_snapshot"] = dict(envelope.context)
        self._collection.update_one(
            {"idempotency_key": document["idempotency_key"]},
            {
                "$set": {
                    "task_id": document["task_id"],
                    "workflow_id": workflow_id,
                    "status": document["status"],
                    "result": document["result"],
                    "error": document["error"],
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": document["created_at"],
                },
            },
            upsert=True,
        )
        return document

    @staticmethod
    def _build_payload_snapshot(envelope: TaskEnvelope) -> MutableMapping[str, Any]:
        payload = envelope.payload
        snapshot: MutableMapping[str, Any] = {
            "workflowId": payload.get("workflowId"),
            "userText": payload.get("userText"),
            "metadata": dict(payload.get("metadata") or {}),
            "coreEnvelope": dict(payload.get("coreEnvelope") or {}),
            "policy": dict(payload.get("policy") or {}),
            "telemetry": dict(payload.get("telemetry") or {}),
            "historyChunks": list(payload.get("historyChunks") or []),
            "source": payload.get("source"),
        }
        if "chatId" in payload:
            snapshot["chatId"] = payload.get("chatId")
        return snapshot

