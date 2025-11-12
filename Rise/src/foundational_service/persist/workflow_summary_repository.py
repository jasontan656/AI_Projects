from __future__ import annotations

"""Chat summary persistence bridge for workflow executions."""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional

from pymongo.database import Database
from redis.asyncio import Redis

from project_utility.telemetry import emit as telemetry_emit

__all__ = ["WorkflowSummaryPersistenceError", "WorkflowSummaryRepository", "SummaryWriteResult"]


@dataclass(slots=True)
class SummaryWriteResult:
    """Outcome flags for Redis + Mongo writes."""

    redis_ok: bool
    mongo_ok: bool

    @property
    def status(self) -> str:
        if self.redis_ok and self.mongo_ok:
            return "success"
        if self.redis_ok or self.mongo_ok:
            return "partial"
        return "failed"


class WorkflowSummaryPersistenceError(RuntimeError):
    """Raised when summary persistence fails."""

    def __init__(
        self,
        *,
        chat_id: str,
        redis_error: Optional[Exception] = None,
        mongo_error: Optional[Exception] = None,
    ) -> None:
        super().__init__("workflow summary persistence failed")
        self.chat_id = chat_id
        self.redis_error = redis_error
        self.mongo_error = mongo_error


class WorkflowSummaryRepository:
    """Persist workflow summaries to Redis (cache) and Mongo (archive)."""

    def __init__(
        self,
        *,
        redis_client: Redis,
        mongo_database: Database,
        max_entries: int = 20,
        ttl_seconds: Optional[int] = 3600,
        collection_name: str = "chat_history",
    ) -> None:
        self._redis = redis_client
        self._collection = mongo_database[collection_name]
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds

    async def append_summary(
        self,
        *,
        chat_id: str,
        summary_entry: Mapping[str, Any],
        request_id: str,
        workflow_id: Optional[str] = None,
    ) -> SummaryWriteResult:
        """Persist the latest workflow summary in Redis + Mongo."""

        redis_error: Optional[Exception] = None
        mongo_error: Optional[Exception] = None

        try:
            await self._write_redis(chat_id, summary_entry)
        except Exception as exc:  # pragma: no cover - network failures
            redis_error = exc

        try:
            await self._write_mongo(chat_id, summary_entry)
        except Exception as exc:  # pragma: no cover - network failures
            mongo_error = exc

        redis_ok = redis_error is None
        mongo_ok = mongo_error is None
        result = SummaryWriteResult(redis_ok=redis_ok, mongo_ok=mongo_ok)
        telemetry_emit(
            "workflow.summary.persisted",
            workflow_id=workflow_id,
            request_id=request_id,
            payload={
                "chat_id": chat_id,
                "status": result.status,
                "redis_ok": redis_ok,
                "mongo_ok": mongo_ok,
            },
            level="warning" if result.status != "success" else "info",
        )
        if redis_error or mongo_error:
            raise WorkflowSummaryPersistenceError(
                chat_id=chat_id,
                redis_error=redis_error,
                mongo_error=mongo_error,
            )
        return result

    async def _write_redis(self, chat_id: str, summary_entry: Mapping[str, Any]) -> None:
        payload: MutableMapping[str, Any] = dict(summary_entry)
        payload.setdefault("chat_id", chat_id)
        payload.setdefault("persisted_at", datetime.now(timezone.utc).isoformat())
        key = f"chat:{chat_id}:summary"
        await self._redis.lpush(key, json.dumps(payload, ensure_ascii=False))
        await self._redis.ltrim(key, 0, self._max_entries - 1)
        if self._ttl_seconds and self._ttl_seconds > 0:
            await self._redis.expire(key, self._ttl_seconds)

    async def _write_mongo(self, chat_id: str, summary_entry: Mapping[str, Any]) -> None:
        entry = dict(summary_entry)
        entry.setdefault("chat_id", chat_id)

        def _run() -> None:
            now = datetime.now(timezone.utc)
            self._collection.update_one(
                {"chat_id": chat_id},
                {
                    "$push": {
                        "entries": {
                            "$each": [entry],
                            "$position": 0,
                            "$slice": self._max_entries,
                        }
                    },
                    "$set": {"updated_at": now},
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )

        await asyncio.to_thread(_run)
