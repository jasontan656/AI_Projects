from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from interface_entry.telegram import routes as telegram_routes


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "passport_status"
SNAPSHOT_ROOT = Path(__file__).parent / "snapshots"


class DummyDispatcher:
    def __init__(self) -> None:
        self.workflow_data: Dict[str, Any] = {}
        self.bot = object()
        self.raw_feeds: List[Dict[str, Any]] = []

    async def feed_raw_update(self, bot: Any, payload: Dict[str, Any], *, headers: Dict[str, Any], scope: Dict[str, Any]) -> None:  # type: ignore[override] # pragma: no cover
        self.raw_feeds.append({"bot": bot, "payload": payload, "headers": dict(headers), "scope": dict(scope)})


@pytest.fixture(scope="session")
def fixture_payload() -> Dict[str, Any]:
    return json.loads(FIXTURE_ROOT.joinpath("passport_status_inbound.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def expected_runtime() -> Dict[str, Any]:
    return json.loads(FIXTURE_ROOT.joinpath("expected_runtime.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def runtime_side_effects() -> Dict[str, Any]:
    return json.loads(FIXTURE_ROOT.joinpath("runtime_side_effects.json").read_text(encoding="utf-8"))


@pytest.fixture()
def telemetry_events(monkeypatch: pytest.MonkeyPatch) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []

    def _emit(event_type: str, **fields: Any) -> None:
        events.append({"name": event_type, **fields})

    monkeypatch.setattr("project_utility.telemetry.emit", _emit)
    monkeypatch.setattr("project_utility.tracing.telemetry_emit", _emit)
    monkeypatch.setattr("interface_entry.telegram.routes.telemetry_emit", _emit)
    return events


@pytest.fixture()
def telegram_testbed(
    monkeypatch: pytest.MonkeyPatch,
    expected_runtime: Dict[str, Any],
    telemetry_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    dispatcher = DummyDispatcher()

    def _fake_webhook_request(headers: Dict[str, Any], webhook_secret: str, _dispatcher: DummyDispatcher) -> Dict[str, Any]:
        return {"telemetry": {"signature_status": "accepted", "workflow": expected_runtime["workflow_id"]}}

    def _fake_core_envelope(payload: Dict[str, Any], *, channel: str) -> Dict[str, Any]:
        envelope = {
            "core_envelope": {
                "workflow_id": expected_runtime["workflow_id"],
                "chat_id": payload["message"]["chat"]["id"],
                "text": payload["message"]["text"],
            },
            "telemetry": {
                "workflow": expected_runtime["workflow_id"],
                "stage": expected_runtime["expected_stage"],
            },
        }
        return envelope

    monkeypatch.setattr(telegram_routes, "behavior_webhook_request", _fake_webhook_request)
    monkeypatch.setattr(telegram_routes, "behavior_core_envelope", _fake_core_envelope)
    monkeypatch.setattr(telegram_routes.toolcalls, "call_prepare_logging", lambda bundle, policy, telemetry: {**bundle, **telemetry})
    monkeypatch.setattr(telegram_routes.toolcalls, "call_emit_schema_alert", lambda *args, **kwargs: None)

    app = FastAPI()
    telegram_routes.register_routes(
        app,
        dispatcher,
        "/telegram/test",
        runtime_policy={"versioning": {"prompt_version": "test", "doc_commit": "HEAD"}},
        webhook_secret="test-secret",
    )
    client = TestClient(app)
    try:
        yield {"client": client, "dispatcher": dispatcher, "app": app, "telemetry": telemetry_events}
    finally:
        client.close()


@pytest.fixture(scope="session")
def snapshot_passport_status() -> Dict[str, Any]:
    import yaml

    return yaml.safe_load(SNAPSHOT_ROOT.joinpath("passport_status_dialog.yml").read_text(encoding="utf-8"))
