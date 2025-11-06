from __future__ import annotations

"""Telegram 会话业务服务：仅走 Workflow Orchestrator。"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Sequence

from business_logic.workflow import WorkflowExecutionContext, WorkflowOrchestrator, WorkflowRunResult
from business_service.conversation.models import ConversationServiceResult
from business_service.conversation.primitives import AdapterBuilder
from business_service.workflow import StageRepository, WorkflowRepository
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

    adapter_builder: AdapterBuilder = field(default_factory=AdapterBuilder)
    workflow_orchestrator_factory: Callable[[], Optional[WorkflowOrchestrator]] = field(
        default=lambda: _build_workflow_orchestrator()
    )
    _workflow_orchestrator: Optional[WorkflowOrchestrator] = field(default=None, init=False, repr=False)

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
        workflow_id = _extract_workflow_id(update, policy)
        if not workflow_id:
            raise RuntimeError("workflow_id_missing")

        orchestrator = self._get_workflow_orchestrator()
        if orchestrator is None:
            raise RuntimeError("workflow_orchestrator_unavailable")

        wf_context = WorkflowExecutionContext(
            workflow_id=workflow_id,
            request_id=context.request_id,
            user_text=context.user_text,
            history_chunks=context.history_chunks,
            policy=context.policy,
            core_envelope=context.core_envelope,
            telemetry=context.telemetry,
        )
        run_result = await orchestrator.execute(wf_context)
        return self._build_workflow_result(context, run_result)

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

    def _build_workflow_result(
        self,
        context: _ConversationContext,
        run_result: WorkflowRunResult,
    ) -> ConversationServiceResult:
        response_text = run_result.final_text
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

        telemetry = dict(run_result.telemetry)
        agent_response = {
            "text": response_text,
            "response_id": ContextBridge.request_id(),
            "usage": _aggregate_usage(run_result),
            "workflow": {
                "stage_results": [
                    {
                        "stage_id": result.stage_id,
                        "name": result.name,
                        "output": result.output_text,
                    }
                    for result in run_result.stage_results
                ]
            },
        }

        return ConversationServiceResult(
            status="handled",
            mode="direct",
            intent="workflow",
            agent_request={"workflow_id": telemetry.get("workflow_id")},
            agent_response=agent_response,
            telemetry=telemetry,
            adapter_contract=adapter_contract,
            outbound_contract=outbound_contract,
            outbound_payload=outbound,
            outbound_metrics=outbound.get("metrics", {}),
            audit_reason="workflow_executed",
            error_hint="",
            user_text=context.user_text,
            logging_payload=context.logging_payload,
            update_type=context.telemetry.get("update_type", ""),
            core_envelope=context.core_envelope,
            legacy_envelope=context.legacy_envelope,
        )

    def _get_workflow_orchestrator(self) -> Optional[WorkflowOrchestrator]:
        if self._workflow_orchestrator is not None:
            return self._workflow_orchestrator
        factory = self.workflow_orchestrator_factory
        if factory is None:
            return None
        orchestrator = factory()
        self._workflow_orchestrator = orchestrator
        return orchestrator


__all__ = ["TelegramConversationService"]


def _build_workflow_orchestrator() -> Optional[WorkflowOrchestrator]:
    try:
        database = get_mongo_database()
    except RuntimeError:
        return None
    workflow_repo = WorkflowRepository(database["workflows"])
    stage_repo = StageRepository(database["workflow_stages"])
    return WorkflowOrchestrator(workflow_repository=workflow_repo, stage_repository=stage_repo)


def _extract_workflow_id(update: Mapping[str, Any], policy: Mapping[str, Any]) -> Optional[str]:
    candidates = [
        policy.get("workflow_id"),
        (policy.get("workflow") or {}).get("id") if isinstance(policy.get("workflow"), Mapping) else None,
        update.get("workflowId"),
        (update.get("workflow") or {}).get("id") if isinstance(update.get("workflow"), Mapping) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _aggregate_usage(run_result: WorkflowRunResult) -> Mapping[str, Any]:
    total_input = 0
    total_output = 0
    for stage in run_result.stage_results:
        usage = stage.raw_response.get("usage") or {}
        total_input += int(usage.get("input_tokens", 0))
        total_output += int(usage.get("output_tokens", 0))
    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
    }
