from __future__ import annotations

"""Append-only workflow history repositories."""

import hashlib
import json
from datetime import datetime
from typing import Mapping, MutableMapping, Optional, Sequence

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING
from pymongo.collection import Collection

from business_service.workflow.models import WorkflowPublishRecord
from business_service.workflow.workflow_repository import PUBLISH_HISTORY_LIMIT

__all__ = [
    "WorkflowHistoryRepository",
    "AsyncWorkflowHistoryRepository",
    "calculate_history_checksum",
]


def calculate_history_checksum(records: Sequence[WorkflowPublishRecord]) -> str:
    """Compute a deterministic checksum for the supplied history slice."""
    if not records:
        return ""
    payload = [
        {
            "version": record.version,
            "action": record.action,
            "actor": record.actor,
            "comment": record.comment,
            "timestamp": record.timestamp.isoformat(),
            "snapshot": record.snapshot,
            "diff": record.diff,
        }
        for record in records
    ]
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _record_checksum(record: WorkflowPublishRecord) -> str:
    payload = record.to_document()
    serialized = json.dumps(
        {
            "version": payload.get("version"),
            "action": payload.get("action"),
            "actor": payload.get("actor"),
            "comment": payload.get("comment"),
            "timestamp": _serialize_timestamp(payload.get("timestamp")),
            "snapshot": payload.get("snapshot"),
            "diff": payload.get("diff"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _serialize_timestamp(value: Optional[datetime]) -> str:
    if value is None:
        return ""
    return value.isoformat()


class WorkflowHistoryRepository:
    """Synchronous repository used by CLI scripts and migrations."""

    def __init__(self, collection: Collection) -> None:
        self._collection = collection
        self._collection.create_index(
            [("workflow_id", ASCENDING), ("version", ASCENDING)],
            unique=True,
            name="uniq_workflow_history_version",
        )

    def append(self, workflow_id: str, record: WorkflowPublishRecord) -> WorkflowPublishRecord:
        document = record.to_document()
        payload: MutableMapping[str, object] = {
            "workflow_id": workflow_id,
            **document,
            "record_checksum": _record_checksum(record),
        }
        self._collection.insert_one(payload)
        return record

    def list_history(self, workflow_id: str, *, limit: int = PUBLISH_HISTORY_LIMIT) -> Sequence[WorkflowPublishRecord]:
        cursor = (
            self._collection.find({"workflow_id": workflow_id})
            .sort("version", -1)
            .limit(limit)
        )
        records = [WorkflowPublishRecord.from_document(doc) for doc in cursor]
        return tuple(reversed(records))

    def get_record(self, workflow_id: str, version: int) -> Optional[WorkflowPublishRecord]:
        doc = self._collection.find_one({"workflow_id": workflow_id, "version": version})
        return WorkflowPublishRecord.from_document(doc) if doc else None


class AsyncWorkflowHistoryRepository:
    """Async repository for the runtime service."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection
        self._indexes_ready = False

    async def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        await self._collection.create_index(
            [("workflow_id", ASCENDING), ("version", ASCENDING)],
            unique=True,
            name="uniq_workflow_history_version",
        )
        self._indexes_ready = True

    async def append(self, workflow_id: str, record: WorkflowPublishRecord) -> WorkflowPublishRecord:
        await self._ensure_indexes()
        document = record.to_document()
        payload: MutableMapping[str, object] = {
            "workflow_id": workflow_id,
            **document,
            "record_checksum": _record_checksum(record),
        }
        await self._collection.insert_one(payload)
        return record

    async def list_history(
        self,
        workflow_id: str,
        *,
        limit: int = PUBLISH_HISTORY_LIMIT,
    ) -> Sequence[WorkflowPublishRecord]:
        await self._ensure_indexes()
        cursor = (
            self._collection.find({"workflow_id": workflow_id})
            .sort("version", -1)
            .limit(limit)
        )
        records = [WorkflowPublishRecord.from_document(doc) async for doc in cursor]
        return tuple(reversed(records))

    async def get_record(self, workflow_id: str, version: int) -> Optional[WorkflowPublishRecord]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"workflow_id": workflow_id, "version": version})
        return WorkflowPublishRecord.from_document(doc) if doc else None
