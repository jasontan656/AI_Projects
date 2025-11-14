"""Neutral workflow execution contracts used by foundational services."""
from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional, Protocol, Sequence

try:  # Python 3.11+ has TypedDict in typing
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict  # type: ignore

__all__ = [
    "WorkflowExecutionPayload",
    "WorkflowStageResultPayload",
    "WorkflowRunResultPayload",
    "WorkflowExecutor",
]


class WorkflowExecutionPayload(TypedDict, total=False):
    """Normalized context forwarded to workflow executors."""

    workflow_id: str
    request_id: str
    user_text: str
    history_chunks: Sequence[str]
    policy: Mapping[str, Any]
    core_envelope: Mapping[str, Any]
    telemetry: MutableMapping[str, Any]
    metadata: Optional[Mapping[str, Any]]
    inbound: Optional[Mapping[str, Any]]


class WorkflowStageResultPayload(TypedDict, total=False):
    """Serializable representation of a single workflow stage."""

    stage_id: str
    name: str
    prompt_used: str
    output_text: str
    raw_response: Mapping[str, Any]


class WorkflowRunResultPayload(TypedDict, total=False):
    """Aggregated workflow run output."""

    final_text: str
    stage_results: Sequence[WorkflowStageResultPayload]
    telemetry: Mapping[str, Any]


class WorkflowExecutor(Protocol):
    """Abstraction for running workflows without leaking orchestrator types."""

    async def execute(self, payload: WorkflowExecutionPayload) -> WorkflowRunResultPayload:
        ...
