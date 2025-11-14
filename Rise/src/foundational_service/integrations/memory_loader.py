"""Shim helpers delegating to injected Knowledge Snapshot services."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, TypedDict, cast

import yaml

from foundational_service.contracts.knowledge_io import (
    KnowledgeAssetGuardReport,
    KnowledgeSnapshotResultDict,
    KnowledgeSnapshotService,
)
from project_utility.clock import philippine_iso, philippine_now

__all__ = [
    "TopLevelAgency",
    "MemorySnapshot",
    "MemoryLoaderResult",
    "load_top_index",
    "behavior_asset_guard",
    "behavior_memory_loader",
    "behavior_kb_pipeline",
    "configure_knowledge_snapshot",
]


class TopLevelAgency(TypedDict):
    key: str
    name: str
    path: str
    keywords: list[str]


class MemorySnapshot(TypedDict):
    org_metadata: Mapping[str, Any]
    routing_table: Sequence[Any]
    agencies: Mapping[str, Any]
    created_at: str
    checksum: str
    missing_agencies: list[str]


class MemoryLoaderResult(TypedDict):
    snapshot: MemorySnapshot
    snapshot_dict: MemorySnapshot
    status: str
    telemetry: Dict[str, Any]
    health: Dict[str, Any]
    missing_agencies: list[str]
    refresh: Callable[[str], Dict[str, Any]]
    loader: Dict[str, Callable[[str], Dict[str, Any]]]
    metadata: Dict[str, Any]


KnowledgeSnapshotBuilder = Callable[..., KnowledgeSnapshotService]

_snapshot_builder: Optional[KnowledgeSnapshotBuilder] = None


def configure_knowledge_snapshot(builder: KnowledgeSnapshotBuilder) -> None:
    """Register a KnowledgeSnapshotService factory supplied by higher layers."""

    global _snapshot_builder
    _snapshot_builder = builder


def _build_snapshot_service(**kwargs: Any) -> KnowledgeSnapshotService:
    if _snapshot_builder is None:
        raise RuntimeError("knowledge snapshot builder not configured")
    return _snapshot_builder(**kwargs)


def load_top_index(index_path: Path) -> list[TopLevelAgency]:
    data: Mapping[str, Any] = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    agencies: list[TopLevelAgency] = []
    for item in data.get("agencies", []):
        if not isinstance(item, Mapping):
            continue
        agency_id = str(item.get("agency_id") or item.get("id") or "").lower()
        agencies.append(
            {
                "key": agency_id,
                "name": str(item.get("name") or item.get("agency_name") or agency_id),
                "path": str(item.get("path") or ""),
                "keywords": [str(k).lower() for k in item.get("keywords", [])],
            }
        )
    return agencies


def behavior_asset_guard(repo_root: Path) -> KnowledgeAssetGuardReport:
    """Run asset guard checks without importing business services."""

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
    root = Path(repo_root).resolve()
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
    return KnowledgeAssetGuardReport(
        status=status,
        checked_at=philippine_iso(),
        missing_dirs=missing_dirs,
        missing_files=missing_files,
        prompt_events=prompt_events,
    )


def behavior_memory_loader(
    *,
    base_path: Path,
    org_index_path: Path,
    agencies: Optional[Iterable[str]] = None,
    redis_url: Optional[str] = None,
    redis_prefix: str = "rise:kb",
    redis_primary: Optional[bool] = None,
    redis_metadata: Optional[Mapping[str, Any]] = None,
) -> MemoryLoaderResult:
    service = _build_snapshot_service(
        base_path=base_path,
        org_index_path=org_index_path,
        redis_url=redis_url,
        redis_prefix=redis_prefix,
        redis_primary=redis_primary,
        redis_metadata=redis_metadata,
    )
    result = service.load(agencies=agencies)
    return _snapshot_result_to_dict(result)


def behavior_kb_pipeline(
    *,
    config: Mapping[str, Any],
    repo_root: Path | str,
) -> Dict[str, Any]:
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
    status = "success" if not issues else "failed"
    duration_ms = (philippine_now() - started).total_seconds() * 1000
    report = {
        "status": status,
        "issues": issues,
        "snapshot_path": snapshot_template or "",
        "approvals": config.get("approvals", {}),
        "duration_ms": duration_ms,
    }
    return {"kb_pipeline_report": report}


def _snapshot_result_to_dict(result: KnowledgeSnapshotResultDict) -> MemoryLoaderResult:
    refresh_fn = cast(Optional[Callable[[str], KnowledgeSnapshotResultDict]], result.get("refresh"))

    def _wrap_refresh(reason: str = "manual") -> Dict[str, Any]:
        if refresh_fn is None:
            raise RuntimeError("refresh handler unavailable")
        refreshed = refresh_fn(reason)
        return _snapshot_result_to_dict(refreshed)

    health = result.get("health") or {}
    missing_agencies = list(result.get("missing_agencies") or [])
    snapshot = dict(result.get("snapshot") or {})
    telemetry = dict(result.get("telemetry") or {})
    metadata = dict(result.get("metadata") or {})

    data: MemoryLoaderResult = {
        "snapshot": snapshot,  # type: ignore[assignment]
        "snapshot_dict": snapshot,  # type: ignore[assignment]
        "status": str(result.get("status", "")),
        "telemetry": telemetry,
        "health": {
            "missing_agencies": list(health.get("missing_agencies") or []),
            "redis_status": health.get("redis_status"),
            "redis_error": health.get("redis_error"),
        },
        "missing_agencies": missing_agencies,
        "refresh": _wrap_refresh,
        "loader": {"refresh": _wrap_refresh},
        "metadata": metadata,
    }
    return data
