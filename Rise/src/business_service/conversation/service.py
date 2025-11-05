from __future__ import annotations

"""Telegram 会话业务服务的最小骨架：直接调用 LLM 并返回结果。"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Sequence

from business_service.conversation.models import ConversationServiceResult
from business_service.conversation.primitives import AdapterBuilder, AgentDelegator
from business_service.pipeline import MongoPipelineNodeRepository, PipelineNodeService
from business_service.pipeline.models import PipelineNode, _now_utc
from foundational_service.contracts import toolcalls
from foundational_service.contracts.telegram import (
    behavior_telegram_inbound as _behavior_telegram_inbound,
    behavior_telegram_outbound as _behavior_telegram_outbound,
)
from project_utility.context import ContextBridge
from project_utility.db import get_mongo_database
BEHAVIOR_TELEGRAM_INBOUND = _behavior_telegram_inbound
BEHAVIOR_TELEGRAM_OUTBOUND = _behavior_telegram_outbound


def behavior_telegram_inbound(update: Mapping[str, Any], policy: Mapping[str, Any]) -> Mapping[str, Any]:
    return BEHAVIOR_TELEGRAM_INBOUND(update, policy)


def behavior_telegram_outbound(chunks: Any, policy: Mapping[str, Any]) -> Mapping[str, Any]:
    return BEHAVIOR_TELEGRAM_OUTBOUND(chunks, policy)


def set_behavior_hooks(
    inbound: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    outbound: Callable[[Any, Mapping[str, Any]], Mapping[str, Any]],
) -> None:
    global BEHAVIOR_TELEGRAM_INBOUND, BEHAVIOR_TELEGRAM_OUTBOUND
    BEHAVIOR_TELEGRAM_INBOUND = inbound
    BEHAVIOR_TELEGRAM_OUTBOUND = outbound



@dataclass(slots=True)
class _ConversationContext:
    update: Mapping[str, Any]
    policy: Mapping[str, Any]
    request_id: str
    inbound: Mapping[str, Any]
    core_envelope: Mapping[str, Any]
    legacy_envelope: Mapping[str, Any]
    logging_payload: MutableMapping[str, Any]
    telemetry: MutableMapping[str, Any]
    user_text: str
    history_chunks: Sequence[str]
    tokens_budget: Mapping[str, Any]


@dataclass(slots=True)
class TelegramConversationService:
    """面向 Telegram 渠道的业务服务门面。"""

    agent_delegator: AgentDelegator = field(default_factory=AgentDelegator)
    adapter_builder: AdapterBuilder = field(default_factory=AdapterBuilder)
    pipeline_service_factory: Callable[[], Optional[PipelineNodeService]] = field(
        default=lambda: _build_pipeline_service()
    )
    _pipeline_service: Optional[PipelineNodeService] = field(default=None, init=False, repr=False)

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

        context = self._build_context(update, policy, inbound, request_id, telemetry)
        prompt_id = inbound.get("prompt_id")
        if prompt_id:
            raise RuntimeError(f"legacy prompt flow detected: {prompt_id}")
        pipeline_node = await self._resolve_pipeline_node(update, policy)
        if pipeline_node is not None:
            context.telemetry["pipeline_node_id"] = pipeline_node.node_id
            context.telemetry["pipeline_node_version"] = pipeline_node.version
            context.logging_payload["pipeline_node_id"] = pipeline_node.node_id
            context.logging_payload["pipeline_node_version"] = pipeline_node.version

        if pipeline_node is not None and not pipeline_node.allow_llm:
            toolcalls.call_record_audit(
                {
                    "event": "audit.pipeline_node",
                    "change_type": "execution_skipped",
                    "node_id": pipeline_node.node_id,
                    "actor": context.logging_payload.get("user_id") or ContextBridge.request_id(),
                    "timestamp": _now_utc().isoformat(),
                    "version": pipeline_node.version,
                    "reason": "allowLLM=false",
                }
            )
            return self._build_blocked_result(context, pipeline_node)

        llm_request = self._build_llm_request(context, pipeline_node=pipeline_node)
        llm_result = await self.agent_delegator.dispatch(llm_request)

        if isinstance(llm_result.get("telemetry"), Mapping):
            context.telemetry.update(llm_result["telemetry"])

        response_text = str(llm_result.get("text", "")).strip()
        bridge_payload = llm_result.get("agent_bridge_result")
        response_mode = "direct"
        outbound_chunks: list[str] = [response_text] if response_text else []
        if isinstance(bridge_payload, Mapping):
            response_mode = str(bridge_payload.get("mode") or "direct")
            bridge_chunks = [str(chunk) for chunk in bridge_payload.get("chunks", []) if chunk]
            if bridge_chunks:
                outbound_chunks = bridge_chunks
                response_text = "\n".join(bridge_chunks).strip()
        if not outbound_chunks:
            outbound_chunks = [response_text or context.user_text]

        outbound = behavior_telegram_outbound(outbound_chunks, context.policy)
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
        agent_output = output_payload["agent_output"]

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
            chunk_metrics=outbound.get("metrics", {}).get("chunk_metrics", []),
            response_text=response_text,
            streaming_mode=response_mode,
        )
        toolcalls.call_validate_telegram_adapter_contract(adapter_contract)

        agent_output.update(
            {
                "text": response_text,
                "response_id": llm_result.get("response_id", ""),
                "usage": llm_result.get("usage", {}),
            }
        )
        if isinstance(bridge_payload, Mapping):
            agent_output["bridge"] = dict(bridge_payload)

        return ConversationServiceResult(
            status="handled",
            mode=response_mode,
            intent="default",
            agent_request=llm_request,
            agent_response=agent_output,
            telemetry=context.telemetry,
            adapter_contract=adapter_contract,
            outbound_contract=outbound_contract,
            outbound_payload=outbound,
            outbound_metrics=outbound.get("metrics", {}),
            audit_reason="",
            error_hint="",
            user_text=context.user_text,
            logging_payload=context.logging_payload,
            update_type=context.telemetry.get("update_type", ""),
            core_envelope=context.core_envelope,
            legacy_envelope=context.legacy_envelope,
        )

    async def _resolve_pipeline_node(
        self,
        update: Mapping[str, Any],
        policy: Mapping[str, Any],
    ) -> Optional[PipelineNode]:
        node_id = _extract_pipeline_node_id(update, policy)
        if not node_id:
            return None
        service = self._get_pipeline_service()
        if service is None:
            return None
        return await asyncio.to_thread(service.get_node, node_id)

    def _build_context(
        self,
        update: Mapping[str, Any],
        policy: Mapping[str, Any],
        inbound: Mapping[str, Any],
        request_id: str,
        telemetry: MutableMapping[str, Any],
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

        return _ConversationContext(
            update=update,
            policy=policy,
            request_id=request_id,
            inbound=inbound,
            core_envelope=core_envelope,
            legacy_envelope=legacy_envelope,
            logging_payload=dict(inbound.get("logging", {})),
            telemetry=telemetry,
            user_text=user_text,
            history_chunks=tuple(history_chunks),
            tokens_budget=tokens_budget,
        )

    def _build_llm_request(
        self,
        context: _ConversationContext,
        *,
        pipeline_node: Optional[PipelineNode] = None,
    ) -> Dict[str, Any]:
        prompt_parts: list[str] = []
        if context.history_chunks:
            prompt_parts.append("\n".join(context.history_chunks))
        prompt_parts.append(context.user_text or "")
        prompt = "\n".join(part for part in prompt_parts if part)
        if pipeline_node is not None and pipeline_node.system_prompt:
            prompt = "\n\n".join(part for part in (pipeline_node.system_prompt, prompt) if part)
        return {
            "prompt": prompt or "",
            "user_text": context.user_text,
            "history": list(context.history_chunks),
            "tokens_budget": context.tokens_budget,
            "request_id": context.request_id,
        }

    def _build_blocked_result(
        self,
        context: _ConversationContext,
        pipeline_node: PipelineNode,
    ) -> ConversationServiceResult:
        response_text = (
            pipeline_node.strategy.get("fallbackResponse")
            if isinstance(pipeline_node.strategy, Mapping)
            else None
        )
        if not response_text:
            response_text = f"Pipeline node '{pipeline_node.name}' has allowLLM disabled."
        outbound = behavior_telegram_outbound([response_text], context.policy)
        core_bundle = {
            "core_envelope": context.core_envelope,
            "telemetry": context.inbound.get("telemetry", {}),
        }
        adapter_contract = self.adapter_builder.build_contract(
            context.update,
            core_bundle=core_bundle,
            agent_request={"request_id": context.request_id},
        )
        outbound_contract = self.adapter_builder.finalize_contract(
            adapter_contract,
            chunk_metrics=outbound.get("metrics", {}).get("chunk_metrics", []),
            response_text=response_text,
            streaming_mode="direct",
        )
        toolcalls.call_validate_telegram_adapter_contract(adapter_contract)
        return ConversationServiceResult(
            status="blocked",
            mode="direct",
            intent="blocked",
            agent_request={},
            agent_response={
                "text": response_text,
                "response_id": "",
                "usage": {},
            },
            telemetry=context.telemetry,
            adapter_contract=adapter_contract,
            outbound_contract=outbound_contract,
            outbound_payload=outbound,
            outbound_metrics=outbound.get("metrics", {}),
            audit_reason="allow_llm_disabled",
            error_hint="allow_llm_disabled",
            user_text=context.user_text,
            logging_payload=context.logging_payload,
            update_type=context.telemetry.get("update_type", ""),
            core_envelope=context.core_envelope,
            legacy_envelope=context.legacy_envelope,
        )

    def _get_pipeline_service(self) -> Optional[PipelineNodeService]:
        if self._pipeline_service is not None:
            return self._pipeline_service
        factory = self.pipeline_service_factory
        if factory is None:
            return None
        service = factory()
        self._pipeline_service = service
        return service


__all__ = ["TelegramConversationService"]


def _build_pipeline_service() -> Optional[PipelineNodeService]:
    try:
        database = get_mongo_database()
    except RuntimeError:
        return None
    repository = MongoPipelineNodeRepository(database["pipeline_nodes"])
    return PipelineNodeService(repository)


def _extract_pipeline_node_id(update: Mapping[str, Any], policy: Mapping[str, Any]) -> Optional[str]:
    candidates = [
        update.get("pipeline_node_id"),
        update.get("pipelineNodeId"),
        (update.get("pipeline") or {}).get("nodeId") if isinstance(update.get("pipeline"), Mapping) else None,
        policy.get("pipeline_node_id"),
        (policy.get("pipeline") or {}).get("nodeId") if isinstance(policy.get("pipeline"), Mapping) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None
