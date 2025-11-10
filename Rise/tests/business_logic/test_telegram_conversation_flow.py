from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, MutableMapping

import pytest

import business_logic.conversation.telegram_flow as flow_module
import business_service.conversation.service as service_module
from business_logic.conversation import TelegramConversationFlow


class StubAdapterBuilder:
    def build_contract(
        self,
        update: Mapping[str, Any],
        *,
        core_bundle: Mapping[str, Any],
        agent_request: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:
        return {
            "outbound": {"chat_id": 123, "parse_mode": "MarkdownV2"},
            "inbound": {},
        }

    def finalize_contract(
        self,
        contract: MutableMapping[str, Any],
        *,
        chunk_metrics: Iterable[Mapping[str, Any]],
        response_text: str,
        streaming_mode: str,
    ) -> MutableMapping[str, Any]:
        contract["outbound"]["disable_web_page_preview"] = True
        contract["outbound"]["streaming_buffer"] = list(chunk_metrics)
        if streaming_mode != "stream":
            contract["outbound"]["text"] = response_text
        return contract["outbound"]


class StubAgentDelegator:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload
        self.called = False

    async def dispatch(self, agent_request: Mapping[str, Any]) -> Dict[str, Any]:
        self.called = True
        return self.payload


@pytest.mark.asyncio
async def test_flow_raises_on_legacy_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy prompt injection should hard fail to surface misconfiguration."""

    def fake_behavior_telegram_inbound(update: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
        core_envelope = {
            "metadata": {"chat_id": "123", "language": "en"},
            "payload": {"user_message": "help me", "context_quotes": []},
            "ext_flags": {},
        }
        return {
            "core_envelope": core_envelope,
            "envelope": core_envelope,
            "agent_request": {"system_tags": []},
            "logging": {},
            "telemetry": {"update_type": "message"},
            "prompt_id": "agent_refusal_policy",
            "prompt_variables": {"rule": "policy"},
        }

    def fake_behavior_telegram_outbound(chunks: Any, policy: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "text": "rendered-policy",
            "metrics": {"chunk_metrics": [], "total_chars": 15},
            "placeholder": "",
            "edits": [],
        }

    monkeypatch.setattr(
        service_module,
        "contracts_telegram_inbound",
        fake_behavior_telegram_inbound,
    )
    monkeypatch.setattr(
        service_module,
        "contracts_telegram_outbound",
        fake_behavior_telegram_outbound,
    )

    flow = TelegramConversationFlow(adapter_builder=StubAdapterBuilder())
    policy = {"tokens_budget": {"per_call_max_tokens": 1000, "summary_threshold_tokens": 400}}
    with pytest.raises(RuntimeError, match="legacy prompt flow detected"):
        await flow.process({"message": {"text": "ignored"}}, policy=policy)


@pytest.mark.asyncio
async def test_flow_invokes_agent_delegator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Flow should invoke agent delegator for compose paths."""

    def fake_behavior_telegram_inbound(update: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
        core_envelope = {
            "metadata": {"chat_id": "321", "language": "en"},
            "payload": {"user_message": "Tell me about visas", "context_quotes": []},
            "ext_flags": {},
        }
        return {
            "core_envelope": core_envelope,
            "envelope": core_envelope,
            "agent_request": {"prompt": "compose", "system_tags": []},
            "logging": {},
            "telemetry": {"update_type": "message"},
        }

    def fake_behavior_telegram_outbound(chunks: Any, policy: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "text": "agent-response",
            "metrics": {
                "chunk_metrics": [{"chunk_index": 0, "char_count": 14, "planned_delay_ms": 0.0}],
                "total_chars": 14,
            },
            "placeholder": "Working…",
            "edits": [],
        }

    monkeypatch.setattr(
        service_module,
        "contracts_telegram_inbound",
        fake_behavior_telegram_inbound,
    )
    monkeypatch.setattr(
        service_module,
        "contracts_telegram_outbound",
        fake_behavior_telegram_outbound,
    )

    delegator_payload = {
        "agent_bridge_result": {
            "mode": "stream",
            "chunks": ["agent-response"],
            "tokens_usage": {"total": 42},
        },
        "telemetry": {"dispatch": "ok"},
    }
    delegator = StubAgentDelegator(delegator_payload)

    flow = TelegramConversationFlow(
        agent_delegator=delegator,
        adapter_builder=StubAdapterBuilder(),
    )
    policy = {"tokens_budget": {"per_call_max_tokens": 1000, "summary_threshold_tokens": 400}}
    result = await flow.process({"message": {"text": "compose"}}, policy=policy)

    assert result.status == "handled"
    assert result.mode == "stream"
    assert delegator.called is True
    assert result.agent_output.get("text") == "agent-response"
    assert result.outbound_contract.get("streaming_buffer") == [
        {"chunk_index": 0, "char_count": 14, "planned_delay_ms": 0.0}
    ]
