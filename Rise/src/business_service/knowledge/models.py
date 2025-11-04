from __future__ import annotations

"""Typed models for knowledge snapshot services."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Optional, Sequence

SnapshotStatus = str  # Either "ready" or "memory_only"


@dataclass(slots=True)
class SnapshotHealth:
    missing_agencies: Sequence[str] = field(default_factory=list)
    redis_status: str = "skipped"
    redis_error: str = ""


@dataclass(slots=True)
class SnapshotResult:
    snapshot: Mapping[str, Any]
    snapshot_dict: Mapping[str, Any]
    status: SnapshotStatus
    telemetry: Mapping[str, Any]
    health: SnapshotHealth
    missing_agencies: List[str] = field(default_factory=list)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    refresh: Optional[Callable[[str], "SnapshotResult"]] = None
    loader: Optional[Mapping[str, Callable[[str], "SnapshotResult"]]] = None


@dataclass(slots=True)
class AssetGuardReport:
    status: str
    checked_at: str
    missing_dirs: Sequence[str]
    missing_files: Sequence[str]
    prompt_events: Sequence[Mapping[str, Any]]


__all__ = [
    "SnapshotStatus",
    "SnapshotResult",
    "SnapshotHealth",
    "AssetGuardReport",
]
