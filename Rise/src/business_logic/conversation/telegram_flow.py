from __future__ import annotations

"""Business Logic 层：Telegram 会话流程包装器。"""

from dataclasses import dataclass, field
from typing import Any, Mapping

from business_logic.conversation.models import ConversationResult
from business_service import ConversationServiceResult, TelegramConversationService


@dataclass(slots=True)
class TelegramConversationFlow:
    """委派到业务服务层进行会话编排。"""

    service: TelegramConversationService = field(default_factory=TelegramConversationService)

    async def process(self, update: Mapping[str, Any], *, policy: Mapping[str, Any]) -> ConversationResult:
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
            triage_prompt=result.triage_prompt,
            agent_bridge=result.agent_bridge,
            agent_bridge_telemetry=result.agent_bridge_telemetry,
            outbound_payload=result.outbound_payload,
            outbound_metrics=result.outbound_metrics,
            update_type=result.update_type,
            core_envelope=result.core_envelope,
            envelope=result.legacy_envelope,
            output_payload=result.output_payload,
        )


__all__ = ["TelegramConversationFlow"]
