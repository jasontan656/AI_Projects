from __future__ import annotations

"""Business Logic 层：Telegram 会话流程包装器。"""

from dataclasses import dataclass, field
from typing import Any, Mapping

from business_logic.conversation.models import ConversationResult
from business_service import ConversationServiceResult, TelegramConversationService
from business_service.conversation import service as conversation_service_module


@dataclass(slots=True, init=False)
class TelegramConversationFlow:
    """委派到业务服务层进行会话编排。"""

    service: TelegramConversationService = field(default_factory=TelegramConversationService)

    def __init__(
        self,
        *,
        service: TelegramConversationService | None = None,
        adapter_builder: Any | None = None,
        workflow_orchestrator_factory: Any | None = None,
    ) -> None:
        if service is not None:
            if workflow_orchestrator_factory is not None:
                service.workflow_orchestrator_factory = workflow_orchestrator_factory
            self.service = service
            return

        service_kwargs: dict[str, Any] = {}
        if adapter_builder is not None:
            service_kwargs["adapter_builder"] = adapter_builder
        if workflow_orchestrator_factory is not None:
            service_kwargs["workflow_orchestrator_factory"] = workflow_orchestrator_factory
        self.service = TelegramConversationService(**service_kwargs)

    async def process(self, update: Mapping[str, Any], *, policy: Mapping[str, Any]) -> ConversationResult:
        conversation_service_module.set_behavior_hooks(behavior_telegram_inbound, behavior_telegram_outbound)
        service_result = await self.service.process_update(update, policy=policy)
        return self._to_result(service_result)

    @staticmethod
    def _to_result(result: ConversationServiceResult) -> ConversationResult:
        return ConversationResult(
            status=result.status,
            mode=result.mode,
            outbound_contract=result.outbound_contract,
            agent_output=result.agent_response,
            telemetry=result.telemetry,
            audit_reason=result.audit_reason,
            error_hint=result.error_hint,
            adapter_contract=result.adapter_contract,
            user_text=result.user_text,
            logging=result.logging_payload,
            intent=result.intent,
            outbound_payload=result.outbound_payload,
            outbound_metrics=result.outbound_payload.get("metrics", {}),
            update_type=result.update_type,
            core_envelope=result.core_envelope,
            envelope=result.legacy_envelope,
        )


behavior_telegram_inbound = conversation_service_module.behavior_telegram_inbound
behavior_telegram_outbound = conversation_service_module.behavior_telegram_outbound


__all__ = ["TelegramConversationFlow", "behavior_telegram_inbound", "behavior_telegram_outbound"]
