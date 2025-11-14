from __future__ import annotations

"""Telegram 会话业务服务：仅走 Workflow Orchestrator。"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
import inspect
import json
import os
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Protocol

from business_service.channel.models import ChannelBindingRuntime
from business_service.channel.health_store import ChannelBindingHealthStore
from business_logic.workflow import WorkflowRunResult, WorkflowStageResult
from business_service.conversation.binding_coordinator import BindingCoordinator, ChannelBindingProvider
from business_service.conversation.config import TelegramEntryConfig
from business_service.conversation.health import (
    ChannelHealthReporter,
    get_channel_health_reporter,
    set_channel_health_reporter,
)
from business_service.conversation.models import ConversationServiceResult
from business_service.conversation.primitives import AdapterBuilder
from business_service.conversation.response_builder import ResponseBuilder
from business_service.conversation.runtime_gateway import (
    AsyncResultHandle as RuntimeAsyncResultHandle,
    AsyncResultHandleFactory,
    EnqueueFailedError,
    RuntimeGateway,
    RuntimeDispatchOutcome,
    set_task_queue_accessors,
)
from business_service.conversation.task_enqueue_service import (
    TaskEnqueueDispatchError,
    TaskEnqueueService,
)
from business_service.conversation.context_factory import ConversationContext, ConversationContextFactory
from business_service.pipeline.service import AsyncPipelineNodeService
from foundational_service.contracts import toolcalls
from foundational_service.contracts.telegram import (
    behavior_telegram_inbound as contracts_telegram_inbound,
)
from foundational_service.persist.task_envelope import TaskStatus
from foundational_service.persist.worker import TaskRuntime
from project_utility.context import ContextBridge
from project_utility.db.redis import get_async_redis

log = logging.getLogger("business_service.conversation.service")

_ASYNC_ACK_TTL_SECONDS = int(os.getenv("TELEGRAM_ASYNC_ACK_TIMEOUT_SECONDS", "86400") or "86400")
_PIPELINE_GUARD_DECISION_TTL_SECONDS = int(os.getenv("PIPELINE_GUARD_DECISION_TTL_SECONDS", "3600") or "3600")

_CHANNEL_BINDING_PROVIDER: Optional["ChannelBindingProvider"] = None
_PIPELINE_GUARD_FACTORY: Optional[Callable[[], Optional["PipelineGuardService"]]] = None

def set_channel_binding_provider(provider: ChannelBindingProvider) -> None:
    """Register the global channel binding provider used by conversation flows."""

    global _CHANNEL_BINDING_PROVIDER
    _CHANNEL_BINDING_PROVIDER = provider


def set_channel_binding_health_store(store: ChannelBindingHealthStore) -> None:
    """Compatibility shim to keep existing bootstrap wiring intact."""

    reporter = ChannelHealthReporter(store=store, redis_client=get_async_redis())
    set_channel_health_reporter(reporter)


def set_pipeline_service_factory(factory: Callable[[], Optional["PipelineGuardService"]]) -> None:
    """Register the factory used to construct pipeline guard services."""

    global _PIPELINE_GUARD_FACTORY
    _PIPELINE_GUARD_FACTORY = factory


class AsyncResultHandle:
    """Async task handle exposed to interface layers."""

    __slots__ = ("_handle", "_task_id", "context", "_resolver")

    def __init__(
        self,
        runtime: Optional[TaskRuntime] = None,
        waiter: Optional[asyncio.Future[Any]] = None,
        task_id: Optional[str] = None,
        *,
        runtime_handle: Optional[RuntimeAsyncResultHandle] = None,
        context: Optional[ConversationContext] = None,
        resolver: Optional[Callable[[Mapping[str, Any]], Any]] = None,
    ) -> None:
        handle = runtime_handle
        if handle is None and runtime is not None and waiter is not None and task_id is not None:
            handle = RuntimeAsyncResultHandle(runtime=runtime, waiter=waiter, task_id=task_id)
        self._handle = handle
        self._task_id = task_id or (handle.task_id if handle is not None else "")
        self.context: Optional[ConversationContext] = context
        self._resolver = resolver

    def bind(
        self,
        *,
        context: ConversationContext,
        resolver: Callable[[Mapping[str, Any]], Any],
    ) -> "AsyncResultHandle":
        self.context = context
        self._resolver = resolver
        return self

    @property
    def task_id(self) -> str:
        return self._task_id

    async def resolve(self) -> Mapping[str, Any] | ConversationServiceResult:
        if self._handle is None:
            raise RuntimeError("async_handle_unbound")
        payload = await self._handle.resolve()
        return await self._apply_resolver(payload)

    async def discard(self) -> None:
        if self._handle is None:
            return
        await self._handle.discard()

    async def _apply_resolver(self, payload: Mapping[str, Any]) -> Any:
        if self._resolver is None:
            return payload
        result = self._resolver(payload)
        if inspect.isawaitable(result):
            return await result
        return result


@dataclass(slots=True)
class PipelineGuardDecision:
    allow_llm: bool
    manual_review: bool = False
    profile: Optional[str] = None
    reason: Optional[str] = None
    degraded: bool = False


class PipelineGuardService(Protocol):
    async def evaluate(self, context: ConversationContext, workflow_id: Optional[str]) -> PipelineGuardDecision:
        ...


class _DefaultPipelineGuardService:
    async def evaluate(self, context: ConversationContext, workflow_id: Optional[str]) -> PipelineGuardDecision:
        entry = context.policy.get("entrypoints")
        telegram_entry: Mapping[str, Any] = {}
        guard_config: Mapping[str, Any] = {}
        if isinstance(entry, Mapping):
            candidate = entry.get("telegram")
            if isinstance(candidate, Mapping):
                telegram_entry = candidate
                raw_guard = candidate.get("guard")
                if isinstance(raw_guard, Mapping):
                    guard_config = raw_guard
        allow_llm = bool(guard_config.get("allow_llm", telegram_entry.get("allow_llm", True)))
        manual_guard = bool(
            guard_config.get("manual_guard", telegram_entry.get("manual_guard", context.entry_config.manual_guard))
        )
        profile = guard_config.get("manual_guard_profile") or guard_config.get("profile")
        reason = guard_config.get("reason")
        if not allow_llm or manual_guard:
            return PipelineGuardDecision(
                allow_llm=False,
                manual_review=True,
                profile=str(profile) if profile else None,
                reason=reason or ("manual_guard" if manual_guard else "llm_blocked"),
            )
        return PipelineGuardDecision(
            allow_llm=True,
            manual_review=False,
            profile=str(profile) if profile else None,
            reason=reason,
        )


@dataclass(slots=True)
class PipelineNodeGuardService(PipelineGuardService):
    pipeline_service: AsyncPipelineNodeService
    fallback: PipelineGuardService = field(default_factory=_DefaultPipelineGuardService)

    async def evaluate(self, context: ConversationContext, workflow_id: Optional[str]) -> PipelineGuardDecision:
        node_decision = await self._evaluate_pipeline_node(context)
        if node_decision is not None:
            return node_decision
        return await self.fallback.evaluate(context, workflow_id)

    async def _evaluate_pipeline_node(self, context: ConversationContext) -> Optional[PipelineGuardDecision]:
        node_id = self._extract_pipeline_node_id(context.policy)
        if not node_id:
            return None
        try:
            node = await self.pipeline_service.get_node(node_id)
        except Exception as exc:  # pragma: no cover - diagnostics only
            log.warning(
                "telegram.pipeline.guard_lookup_failed",
                extra={"node_id": node_id, "error": str(exc)},
            )
            return PipelineGuardDecision(
                allow_llm=True,
                manual_review=False,
                profile="pipeline",
                reason="pipeline_guard_error",
                degraded=True,
            )
        if node is None:
            return PipelineGuardDecision(
                allow_llm=True,
                manual_review=False,
                profile="pipeline",
                reason="pipeline_node_missing",
            )
        if not getattr(node, "allow_llm", True):
            return PipelineGuardDecision(
                allow_llm=False,
                manual_review=True,
                profile="pipeline",
                reason="pipeline_node_blocked",
            )
        return PipelineGuardDecision(
            allow_llm=True,
            manual_review=False,
            profile="pipeline",
            reason="pipeline_node_allowed",
        )

    @staticmethod
    def _extract_pipeline_node_id(policy: Mapping[str, Any]) -> Optional[str]:
        entrypoints = policy.get("entrypoints")
        telegram_entry = entrypoints.get("telegram") if isinstance(entrypoints, Mapping) else None
        guard_section = {}
        if isinstance(telegram_entry, Mapping):
            guard_candidate = telegram_entry.get("guard")
            if isinstance(guard_candidate, Mapping):
                guard_section = guard_candidate
        candidate_keys = (
            "pipeline_node_id",
            "pipelineNodeId",
            "node_id",
            "nodeId",
        )
        for source in (guard_section, telegram_entry or {}, policy):
            if not isinstance(source, Mapping):
                continue
            for key in candidate_keys:
                value = source.get(key)
                if value:
                    return str(value)
        return None


@dataclass(slots=True)
class TelegramConversationService:
    """面向 Telegram 渠道的业务服务门面。"""

    adapter_builder: AdapterBuilder = field(default_factory=AdapterBuilder)
    task_submitter_factory: Optional[Callable[[], Optional[Any]]] = None
    task_runtime_factory: Optional[Callable[[], Optional[Any]]] = None
    binding_provider: Optional[ChannelBindingProvider] = None
    runtime_gateway: RuntimeGateway = field(default_factory=RuntimeGateway)
    health_reporter: Optional[ChannelHealthReporter] = None
    agent_delegator: Optional[Any] = None
    pipeline_service_factory: Optional[Callable[[], Optional[PipelineGuardService]]] = None
    async_handle_factory: Optional[AsyncResultHandleFactory] = None
    task_enqueue_service: TaskEnqueueService = field(init=False, repr=False)
    response_builder: ResponseBuilder = field(init=False, repr=False)
    context_factory: ConversationContextFactory = field(default_factory=ConversationContextFactory)
    binding_coordinator: BindingCoordinator = field(default_factory=BindingCoordinator)
    _pipeline_guard_default: PipelineGuardService = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.task_submitter_factory is not None or self.task_runtime_factory is not None:
            self.runtime_gateway = RuntimeGateway(
                submitter_factory=self.task_submitter_factory,
                runtime_factory=self.task_runtime_factory,
            )
        object.__setattr__(self, "_pipeline_guard_default", _DefaultPipelineGuardService())
        if self.async_handle_factory is None:
            try:
                self.async_handle_factory = AsyncResultHandleFactory(ttl_seconds=_ASYNC_ACK_TTL_SECONDS)
            except Exception:  # pragma: no cover - defensive fallback
                self.async_handle_factory = None
        if self.pipeline_service_factory is None and _PIPELINE_GUARD_FACTORY is not None:
            self.pipeline_service_factory = _PIPELINE_GUARD_FACTORY
        self.response_builder = ResponseBuilder(
            adapter_builder=self.adapter_builder,
            schedule_health_error=self._schedule_health_error,
        )
        self.task_enqueue_service = TaskEnqueueService(
            runtime_gateway=self.runtime_gateway,
            async_handle_factory=self.async_handle_factory,
        )

    async def process_update(self, update: Mapping[str, Any], *, policy: Mapping[str, Any]) -> ConversationServiceResult:
        request_id = ContextBridge.request_id()
        inbound = contracts_telegram_inbound(dict(update), policy)
        telemetry = dict(inbound.get("telemetry", {}))
        binding_provider = self.binding_provider or _CHANNEL_BINDING_PROVIDER

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

        prompt_id = inbound.get("prompt_id")
        if prompt_id:
            raise RuntimeError(f"legacy prompt flow detected: {prompt_id}")

        context = self.context_factory.build(update, policy, inbound, request_id, telemetry)
        delegator_result = await self._maybe_dispatch_agent_delegator(context, inbound)
        if delegator_result is not None:
            return delegator_result

        binding_runtime = await self.binding_coordinator.resolve_runtime(
            provider=binding_provider,
            context=context,
        )
        if binding_runtime is None:
            log.warning(
                "telegram.binding.unavailable",
                extra={"request_id": request_id, "update_type": telemetry.get("update_type")},
            )
            version_hint = self.binding_coordinator.binding_version_hint(binding_provider)
            self.binding_coordinator.record_snapshot(
                context,
                workflow_id=None,
                version=version_hint,
                status="missing",
            )
            return self._build_binding_missing_result(context)

        self.binding_coordinator.apply_entry_config(context, binding_runtime.policy)
        if not self.binding_coordinator.is_chat_allowed(context, binding_runtime.policy):
            log.warning(
                "telegram.binding.chat_not_allowed",
                extra={
                    "chat_id": context.chat_id,
                    "workflow_id": binding_runtime.workflow_id,
                },
            )
            self._schedule_health_error("telegram", binding_runtime.workflow_id, "chat_not_allowed")
            self.binding_coordinator.record_snapshot(
                context,
                workflow_id=binding_runtime.workflow_id,
                version=binding_runtime.version,
                status="blocked",
                fallback=binding_runtime.version < 0,
                policy=binding_runtime.policy,
            )
            return self._build_binding_missing_result(context, binding_fallback=binding_runtime.version < 0)
        self.binding_coordinator.record_snapshot(
            context,
            workflow_id=binding_runtime.workflow_id,
            version=binding_runtime.version,
            fallback=binding_runtime.version < 0,
            policy=binding_runtime.policy,
        )

        guard_decision = await self._evaluate_pipeline_guard(context, binding_runtime.workflow_id)
        if not guard_decision.allow_llm:
            log.info(
                "telegram.pipeline.guard_blocked",
                extra={
                    "workflow_id": binding_runtime.workflow_id,
                    "chat_id": context.chat_id,
                    "profile": guard_decision.profile,
                },
            )
            await self._record_guard_decision(context, binding_runtime.workflow_id, guard_decision)
            telemetry_extra = {
                "guard_status": "blocked",
                "queue_status": "guard_blocked",
            }
            if guard_decision.profile:
                telemetry_extra["guard_profile"] = guard_decision.profile
            return self.response_builder.guard_block(
                context,
                error_hint=guard_decision.reason or "llm_blocked",
                workflow_id=binding_runtime.workflow_id,
                telemetry_extra=telemetry_extra,
            )

        workflow_id = binding_runtime.workflow_id
        workflow_status = "ready"
        pending_reason: Optional[str] = None

        try:
            enqueue_result = await self.task_enqueue_service.dispatch(
                context,
                workflow_id=workflow_id,
                workflow_status=workflow_status,
                pending_reason=pending_reason,
            )
        except TaskEnqueueDispatchError as exc:
            log.exception(
                "telegram.queue.enqueue_failed",
                extra={"task_id": exc.envelope.task_id, "error": str(exc.error)},
            )
            return self.response_builder.enqueue_failure(context, exc.envelope, context.entry_config)

        await self._record_health_snapshot(context, workflow_id=workflow_id)

        envelope = enqueue_result.envelope
        reservation = enqueue_result.reservation

        if enqueue_result.duplicate:
            log.info(
                "telegram.queue.duplicate_message",
                extra={
                    "idempotency_key": reservation.idempotency_key,
                    "task_id": reservation.task_id,
                    "chat_id": context.chat_id,
                },
            )
            return self.response_builder.async_ack(
                context,
                envelope,
                handle=None,
                telemetry_hint={"queue_status": "duplicate"},
                task_id_override=reservation.task_id,
                duplicate=True,
                idempotency_key=reservation.idempotency_key,
            )

        outcome = enqueue_result.outcome
        if outcome is None:
            raise RuntimeError("task_enqueue_missing_outcome")

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

        if outcome.status == "completed" and outcome.result_payload is not None:
            return self._build_response_from_worker_payload(context, outcome.result_payload)

        wrapped_handle = self._wrap_async_handle(outcome.handle, context, task_id=envelope.task_id)

        if outcome.status == "timeout":
            log.warning(
                "telegram.task_result_timeout",
                extra={"task_id": envelope.task_id, "timeout_seconds": enqueue_result.wait_timeout},
            )
            await self.task_enqueue_service.track_pending(context, envelope)
            degraded_template = self.response_builder.resolve_template(
                context,
                "degraded",
                context.entry_config.degraded_text,
            )
            return self.response_builder.async_ack(
                context,
                envelope,
                handle=wrapped_handle,
                telemetry_hint={"queue_status": "timeout"},
                idempotency_key=reservation.idempotency_key,
                template_key="degraded",
                fallback_text=degraded_template,
            )
        if outcome.status == "async_ack":
            await self.task_enqueue_service.track_pending(context, envelope)
            return self.response_builder.async_ack(
                context,
                envelope,
                handle=wrapped_handle,
                telemetry_hint={"queue_status": "async"},
                idempotency_key=reservation.idempotency_key,
            )

        return self.response_builder.pending_workflow(
            context,
            envelope,
            pending_reason=pending_reason or "workflow_pending",
        )

    async def _get_binding_runtime(
        self,
        provider: Optional[ChannelBindingProvider],
    ) -> Optional[ChannelBindingRuntime]:
        if provider is None:
            return None
        try:
            binding = await provider.get_active_binding("telegram")
            if binding:
                return binding
            refreshed = await self._attempt_binding_refresh(provider)
            if refreshed:
                return refreshed
            return None
        except Exception as exc:  # pragma: no cover - defensive logging
            log.warning("telegram.binding.lookup_failed", extra={"error": str(exc)})
            return None

    async def _attempt_binding_refresh(self, provider: ChannelBindingProvider) -> Optional[ChannelBindingRuntime]:
        refresh_fn = getattr(provider, "refresh", None)
        if refresh_fn is None:
            return None
        try:
            await asyncio.wait_for(refresh_fn("telegram"), timeout=_BINDING_REFRESH_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            log.warning("telegram.binding.refresh_timeout", extra={"timeout": _BINDING_REFRESH_TIMEOUT_SECONDS})
            return None
        except Exception as exc:
            log.warning("telegram.binding.refresh_failed", extra={"error": str(exc)})
            return None
        return await provider.get_active_binding("telegram")

    def _build_binding_missing_result(
        self,
        context: ConversationContext,
        *,
        binding_fallback: bool = False,
    ) -> ConversationServiceResult:
        telemetry_extra = {"workflow_status": "missing", "bindingFallback": binding_fallback}
        workflow_id = self._extract_policy_workflow(context.policy)
        self._schedule_health_error("telegram", workflow_id, "workflow_missing")
        if context.entry_config.manual_guard:
            manual_text = self.response_builder.resolve_template(
                context,
                "manual_review",
                context.entry_config.manual_review_text,
            )
            return self.response_builder.static(
                context,
                text=manual_text,
                status="ignored",
                mode="manual",
                intent="workflow_missing",
                audit_reason="workflow_missing",
                error_hint="workflow_missing",
                telemetry_extra=telemetry_extra,
            )
        return self.response_builder.workflow_missing(context, telemetry_extra=telemetry_extra)

    async def _maybe_dispatch_agent_delegator(
        self,
        context: ConversationContext,
        inbound: Mapping[str, Any],
    ) -> Optional[ConversationServiceResult]:
        if self.agent_delegator is None:
            return None
        agent_request = inbound.get("agent_request")
        if not agent_request:
            return None
        dispatch = getattr(self.agent_delegator, "dispatch", None)
        if dispatch is None:
            log.warning("telegram.agent_delegator.invalid_handler")
            return None
        try:
            bridge_payload = await dispatch(agent_request)
        except Exception as exc:  # pragma: no cover - defensive logging
            log.exception("telegram.agent_delegator.failed", extra={"error": str(exc)})
            raise
        if not isinstance(bridge_payload, Mapping):
            log.warning("telegram.agent_delegator.invalid_payload")
            return self.response_builder.static(
                context,
                text=context.user_text or "",
                status="handled",
                mode="direct",
                intent="agent_bridge",
                audit_reason="agent_bridge_invalid_payload",
                error_hint="agent_bridge_invalid_payload",
                agent_request_extra=agent_request,
            )
        return self._build_agent_bridge_response(context, agent_request, bridge_payload)

    def _build_agent_bridge_response(
        self,
        context: ConversationContext,
        agent_request: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> ConversationServiceResult:
        bridge_result = payload.get("agent_bridge_result") or {}
        telemetry_extra = payload.get("telemetry") or {}
        chunks = list(bridge_result.get("chunks") or [])
        text = bridge_result.get("text") or "".join(chunks)
        if not text:
            text = context.user_text or ""
        mode = bridge_result.get("mode") or "direct"
        agent_response_extra = {
            "chunks": chunks,
            "tokens_usage": bridge_result.get("tokens_usage", {}),
            "dispatch": "agent_bridge",
        }
        return self.response_builder.static(
            context,
            text=text,
            status="handled",
            mode=mode,
            intent=str(agent_request.get("prompt") or "agent_bridge"),
            audit_reason="agent_bridge",
            error_hint="agent_bridge",
            telemetry_extra=telemetry_extra,
            agent_response_extra=agent_response_extra,
            agent_request_extra=agent_request,
            chunks=chunks or None,
            streaming_mode=mode,
        )

    def _wrap_async_handle(
        self,
        handle: Optional[RuntimeAsyncResultHandle | AsyncResultHandle],
        context: ConversationContext,
        *,
        task_id: Optional[str],
    ) -> Optional[AsyncResultHandle]:
        if handle is None:
            return None
        resolver = lambda payload: self._build_response_from_worker_payload(context, payload)
        if isinstance(handle, AsyncResultHandle):
            return handle.bind(context=context, resolver=resolver)
        return AsyncResultHandle(runtime_handle=handle, context=context, resolver=resolver, task_id=task_id)

    def _build_response_from_worker_payload(
        self,
        context: ConversationContext,
        broker_payload: Mapping[str, Any],
    ) -> ConversationServiceResult:
        if not isinstance(broker_payload, Mapping):
            raise RuntimeError("task_result_invalid")
        status_value = broker_payload.get("status")
        if status_value != TaskStatus.COMPLETED.value:
            error_hint = broker_payload.get("error") or status_value or "task_failed"
            raise RuntimeError(str(error_hint))
        workflow_result = self._build_run_result_from_worker_payload(broker_payload.get("result") or {})
        return self.response_builder.workflow_result(context, workflow_result)

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
    def _extract_policy_workflow(policy: Mapping[str, Any]) -> Optional[str]:
        entrypoints = policy.get("entrypoints")
        if not isinstance(entrypoints, Mapping):
            return None
        telegram_entry = entrypoints.get("telegram")
        if not isinstance(telegram_entry, Mapping):
            return None
        workflow_id = telegram_entry.get("workflow_id") or telegram_entry.get("workflowId")
        if workflow_id:
            return str(workflow_id)
        return None

    def _schedule_health_error(self, channel: str, workflow_id: Optional[str], error_type: str) -> None:
        reporter = self._get_health_reporter()
        if reporter is None:
            return
        reporter.schedule_error(channel, workflow_id, error_type)

    def _get_health_reporter(self) -> Optional[ChannelHealthReporter]:
        return self.health_reporter or get_channel_health_reporter()

    async def _record_health_snapshot(
        self,
        context: ConversationContext,
        *,
        workflow_id: Optional[str],
        pending: int = 0,
    ) -> None:
        reporter = self._get_health_reporter()
        if reporter is None:
            return
        latency_value = context.telemetry.get("latency_ms")
        try:
            latency_ms = float(latency_value) if latency_value is not None else None
        except (TypeError, ValueError):
            latency_ms = None
        await reporter.record_snapshot(
            channel="telegram",
            workflow_id=workflow_id,
            mode=context.entry_config.mode.value,
            pending=pending,
            latency_ms=latency_ms,
            manual_guard=context.entry_config.manual_guard,
        )

    def _resolve_pipeline_guard(self) -> PipelineGuardService:
        if self.pipeline_service_factory is None:
            return self._pipeline_guard_default
        try:
            service = self.pipeline_service_factory()
        except Exception:  # pragma: no cover - factory failures fallback
            return self._pipeline_guard_default
        if service is None:
            return self._pipeline_guard_default
        if hasattr(service, "evaluate"):
            return service  # type: ignore[return-value]
        if isinstance(service, AsyncPipelineNodeService) or hasattr(service, "get_node"):
            return PipelineNodeGuardService(
                pipeline_service=service,  # type: ignore[arg-type]
                fallback=self._pipeline_guard_default,
            )
        return self._pipeline_guard_default

    async def _evaluate_pipeline_guard(
        self,
        context: ConversationContext,
        workflow_id: Optional[str],
    ) -> PipelineGuardDecision:
        service = self._resolve_pipeline_guard()
        try:
            decision = await service.evaluate(context, workflow_id)
        except Exception as exc:  # pragma: no cover - guard isolation
            log.exception(
                "telegram.pipeline.guard_failed",
                extra={"error": str(exc), "workflow_id": workflow_id},
            )
            context.telemetry["guard_status"] = "degraded"
            return PipelineGuardDecision(allow_llm=True, degraded=True, reason="guard_failed")
        if decision.manual_review or not decision.allow_llm:
            context.telemetry["guard_status"] = "blocked"
            if decision.profile:
                context.telemetry["guard_profile"] = decision.profile
        else:
            context.telemetry["guard_status"] = "allowed"
            if decision.profile:
                context.telemetry["guard_profile"] = decision.profile
        return decision

    async def _record_guard_decision(
        self,
        context: ConversationContext,
        workflow_id: Optional[str],
        decision: PipelineGuardDecision,
    ) -> None:
        if context.chat_id is None:
            return
        try:
            client = get_async_redis()
        except Exception:
            return
        payload = {
            "chat_id": context.chat_id,
            "workflow_id": workflow_id,
            "decision": "allow" if decision.allow_llm else "block",
            "manual_review": decision.manual_review,
            "profile": decision.profile,
        }
        try:
            await client.set(
                f"rise:pipeline_guard:decision:{context.chat_id}",
                json.dumps(payload, ensure_ascii=False),
                ex=_PIPELINE_GUARD_DECISION_TTL_SECONDS,
            )
        except Exception:  # pragma: no cover - metrics best effort
            return

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
    def _extract_policy_workflow(policy: Mapping[str, Any]) -> Optional[str]:
        entrypoints = policy.get("entrypoints")
        if not isinstance(entrypoints, Mapping):
            return None
        telegram_entry = entrypoints.get("telegram")
        if not isinstance(telegram_entry, Mapping):
            return None
        workflow_id = telegram_entry.get("workflow_id") or telegram_entry.get("workflowId")
        if workflow_id:
            return str(workflow_id)
        return None

    def _schedule_health_error(self, channel: str, workflow_id: Optional[str], error_type: str) -> None:
        reporter = self._get_health_reporter()
        if reporter is None:
            return
        reporter.schedule_error(channel, workflow_id, error_type)

    def _get_health_reporter(self) -> Optional[ChannelHealthReporter]:
        return self.health_reporter or get_channel_health_reporter()

    async def _record_health_snapshot(
        self,
        context: ConversationContext,
        *,
        workflow_id: Optional[str],
        pending: int = 0,
    ) -> None:
        reporter = self._get_health_reporter()
        if reporter is None:
            return
        latency_value = context.telemetry.get("latency_ms")
        try:
            latency_ms = float(latency_value) if latency_value is not None else None
        except (TypeError, ValueError):
            latency_ms = None
        await reporter.record_snapshot(
            channel="telegram",
            workflow_id=workflow_id,
            mode=context.entry_config.mode.value,
            pending=pending,
            latency_ms=latency_ms,
            manual_guard=context.entry_config.manual_guard,
        )

    def _resolve_pipeline_guard(self) -> PipelineGuardService:
        if self.pipeline_service_factory is None:
            return self._pipeline_guard_default
        try:
            service = self.pipeline_service_factory()
        except Exception:  # pragma: no cover - factory failures fallback
            return self._pipeline_guard_default
        if service is None:
            return self._pipeline_guard_default
        if hasattr(service, "evaluate"):
            return service  # type: ignore[return-value]
        if isinstance(service, AsyncPipelineNodeService) or hasattr(service, "get_node"):
            return PipelineNodeGuardService(
                pipeline_service=service,  # type: ignore[arg-type]
                fallback=self._pipeline_guard_default,
            )
        return self._pipeline_guard_default

    async def _evaluate_pipeline_guard(
        self,
        context: ConversationContext,
        workflow_id: Optional[str],
    ) -> PipelineGuardDecision:
        service = self._resolve_pipeline_guard()
        try:
            decision = await service.evaluate(context, workflow_id)
        except Exception as exc:  # pragma: no cover - guard isolation
            log.exception(
                "telegram.pipeline.guard_failed",
                extra={"error": str(exc), "workflow_id": workflow_id},
            )
            context.telemetry["guard_status"] = "degraded"
            return PipelineGuardDecision(allow_llm=True, degraded=True, reason="guard_failed")
        if decision.manual_review or not decision.allow_llm:
            context.telemetry["guard_status"] = "blocked"
            if decision.profile:
                context.telemetry["guard_profile"] = decision.profile
        else:
            context.telemetry["guard_status"] = "allowed"
            if decision.profile:
                context.telemetry["guard_profile"] = decision.profile
        return decision

    async def _record_guard_decision(
        self,
        context: ConversationContext,
        workflow_id: Optional[str],
        decision: PipelineGuardDecision,
    ) -> None:
        if context.chat_id is None:
            return
        try:
            client = get_async_redis()
        except Exception:
            return
        payload = {
            "chat_id": context.chat_id,
            "workflow_id": workflow_id,
            "decision": "allow" if decision.allow_llm else "block",
            "manual_review": decision.manual_review,
            "profile": decision.profile,
        }
        try:
            await client.set(
                f"rise:pipeline_guard:decision:{context.chat_id}",
                json.dumps(payload, ensure_ascii=False),
                ex=_PIPELINE_GUARD_DECISION_TTL_SECONDS,
            )
        except Exception:  # pragma: no cover - metrics best effort
            return

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


__all__ = [
    "TelegramConversationService",
    "set_task_queue_accessors",
    "set_channel_binding_provider",
    "set_channel_binding_health_store",
    "set_pipeline_service_factory",
    "AsyncResultHandle",
    "PipelineNodeGuardService",
    "ChannelBindingProvider",
]


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



