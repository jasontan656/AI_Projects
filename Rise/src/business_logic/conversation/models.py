from __future__ import annotations

"""Typed models for business logic conversation flows."""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Literal, Mapping, MutableMapping, Optional

ConversationMode = Literal["stream", "direct", "prompt", "refusal", "ignored"]
ConversationStatus = Literal["handled", "ignored"]


@dataclass(slots=True)
class ConversationResult:
    status: ConversationStatus
    mode: ConversationMode
    outbound_contract: MutableMapping[str, Any]
    agent_output: Mapping[str, Any]
    telemetry: Mapping[str, Any]
    audit_reason: str = ""
    error_hint: str = ""
    adapter_contract: Optional[Mapping[str, Any]] = None
    user_text: str = ""
    logging: Mapping[str, Any] = field(default_factory=dict)
    intent: str = ""
    triage_prompt: str = ""
    agent_bridge: Mapping[str, Any] = field(default_factory=dict)
    agent_bridge_telemetry: Mapping[str, Any] = field(default_factory=dict)
    outbound_payload: Mapping[str, Any] = field(default_factory=dict)
    outbound_metrics: Mapping[str, Any] = field(default_factory=dict)
    update_type: str = ""
    core_envelope: Mapping[str, Any] = field(default_factory=dict)
    envelope: Mapping[str, Any] = field(default_factory=dict)
    output_payload: Mapping[str, Any] = field(default_factory=dict)


__all__ = [
    "ConversationMode",
    "ConversationResult",
    "ConversationStatus",
]
