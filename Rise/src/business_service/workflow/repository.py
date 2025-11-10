from __future__ import annotations

"""Mongo repositories for workflow domain."""

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, MutableMapping, Optional, Sequence, Tuple

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.collection import Collection
from pymongo import ASCENDING, ReturnDocument

from business_service.workflow.models import StageDefinition, ToolDefinition, WorkflowDefinition, WorkflowPublishRecord

__all__ = [
    "AsyncToolRepository",
    "AsyncStageRepository",
    "AsyncWorkflowRepository",
    "ToolRepository",
    "StageRepository",
    "WorkflowRepository",
    "WorkflowVersionConflict",
]

PUBLISH_HISTORY_LIMIT = 50


class WorkflowVersionConflict(RuntimeError):
    """Raised when optimistic concurrency check fails for workflow operations."""


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ToolRepository:
    def __init__(self, collection: Collection) -> None:
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index([("tool_id", ASCENDING)], unique=True, name="uniq_tool_id")

    def create(self, tool: ToolDefinition) -> ToolDefinition:
        document = tool.to_document()
        self._collection.insert_one(document)
        return ToolDefinition.from_document(document)

    def update(self, tool_id: str, updates: Mapping[str, Any]) -> ToolDefinition:
        now = datetime.utcnow()
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = now
        updated = self._collection.find_one_and_update(
            {"tool_id": tool_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(tool_id)
        return ToolDefinition.from_document(updated)

    def delete(self, tool_id: str) -> Optional[ToolDefinition]:
        deleted = self._collection.find_one_and_delete({"tool_id": tool_id})
        return ToolDefinition.from_document(deleted) if deleted else None

    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        doc = self._collection.find_one({"tool_id": tool_id})
        return ToolDefinition.from_document(doc) if doc else None

    def list_tools(self) -> Sequence[ToolDefinition]:
        return [ToolDefinition.from_document(doc) for doc in self._collection.find().sort("updated_at", -1)]


class AsyncToolRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def _ensure_indexes(self) -> None:
        await self._collection.create_index([("tool_id", ASCENDING)], unique=True, name="uniq_tool_id")

    async def create(self, tool: ToolDefinition) -> ToolDefinition:
        await self._ensure_indexes()
        document = tool.to_document()
        await self._collection.insert_one(document)
        return ToolDefinition.from_document(document)

    async def update(self, tool_id: str, updates: Mapping[str, Any]) -> ToolDefinition:
        await self._ensure_indexes()
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = datetime.utcnow()
        updated = await self._collection.find_one_and_update(
            {"tool_id": tool_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(tool_id)
        return ToolDefinition.from_document(updated)

    async def delete(self, tool_id: str) -> Optional[ToolDefinition]:
        await self._ensure_indexes()
        deleted = await self._collection.find_one_and_delete({"tool_id": tool_id})
        return ToolDefinition.from_document(deleted) if deleted else None

    async def get(self, tool_id: str) -> Optional[ToolDefinition]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"tool_id": tool_id})
        return ToolDefinition.from_document(doc) if doc else None

    async def list_tools(self) -> Sequence[ToolDefinition]:
        await self._ensure_indexes()
        cursor = self._collection.find().sort("updated_at", -1)
        return [ToolDefinition.from_document(doc) async for doc in cursor]

    async def get_many(self, tool_ids: Iterable[str]) -> Sequence[ToolDefinition]:
        ids = list(tool_ids)
        if not ids:
            return ()
        await self._ensure_indexes()
        cursor = self._collection.find({"tool_id": {"$in": ids}})
        return [ToolDefinition.from_document(doc) async for doc in cursor]


class StageRepository:
    def __init__(self, collection: Collection) -> None:
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index([("stage_id", ASCENDING)], unique=True, name="uniq_stage_id")

    def create(self, stage: StageDefinition) -> StageDefinition:
        document = stage.to_document()
        self._collection.insert_one(document)
        return StageDefinition.from_document(document)

    def update(self, stage_id: str, updates: Mapping[str, Any]) -> StageDefinition:
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = datetime.utcnow()
        updated = self._collection.find_one_and_update(
            {"stage_id": stage_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(stage_id)
        return StageDefinition.from_document(updated)

    def delete(self, stage_id: str) -> Optional[StageDefinition]:
        deleted = self._collection.find_one_and_delete({"stage_id": stage_id})
        return StageDefinition.from_document(deleted) if deleted else None

    def get(self, stage_id: str) -> Optional[StageDefinition]:
        doc = self._collection.find_one({"stage_id": stage_id})
        return StageDefinition.from_document(doc) if doc else None

    def list_stages(self) -> Sequence[StageDefinition]:
        return [StageDefinition.from_document(doc) for doc in self._collection.find().sort("updated_at", -1)]

    def get_many(self, stage_ids: Iterable[str]) -> Sequence[StageDefinition]:
        docs = self._collection.find({"stage_id": {"$in": list(stage_ids)}})
        return [StageDefinition.from_document(doc) for doc in docs]


class AsyncStageRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def _ensure_indexes(self) -> None:
        await self._collection.create_index([("stage_id", ASCENDING)], unique=True, name="uniq_stage_id")

    async def create(self, stage: StageDefinition) -> StageDefinition:
        await self._ensure_indexes()
        document = stage.to_document()
        await self._collection.insert_one(document)
        return StageDefinition.from_document(document)

    async def update(self, stage_id: str, updates: Mapping[str, Any]) -> StageDefinition:
        await self._ensure_indexes()
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = datetime.utcnow()
        updated = await self._collection.find_one_and_update(
            {"stage_id": stage_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(stage_id)
        return StageDefinition.from_document(updated)

    async def delete(self, stage_id: str) -> Optional[StageDefinition]:
        await self._ensure_indexes()
        deleted = await self._collection.find_one_and_delete({"stage_id": stage_id})
        return StageDefinition.from_document(deleted) if deleted else None

    async def get(self, stage_id: str) -> Optional[StageDefinition]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"stage_id": stage_id})
        return StageDefinition.from_document(doc) if doc else None

    async def list_stages(self) -> Sequence[StageDefinition]:
        await self._ensure_indexes()
        cursor = self._collection.find().sort("updated_at", -1)
        return [StageDefinition.from_document(doc) async for doc in cursor]

    async def get_many(self, stage_ids: Iterable[str]) -> Sequence[StageDefinition]:
        await self._ensure_indexes()
        cursor = self._collection.find({"stage_id": {"$in": list(stage_ids)}})
        return [StageDefinition.from_document(doc) async for doc in cursor]


class WorkflowRepository:
    def __init__(self, collection: Collection) -> None:
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index([("workflow_id", ASCENDING)], unique=True, name="uniq_workflow_id")

    def create(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        document = workflow.to_document()
        self._collection.insert_one(document)
        stored = self._collection.find_one({"workflow_id": workflow.workflow_id}) or document
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
    ) -> WorkflowDefinition:
        command = _build_workflow_update_command(
            updates,
            status=status,
            pending_changes=pending_changes,
            published_version=published_version,
            publish_record=publish_record,
            increment_version=increment_version,
        )
        filter_doc: MutableMapping[str, Any] = {"workflow_id": workflow_id}
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
        deleted = self._collection.find_one_and_delete({"workflow_id": workflow_id})
        return WorkflowDefinition.from_document(_sanitize_workflow_document(deleted)) if deleted else None

    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        doc = self._collection.find_one({"workflow_id": workflow_id})
        return WorkflowDefinition.from_document(_sanitize_workflow_document(doc)) if doc else None

    def list_workflows(self) -> Sequence[WorkflowDefinition]:
        return [
            WorkflowDefinition.from_document(_sanitize_workflow_document(doc))
            for doc in self._collection.find().sort("updated_at", -1)
        ]


class AsyncWorkflowRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def _ensure_indexes(self) -> None:
        await self._collection.create_index([("workflow_id", ASCENDING)], unique=True, name="uniq_workflow_id")

    async def create(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        await self._ensure_indexes()
        document = workflow.to_document()
        await self._collection.insert_one(document)
        stored = await self._collection.find_one({"workflow_id": workflow.workflow_id}) or document
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
    ) -> WorkflowDefinition:
        await self._ensure_indexes()
        command = _build_workflow_update_command(
            updates,
            status=status,
            pending_changes=pending_changes,
            published_version=published_version,
            publish_record=publish_record,
            increment_version=increment_version,
        )
        filter_doc: MutableMapping[str, Any] = {"workflow_id": workflow_id}
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
        deleted = await self._collection.find_one_and_delete({"workflow_id": workflow_id})
        return WorkflowDefinition.from_document(_sanitize_workflow_document(deleted)) if deleted else None

    async def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"workflow_id": workflow_id})
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
) -> MutableMapping[str, Any]:
    set_payload: MutableMapping[str, Any] = {"updated_at": _now_utc()}
    set_payload.update(dict(updates))
    if status is not None:
        set_payload["status"] = status
    if pending_changes is not None:
        set_payload["pending_changes"] = pending_changes
    if published_version is not None:
        set_payload["published_version"] = published_version
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
