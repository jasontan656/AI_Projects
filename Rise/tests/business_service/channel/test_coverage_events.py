from __future__ import annotations

import pytest

from business_service.channel.coverage_status import CoverageStatusService


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value


class StubRecorder:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def record_completion(self, workflow_id: str, **kwargs):
        self.events.append({"workflowId": workflow_id, **kwargs})


@pytest.mark.asyncio
async def test_mark_status_emits_event_on_completion() -> None:
    recorder = StubRecorder()
    service = CoverageStatusService(
        redis_client=FakeRedis(),
        history_collection=None,
        event_recorder=recorder,
    )

    await service.mark_status(
        "wf-alpha",
        status="green",
        scenarios=["passport_text"],
        mode="webhook",
        actor_id="operator-1",
        last_run_id="run-123",
        metadata={"botUsername": "rise_bot", "durationMs": 3200},
    )

    assert len(recorder.events) == 1
    event = recorder.events[0]
    assert event["workflowId"] == "wf-alpha"
    assert event["status"] == "green"
    assert event["scenarios"] == ["passport_text"]
    assert event["metadata"]["durationMs"] == 3200


@pytest.mark.asyncio
async def test_pending_status_does_not_emit_event() -> None:
    recorder = StubRecorder()
    service = CoverageStatusService(
        redis_client=FakeRedis(),
        history_collection=None,
        event_recorder=recorder,
    )

    await service.mark_status(
        "wf-alpha",
        status="pending",
        scenarios=["passport_text"],
        mode="webhook",
        actor_id="operator-1",
        metadata={"trigger": "manual"},
    )

    assert recorder.events == []
