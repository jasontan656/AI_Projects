from __future__ import annotations

"""Knowledge snapshot loader business service."""

import json
import logging
import os
import shutil
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence

import yaml

from business_service.knowledge.models import AssetGuardReport, SnapshotHealth, SnapshotResult, SnapshotStatus
from project_utility.clock import philippine_iso, philippine_now

try:  # pragma: no cover - redis optional in some environments
    import redis  # type: ignore[import]
    from redis.exceptions import RedisError  # type: ignore[import]
except Exception:  # pragma: no cover - handle environments without redis available
    redis = None  # type: ignore[assignment]

    class RedisError(Exception):  # type: ignore[misc,override]
        """Placeholder error used when redis is not installed."""


logger = logging.getLogger("business_service.knowledge.snapshot")


@dataclass(slots=True)
class _RedisStage:
    status: str
    details: Dict[str, Any]


class KnowledgeSnapshotService:
    """Business-layer service orchestrating knowledge snapshot lifecycle."""

    def __init__(
        self,
        *,
        base_path: Path | str,
        org_index_path: Path | str,
        redis_url: Optional[str] = None,
        redis_prefix: str = "rise:kb",
        redis_primary: Optional[bool] = None,
        redis_metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._base_path = Path(base_path).resolve()
        self._org_index_path = Path(org_index_path).resolve()
        self._redis_url = redis_url or os.getenv("REDIS_URL") or ""
        self._redis_prefix = redis_prefix
        self._redis_primary = redis_primary
        self._redis_metadata = dict(redis_metadata) if redis_metadata else None

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def load(self, *, agencies: Optional[Iterable[str]] = None) -> SnapshotResult:
        """Load knowledge snapshot and optionally publish it to Redis."""

        snapshot, missing = self._load_snapshot(agencies=agencies)
        telemetry: Dict[str, Any] = {"stages": []}
        telemetry["stages"].append(
            {"stage": "initial_load", "status": "attention" if missing else "ready", "missing_agencies": list(missing)}
        )
        redis_stage = self._sync_to_redis(snapshot, reason="initial_load")
        telemetry["stages"].append(redis_stage.details)

        status: SnapshotStatus = "ready"
        if missing or redis_stage.status not in {"ready", "skipped"}:
            status = "memory_only"

        health = SnapshotHealth(
            missing_agencies=list(missing),
            redis_status=redis_stage.status,
            redis_error=str(redis_stage.details.get("error", "")),
        )

        metadata = {"redis": self._build_redis_metadata(redis_stage.details, redis_stage.status)}
        result = SnapshotResult(
            snapshot=snapshot,
            snapshot_dict=snapshot,
            status=status,
            telemetry=telemetry,
            health=health,
            missing_agencies=list(missing),
            metadata=metadata,
            refresh=self.refresh,
            loader={"refresh": self.refresh},
        )
        return result

    def refresh(self, reason: str = "manual") -> SnapshotResult:
        """Refresh snapshot and redis publish state."""

        snapshot, missing = self._load_snapshot()
        redis_stage = self._sync_to_redis(snapshot, reason=reason)

        status: SnapshotStatus = "ready"
        if missing or redis_stage.status not in {"ready", "skipped"}:
            status = "memory_only"

        telemetry = {"stages": [redis_stage.details]}
        health = SnapshotHealth(
            missing_agencies=list(missing),
            redis_status=redis_stage.status,
            redis_error=str(redis_stage.details.get("error", "")),
        )
        metadata = {"redis": self._build_redis_metadata(redis_stage.details, redis_stage.status)}
        result = SnapshotResult(
            snapshot=snapshot,
            snapshot_dict=snapshot,
            status=status,
            telemetry=telemetry,
            health=health,
            missing_agencies=list(missing),
            metadata=metadata,
        )
        result.refresh = self.refresh
        result.loader = {"refresh": self.refresh}
        return result

    @staticmethod
    def asset_guard(repo_root: Path | str) -> AssetGuardReport:
        """Ensure required directories/files exist and surface prompt events."""

        root = Path(repo_root).resolve()
        required_dirs = [
            "config",
            "src/foundational_service/contracts",
            "src/project_utility",
            "src/interface_entry/telegram",
            "KnowledgeBase",
        ]
        required_files = [
            ("KnowledgeBase/KnowledgeBase_index.yaml", "kb_index"),
        ]

        missing_dirs = [name for name in required_dirs if not (root / name).exists()]
        missing_files = [path for path, _ in required_files if not (root / path).exists()]

        prompt_events: list[Dict[str, Any]] = []
        for missing in missing_dirs:
            prompt_events.append(
                {
                    "prompt_id": "asset_guard_violation",
                    "prompt_variables": {"component": missing, "kind": "directory"},
                }
            )
        for missing in missing_files:
            prompt_events.append(
                {
                    "prompt_id": "asset_guard_violation",
                    "prompt_variables": {"component": missing, "kind": "file"},
                }
            )

        status = "ok" if not (missing_dirs or missing_files) else "violation"
        report = AssetGuardReport(
            status=status,
            checked_at=philippine_iso(),
            missing_dirs=missing_dirs,
            missing_files=missing_files,
            prompt_events=prompt_events,
        )
        return report

    @staticmethod
    def pipeline_check(*, config: Mapping[str, Any], repo_root: Path | str) -> Dict[str, Any]:
        """Validate Knowledge Base tooling during CI pipelines."""

        started = philippine_now()
        issues: list[str] = []
        tools = config.get("required_tools", [])
        for tool in tools:
            if not shutil.which(str(tool)):
                issues.append(f"required tool missing: {tool}")

        kb_root = Path(repo_root).resolve() / "KnowledgeBase"
        if not kb_root.exists():
            issues.append(f"knowledge base root missing: {kb_root}")

        snapshot_template = (
            config.get("publish_targets", {}).get("snapshot_path")
            if isinstance(config.get("publish_targets"), Mapping)
            else None
        )

        status: str = "success" if not issues else "failed"
        duration_ms = (philippine_now() - started).total_seconds() * 1000

        report = {
            "status": status,
            "issues": issues,
            "snapshot_path": snapshot_template or "",
            "approvals": config.get("approvals", {}),
            "duration_ms": duration_ms,
        }
        return {"kb_pipeline_report": report}

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _load_snapshot(self, *, agencies: Optional[Iterable[str]] = None) -> tuple[Dict[str, Any], list[str]]:
        if not self._org_index_path.exists():
            raise FileNotFoundError(f"org index missing: {self._org_index_path}")

        org_payload = yaml.safe_load(self._org_index_path.read_text(encoding="utf-8")) or {}
        snapshot: Dict[str, Any] = {
            "org_metadata": org_payload.get("org_metadata", {}),
            "routing_table": org_payload.get("routing_table", []),
            "agencies": {},
            "created_at": philippine_iso(),
            "checksum": "",
            "missing_agencies": [],
        }

        requested_agencies = list(agencies or [])
        if not requested_agencies:
            requested_agencies = [
                str(entry.get("agency_id"))
                for entry in org_payload.get("agencies", [])
                if isinstance(entry, Mapping)
            ]

        missing_agencies: list[str] = []
        digest = sha256(self._org_index_path.read_bytes())
        for agency_id in filter(None, requested_agencies):
            agency_path = (self._base_path / agency_id) / f"{agency_id}_index.yaml"
            if not agency_path.exists():
                missing_agencies.append(agency_id)
                continue
            payload = yaml.safe_load(agency_path.read_text(encoding="utf-8")) or {}
            snapshot["agencies"][agency_id] = payload
            digest.update(agency_path.read_bytes())
        snapshot["missing_agencies"] = list(missing_agencies)
        snapshot["checksum"] = f"sha256::{digest.hexdigest()}"
        return snapshot, missing_agencies

    def _sync_to_redis(self, snapshot: Mapping[str, Any], *, reason: str) -> _RedisStage:
        stage_details: Dict[str, Any] = {"stage": "redis_sync", "reason": reason, "status": "skipped"}
        if not self._redis_url:
            return _RedisStage(status="skipped", details=stage_details)

        stage_details["redis_url"] = self._redis_url
        if redis is None:
            stage_details.update(status="redis_unavailable", error="redis_dependency_missing")
            return _RedisStage(status="redis_unavailable", details=stage_details)

        client = None
        try:
            client = redis.Redis.from_url(  # type: ignore[attr-defined]
                self._redis_url,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
            )
            client.ping()
            payload = json.dumps(snapshot, ensure_ascii=False)
            cached_at = philippine_iso()
            snapshot_key = f"{self._redis_prefix}:snapshot"
            metadata_key = f"{self._redis_prefix}:metadata"
            client.set(snapshot_key, payload)
            client.hset(
                metadata_key,
                mapping={
                    "updated_at": cached_at,
                    "reason": reason,
                    "checksum": snapshot.get("checksum", ""),
                    "missing_agencies": json.dumps(snapshot.get("missing_agencies", []), ensure_ascii=False),
                },
            )
            stage_details.update(
                status="ready",
                snapshot_key=snapshot_key,
                metadata_key=metadata_key,
                cached_at=cached_at,
            )
            return _RedisStage(status="ready", details=stage_details)
        except RedisError as exc:  # type: ignore[misc]
            stage_details.update(status="redis_unavailable", error=str(exc))
            logger.warning("knowledge.redis_unavailable", extra={"reason": reason, "error": str(exc)})
            return _RedisStage(status="redis_unavailable", details=stage_details)
        except Exception as exc:  # pragma: no cover - defensive
            stage_details.update(status="redis_unavailable", error=str(exc))
            logger.exception("knowledge.redis_sync_failed", extra={"reason": reason})
            return _RedisStage(status="redis_unavailable", details=stage_details)
        finally:
            if client is not None:
                try:
                    client.close()  # type: ignore[attr-defined]
                except Exception:
                    pass

    def _build_redis_metadata(self, stage: Mapping[str, Any], status: str) -> Dict[str, Any]:
        redis_details: Dict[str, Any] = {
            "backend": "redis" if status == "ready" else "memory",
            "primary": "redis" if self._redis_primary else "memory",
            "status": status,
            "available": status == "ready",
        }
        for key, value in stage.items():
            if key not in {"stage", "reason"}:
                redis_details[key] = value
        if self._redis_metadata:
            redis_details["metadata"] = dict(self._redis_metadata)
        return redis_details


__all__ = [
    "KnowledgeSnapshotService",
]
