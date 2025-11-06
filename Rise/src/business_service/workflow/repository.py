from __future__ import annotations

"""Mongo repositories for workflow domain."""

from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.collection import Collection
from pymongo import ASCENDING

from business_service.workflow.models import StageDefinition, ToolDefinition, WorkflowDefinition

__all__ = [
    "AsyncToolRepository",
    "AsyncStageRepository",
    "AsyncWorkflowRepository",
    "ToolRepository",
    "StageRepository",
    "WorkflowRepository",
]


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
        return WorkflowDefinition.from_document(document)

    def update(self, workflow_id: str, updates: Mapping[str, Any]) -> WorkflowDefinition:
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = datetime.utcnow()
        updated = self._collection.find_one_and_update(
            {"workflow_id": workflow_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(workflow_id)
        return WorkflowDefinition.from_document(updated)

    def delete(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        deleted = self._collection.find_one_and_delete({"workflow_id": workflow_id})
        return WorkflowDefinition.from_document(deleted) if deleted else None

    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        doc = self._collection.find_one({"workflow_id": workflow_id})
        return WorkflowDefinition.from_document(doc) if doc else None

    def list_workflows(self) -> Sequence[WorkflowDefinition]:
        return [
            WorkflowDefinition.from_document(doc)
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
        return WorkflowDefinition.from_document(document)

    async def update(self, workflow_id: str, updates: Mapping[str, Any]) -> WorkflowDefinition:
        await self._ensure_indexes()
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = datetime.utcnow()
        updated = await self._collection.find_one_and_update(
            {"workflow_id": workflow_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(workflow_id)
        return WorkflowDefinition.from_document(updated)

    async def delete(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        await self._ensure_indexes()
        deleted = await self._collection.find_one_and_delete({"workflow_id": workflow_id})
        return WorkflowDefinition.from_document(deleted) if deleted else None

    async def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"workflow_id": workflow_id})
        return WorkflowDefinition.from_document(doc) if doc else None

    async def list_workflows(self) -> Sequence[WorkflowDefinition]:
        await self._ensure_indexes()
        cursor = self._collection.find().sort("updated_at", -1)
        return [WorkflowDefinition.from_document(doc) async for doc in cursor]
