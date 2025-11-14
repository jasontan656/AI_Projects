from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pytest

from business_service.channel.coverage_status import CoverageStatusService


class FakeRedis:
    def __init__(self) -> None:
        self._store: Dict[str, str] = {}
        self.set_calls: list[Dict[str, Any]] = []

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self._store[key] = value
        self.set_calls.append({"key": key, "value": value, "ttl": ex})


class FakeCollection:
    def __init__(self) -> None:
        self.records: list[Dict[str, Any]] = []

    async def insert_one(self, document: Dict[str, Any]) -> None:
        self.records.append(document)


@pytest.mark.asyncio
async def test_mark_status_persists_to_redis_and_history() -> None:
    redis = FakeRedis()
    collection = FakeCollection()
    service = CoverageStatusService(redis_client=redis, history_collection=collection, ttl_seconds=10)

    status = await service.mark_status(
        "wf-01",
        status="pending",
        scenarios=["passport_text", "passport_attachment"],
        mode="webhook",
        actor_id="operator-1",
        metadata={"trigger": "manual"},
    )

    assert status.workflow_id == "wf-01"
    assert status.status == "pending"
    assert status.scenarios == ["passport_text", "passport_attachment"]
    assert redis.set_calls[0]["ttl"] == 10
    assert collection.records[0]["workflowId"] == "wf-01"
    assert collection.records[0]["status"] == "pending"

    cached = await service.get_status("wf-01")
    assert cached.status == "pending"
    assert cached.mode == "webhook"


@pytest.mark.asyncio
async def test_get_status_returns_unknown_when_missing() -> None:
    service = CoverageStatusService(redis_client=FakeRedis(), history_collection=None)
    status = await service.get_status("wf-missing")
    assert status.status == "unknown"
    assert status.scenarios == []
    assert status.updated_at.tzinfo in (timezone.utc, None)
