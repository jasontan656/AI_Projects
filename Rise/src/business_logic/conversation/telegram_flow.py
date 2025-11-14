from __future__ import annotations

"""Business Logic 层：Telegram 会话流程包装器。"""

from dataclasses import dataclass
from typing import Any, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from business_service.conversation.binding_coordinator import BindingCoordinator
    from business_service.conversation.context_factory import ConversationContextFactory
    from business_service.conversation.models import ConversationServiceResult
    from business_service.conversation.service import TelegramConversationService

from business_logic.conversation.models import ConversationResult


@dataclass(slots=True, init=False)
class TelegramConversationFlow:
    """委派到业务服务层进行会话编排。"""

    service: "TelegramConversationService"

    def __init__(
        self,
        *,
        service: "TelegramConversationService" | None = None,
        adapter_builder: Any | None = None,
        agent_delegator: Any | None = None,
        context_factory: "ConversationContextFactory" | None = None,
        binding_coordinator: "BindingCoordinator" | None = None,
    ) -> None:
        if service is not None:
            self.service = service
            return

        from business_service.conversation.service import TelegramConversationService as _TelegramConversationService

        service_kwargs: dict[str, Any] = {}
        if adapter_builder is not None:
            service_kwargs["adapter_builder"] = adapter_builder
        if agent_delegator is not None:
            service_kwargs["agent_delegator"] = agent_delegator
        if context_factory is not None:
            service_kwargs["context_factory"] = context_factory
        if binding_coordinator is not None:
            service_kwargs["binding_coordinator"] = binding_coordinator
        self.service = _TelegramConversationService(**service_kwargs)

    async def process(self, update: Mapping[str, Any], *, policy: Mapping[str, Any]) -> ConversationResult:
        service_result = await self.service.process_update(update, policy=policy)
        return self._to_result(service_result)

    @staticmethod
    def _to_result(result: "ConversationServiceResult") -> ConversationResult:
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


__all__ = ["TelegramConversationFlow"]

