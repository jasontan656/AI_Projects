"""Knowledge snapshot contracts shared across layers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Protocol, Sequence

try:
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict  # type: ignore

__all__ = [
    "KnowledgeAssetGuardReport",
    "KnowledgeSnapshotHealth",
    "KnowledgeSnapshotResultDict",
    "KnowledgeSnapshotService",
]


class KnowledgeAssetGuardReport(TypedDict, total=False):
    status: str
    checked_at: str
    missing_dirs: Sequence[str]
    missing_files: Sequence[str]
    prompt_events: Sequence[Mapping[str, Any]]


class KnowledgeSnapshotHealth(TypedDict, total=False):
    missing_agencies: Sequence[str]
    redis_status: str
    redis_error: str


class KnowledgeSnapshotMetadata(TypedDict, total=False):
    redis: Mapping[str, Any]


class KnowledgeSnapshotResultDict(TypedDict, total=False):
    snapshot: Mapping[str, Any]
    snapshot_dict: Mapping[str, Any]
    status: str
    telemetry: Mapping[str, Any]
    health: KnowledgeSnapshotHealth
    missing_agencies: Sequence[str]
    refresh: Callable[[str], Mapping[str, Any]]
    loader: Mapping[str, Callable[[str], Mapping[str, Any]]]
    metadata: KnowledgeSnapshotMetadata


class KnowledgeSnapshotService(Protocol):
    """Protocol describing the subset of knowledge snapshot behavior needed by foundational code."""

    def load(self, *, agencies: Optional[Iterable[str]] = None) -> KnowledgeSnapshotResultDict:
        ...

    def refresh(self, reason: str = "manual") -> KnowledgeSnapshotResultDict:
        ...

    def asset_guard(self, repo_root: Path | str) -> KnowledgeAssetGuardReport:
        ...

    def pipeline_check(self, *, config: Mapping[str, Any], repo_root: Path | str) -> Mapping[str, Any]:
        ...
