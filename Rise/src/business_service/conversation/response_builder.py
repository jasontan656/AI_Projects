from __future__ import annotations

"""Response construction helpers for Telegram conversation service."""

from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping, Optional, Sequence

from business_service.conversation.config import TelegramEntryConfig
from business_service.conversation.context_factory import ConversationContext
from business_service.conversation.models import ConversationServiceResult
from business_service.conversation.primitives import AdapterBuilder
from foundational_service.contracts import toolcalls
from foundational_service.contracts.telegram import behavior_telegram_outbound as contracts_telegram_outbound
from foundational_service.persist.task_envelope import TaskEnvelope
from business_logic.workflow import WorkflowRunResult
from project_utility.context import ContextBridge


@dataclass(slots=True)
class ResponseBuilder:
    adapter_builder: AdapterBuilder
    schedule_health_error: Callable[[str, Optional[str], str], None]
    default_locale: str = "zh"

    def async_ack(
        self,
        context: ConversationContext,
        envelope: TaskEnvelope,
        *,
        handle: Optional[Any],
        telemetry_hint: Optional[Mapping[str, Any]] = None,
        task_id_override: Optional[str] = None,
        duplicate: bool = False,
        idempotency_key: Optional[str] = None,
        template_key: str = "ack",
        fallback_text: Optional[str] = None,
    ) -> ConversationServiceResult:
        source_text = fallback_text if fallback_text is not None else context.entry_config.async_ack_text
        template = self.resolve_template(context, template_key, source_text)
        task_id = task_id_override or envelope.task_id
        ack_text = self._format_ack_text(template, task_id)
        telemetry_extra: MutableMapping[str, Any] = {"task_id": task_id, "queue_mode": "async"}
        if telemetry_hint:
            telemetry_extra.update(telemetry_hint)
        if duplicate:
            telemetry_extra.setdefault("queue_status", "duplicate")
        async_payload: MutableMapping[str, Any] = {
            "task_id": task_id,
            "duplicate": duplicate,
        }
        if idempotency_key:
            async_payload["idempotency_key"] = idempotency_key
        if handle is not None:
            async_payload["handle"] = handle
        agent_response_extra = {
            "task_id": task_id,
            "async_handle": async_payload,
            "dispatch": "async_ack",
        }
        agent_request_extra = {
            "workflow_id": envelope.payload.get("workflowId"),
            "task_id": task_id,
        }
        return self.static(
            context,
            text=ack_text,
            status="handled",
            mode="queued",
            intent="workflow_enqueue",
            audit_reason="workflow_enqueued",
            error_hint="task_enqueued",
            telemetry_extra=telemetry_extra,
            agent_response_extra=agent_response_extra,
            agent_request_extra=agent_request_extra,
        )

    def enqueue_failure(
        self,
        context: ConversationContext,
        envelope: TaskEnvelope,
        entry_config: TelegramEntryConfig,
    ) -> ConversationServiceResult:
        template = self.resolve_template(context, "enqueue_failure", entry_config.enqueue_failure_text)
        failure_text = self._format_ack_text(template, envelope.task_id)
        telemetry_extra = {"queue_status": "enqueue_failed", "task_id": envelope.task_id}
        agent_response_extra = {"task_id": envelope.task_id, "dispatch": "enqueue_failed"}
        agent_request_extra = {
            "workflow_id": envelope.payload.get("workflowId"),
            "task_id": envelope.task_id,
        }
        self.schedule_health_error("telegram", envelope.payload.get("workflowId"), "enqueue_failed")
        return self.static(
            context,
            text=failure_text,
            status="handled",
            mode="direct",
            intent="workflow_queue_failure",
            audit_reason="queue_enqueue_failed",
            error_hint="task_enqueue_failed",
            telemetry_extra=telemetry_extra,
            agent_response_extra=agent_response_extra,
            agent_request_extra=agent_request_extra,
        )

    def workflow_missing(
        self,
        context: ConversationContext,
        *,
        telemetry_extra: Optional[Mapping[str, Any]] = None,
    ) -> ConversationServiceResult:
        template = self.resolve_template(context, "workflow_missing", context.entry_config.workflow_missing_text)
        merged_telemetry: MutableMapping[str, Any] = {"workflow_status": "missing"}
        if telemetry_extra:
            merged_telemetry.update(telemetry_extra)
        return self.static(
            context,
            text=template,
            status="ignored",
            mode="ignored",
            intent="workflow_missing",
            audit_reason="workflow_missing",
            error_hint="workflow_missing",
            telemetry_extra=merged_telemetry,
        )

    def pending_workflow(
        self,
        context: ConversationContext,
        envelope: TaskEnvelope,
        *,
        pending_reason: Optional[str],
    ) -> ConversationServiceResult:
        telemetry_extra = {
            "queue_status": "pending",
            "pending_reason": pending_reason,
            "task_id": envelope.task_id,
        }
        agent_response_extra = {
            "task_id": envelope.task_id,
        }
        agent_request_extra = {
            "workflow_id": envelope.payload.get("workflowId"),
            "task_id": envelope.task_id,
        }
        pending_text = self.resolve_template(context, "degraded", context.entry_config.degraded_text)
        return self.static(
            context,
            text=pending_text,
            status="handled",
            mode="queued",
            intent="workflow_pending",
            audit_reason=pending_reason or "workflow_pending",
            error_hint=pending_reason or "workflow_pending",
            telemetry_extra=telemetry_extra,
            agent_response_extra=agent_response_extra,
            agent_request_extra=agent_request_extra,
        )

    def guard_block(
        self,
        context: ConversationContext,
        *,
        error_hint: str,
        workflow_id: Optional[str],
        telemetry_extra: Mapping[str, Any],
    ) -> ConversationServiceResult:
        template = self.resolve_template(context, "manual_review", context.entry_config.manual_review_text)
        self.schedule_health_error("telegram", workflow_id, "guard_blocked")
        return self.static(
            context,
            text=template,
            status="handled",
            mode="manual",
            intent="pipeline_guard_blocked",
            audit_reason="llm_blocked",
            error_hint=error_hint,
            telemetry_extra=telemetry_extra,
        )

    def workflow_result(
        self,
        context: ConversationContext,
        run_result: WorkflowRunResult,
    ) -> ConversationServiceResult:
        response_text = run_result.final_text
        outbound = contracts_telegram_outbound([response_text], context.policy)
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

    def static(
        self,
        context: ConversationContext,
        *,
        text: str,
        status: str,
        mode: str,
        intent: str,
        audit_reason: str,
        error_hint: str,
        telemetry_extra: Optional[Mapping[str, Any]] = None,
        agent_response_extra: Optional[Mapping[str, Any]] = None,
        agent_request_extra: Optional[Mapping[str, Any]] = None,
        chunks: Optional[Sequence[str]] = None,
        streaming_mode: str = "direct",
    ) -> ConversationServiceResult:
        chunk_payload = list(chunks) if chunks else [text]
        outbound = contracts_telegram_outbound(chunk_payload, context.policy)
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
            response_text=text,
            streaming_mode=streaming_mode,
        )
        toolcalls.call_validate_telegram_adapter_contract(adapter_contract)

        telemetry = dict(context.telemetry)
        if telemetry_extra:
            telemetry.update(telemetry_extra)
        agent_response = {
            "text": text,
            "response_id": ContextBridge.request_id(),
            "usage": {},
            "chunks": chunk_payload,
        }
        if agent_response_extra:
            agent_response.update(agent_response_extra)
        agent_request: MutableMapping[str, Any] = {}
        if agent_request_extra:
            agent_request.update(agent_request_extra)
        logging_payload = dict(context.logging_payload)
        logging_payload["audit_reason"] = audit_reason

        return ConversationServiceResult(
            status=status,
            mode=mode,
            intent=intent,
            agent_request=agent_request,
            agent_response=agent_response,
            telemetry=telemetry,
            adapter_contract=adapter_contract,
            outbound_contract=outbound_contract,
            outbound_payload=outbound,
            outbound_metrics=outbound.get("metrics", {}),
            audit_reason=audit_reason,
            error_hint=error_hint,
            user_text=context.user_text,
            logging_payload=logging_payload,
            update_type=context.telemetry.get("update_type", ""),
            core_envelope=context.core_envelope,
            legacy_envelope=context.legacy_envelope,
        )

    def resolve_template(
        self,
        context: ConversationContext,
        template_key: str,
        fallback: str,
    ) -> str:
        return self._resolve_localized_template(context, template_key, fallback)

    def _resolve_localized_template(
        self,
        context: ConversationContext,
        template_key: str,
        fallback: str,
    ) -> str:
        localization = context.policy.get("localization")
        if not isinstance(localization, Mapping):
            return fallback
        template_map = localization.get(template_key) or localization.get(f"{template_key}_text")
        if not isinstance(template_map, Mapping):
            return fallback
        locale = self._determine_locale(context, localization)
        candidate = template_map.get(locale) or template_map.get("default")
        if isinstance(candidate, str) and candidate.strip():
            return candidate
        return fallback

    def _determine_locale(
        self,
        context: ConversationContext,
        localization: Mapping[str, Any],
    ) -> str:
        binding = context.telemetry.get("binding")
        if isinstance(binding, Mapping):
            locale = binding.get("locale")
            if isinstance(locale, str) and locale.strip():
                return locale.strip().lower()
        default_locale = localization.get("default_locale") or localization.get("defaultLocale")
        if isinstance(default_locale, str) and default_locale.strip():
            return default_locale.strip().lower()
        return self.default_locale

    @staticmethod
    def _format_ack_text(template: str, task_id: str) -> str:
        safe_template = template or ""
        safe_task_id = task_id or "pending"
        try:
            return safe_template.format(task_id=safe_task_id)
        except Exception:  # pragma: no cover - fall back to literal template
            return safe_template


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


__all__ = ["ResponseBuilder"]
