from __future__ import annotations

"""Conversation-level primitives exposed by the Business Service layer."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, MutableMapping

from foundational_service.integrations.openai_bridge import behavior_agents_bridge
from interface_entry.telegram.adapters import append_streaming_buffer, telegram_update_to_core


@dataclass(slots=True)
class AgentDelegator:
    """Delegate orchestration to the OpenAI agents bridge."""

    async def dispatch(self, agent_request: Mapping[str, Any]) -> Dict[str, Any]:
        return await behavior_agents_bridge(agent_request)


@dataclass(slots=True)
class AdapterBuilder:
    """Construct adapter contracts consumed by interface layers."""

    def build_contract(
        self,
        update: Mapping[str, Any],
        *,
        core_bundle: Mapping[str, Any],
        agent_request: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:
        return telegram_update_to_core(dict(update), core_bundle=core_bundle, agent_request=dict(agent_request))

    def finalize_contract(
        self,
        contract: MutableMapping[str, Any],
        *,
        chunk_metrics: Iterable[Mapping[str, Any]],
        response_text: str,
        streaming_mode: str,
    ) -> MutableMapping[str, Any]:
        outbound_contract = contract["outbound"]
        reply_to_message_id = contract["inbound"].get("reply_to_message_id")
        if reply_to_message_id is not None:
            outbound_contract["reply_to_message_id"] = int(reply_to_message_id)
        outbound_contract["disable_web_page_preview"] = True
        append_streaming_buffer(contract, chunk_metrics)
        if streaming_mode != "stream":
            outbound_contract["text"] = response_text
        return outbound_contract


__all__ = [
    "AdapterBuilder",
    "AgentDelegator",
]
