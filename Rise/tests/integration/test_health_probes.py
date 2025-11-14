from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from starlette.testclient import TestClient

from interface_entry.bootstrap.health_routes import register_health_routes


class _DummyRegistry:
    def __init__(self, snapshot: dict[str, dict[str, object]]) -> None:
        self._snapshot = snapshot

    def snapshot(self) -> dict[str, dict[str, object]]:
        return self._snapshot


def test_healthz_reports_router_and_capability_status() -> None:
    app = FastAPI()
    register_health_routes(app, public_url="https://example.com/webhook")
    app.state.capabilities = _DummyRegistry({"mongo": {"status": "available"}})
    app.state.telegram = SimpleNamespace(router=SimpleNamespace(name="demo-router"))

    client = TestClient(app)
    response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["router"] == "demo-router"
    assert data["status"] == "ok"
    assert data["capabilities"]["mongo"]["status"] == "available"


def test_memory_health_exposes_snapshot_and_metadata() -> None:
    app = FastAPI()
    register_health_routes(app, public_url="https://example.com/webhook")
    app.state.memory_snapshot = {"snapshot_version": "v1", "checksum": "abc", "stats": {"checksum_status": "fallback"}}
    app.state.memory_snapshot_status = "ok"
    app.state.memory_snapshot_telemetry = {"checksum_status": "warn"}
    app.state.memory_snapshot_health = {"checksum_status": "fail"}
    app.state.memory_snapshot_missing_agencies = ["bi"]
    app.state.memory_loader_metadata = {"redis": {"available": True}}

    client = TestClient(app)
    response = client.get("/internal/memory_health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["snapshot_version"] == "v1"
    assert data["snapshot_checksum"] == "abc"
    # telemetry checksum has highest priority
    assert data["checksum_status"] == "warn"
    assert data["missing_agencies"] == ["bi"]
