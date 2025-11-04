"""Shim helpers delegating to Business Service knowledge snapshot orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, TypedDict

import yaml

from business_service.knowledge import KnowledgeSnapshotService
from business_service.knowledge.models import AssetGuardReport, SnapshotResult

__all__ = [
    "TopLevelAgency",
    "MemorySnapshot",
    "MemoryLoaderResult",
    "load_top_index",
    "behavior_asset_guard",
    "behavior_memory_loader",
    "behavior_kb_pipeline",
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


def behavior_asset_guard(repo_root: Path) -> Dict[str, Any]:
    report = KnowledgeSnapshotService.asset_guard(repo_root)
    return {
        "status": report.status,
        "checked_at": report.checked_at,
        "missing_dirs": list(report.missing_dirs),
        "missing_files": list(report.missing_files),
        "prompt_events": list(report.prompt_events),
    }


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
    service = KnowledgeSnapshotService(
        base_path=base_path,
        org_index_path=org_index_path,
        redis_url=redis_url,
        redis_prefix=redis_prefix,
        redis_primary=redis_primary,
        redis_metadata=redis_metadata,
    )
    result = service.load(agencies=agencies)
    return _snapshot_result_to_dict(result, service)


def behavior_kb_pipeline(
    *,
    config: Mapping[str, Any],
    repo_root: Path | str,
) -> Dict[str, Any]:
    return KnowledgeSnapshotService.pipeline_check(config=config, repo_root=repo_root)


def _snapshot_result_to_dict(result: SnapshotResult, service: KnowledgeSnapshotService) -> MemoryLoaderResult:
    def _wrap_refresh(reason: str = "manual") -> Dict[str, Any]:
        refreshed = service.refresh(reason)
        return _snapshot_result_to_dict(refreshed, service)

    health = result.health
    missing_agencies = list(result.missing_agencies)
    snapshot = dict(result.snapshot)

    data: MemoryLoaderResult = {
        "snapshot": snapshot,  # type: ignore[assignment]
        "snapshot_dict": snapshot,  # type: ignore[assignment]
        "status": result.status,
        "telemetry": dict(result.telemetry),
        "health": {
            "missing_agencies": list(health.missing_agencies),
            "redis_status": health.redis_status,
            "redis_error": health.redis_error,
        },
        "missing_agencies": missing_agencies,
        "refresh": _wrap_refresh,
        "loader": {"refresh": _wrap_refresh},
        "metadata": dict(result.metadata),
    }
    return data
