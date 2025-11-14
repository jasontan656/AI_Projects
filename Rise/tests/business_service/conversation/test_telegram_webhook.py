from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient
from foundational_service.contracts.envelope import SchemaValidationError

from interface_entry.telegram import routes as telegram_routes


SNAPSHOT_FILE = Path(__file__).parent / "snapshots" / "passport_status_dialog.yml"


def _assert_snapshot(events: List[Dict[str, object]], snapshot: Dict[str, object]) -> None:
    expected_events = snapshot.get("events", [])
    for expected in expected_events:
        name = expected["name"]
        match = next((event for event in events if event["name"] == name), None)
        assert match is not None, f"缺少事件 {name}"
        for field_name, field_value in expected.get("fields", {}).items():
            candidate = match.get(field_name)
            if candidate is None:
                payload = match.get("payload") or {}
                if isinstance(payload, dict):
                    candidate = payload.get(field_name)
            assert candidate == field_value, f"{name}.{field_name}={candidate} != {field_value}"


def test_passport_status_dialog_runs_happy_path(
    telegram_testbed: Dict[str, object],
    fixture_payload: Dict[str, object],
    snapshot_passport_status: Dict[str, object],
) -> None:
    client: TestClient = telegram_testbed["client"]  # type: ignore[assignment]
    dispatcher = telegram_testbed["dispatcher"]  # type: ignore[assignment]
    telemetry_events = telegram_testbed["telemetry"]  # type: ignore[assignment]
    response = client.post("/telegram/test", json=fixture_payload)
    assert response.status_code == 200
    assert len(dispatcher.raw_feeds) == 1  # type: ignore[attr-defined]
    metrics = telegram_testbed["app"].state.telegram_metrics  # type: ignore[index]
    assert metrics["telegram_updates_total"] == 1
    assert metrics["webhook_rtt_ms_count"] == 1
    _assert_snapshot(telemetry_events, snapshot_passport_status)


def test_passport_status_dialog_schema_violation_rejected(
    telegram_testbed: Dict[str, object],
    fixture_payload: Dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_schema_error(payload: Dict[str, object], *, channel: str) -> Dict[str, object]:
        raise SchemaValidationError("invalid payload")  # type: ignore[arg-type]

    monkeypatch.setattr(telegram_routes, "behavior_core_envelope", _raise_schema_error)
    client: TestClient = telegram_testbed["client"]  # type: ignore[assignment]
    telemetry_events = telegram_testbed["telemetry"]  # type: ignore[assignment]
    response = client.post("/telegram/test", json=fixture_payload)
    assert response.status_code == 422
    reject_events = [event for event in telemetry_events if event["name"] == "telegram.webhook.reject"]
    assert reject_events, "缺少 reject 事件"
    payload = reject_events[-1].get("payload") or {}
    assert payload.get("status_code") == 422
