from __future__ import annotations

"""Workflow domain models shared across orchestrator collaborators."""

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Optional, Sequence

__all__ = [
    "WorkflowExecutionContext",
    "WorkflowRunResult",
    "WorkflowStageResult",
]


@dataclass(slots=True)
class WorkflowStageResult:
    """Represents the outcome of a single workflow stage execution."""

    stage_id: str
    name: str
    prompt_used: str
    output_text: str
    raw_response: Mapping[str, Any]


@dataclass(slots=True)
class WorkflowRunResult:
    """Aggregated result for an entire workflow invocation."""

    final_text: str
    stage_results: Sequence[WorkflowStageResult]
    telemetry: Mapping[str, Any]


@dataclass(slots=True)
class WorkflowExecutionContext:
    """Normalized execution context passed into the orchestrator."""

    workflow_id: str
    request_id: str
    user_text: str
    history_chunks: Sequence[str]
    policy: Mapping[str, Any]
    core_envelope: Mapping[str, Any]
    telemetry: MutableMapping[str, Any]
    # Additional metadata payloads are optional to keep the dataclass flexible.
    metadata: Optional[Mapping[str, Any]] = None
    inbound: Optional[Mapping[str, Any]] = None

    def chat_id(self) -> Optional[str]:
        """Resolve the chat/conversation identifier from known payloads."""

        metadata = self.metadata or self.core_envelope.get("metadata", {})
        chat_id = metadata.get("chat_id") or metadata.get("conversation_id")
        if chat_id is None:
            inbound_envelope = self.inbound or self.core_envelope.get("inbound", {})
            chat_id = inbound_envelope.get("chat_id")
        if chat_id is None:
            return None
        return str(chat_id)
