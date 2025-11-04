from __future__ import annotations

"""Telegram 会话业务服务的最小骨架：直接调用 LLM 并返回结果。"""

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping, Sequence

from business_service.conversation.models import ConversationServiceResult
from business_service.conversation.primitives import AdapterBuilder, AgentDelegator
from foundational_service.contracts import toolcalls
from foundational_service.contracts.telegram import behavior_telegram_inbound, behavior_telegram_outbound
from project_utility.context import ContextBridge


@dataclass(slots=True)
class _ConversationContext:
    update: Mapping[str, Any]
    policy: Mapping[str, Any]
    request_id: str
    inbound: Mapping[str, Any]
    core_envelope: Mapping[str, Any]
    legacy_envelope: Mapping[str, Any]
    logging_payload: Mapping[str, Any]
    user_text: str
    history_chunks: Sequence[str]
    tokens_budget: Mapping[str, Any]


@dataclass(slots=True)
class TelegramConversationService:
    """面向 Telegram 渠道的业务服务门面。"""

    agent_delegator: AgentDelegator = field(default_factory=AgentDelegator)
    adapter_builder: AdapterBuilder = field(default_factory=AdapterBuilder)

    async def process_update(self, update: Mapping[str, Any], *, policy: Mapping[str, Any]) -> ConversationServiceResult:
        request_id = ContextBridge.request_id()
        inbound = behavior_telegram_inbound(dict(update), policy)
        telemetry = dict(inbound.get("telemetry", {}))

        if inbound.get("response_status") == "ignored":
            ignored_payload = update.get("message") or {}
            ignored_user_text = str(ignored_payload.get("text") or ignored_payload.get("caption") or "")
            empty_contract: MutableMapping[str, Any] = {}
            return ConversationServiceResult(
                status="ignored",
                mode="ignored",
                intent="ignored",
                agent_request={},
                agent_response={},
                telemetry=telemetry,
                adapter_contract=empty_contract,
                outbound_contract=empty_contract,
                outbound_payload={},
                outbound_metrics={},
                audit_reason=inbound.get("error_hint", "ignored"),
                error_hint=inbound.get("error_hint", "ignored"),
                user_text=ignored_user_text,
                logging_payload=inbound.get("logging", {}),
                update_type=telemetry.get("update_type", ""),
                core_envelope=inbound.get("core_envelope", {}),
                legacy_envelope=inbound.get("envelope", inbound.get("core_envelope", {})),
            )

        context = self._build_context(update, policy, inbound, request_id)
        llm_request = self._build_llm_request(context)
        llm_result = await self.agent_delegator.dispatch(llm_request)

        response_text = llm_result.get("text", "").strip()
        outbound = behavior_telegram_outbound([response_text], context.policy)
        outbound_metrics = outbound.get("metrics", {})

        output_payload = toolcalls.call_validate_output(
            {
                "agent_output": {
                    "chat_id": context.legacy_envelope.get("metadata", {}).get("chat_id", ""),
                    "text": response_text,
                    "parse_mode": "MarkdownV2",
                    "status_code": 200,
                    "error_hint": "",
                }
            }
        )

        core_bundle = {
            "core_envelope": context.core_envelope,
            "telemetry": context.inbound.get("telemetry", {}),
        }
        adapter_contract = self.adapter_builder.build_contract(
            context.update,
            core_bundle=core_bundle,
            agent_request=llm_request,
        )
        outbound_contract = self.adapter_builder.finalize_contract(
            adapter_contract,
            chunk_metrics=[],
            response_text=response_text,
            streaming_mode="direct",
        )
        toolcalls.call_validate_telegram_adapter_contract(adapter_contract)

        agent_response = {
            "text": response_text,
            "response_id": llm_result.get("response_id", ""),
            "usage": llm_result.get("usage", {}),
        }

        return ConversationServiceResult(
            status="handled",
            mode="direct",
            intent="default",
            agent_request=llm_request,
            agent_response=agent_response,
            telemetry=telemetry,
            adapter_contract=adapter_contract,
            outbound_contract=outbound_contract,
            outbound_payload=outbound,
            outbound_metrics=outbound_metrics,
            audit_reason="",
            error_hint="",
            user_text=context.user_text,
            logging_payload=context.logging_payload,
            update_type=telemetry.get("update_type", ""),
            core_envelope=context.core_envelope,
            legacy_envelope=context.legacy_envelope,
            output_payload=output_payload,
        )

    def _build_context(
        self,
        update: Mapping[str, Any],
        policy: Mapping[str, Any],
        inbound: Mapping[str, Any],
        request_id: str,
    ) -> _ConversationContext:
        core_envelope = dict(inbound.get("core_envelope", {}))
        legacy_envelope = inbound.get("envelope", core_envelope)
        payload_section = dict(core_envelope.get("payload", {}))
        tokens_budget = policy.get("tokens_budget") or {
            "per_call_max_tokens": 3000,
            "per_flow_max_tokens": 6000,
        }

        history_chunks = [
            quote.get("excerpt", "")
            for quote in payload_section.get("context_quotes", [])
            if isinstance(quote, Mapping)
        ]
        user_text = payload_section.get("user_message", "")

        agent_request = {
            "request_id": request_id,
            "chat_id": legacy_envelope.get("metadata", {}).get("chat_id", ""),
            "tokens_budget": tokens_budget,
        }

        return _ConversationContext(
            update=update,
            policy=policy,
            request_id=request_id,
            inbound=inbound,
            core_envelope=core_envelope,
            legacy_envelope=legacy_envelope,
            logging_payload=inbound.get("logging", {}),
            user_text=user_text,
            history_chunks=tuple(history_chunks),
            tokens_budget=tokens_budget,
        )

    def _build_llm_request(self, context: _ConversationContext) -> Dict[str, Any]:
        prompt_parts: list[str] = []
        if context.history_chunks:
            prompt_parts.append("\n".join(context.history_chunks))
        prompt_parts.append(context.user_text or "")
        prompt = "\n".join(part for part in prompt_parts if part)
        return {
            "prompt": prompt or "",
            "user_text": context.user_text,
            "history": list(context.history_chunks),
            "tokens_budget": context.tokens_budget,
            "request_id": context.request_id,
        }


__all__ = ["TelegramConversationService"]
