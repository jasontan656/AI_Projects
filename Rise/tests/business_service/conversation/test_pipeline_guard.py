from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from business_service.conversation.primitives import AdapterBuilder, AgentDelegator
from business_service.conversation.service import TelegramConversationService
from business_service.pipeline.models import PipelineNode


class StubDelegator(AgentDelegator):
    def __init__(self, response: Dict[str, Any] | None = None) -> None:
        super().__init__()
        self.calls: list[Dict[str, Any]] = []
        self._response = response or {"text": "ok", "usage": {}, "response_id": "resp-1"}

    async def dispatch(self, agent_request: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        self.calls.append(agent_request)
        return self._response


def _fake_inbound(_: Dict[str, Any], __: Dict[str, Any]) -> Dict[str, Any]:
    envelope = {
        "metadata": {"chat_id": "123", "convo_id": "123", "language": "en"},
        "payload": {"user_message": "Hello", "context_quotes": []},
    }
    return {
        "response_status": "handled",
        "telemetry": {"update_type": "message"},
        "core_envelope": envelope,
        "envelope": envelope,
        "logging": {},
    }


def _fake_outbound(chunks: Any, _: Any) -> Dict[str, Any]:
    return {"text": "\n".join(chunk for chunk in chunks if chunk)}


@pytest.fixture(autouse=True)
def stub_contracts(monkeypatch):
    monkeypatch.setattr("business_service.conversation.service.behavior_telegram_inbound", _fake_inbound)
    monkeypatch.setattr("business_service.conversation.service.behavior_telegram_outbound", _fake_outbound)
    monkeypatch.setattr(
        "business_service.conversation.service.toolcalls.call_validate_output",
        lambda payload: payload,
    )
    monkeypatch.setattr(
        "business_service.conversation.service.toolcalls.call_validate_telegram_adapter_contract",
        lambda contract: None,
    )


@pytest.mark.asyncio
async def test_pipeline_node_blocks_llm(monkeypatch):
    node = PipelineNode.new(
        name="Blocked Node",
        allow_llm=False,
        system_prompt="Do not call LLM",
        strategy={"fallbackResponse": "Fallback message"},
        actor="tester",
    )
    node.node_id = "node-blocked"
    pipeline_service = SimpleNamespace(get_node=lambda node_id: node if node_id == node.node_id else None)
    delegator = StubDelegator()

    service = TelegramConversationService(
        agent_delegator=delegator,
        adapter_builder=AdapterBuilder(),
        pipeline_service_factory=lambda: pipeline_service,
    )

    result = await service.process_update({"pipeline_node_id": node.node_id}, policy={})
    assert result.status == "blocked"
    assert result.agent_request == {}
    assert result.agent_response["text"] == "Fallback message"
    assert delegator.calls == []


@pytest.mark.asyncio
async def test_pipeline_node_with_allow_llm_appends_system_prompt(monkeypatch):
    node = PipelineNode.new(
        name="LLM Node",
        allow_llm=True,
        system_prompt="System prompt text",
        actor="tester",
    )
    node.node_id = "node-allowed"

    delegator = StubDelegator()
    pipeline_service = SimpleNamespace(get_node=lambda node_id: node if node_id == node.node_id else None)
    service = TelegramConversationService(
        agent_delegator=delegator,
        adapter_builder=AdapterBuilder(),
        pipeline_service_factory=lambda: pipeline_service,
    )

    result = await service.process_update({"pipeline_node_id": node.node_id}, policy={})
    assert result.status == "handled"
    assert delegator.calls, "LLM delegator should be invoked"
    request_payload = delegator.calls[0]
    assert "System prompt text" in request_payload["prompt"]
    assert result.telemetry.get("pipeline_node_id") == node.node_id
