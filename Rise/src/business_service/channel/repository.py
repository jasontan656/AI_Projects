from __future__ import annotations

"""Mongo repository for workflow channel policies."""

import asyncio
from typing import Optional, Sequence

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING

from business_service.channel.models import WorkflowChannelPolicy

__all__ = ["AsyncWorkflowChannelRepository"]


class AsyncWorkflowChannelRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection
        self._index_lock = asyncio.Lock()
        self._indexes_created = False

    async def _ensure_indexes(self) -> None:
        if self._indexes_created:
            return
        async with self._index_lock:
            if self._indexes_created:
                return
            await self._collection.create_index(
                [("workflow_id", ASCENDING), ("channel", ASCENDING)],
                unique=True,
                name="uniq_workflow_channel",
            )
            self._indexes_created = True

    async def upsert(self, policy: WorkflowChannelPolicy) -> WorkflowChannelPolicy:
        await self._ensure_indexes()
        document = policy.to_document()
        await self._collection.update_one(
            {"workflow_id": policy.workflow_id, "channel": policy.channel},
            {"$set": document},
            upsert=True,
        )
        stored = await self._collection.find_one({"workflow_id": policy.workflow_id, "channel": policy.channel})
        return WorkflowChannelPolicy.from_document(stored or document)

    async def get(self, workflow_id: str, channel: str) -> Optional[WorkflowChannelPolicy]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"workflow_id": workflow_id, "channel": channel})
        if doc is None:
            return None
        return WorkflowChannelPolicy.from_document(doc)

    async def delete(self, workflow_id: str, channel: str) -> bool:
        await self._ensure_indexes()
        result = await self._collection.delete_one({"workflow_id": workflow_id, "channel": channel})
        return result.deleted_count > 0

    async def list_by_channel(self, channel: str) -> Sequence[WorkflowChannelPolicy]:
        await self._ensure_indexes()
        cursor = self._collection.find({"channel": channel}).sort("updated_at", -1)
        return [WorkflowChannelPolicy.from_document(doc) async for doc in cursor]
