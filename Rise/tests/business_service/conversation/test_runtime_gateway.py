from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Mapping, Optional

import pytest

from business_service.channel.health_store import ChannelBindingHealthStore
from business_service.conversation.runtime_dispatch import DispatchConfig, RuntimeDispatchController
from business_service.conversation.runtime_gateway import EnqueueFailedError, RuntimeDispatchOutcome
from foundational_service.persist.task_envelope import TaskEnvelope


class FakeGateway:
    def __init__(self, *, outcome: Optional[RuntimeDispatchOutcome] = None, error: Optional[Exception] = None) -> None:
        self._outcome = outcome
        self._error = error
        self.calls: List[Dict[str, Any]] = []

    async def dispatch(self, **kwargs: Any) -> RuntimeDispatchOutcome:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        if self._outcome is None:
            raise RuntimeError("missing outcome in fake gateway")
        return self._outcome


class FakeHealthStore:
    def __init__(self) -> None:
        self.heartbeats: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    async def record_test_heartbeat(self, channel: str, workflow_id: str, *, status: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.heartbeats.append(
            {"channel": channel, "workflow_id": workflow_id, "status": status, "metadata": metadata or {}},
        )

    async def increment_error(self, channel: str, workflow_id: str, error_type: str) -> None:
        self.errors.append({"channel": channel, "workflow_id": workflow_id, "error_type": error_type})


class FakeReservation:
    def __init__(self, *, is_new: bool) -> None:
        self.is_new = is_new


class FakeAckFactory:
    def __init__(self, reservation: FakeReservation) -> None:
        self._reservation = reservation
        self.calls: List[Dict[str, Any]] = []

    async def reserve(self, *, idempotency_key: Optional[str], task_id: str) -> FakeReservation:
        self.calls.append({"idempotency_key": idempotency_key, "task_id": task_id})
        return self._reservation


@pytest.mark.asyncio
async def test_controller_records_heartbeat_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("business_service.conversation.runtime_dispatch.telemetry_emit", lambda *args, **kwargs: None)
    envelope = TaskEnvelope.new(task_type="telegram", payload={"message": "ping"})
    outcome = RuntimeDispatchOutcome(envelope=envelope, status="completed", result_payload={"reply": "pong"})
    gateway = FakeGateway(outcome=outcome)
    store = FakeHealthStore()
    controller = RuntimeDispatchController(gateway=gateway, health_store=store)

    result = await controller.dispatch(
        envelope=envelope,
        workflow_id="wf-passport",
        channel="telegram",
        config=DispatchConfig(expects_result=True, wait_for_result=False),
        metadata={"workflowSlug": "passport_status"},
    )

    assert result.status == "completed"
    assert len(store.heartbeats) == 1
    heartbeat = store.heartbeats[0]
    assert heartbeat["status"] == "completed"
    assert heartbeat["metadata"]["workflowSlug"] == "passport_status"
    assert heartbeat["metadata"]["taskId"] == envelope.task_id


@pytest.mark.asyncio
async def test_controller_skips_dispatch_when_idempotency_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("business_service.conversation.runtime_dispatch.telemetry_emit", lambda *args, **kwargs: None)
    envelope = TaskEnvelope.new(task_type="telegram", payload={}, context={})
    gateway = FakeGateway(outcome=RuntimeDispatchOutcome(envelope=envelope, status="pending"))
    store = FakeHealthStore()
    ack_factory = FakeAckFactory(FakeReservation(is_new=False))
    controller = RuntimeDispatchController(gateway=gateway, health_store=store, async_handle_factory=ack_factory)

    outcome = await controller.dispatch(
        envelope=envelope,
        workflow_id="wf-passport",
        channel="telegram",
        config=DispatchConfig(idempotency_key="dup-key"),
    )

    assert outcome.status == "duplicate"
    assert not gateway.calls
    assert store.heartbeats[0]["status"] == "duplicate"


@pytest.mark.asyncio
async def test_controller_records_enqueue_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("business_service.conversation.runtime_dispatch.telemetry_emit", lambda *args, **kwargs: None)
    envelope = TaskEnvelope.new(task_type="telegram", payload={}, context={})
    gateway_error = EnqueueFailedError(envelope, RuntimeError("queue down"))
    gateway = FakeGateway(error=gateway_error)
    store = FakeHealthStore()
    controller = RuntimeDispatchController(gateway=gateway, health_store=store)

    with pytest.raises(EnqueueFailedError):
        await controller.dispatch(
            envelope=envelope,
            workflow_id="wf-passport",
            channel="telegram",
            config=DispatchConfig(),
        )

    assert store.errors == [
        {"channel": "telegram", "workflow_id": "wf-passport", "error_type": "enqueue_failed"}
    ]
    assert store.heartbeats == []


@pytest.mark.asyncio
async def test_channel_health_store_records_heartbeat_payload() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.calls: List[Any] = []

        async def hset(self, key: str, mapping: Mapping[str, Any]) -> None:  # type: ignore[override]
            self.calls.append(("hset", key, dict(mapping)))

        async def expire(self, key: str, ttl: int) -> None:
            self.calls.append(("expire", key, ttl))

    redis = FakeRedis()
    store = ChannelBindingHealthStore(redis_client=redis, ttl_seconds=60)
    await store.record_test_heartbeat(
        "telegram",
        "wf-passport",
        status="completed",
        metadata={"taskId": "abc123", "idempotencyKey": "dup"},
    )

    assert redis.calls[0][0] == "hset"
    assert redis.calls[0][1].endswith("wf-passport")
    payload = redis.calls[0][2]
    assert payload["lastHeartbeatStatus"] == "completed"
    assert payload["heartbeat_taskId"] == "abc123"
    assert payload["heartbeat_idempotencyKey"] == "dup"
    assert redis.calls[1] == ("expire", redis.calls[0][1], 60)
