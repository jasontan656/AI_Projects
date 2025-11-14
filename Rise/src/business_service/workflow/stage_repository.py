from __future__ import annotations

"""Stage repositories backed by Mongo."""

from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Sequence

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.collection import Collection

from business_service.workflow.mixins import AsyncMongoCrudMixin, SyncMongoCrudMixin
from business_service.workflow.models import StageDefinition

__all__ = ["StageRepository", "AsyncStageRepository"]


class StageRepository(SyncMongoCrudMixin[StageDefinition]):
    id_field = "stage_id"

    def __init__(self, collection: Collection) -> None:
        super().__init__(collection, factory=StageDefinition.from_document)

    def create(self, stage: StageDefinition) -> StageDefinition:
        return self._insert_document(stage.to_document())

    def update(self, stage_id: str, updates: Mapping[str, Any]) -> StageDefinition:
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = datetime.utcnow()
        updated = self._collection.find_one_and_update(
            {self.id_field: stage_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(stage_id)
        return StageDefinition.from_document(updated)

    def delete(self, stage_id: str) -> Optional[StageDefinition]:
        return self._delete_by_id(stage_id)

    def get(self, stage_id: str) -> Optional[StageDefinition]:
        return self._find_by_id(stage_id)

    def list_stages(self) -> Sequence[StageDefinition]:
        return self._list_all()

    def get_many(self, stage_ids: Iterable[str]) -> Sequence[StageDefinition]:
        return self._find_many(stage_ids)


class AsyncStageRepository(AsyncMongoCrudMixin[StageDefinition]):
    id_field = "stage_id"

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        super().__init__(collection, factory=StageDefinition.from_document)

    async def create(self, stage: StageDefinition) -> StageDefinition:
        return await self._insert_document(stage.to_document())

    async def update(self, stage_id: str, updates: Mapping[str, Any]) -> StageDefinition:
        await self._ensure_indexes()
        command = {"$set": dict(updates)}
        command["$set"]["updated_at"] = datetime.utcnow()
        updated = await self._collection.find_one_and_update(
            {self.id_field: stage_id},
            command,
            return_document=True,
        )
        if updated is None:
            raise KeyError(stage_id)
        return StageDefinition.from_document(updated)

    async def delete(self, stage_id: str) -> Optional[StageDefinition]:
        return await self._delete_by_id(stage_id)

    async def get(self, stage_id: str) -> Optional[StageDefinition]:
        return await self._find_by_id(stage_id)

    async def list_stages(self) -> Sequence[StageDefinition]:
        return await self._list_all()

    async def get_many(self, stage_ids: Iterable[str]) -> Sequence[StageDefinition]:
        return await self._find_many(stage_ids)
