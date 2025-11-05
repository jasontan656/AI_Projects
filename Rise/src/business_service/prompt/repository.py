from __future__ import annotations

"""Mongo-backed repository for prompt records."""

import asyncio
from datetime import datetime
from typing import Any, List, Mapping, Optional, Protocol, Tuple

from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection

from business_service.prompt.models import Prompt, _now_utc
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError


class PromptRepository(Protocol):
    def create(self, prompt: Prompt) -> Prompt:
        ...

    def update(self, prompt_id: str, payload: Mapping[str, Any]) -> Prompt:
        ...

    def delete(self, prompt_id: str) -> Optional[Prompt]:
        ...

    def get(self, prompt_id: str) -> Optional[Prompt]:
        ...

    def list_prompts(
        self,
        *,
        page: int,
        page_size: int,
    ) -> Tuple[List[Prompt], int]:
        ...


class MongoPromptRepository:
    def __init__(self, collection: Collection) -> None:
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index(
            [("prompt_id", ASCENDING)],
            unique=True,
            name="uniq_prompt_id",
        )
        self._collection.create_index(
            [("name", ASCENDING)],
            name="prompt_name_idx",
        )

    def create(self, prompt: Prompt) -> Prompt:
        document = self._serialize(prompt)
        self._collection.insert_one(document)
        stored = self._collection.find_one({"prompt_id": prompt.prompt_id}) or document
        return Prompt.from_document(stored)

    def update(self, prompt_id: str, payload: Mapping[str, Any]) -> Prompt:
        command = self._sanitize_updates(payload, updated_at=_now_utc())
        updated = self._collection.find_one_and_update(
            {"prompt_id": prompt_id},
            command,
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise KeyError(prompt_id)
        return Prompt.from_document(updated)

    def delete(self, prompt_id: str) -> Optional[Prompt]:
        deleted = self._collection.find_one_and_delete({"prompt_id": prompt_id})
        if deleted is None:
            return None
        return Prompt.from_document(deleted)

    def get(self, prompt_id: str) -> Optional[Prompt]:
        doc = self._collection.find_one({"prompt_id": prompt_id})
        if doc is None:
            return None
        return Prompt.from_document(doc)

    def list_prompts(
        self,
        *,
        page: int,
        page_size: int,
    ) -> Tuple[List[Prompt], int]:
        filters: dict[str, Any] = {}
        total = self._collection.count_documents(filters)
        skip = max(0, (page - 1) * page_size)
        cursor = (
            self._collection.find(filters)
            .sort("updated_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        items = [Prompt.from_document(doc) for doc in cursor]
        return items, total

    def _serialize(self, prompt: Prompt) -> Mapping[str, Any]:
        document = prompt.to_document()
        document["created_at"] = _ensure_datetime(document["created_at"])
        document["updated_at"] = _ensure_datetime(document["updated_at"])
        return document

    @staticmethod
    def _sanitize_updates(payload: Mapping[str, Any], *, updated_at: datetime) -> Mapping[str, Any]:
        set_payload: dict[str, Any] = {"updated_at": updated_at}
        if "name" in payload:
            set_payload["name"] = str(payload["name"])
        if "markdown" in payload:
            set_payload["markdown"] = str(payload["markdown"])
        if "updated_by" in payload:
            set_payload["updated_by"] = payload["updated_by"]
        return {
            "$set": set_payload,
            "$inc": {"version": 1},
        }


class AsyncPromptRepository(Protocol):
    async def create(self, prompt: Prompt) -> Prompt:
        ...

    async def update(self, prompt_id: str, payload: Mapping[str, Any]) -> Prompt:
        ...

    async def delete(self, prompt_id: str) -> Optional[Prompt]:
        ...

    async def get(self, prompt_id: str) -> Optional[Prompt]:
        ...

    async def list_prompts(
        self,
        *,
        page: int,
        page_size: int,
    ) -> Tuple[List[Prompt], int]:
        ...


class AsyncMongoPromptRepository:
    """Motor-based prompt repository for async workflows."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection
        self._index_lock = asyncio.Lock()
        self._indexes_created = False

    async def create(self, prompt: Prompt) -> Prompt:
        await self._ensure_indexes()
        document = self._serialize(prompt)
        await self._collection.insert_one(document)
        stored = await self._collection.find_one({"prompt_id": prompt.prompt_id}) or document
        return Prompt.from_document(stored)

    async def update(self, prompt_id: str, payload: Mapping[str, Any]) -> Prompt:
        await self._ensure_indexes()
        command = self._sanitize_updates(payload, updated_at=_now_utc())
        updated = await self._collection.find_one_and_update(
            {"prompt_id": prompt_id},
            command,
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise KeyError(prompt_id)
        return Prompt.from_document(updated)

    async def delete(self, prompt_id: str) -> Optional[Prompt]:
        await self._ensure_indexes()
        deleted = await self._collection.find_one_and_delete({"prompt_id": prompt_id})
        if deleted is None:
            return None
        return Prompt.from_document(deleted)

    async def get(self, prompt_id: str) -> Optional[Prompt]:
        await self._ensure_indexes()
        doc = await self._collection.find_one({"prompt_id": prompt_id})
        if doc is None:
            return None
        return Prompt.from_document(doc)

    async def list_prompts(
        self,
        *,
        page: int,
        page_size: int,
    ) -> Tuple[List[Prompt], int]:
        await self._ensure_indexes()
        filters: dict[str, Any] = {}
        total = await self._collection.count_documents(filters)
        skip = max(0, (page - 1) * page_size)
        cursor = (
            self._collection.find(filters)
            .sort("updated_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        items: List[Prompt] = []
        async for doc in cursor:
            items.append(Prompt.from_document(doc))
        return items, total

    async def _ensure_indexes(self) -> None:
        if self._indexes_created:
            return
        async with self._index_lock:
            if self._indexes_created:
                return
            await self._collection.create_index(
                [("prompt_id", ASCENDING)],
                unique=True,
                name="uniq_prompt_id",
            )
            # tolerate duplicate name creation attempts
            try:
                await self._collection.create_index(
                    [("name", ASCENDING)],
                    name="prompt_name_idx",
                )
            except DuplicateKeyError:
                pass
            self._indexes_created = True

    def _serialize(self, prompt: Prompt) -> Mapping[str, Any]:
        document = prompt.to_document()
        document["created_at"] = _ensure_datetime(document["created_at"])
        document["updated_at"] = _ensure_datetime(document["updated_at"])
        return document

    @staticmethod
    def _sanitize_updates(payload: Mapping[str, Any], *, updated_at: datetime) -> Mapping[str, Any]:
        set_payload: dict[str, Any] = {"updated_at": updated_at}
        if "name" in payload:
            set_payload["name"] = str(payload["name"])
        if "markdown" in payload:
            set_payload["markdown"] = str(payload["markdown"])
        if "updated_by" in payload:
            set_payload["updated_by"] = payload["updated_by"]
        return {
            "$set": set_payload,
            "$inc": {"version": 1},
        }


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


__all__ = [
    "PromptRepository",
    "MongoPromptRepository",
    "AsyncPromptRepository",
    "AsyncMongoPromptRepository",
]
