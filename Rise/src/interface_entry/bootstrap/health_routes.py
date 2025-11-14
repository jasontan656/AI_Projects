from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Response, status

from interface_entry.bootstrap.capability_service import derive_health_status, snapshot_capabilities


def register_health_routes(app: FastAPI, *, public_url: str) -> None:
    def _capability_snapshot() -> Dict[str, Dict[str, object]]:
        return snapshot_capabilities(app)

    def _status(snapshot: Dict[str, Dict[str, object]]) -> str:
        return derive_health_status(snapshot)

    @app.get("/")
    async def root_probe() -> Dict[str, object]:
        snapshot = _capability_snapshot()
        return {
            "status": _status(snapshot),
            "public_url": public_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.head("/")
    async def root_probe_head() -> Response:
        return Response(status_code=status.HTTP_200_OK)

    @app.get("/healthz")
    async def healthz() -> Dict[str, object]:
        snapshot = _capability_snapshot()
        state = getattr(app.state, "telegram", None)
        return {
            "status": _status(snapshot),
            "router": getattr(state.router, "name", "pending") if state else "pending",
            "capabilities": snapshot,
        }

    @app.get("/healthz/startup")
    async def startup_health() -> Dict[str, object]:
        snapshot = _capability_snapshot()
        return {
            "status": _status(snapshot),
            "capabilities": snapshot,
        }

    @app.get("/healthz/readiness")
    async def readiness_health() -> Dict[str, object]:
        refresher = getattr(app.state, "capability_refresh", None)
        if callable(refresher):
            await refresher()
        snapshot = _capability_snapshot()
        return {
            "status": _status(snapshot),
            "capabilities": snapshot,
        }

    @app.get("/internal/memory_health")
    async def memory_health() -> Dict[str, Any]:
        snapshot = getattr(app.state, "memory_snapshot", {})
        status_value = getattr(app.state, "memory_snapshot_status", "unknown")
        telemetry_state = getattr(app.state, "memory_snapshot_telemetry", {})
        health = getattr(app.state, "memory_snapshot_health", {})
        missing = getattr(app.state, "memory_snapshot_missing_agencies", [])
        metadata = getattr(app.state, "memory_loader_metadata", {})
        checksum_status = (
            telemetry_state.get("checksum_status")
            or health.get("checksum_status")
            or snapshot.get("stats", {}).get("checksum_status")
        )
        return {
            "status": status_value,
            "snapshot_version": snapshot.get("snapshot_version"),
            "snapshot_checksum": snapshot.get("checksum"),
            "checksum_status": checksum_status,
            "stats": snapshot.get("stats", {}),
            "health": health,
            "missing_agencies": missing,
            "telemetry": telemetry_state,
            "metadata": metadata,
        }
