from __future__ import annotations

"""Mongo-backed repository for pipeline nodes."""

import asyncio
from datetime import datetime
from typing import Any, Iterable, List, Mapping, Optional, Protocol, Tuple

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from business_service.pipeline.models import PipelineNode, _now_utc


class PipelineNodeRepository(Protocol):
    """Repository interface for pipeline nodes."""

    def create(self, node: PipelineNode) -> PipelineNode:
        ...

    def update(self, node_id: str, updates: Mapping[str, Any]) -> PipelineNode:
        ...

    def get(self, node_id: str) -> Optional[PipelineNode]:
        ...

    def list_nodes(
        self,
        pipeline_id: Optional[str],
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[PipelineNode], int]:
        ...

    def delete(self, node_id: str) -> Optional[PipelineNode]:
        ...


class DuplicateNodeNameError(RuntimeError):
    """Raised when attempting to create/update a node with a colliding name."""

    def __init__(self, name: str, pipeline_id: Optional[str]) -> None:
        scope = pipeline_id or "global"
        super().__init__(f"duplicate node name '{name}' in pipeline '{scope}'")
        self.name = name
        self.pipeline_id = pipeline_id


class MongoPipelineNodeRepository:
    """Mongo collection backed repository implementation."""

    def __init__(self, collection: Collection) -> None:
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index(
            [("name", ASCENDING), ("pipeline_id", ASCENDING)],
            unique=True,
            name="uniq_pipeline_name",
        )
        self._collection.create_index(
            [("node_id", ASCENDING)],
            unique=True,
            name="uniq_node_id",
        )

    def create(self, node: PipelineNode) -> PipelineNode:
        document = self._serialize(node)
        try:
            self._collection.insert_one(document)
        except DuplicateKeyError as exc:  # pragma: no cover - branch exercised via error handling
            raise DuplicateNodeNameError(node.name, node.pipeline_id) from exc
        stored = self._collection.find_one({"node_id": node.node_id}) or document
        return PipelineNode.from_document(stored)

    def update(self, node_id: str, updates: Mapping[str, Any]) -> PipelineNode:
        now = _now_utc()
        command = self._sanitize_updates(updates, updated_at=now)
        try:
            updated = self._collection.find_one_and_update(
                {"node_id": node_id},
                command,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            name = updates.get("name", "")
            pipeline_id = updates.get("pipeline_id")
            raise DuplicateNodeNameError(str(name), pipeline_id) from exc

        if updated is None:
            raise KeyError(node_id)
        return PipelineNode.from_document(updated)

    def get(self, node_id: str) -> Optional[PipelineNode]:
        doc = self._collection.find_one({"node_id": node_id})
        if not doc:
            return None
        return PipelineNode.from_document(doc)

    def list_nodes(
        self,
        *,
        pipeline_id: Optional[str],
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[PipelineNode], int]:
        filters: dict[str, Any] = {}
        if pipeline_id is not None:
            filters["pipeline_id"] = pipeline_id
        if status:
            filters["status"] = status
        total = self._collection.count_documents(filters)
        skip = max(0, (page - 1) * page_size)
        cursor = (
            self._collection.find(filters)
            .sort("updated_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        items = [PipelineNode.from_document(doc) for doc in cursor]
        return items, total

    def delete(self, node_id: str) -> Optional[PipelineNode]:
        deleted = self._collection.find_one_and_delete({"node_id": node_id})
        if deleted is None:
            return None
        return PipelineNode.from_document(deleted)

    def _serialize(self, node: PipelineNode) -> Mapping[str, Any]:
        document = node.to_document()
        document.setdefault("created_at", _ensure_datetime(document["created_at"]))
        document.setdefault("updated_at", _ensure_datetime(document["updated_at"]))
        if document.get("client_created_at"):
            document["client_created_at"] = _ensure_datetime(document["client_created_at"])
        return document

    @staticmethod
    def _sanitize_updates(updates: Mapping[str, Any], *, updated_at: datetime) -> Mapping[str, Any]:
        allowed_fields = {
            "name",
            "allow_llm",
            "system_prompt",
            "status",
            "strategy",
            "pipeline_id",
            "updated_by",
        }
        sanitized: dict[str, Any] = {}
        set_payload: dict[str, Any] = {}
        for key, value in updates.items():
            if key not in allowed_fields:
                continue
            if key == "strategy" and value is None:
                value = {}
            if key in {"allow_llm"}:
                value = bool(value)
            set_payload[key] = value
        set_payload["updated_at"] = updated_at
        if set_payload:
            sanitized["$set"] = set_payload
        else:
            sanitized["$set"] = {"updated_at": updated_at}
        sanitized["$inc"] = {"version": 1}
        return sanitized


class AsyncPipelineNodeRepository(Protocol):
    async def create(self, node: PipelineNode) -> PipelineNode:
        ...

    async def update(self, node_id: str, updates: Mapping[str, Any]) -> PipelineNode:
        ...

    async def get(self, node_id: str) -> Optional[PipelineNode]:
        ...

    async def list_nodes(
        self,
        pipeline_id: Optional[str],
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[PipelineNode], int]:
        ...

    async def delete(self, node_id: str) -> Optional[PipelineNode]:
        ...


class AsyncMongoPipelineNodeRepository:
    """Motor-backed repository implementation for pipeline nodes."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection
        self._index_lock = asyncio.Lock()
        self._indexes_created = False

    async def create(self, node: PipelineNode) -> PipelineNode:
        await self._ensure_indexes()
        document = self._serialize(node)
        try:
            await self._collection.insert_one(document)
        except DuplicateKeyError as exc:
            raise DuplicateNodeNameError(node.name, node.pipeline_id) from exc
        stored = await self._collection.find_one({"node_id": node.node_id}) or document
        return PipelineNode.from_document(stored)

    async def update(self, node_id: str, updates: Mapping[str, Any]) -> PipelineNode:
        await self._ensure_indexes()
        now = _now_utc()
        command = self._sanitize_updates(updates, updated_at=now)
        try:
            updated = await self._collection.find_one_and_update(
                {"node_id": node_id},
                command,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            name = updates.get("name", "")
            pipeline_id = updates.get("pipeline_id")
            raise DuplicateNodeNameError(str(name), pipeline_id) from exc
        if updated is None:
            raise KeyError(node_id)
        return PipelineNode.from_document(updated)

    async def get(self, node_id: str) -> Optional[PipelineNode]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"node_id": node_id})
        if not doc:
            return None
        return PipelineNode.from_document(doc)

    async def list_nodes(
        self,
        *,
        pipeline_id: Optional[str],
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[PipelineNode], int]:
        await self._ensure_indexes()
        filters: dict[str, Any] = {}
        if pipeline_id is not None:
            filters["pipeline_id"] = pipeline_id
        if status:
            filters["status"] = status
        total = await self._collection.count_documents(filters)
        skip = max(0, (page - 1) * page_size)
        cursor = (
            self._collection.find(filters)
            .sort("updated_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        items: List[PipelineNode] = []
        async for doc in cursor:
            items.append(PipelineNode.from_document(doc))
        return items, total

    async def delete(self, node_id: str) -> Optional[PipelineNode]:
        await self._ensure_indexes()
        deleted = await self._collection.find_one_and_delete({"node_id": node_id})
        if deleted is None:
            return None
        return PipelineNode.from_document(deleted)

    async def _ensure_indexes(self) -> None:
        if self._indexes_created:
            return
        async with self._index_lock:
            if self._indexes_created:
                return
            await self._collection.create_index(
                [("name", ASCENDING), ("pipeline_id", ASCENDING)],
                unique=True,
                name="uniq_pipeline_name",
            )
            await self._collection.create_index(
                [("node_id", ASCENDING)],
                unique=True,
                name="uniq_node_id",
            )
            self._indexes_created = True

    def _serialize(self, node: PipelineNode) -> Mapping[str, Any]:
        document = node.to_document()
        document.setdefault("created_at", _ensure_datetime(document["created_at"]))
        document.setdefault("updated_at", _ensure_datetime(document["updated_at"]))
        if document.get("client_created_at"):
            document["client_created_at"] = _ensure_datetime(document["client_created_at"])
        return document

    def _sanitize_updates(self, updates: Mapping[str, Any], *, updated_at: datetime) -> Mapping[str, Any]:
        return MongoPipelineNodeRepository._sanitize_updates(updates, updated_at=updated_at)


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
