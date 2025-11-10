from __future__ import annotations

"""Async readers for workflow run observability artifacts."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

__all__ = ["WorkflowRunReadRepository"]


class WorkflowRunReadRepository:
    """Query helper over the workflow_runs collection for observability use cases."""

    def __init__(self, collection: AsyncIOMotorCollection, *, default_task_limit: int = 25) -> None:
        self._collection = collection
        self._default_task_limit = default_task_limit
        self._indexes_created = False
        self._index_lock = asyncio.Lock()

    async def list_runs(
        self,
        workflow_id: str,
        *,
        limit_tasks: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> Sequence[Mapping[str, Any]]:
        await self._ensure_indexes()
        filters: MutableMapping[str, Any] = {"workflow_id": workflow_id}
        if since is not None:
            filters["updated_at"] = {"$gte": self._as_utc(since)}
        cursor = (
            self._collection.find(filters)
            .sort("updated_at", DESCENDING)
            .limit(limit_tasks or self._default_task_limit)
        )
        documents: List[Mapping[str, Any]] = []
        async for doc in cursor:
            documents.append(self._normalize(doc))
        return documents

    async def get_latest(self, workflow_id: str) -> Optional[Mapping[str, Any]]:
        await self._ensure_indexes()
        doc = await (
            self._collection.find({"workflow_id": workflow_id}).sort("updated_at", DESCENDING).limit(1).to_list(1)
        )
        if not doc:
            return None
        return self._normalize(doc[0])

    async def get_by_task(self, workflow_id: str, task_id: str) -> Optional[Mapping[str, Any]]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"workflow_id": workflow_id, "task_id": task_id})
        if doc is None:
            return None
        return self._normalize(doc)

    async def list_by_tasks(self, workflow_id: str, task_ids: Iterable[str]) -> Sequence[Mapping[str, Any]]:
        ids = list(task_ids)
        if not ids:
            return ()
        await self._ensure_indexes()
        cursor = (
            self._collection.find({"workflow_id": workflow_id, "task_id": {"$in": ids}})
            .sort("updated_at", DESCENDING)
        )
        documents: List[Mapping[str, Any]] = []
        async for doc in cursor:
            documents.append(self._normalize(doc))
        return documents

    async def _ensure_indexes(self) -> None:
        if self._indexes_created:
            return
        async with self._index_lock:
            if self._indexes_created:
                return
            await self._collection.create_index(
                [("workflow_id", ASCENDING), ("updated_at", DESCENDING)],
                name="workflow_observe_idx",
            )
            await self._collection.create_index(
                [("task_id", ASCENDING)],
                name="workflow_task_lookup",
            )
            self._indexes_created = True

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _normalize(doc: Mapping[str, Any]) -> Mapping[str, Any]:
        normalized: MutableMapping[str, Any] = dict(doc)
        updated_at = normalized.get("updated_at")
        created_at = normalized.get("created_at")
        if isinstance(updated_at, str):
            normalized["updated_at"] = datetime.fromisoformat(updated_at)
        if isinstance(created_at, str):
            normalized["created_at"] = datetime.fromisoformat(created_at)
        return normalized
