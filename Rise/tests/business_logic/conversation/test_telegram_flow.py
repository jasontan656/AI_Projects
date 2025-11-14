from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from business_logic.conversation.telegram_flow import TelegramConversationFlow
from business_service.conversation.binding_coordinator import BindingCoordinator
from business_service.conversation.context_factory import ConversationContextFactory
from business_service.conversation.models import ConversationServiceResult


@dataclass
class _FakeService:
    context_factory: ConversationContextFactory
    binding_coordinator: BindingCoordinator
    payloads: list[Mapping[str, Any]]

    async def process_update(self, update: Mapping[str, Any], *, policy: Mapping[str, Any]) -> ConversationServiceResult:
        self.payloads.append({"update": update, "policy": policy})
        return ConversationServiceResult(
            status="ok",
            mode="sync",
            outbound_contract={},
            agent_response={},
            agent_request={},
            telemetry={},
            audit_reason="",
            error_hint="",
            adapter_contract={},
            user_text="",
            logging_payload={},
            intent="",
            outbound_payload={},
            outbound_metrics={},
            update_type="",
            core_envelope={},
            legacy_envelope={},
        )


@pytest.mark.asyncio
async def test_flow_passes_context_factory_and_binding_coordinator() -> None:
    context_factory = ConversationContextFactory()
    binding_coordinator = BindingCoordinator()
    flow = TelegramConversationFlow(context_factory=context_factory, binding_coordinator=binding_coordinator)

    assert flow.service.context_factory is context_factory
    assert flow.service.binding_coordinator is binding_coordinator


@pytest.mark.asyncio
async def test_flow_uses_provided_service_for_context_calls() -> None:
    context_factory = ConversationContextFactory()
    binding_coordinator = BindingCoordinator()
    fake_service = _FakeService(context_factory=context_factory, binding_coordinator=binding_coordinator, payloads=[])
    flow = TelegramConversationFlow(service=fake_service)

    result = await flow.process({"message": {"text": "ping"}}, policy={})

    assert result.status == "ok"
    assert fake_service.payloads and fake_service.payloads[0]["update"]["message"]["text"] == "ping"
