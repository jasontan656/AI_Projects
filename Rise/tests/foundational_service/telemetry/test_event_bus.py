from __future__ import annotations

from typing import Any, Mapping

import pytest

from foundational_service.telemetry.event_bus import TelemetryEventBus, publish_event


class FakeEmitter:
    def __init__(self) -> None:
        self.callback = None

    def register(self, callback):
        self.callback = callback

    def unregister(self, callback):
        if self.callback == callback:
            self.callback = None

    def push(self, event: Mapping[str, Any]) -> None:
        if self.callback:
            self.callback(event)


def test_event_bus_forwards_events_to_subscribers() -> None:
    emitter = FakeEmitter()
    bus = TelemetryEventBus(register_fn=emitter.register, unregister_fn=emitter.unregister)

    received: list[Mapping[str, Any]] = []

    def listener(event: Mapping[str, Any]) -> None:
        received.append(event)

    bus.subscribe(listener)
    assert emitter.callback is not None

    sample = {"event_type": "workflow.test", "payload": {"status": "ok"}}
    emitter.push(sample)

    assert received == [sample]

    bus.unsubscribe(listener)
    assert emitter.callback is None


def test_publish_event_invokes_underlying_emitter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_emit(event_type: str, **kwargs: Any) -> None:
        captured["event_type"] = event_type
        captured["kwargs"] = kwargs

    monkeypatch.setattr("foundational_service.telemetry.event_bus.telemetry_emit", fake_emit)

    publish_event("workflow.sample", level="warning", payload={"foo": "bar"})

    assert captured["event_type"] == "workflow.sample"
    assert captured["kwargs"]["level"] == "warning"
    assert captured["kwargs"]["payload"] == {"foo": "bar"}
