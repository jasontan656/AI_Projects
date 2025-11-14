from __future__ import annotations

"""Workflow repositories and helpers."""

from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional, Sequence

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.collection import Collection

from business_service.workflow.mixins import AsyncMongoCrudMixin, SyncMongoCrudMixin
from business_service.workflow.models import WorkflowDefinition, WorkflowPublishRecord

__all__ = [
    "WorkflowRepository",
    "AsyncWorkflowRepository",
    "WorkflowVersionConflict",
    "PUBLISH_HISTORY_LIMIT",
]

PUBLISH_HISTORY_LIMIT = 50


class WorkflowVersionConflict(RuntimeError):
    """Raised when optimistic concurrency check fails for workflow operations."""


class WorkflowRepository(SyncMongoCrudMixin[WorkflowDefinition]):
    id_field = "workflow_id"

    def __init__(self, collection: Collection) -> None:
        super().__init__(
            collection,
            factory=lambda doc: WorkflowDefinition.from_document(_sanitize_workflow_document(doc)),
        )

    def create(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        document = workflow.to_document()
        self._collection.insert_one(document)
        stored = self._collection.find_one({self.id_field: workflow.workflow_id}) or document
        return WorkflowDefinition.from_document(_sanitize_workflow_document(stored))

    def update(
        self,
        workflow_id: str,
        updates: Mapping[str, Any],
        *,
        expected_version: Optional[int] = None,
        status: Optional[str] = None,
        pending_changes: Optional[bool] = None,
        published_version: Optional[int] = None,
        publish_record: Optional[WorkflowPublishRecord] = None,
        increment_version: bool = True,
        history_checksum: Optional[str] = None,
    ) -> WorkflowDefinition:
        command = _build_workflow_update_command(
            updates,
            status=status,
            pending_changes=pending_changes,
            published_version=published_version,
            publish_record=publish_record,
            increment_version=increment_version,
            history_checksum=history_checksum,
        )
        filter_doc: MutableMapping[str, Any] = {self.id_field: workflow_id}
        if expected_version is not None:
            filter_doc["version"] = expected_version
        updated = self._collection.find_one_and_update(
            filter_doc,
            command,
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            if expected_version is not None:
                raise WorkflowVersionConflict(f"workflow '{workflow_id}' version mismatch")
            raise KeyError(workflow_id)
        return WorkflowDefinition.from_document(_sanitize_workflow_document(updated))

    def delete(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        deleted = self._collection.find_one_and_delete({self.id_field: workflow_id})
        return WorkflowDefinition.from_document(_sanitize_workflow_document(deleted)) if deleted else None

    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        doc = self._collection.find_one({self.id_field: workflow_id})
        return WorkflowDefinition.from_document(_sanitize_workflow_document(doc)) if doc else None

    def list_workflows(self) -> Sequence[WorkflowDefinition]:
        return [
            WorkflowDefinition.from_document(_sanitize_workflow_document(doc))
            for doc in self._collection.find().sort("updated_at", -1)
        ]


class AsyncWorkflowRepository(AsyncMongoCrudMixin[WorkflowDefinition]):
    id_field = "workflow_id"

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        super().__init__(collection, factory=lambda doc: WorkflowDefinition.from_document(_sanitize_workflow_document(doc)))

    async def create(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        await self._ensure_indexes()
        document = workflow.to_document()
        await self._collection.insert_one(document)
        stored = await self._collection.find_one({self.id_field: workflow.workflow_id}) or document
        return WorkflowDefinition.from_document(_sanitize_workflow_document(stored))

    async def update(
        self,
        workflow_id: str,
        updates: Mapping[str, Any],
        *,
        expected_version: Optional[int] = None,
        status: Optional[str] = None,
        pending_changes: Optional[bool] = None,
        published_version: Optional[int] = None,
        publish_record: Optional[WorkflowPublishRecord] = None,
        increment_version: bool = True,
        history_checksum: Optional[str] = None,
    ) -> WorkflowDefinition:
        await self._ensure_indexes()
        command = _build_workflow_update_command(
            updates,
            status=status,
            pending_changes=pending_changes,
            published_version=published_version,
            publish_record=publish_record,
            increment_version=increment_version,
            history_checksum=history_checksum,
        )
        filter_doc: MutableMapping[str, Any] = {self.id_field: workflow_id}
        if expected_version is not None:
            filter_doc["version"] = expected_version
        updated = await self._collection.find_one_and_update(
            filter_doc,
            command,
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            if expected_version is not None:
                raise WorkflowVersionConflict(f"workflow '{workflow_id}' version mismatch")
            raise KeyError(workflow_id)
        return WorkflowDefinition.from_document(_sanitize_workflow_document(updated))

    async def delete(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        await self._ensure_indexes()
        deleted = await self._collection.find_one_and_delete({self.id_field: workflow_id})
        return WorkflowDefinition.from_document(_sanitize_workflow_document(deleted)) if deleted else None

    async def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({self.id_field: workflow_id})
        return WorkflowDefinition.from_document(_sanitize_workflow_document(doc)) if doc else None

    async def list_workflows(self) -> Sequence[WorkflowDefinition]:
        await self._ensure_indexes()
        cursor = self._collection.find().sort("updated_at", -1)
        return [WorkflowDefinition.from_document(_sanitize_workflow_document(doc)) async for doc in cursor]


def _build_workflow_update_command(
    updates: Mapping[str, Any],
    *,
    status: Optional[str],
    pending_changes: Optional[bool],
    published_version: Optional[int],
    publish_record: Optional[WorkflowPublishRecord],
    increment_version: bool,
    history_checksum: Optional[str],
) -> MutableMapping[str, Any]:
    set_payload: MutableMapping[str, Any] = {"updated_at": _now_utc()}
    set_payload.update(dict(updates))
    if status is not None:
        set_payload["status"] = status
    if pending_changes is not None:
        set_payload["pending_changes"] = pending_changes
    if published_version is not None:
        set_payload["published_version"] = published_version
    if history_checksum is not None:
        set_payload["history_checksum"] = history_checksum
    command: MutableMapping[str, Any] = {"$set": set_payload}
    if increment_version:
        command.setdefault("$inc", {})["version"] = 1
    if publish_record is not None:
        command.setdefault("$push", {})["publish_history"] = {
            "$each": [publish_record.to_document()],
            "$slice": -PUBLISH_HISTORY_LIMIT,
        }
    return command


def _sanitize_workflow_document(doc: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    if doc is None:
        return {}
    normalized: MutableMapping[str, Any] = dict(doc)
    normalized.setdefault("stage_ids", [])
    normalized.setdefault("metadata", {})
    normalized.setdefault("node_sequence", [])
    normalized.setdefault("prompt_bindings", [])
    normalized.setdefault("strategy", {})
    normalized.setdefault("status", "draft")
    normalized.setdefault("version", 1)
    normalized.setdefault("history_checksum", "")
    normalized.setdefault(
        "published_version",
        normalized.get("publishedVersion", 0) or 0,
    )
    normalized.setdefault(
        "pending_changes",
        normalized.get("pendingChanges", normalized.get("status") != "published"),
    )
    history = normalized.get("publish_history") or normalized.get("publishHistory") or []
    if not isinstance(history, list):
        history = []
    normalized["publish_history"] = history
    normalized["created_at"] = _ensure_datetime(normalized.get("created_at"))
    normalized["updated_at"] = _ensure_datetime(normalized.get("updated_at"))
    return normalized


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if value is None:
        return _now_utc()
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return _now_utc()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)
