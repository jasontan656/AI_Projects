from __future__ import annotations

"""Telegram 会话业务服务：仅走 Workflow Orchestrator。"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Protocol, Sequence

from business_service.channel.models import ChannelBindingRuntime, WorkflowChannelPolicy
from business_logic.workflow import WorkflowRunResult, WorkflowStageResult
from business_service.conversation.models import ConversationServiceResult
from business_service.conversation.primitives import AdapterBuilder
from foundational_service.contracts import toolcalls
from foundational_service.contracts.telegram import (
    behavior_telegram_inbound as contracts_telegram_inbound,
    behavior_telegram_outbound as contracts_telegram_outbound,
)
from foundational_service.persist.task_envelope import RetryState, TaskEnvelope, TaskStatus
from foundational_service.persist.worker import TaskRuntime, TaskSubmitter
from project_utility.context import ContextBridge

log = logging.getLogger("business_service.conversation.service")

RAW_PAYLOAD_LIMIT_BYTES = int(os.getenv("TELEGRAM_RAW_PAYLOAD_MAX_BYTES", "262144"))

_TASK_SUBMITTER_FACTORY: Optional[Callable[[], Optional[TaskSubmitter]]] = None
_TASK_RUNTIME_FACTORY: Optional[Callable[[], Optional[TaskRuntime]]] = None
_CHANNEL_BINDING_PROVIDER: Optional["ChannelBindingProvider"] = None


class ChannelBindingProvider(Protocol):
    async def get_active_binding(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        ...


def set_task_queue_accessors(
    *,
    submitter_factory: Callable[[], Optional[TaskSubmitter]],
    runtime_factory: Callable[[], Optional[TaskRuntime]],
) -> None:
    """Allow bootstrap层注入 TaskSubmitter / TaskRuntime 的工厂。"""

    global _TASK_SUBMITTER_FACTORY, _TASK_RUNTIME_FACTORY
    _TASK_SUBMITTER_FACTORY = submitter_factory
    _TASK_RUNTIME_FACTORY = runtime_factory


def set_channel_binding_provider(provider: ChannelBindingProvider) -> None:
    """Register the global channel binding provider used by conversation flows."""

    global _CHANNEL_BINDING_PROVIDER
    _CHANNEL_BINDING_PROVIDER = provider


@dataclass(slots=True)
class TelegramEntryConfig:
    wait_for_result: bool = True
    async_ack_text: str = "已收到消息，任务已排队，将在处理完成后答复。任务 ID: {task_id}"
    enqueue_failure_text: str = "当前对话系统繁忙，请稍后重试。"
    workflow_missing_text: str = "未找到对应流程，请联系管理员。"
    async_failure_text: str = "处理遇到问题，已通知管理员，请稍后重试。任务 ID: {task_id}"
    wait_timeout_seconds: Optional[float] = None


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
    entry_config: TelegramEntryConfig
    channel_payload: Mapping[str, Any]
    raw_payload_meta: Mapping[str, Any]


@dataclass(slots=True)
class AsyncResultHandle:
    service: "TelegramConversationService"
    context: _ConversationContext
    runtime: TaskRuntime
    waiter: asyncio.Future[Any]
    task_id: str
    entry_config: TelegramEntryConfig

    async def resolve(self) -> ConversationServiceResult:
        try:
            payload = await self.waiter
        finally:
            await self.runtime.results.discard(self.task_id, self.waiter)
        return self.service._build_response_from_worker_payload(self.context, payload)

    def format_ack_text(self, template: Optional[str] = None) -> str:
        return self.service._format_ack_text(template or self.entry_config.async_ack_text, self.task_id)

    def format_failure_text(self) -> str:
        return self.service._format_ack_text(self.entry_config.async_failure_text, self.task_id)


@dataclass(slots=True)
class TelegramConversationService:
    """面向 Telegram 渠道的业务服务门面。"""

    adapter_builder: AdapterBuilder = field(default_factory=AdapterBuilder)
    task_submitter_factory: Optional[Callable[[], Optional[TaskSubmitter]]] = None
    task_runtime_factory: Optional[Callable[[], Optional[TaskRuntime]]] = None
    binding_provider: Optional[ChannelBindingProvider] = None

    async def process_update(self, update: Mapping[str, Any], *, policy: Mapping[str, Any]) -> ConversationServiceResult:
        request_id = ContextBridge.request_id()
        inbound = contracts_telegram_inbound(dict(update), policy)
        telemetry = dict(inbound.get("telemetry", {}))
        binding_runtime = await self._get_binding_runtime()

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
        if binding_runtime:
            self._apply_binding_entry_config(context, binding_runtime.policy)
            binding_snapshot = dict(context.telemetry.get("binding") or {})
            binding_snapshot.update(
                {
                    "version": binding_runtime.version,
                    "workflow_id": binding_runtime.workflow_id,
                }
            )
            context.telemetry["binding"] = binding_snapshot
        workflow_id = binding_runtime.workflow_id if binding_runtime else _extract_workflow_id(update, policy)
        workflow_status = "ready" if workflow_id else "pending"
        pending_reason = None if workflow_id else "workflow_missing"

        submitter = self._get_task_submitter()
        runtime = self._get_task_runtime()
        if submitter is None or runtime is None:
            raise RuntimeError("task_runtime_unavailable")

        envelope = self._build_task_envelope(
            context,
            workflow_id=workflow_id,
            workflow_status=workflow_status,
            pending_reason=pending_reason,
        )
        wait_timeout = self._resolve_wait_timeout(context.entry_config, context.policy)
        handle: Optional[AsyncResultHandle] = None
        waiter: Optional[asyncio.Future[Any]] = None
        if workflow_id:
            waiter = await runtime.results.register(envelope.task_id)
            handle = AsyncResultHandle(
                service=self,
                context=context,
                runtime=runtime,
                waiter=waiter,
                task_id=envelope.task_id,
                entry_config=context.entry_config,
            )

        try:
            await submitter.submit(envelope)
        except Exception as exc:
            if waiter is not None:
                await runtime.results.discard(envelope.task_id, waiter)
            log.exception(
                "telegram.queue.enqueue_failed",
                extra={"task_id": envelope.task_id, "error": str(exc)},
            )
            return self._build_enqueue_failure_result(context, envelope, context.entry_config)

        log.info(
            "telegram.queue.enqueued",
            extra={
                "task_id": envelope.task_id,
                "mode": (
                    "workflow_pending"
                    if workflow_status == "pending"
                    else ("sync" if context.entry_config.wait_for_result else "async")
                ),
                "workflow_status": workflow_status,
            },
        )

        if workflow_id and context.entry_config.wait_for_result:
            try:
                result_payload = await asyncio.wait_for(waiter, timeout=wait_timeout)
            except asyncio.TimeoutError:
                log.warning(
                    "telegram.task_result_timeout",
                    extra={"task_id": envelope.task_id, "timeout_seconds": wait_timeout},
                )
                return self._build_async_ack_result(
                    context,
                    envelope,
                    handle,
                    telemetry_hint={"queue_status": "timeout"},
                )
            except Exception:
                await runtime.results.discard(envelope.task_id, waiter)
                raise

            await runtime.results.discard(envelope.task_id, waiter)
            return self._build_response_from_worker_payload(context, result_payload)

        if workflow_id and handle is not None:
            return self._build_async_ack_result(
                context,
                envelope,
                handle,
                telemetry_hint={"queue_status": "async"},
            )

        return self._build_pending_workflow_result(
            context,
            envelope,
            pending_reason=pending_reason or "workflow_pending",
        )

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
        entry_config = self._resolve_entry_config(policy)
        channel_payload, raw_meta = self._build_channel_payload(update)

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
            entry_config=entry_config,
            channel_payload=channel_payload,
            raw_payload_meta=raw_meta,
        )

    def _get_task_submitter(self) -> Optional[TaskSubmitter]:
        factory = self.task_submitter_factory or _TASK_SUBMITTER_FACTORY
        if factory is None:
            return None
        return factory()

    def _get_task_runtime(self) -> Optional[TaskRuntime]:
        factory = self.task_runtime_factory or _TASK_RUNTIME_FACTORY
        if factory is None:
            return None
        return factory()

    async def _get_binding_runtime(self) -> Optional[ChannelBindingRuntime]:
        provider = self.binding_provider or _CHANNEL_BINDING_PROVIDER
        if provider is None:
            return None
        try:
            return await provider.get_active_binding("telegram")
        except Exception as exc:  # pragma: no cover - defensive logging
            log.warning("telegram.binding.lookup_failed", extra={"error": str(exc)})
            return None

    @staticmethod
    def _apply_binding_entry_config(context: _ConversationContext, policy: WorkflowChannelPolicy) -> None:
        context.entry_config.wait_for_result = policy.wait_for_result
        context.entry_config.workflow_missing_text = policy.workflow_missing_message
        context.entry_config.async_failure_text = policy.timeout_message

    def _build_task_envelope(
        self,
        context: _ConversationContext,
        workflow_id: Optional[str],
        *,
        workflow_status: str,
        pending_reason: Optional[str],
    ) -> TaskEnvelope:
        core_envelope = dict(context.core_envelope)
        metadata = dict(core_envelope.get("metadata") or {})
        chat_id = metadata.get("chat_id")
        if not chat_id:
            raise RuntimeError("chat_id_missing")

        telemetry = dict(context.telemetry)
        telemetry.setdefault("channel", "telegram")
        telemetry.setdefault("requestId", context.request_id)
        telemetry.setdefault("workflow_status", workflow_status)
        raw_meta = context.raw_payload_meta
        if raw_meta.get("raw_size_bytes") is not None:
            telemetry["raw_size_bytes"] = raw_meta["raw_size_bytes"]
        if raw_meta.get("raw_truncated"):
            telemetry["raw_truncated"] = True

        payload_metadata = dict(context.inbound.get("metadata") or metadata)
        payload_metadata.setdefault("chat_id", chat_id)
        payload_metadata.setdefault("source", payload_metadata.get("source") or "telegram-bot")

        message_id = self._extract_message_id(context.update)
        payload = {
            "workflowId": workflow_id,
            "workflowStatus": workflow_status,
            "userText": context.user_text,
            "historyChunks": list(context.history_chunks),
            "policy": dict(context.policy),
            "coreEnvelope": core_envelope,
            "telemetry": telemetry,
            "metadata": payload_metadata,
            "source": "telegram",
            "channelPayload": dict(context.channel_payload),
        }
        if pending_reason:
            payload["pendingReason"] = pending_reason
        idempotency_key = self._build_idempotency_key(
            channel="telegram",
            workflow_id=workflow_id,
            chat_id=str(chat_id),
            message_id=message_id,
        )
        user_context = {"chat_id": chat_id}
        if message_id:
            user_context["message_id"] = message_id
        task_context = {
            "idempotencyKey": idempotency_key,
            "traceId": context.request_id,
            "user": user_context,
            "requestId": context.request_id,
        }
        retry_max = int(context.policy.get("retry_max") or 3)
        retry_state = RetryState(count=0, max=retry_max)
        return TaskEnvelope.new(task_type="workflow.execute", payload=payload, context=task_context, retry=retry_state)

    @staticmethod
    def _build_idempotency_key(
        *,
        channel: str,
        workflow_id: Optional[str],
        chat_id: str,
        message_id: Optional[str],
    ) -> str:
        suffix = message_id or ContextBridge.request_id()
        if not suffix:
            suffix = str(int(datetime.now(timezone.utc).timestamp() * 1000))
        workflow_segment = workflow_id or "pending"
        return f"{channel}:{workflow_segment}:{chat_id}:{suffix}"

    @staticmethod
    def _resolve_wait_timeout(entry_config: TelegramEntryConfig, policy: Mapping[str, Any]) -> float:
        candidates: list[Optional[float]] = [entry_config.wait_timeout_seconds]
        candidate_policy = policy.get("wait_timeout_seconds")
        if candidate_policy is not None:
            try:
                candidates.append(float(candidate_policy))
            except (TypeError, ValueError):
                pass
        for candidate in candidates:
            if candidate is None:
                continue
            try:
                timeout = float(candidate)
            except (TypeError, ValueError):
                continue
            if timeout > 0:
                return min(timeout, 120.0)
        return 20.0

    @staticmethod
    @staticmethod
    def _resolve_entry_config(policy: Mapping[str, Any]) -> TelegramEntryConfig:
        defaults = TelegramEntryConfig()
        entrypoints = policy.get("entrypoints")
        telegram_entry: Mapping[str, Any] = {}
        if isinstance(entrypoints, Mapping):
            raw = entrypoints.get("telegram")
            if isinstance(raw, Mapping):
                telegram_entry = raw

        def _coerce_bool(value: Any, default: bool) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"false", "0", "off", "no"}:
                    return False
                if lowered in {"true", "1", "on", "yes"}:
                    return True
            if value is None:
                return default
            return bool(value)

        def _coerce_text(value: Any, default: str) -> str:
            if isinstance(value, str) and value.strip():
                return value
            return default

        def _coerce_float(value: Any) -> Optional[float]:
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        return TelegramEntryConfig(
            wait_for_result=_coerce_bool(telegram_entry.get("wait_for_result"), defaults.wait_for_result),
            async_ack_text=_coerce_text(telegram_entry.get("async_ack_text"), defaults.async_ack_text),
            enqueue_failure_text=_coerce_text(telegram_entry.get("enqueue_failure_text"), defaults.enqueue_failure_text),
            workflow_missing_text=_coerce_text(telegram_entry.get("workflow_missing_text"), defaults.workflow_missing_text),
            async_failure_text=_coerce_text(telegram_entry.get("async_failure_text"), defaults.async_failure_text),
            wait_timeout_seconds=_coerce_float(telegram_entry.get("wait_timeout_seconds")),
        )

    @staticmethod
    def _format_ack_text(template: str, task_id: str) -> str:
        safe_template = template or ""
        safe_task_id = task_id or "pending"
        try:
            return safe_template.format(task_id=safe_task_id)
        except Exception:
            return safe_template

    def _build_async_ack_result(
        self,
        context: _ConversationContext,
        envelope: TaskEnvelope,
        handle: AsyncResultHandle,
        *,
        telemetry_hint: Optional[Mapping[str, Any]] = None,
    ) -> ConversationServiceResult:
        ack_text = handle.format_ack_text()
        telemetry_extra = {"task_id": envelope.task_id, "queue_mode": "async"}
        if telemetry_hint:
            telemetry_extra.update(telemetry_hint)
        agent_response_extra = {
            "task_id": envelope.task_id,
            "async_handle": handle,
            "dispatch": "async_ack",
        }
        agent_request_extra = {
            "workflow_id": envelope.payload.get("workflowId"),
            "task_id": envelope.task_id,
        }
        return self._build_static_response(
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

    def _build_enqueue_failure_result(
        self,
        context: _ConversationContext,
        envelope: TaskEnvelope,
        entry_config: TelegramEntryConfig,
    ) -> ConversationServiceResult:
        failure_text = self._format_ack_text(entry_config.enqueue_failure_text, envelope.task_id)
        telemetry_extra = {"queue_status": "enqueue_failed", "task_id": envelope.task_id}
        agent_response_extra = {"task_id": envelope.task_id, "dispatch": "enqueue_failed"}
        agent_request_extra = {
            "workflow_id": envelope.payload.get("workflowId"),
            "task_id": envelope.task_id,
        }
        return self._build_static_response(
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

    def _build_static_response(
        self,
        context: _ConversationContext,
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
    ) -> ConversationServiceResult:
        outbound = contracts_telegram_outbound([text], context.policy)
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
            streaming_mode="direct",
        )
        toolcalls.call_validate_telegram_adapter_contract(adapter_contract)

        telemetry = dict(context.telemetry)
        if telemetry_extra:
            telemetry.update(telemetry_extra)
        agent_response = {
            "text": text,
            "response_id": ContextBridge.request_id(),
            "usage": {},
        }
        if agent_response_extra:
            agent_response.update(agent_response_extra)
        agent_request: Dict[str, Any] = {}
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

    def _build_workflow_missing_result(self, context: _ConversationContext) -> ConversationServiceResult:
        telemetry_extra = {"workflow_status": "missing"}
        return self._build_static_response(
            context,
            text=context.entry_config.workflow_missing_text,
            status="ignored",
            mode="ignored",
            intent="workflow_missing",
            audit_reason="workflow_missing",
            error_hint="workflow_missing",
            telemetry_extra=telemetry_extra,
        )

    def _build_pending_workflow_result(
        self,
        context: _ConversationContext,
        envelope: TaskEnvelope,
        *,
        pending_reason: str,
    ) -> ConversationServiceResult:
        telemetry_extra = {
            "workflow_status": "pending",
            "queue_status": "workflow_pending",
            "task_id": envelope.task_id,
        }
        agent_response_extra = {"task_id": envelope.task_id, "dispatch": "workflow_pending"}
        agent_request_extra = {"task_id": envelope.task_id}
        return self._build_static_response(
            context,
            text=context.entry_config.workflow_missing_text,
            status="handled",
            mode="queued",
            intent="workflow_pending",
            audit_reason=pending_reason,
            error_hint=pending_reason,
            telemetry_extra=telemetry_extra,
            agent_response_extra=agent_response_extra,
            agent_request_extra=agent_request_extra,
        )

    def _build_channel_payload(self, update: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        serialized = json.dumps(update, ensure_ascii=False, separators=(",", ":"))
        encoded = serialized.encode("utf-8")
        size = len(encoded)
        truncated = size > RAW_PAYLOAD_LIMIT_BYTES
        payload: Dict[str, Any] = {
            "version": "telegram.v1",
            "rawSizeBytes": size,
            "rawTruncated": truncated,
        }
        if truncated:
            payload["raw"] = None
            payload["rawPreview"] = serialized[:RAW_PAYLOAD_LIMIT_BYTES]
        else:
            payload["raw"] = json.loads(serialized)
        meta = {"raw_size_bytes": size, "raw_truncated": truncated}
        return payload, meta

    def _build_response_from_worker_payload(
        self,
        context: _ConversationContext,
        broker_payload: Mapping[str, Any],
    ) -> ConversationServiceResult:
        if not isinstance(broker_payload, Mapping):
            raise RuntimeError("task_result_invalid")
        status_value = broker_payload.get("status")
        if status_value != TaskStatus.COMPLETED.value:
            error_hint = broker_payload.get("error") or status_value or "task_failed"
            raise RuntimeError(str(error_hint))
        workflow_result = self._build_run_result_from_worker_payload(broker_payload.get("result") or {})
        return self._build_workflow_result(context, workflow_result)

    @staticmethod
    def _extract_message_id(update: Mapping[str, Any]) -> Optional[str]:
        message = update.get("message")
        if not isinstance(message, Mapping):
            return None
        message_id = message.get("message_id")
        if message_id is None:
            return None
        return str(message_id)


    @staticmethod
    def _build_run_result_from_worker_payload(payload: Mapping[str, Any]) -> WorkflowRunResult:
        stage_results: list[WorkflowStageResult] = []
        for stage in payload.get("stageResults", []) or []:
            if not isinstance(stage, Mapping):
                continue
            stage_results.append(
                WorkflowStageResult(
                    stage_id=str(stage.get("stageId", "")),
                    name=str(stage.get("name", "")),
                    prompt_used=str(stage.get("promptUsed", "")),
                    output_text=str(stage.get("outputText", "")),
                    raw_response={"usage": stage.get("usage")},
                )
            )
        telemetry = dict(payload.get("telemetry") or {})
        telemetry.setdefault("workflow_id", payload.get("workflowId"))
        return WorkflowRunResult(
            final_text=str(payload.get("finalText", "")),
            stage_results=tuple(stage_results),
            telemetry=telemetry,
        )

    def _build_workflow_result(
        self,
        context: _ConversationContext,
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

__all__ = [
    "TelegramConversationService",
    "set_task_queue_accessors",
    "set_channel_binding_provider",
    "AsyncResultHandle",
]


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



