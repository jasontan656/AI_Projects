from __future__ import annotations

"""Tool repositories backed by Mongo."""

from datetime import datetime
from typing import Any, Mapping, Optional, Sequence

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.collection import Collection

from business_service.workflow.mixins import AsyncMongoCrudMixin, SyncMongoCrudMixin
from business_service.workflow.models import ToolDefinition

__all__ = ["ToolRepository", "AsyncToolRepository"]


class ToolRepository(SyncMongoCrudMixin[ToolDefinition]):
    id_field = "tool_id"

    def __init__(self, collection: Collection) -> None:
        super().__init__(collection, factory=ToolDefinition.from_document)

    def create(self, tool: ToolDefinition) -> ToolDefinition:
        return self._insert_document(tool.to_document())

    def update(self, tool_id: str, updates: Mapping[str, Any]) -> ToolDefinition:
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = datetime.utcnow()
        updated = self._collection.find_one_and_update(
            {self.id_field: tool_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(tool_id)
        return ToolDefinition.from_document(updated)

    def delete(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._delete_by_id(tool_id)

    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._find_by_id(tool_id)

    def list_tools(self) -> Sequence[ToolDefinition]:
        return self._list_all()


class AsyncToolRepository(AsyncMongoCrudMixin[ToolDefinition]):
    id_field = "tool_id"

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        super().__init__(collection, factory=ToolDefinition.from_document)

    async def create(self, tool: ToolDefinition) -> ToolDefinition:
        return await self._insert_document(tool.to_document())

    async def update(self, tool_id: str, updates: Mapping[str, Any]) -> ToolDefinition:
        await self._ensure_indexes()
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = datetime.utcnow()
        updated = await self._collection.find_one_and_update(
            {self.id_field: tool_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(tool_id)
        return ToolDefinition.from_document(updated)

    async def delete(self, tool_id: str) -> Optional[ToolDefinition]:
        return await self._delete_by_id(tool_id)

    async def get(self, tool_id: str) -> Optional[ToolDefinition]:
        return await self._find_by_id(tool_id)

    async def list_tools(self) -> Sequence[ToolDefinition]:
        return await self._list_all()
