from __future__ import annotations

"""Typed数据模型：业务服务层的会话编排结果与上下文。"""

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

ConversationStatus = str  # "handled" 或 "ignored"
ConversationMode = str  # "direct" / "ignored"


@dataclass(slots=True)
class ConversationServiceResult:
    """业务服务层对外返回的结构化结果。"""

    status: ConversationStatus
    mode: ConversationMode
    intent: str
    agent_request: Mapping[str, Any]
    agent_response: Mapping[str, Any]
    telemetry: Mapping[str, Any]
    adapter_contract: MutableMapping[str, Any]
    outbound_contract: MutableMapping[str, Any]
    outbound_payload: Mapping[str, Any]
    outbound_metrics: Mapping[str, Any]
    audit_reason: str
    error_hint: str
    user_text: str
    logging_payload: Mapping[str, Any]
    update_type: str
    core_envelope: Mapping[str, Any]
    legacy_envelope: Mapping[str, Any]
