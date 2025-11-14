from __future__ import annotations

"""Reusable CRUD helpers for Mongo-backed repositories."""

from typing import Any, Callable, Iterable, Mapping, MutableMapping, Optional, Sequence, TypeVar, Generic

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING
from pymongo.collection import Collection

TDom = TypeVar("TDom")
DocumentFactory = Callable[[Mapping[str, Any]], TDom]


class SyncMongoCrudMixin(Generic[TDom]):
    """Provides shared CRUD helpers for synchronous PyMongo repositories."""

    id_field: str = "_id"
    sort_field: str = "updated_at"
    index_name: Optional[str] = None

    def __init__(self, collection: Collection, *, factory: DocumentFactory) -> None:
        self._collection = collection
        self._factory = factory
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index(
            [(self.id_field, ASCENDING)],
            unique=True,
            name=self.index_name or f"uniq_{self.id_field}",
        )

    def _insert_document(self, document: MutableMapping[str, Any]) -> TDom:
        self._collection.insert_one(document)
        return self._factory(document)

    def _delete_by_id(self, entity_id: str) -> Optional[TDom]:
        deleted = self._collection.find_one_and_delete({self.id_field: entity_id})
        return self._factory(deleted) if deleted else None

    def _find_by_id(self, entity_id: str) -> Optional[TDom]:
        doc = self._collection.find_one({self.id_field: entity_id})
        return self._factory(doc) if doc else None

    def _list_all(self) -> Sequence[TDom]:
        cursor = self._collection.find().sort(self.sort_field, -1)
        return [self._factory(doc) for doc in cursor]

    def _find_many(self, entity_ids: Iterable[str]) -> Sequence[TDom]:
        ids = list(entity_ids)
        if not ids:
            return ()
        cursor = self._collection.find({self.id_field: {"$in": ids}})
        return [self._factory(doc) for doc in cursor]


class AsyncMongoCrudMixin(Generic[TDom]):
    """Provides shared CRUD helpers for Motor repositories."""

    id_field: str = "_id"
    sort_field: str = "updated_at"
    index_name: Optional[str] = None

    def __init__(self, collection: AsyncIOMotorCollection, *, factory: DocumentFactory) -> None:
        self._collection = collection
        self._factory = factory
        self._indexes_ready = False

    async def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        await self._collection.create_index(
            [(self.id_field, ASCENDING)],
            unique=True,
            name=self.index_name or f"uniq_{self.id_field}",
        )
        self._indexes_ready = True

    async def _insert_document(self, document: MutableMapping[str, Any]) -> TDom:
        await self._ensure_indexes()
        await self._collection.insert_one(document)
        return self._factory(document)

    async def _delete_by_id(self, entity_id: str) -> Optional[TDom]:
        await self._ensure_indexes()
        deleted = await self._collection.find_one_and_delete({self.id_field: entity_id})
        return self._factory(deleted) if deleted else None

    async def _find_by_id(self, entity_id: str) -> Optional[TDom]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({self.id_field: entity_id})
        return self._factory(doc) if doc else None

    async def _list_all(self) -> Sequence[TDom]:
        await self._ensure_indexes()
        cursor = self._collection.find().sort(self.sort_field, -1)
        return [self._factory(doc) async for doc in cursor]

    async def _find_many(self, entity_ids: Iterable[str]) -> Sequence[TDom]:
        ids = list(entity_ids)
        if not ids:
            return ()
        await self._ensure_indexes()
        cursor = self._collection.find({self.id_field: {"$in": ids}})
        return [self._factory(doc) async for doc in cursor]
