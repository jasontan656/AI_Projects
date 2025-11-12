from __future__ import annotations

"""Telegram 会话业务服务：仅走 Workflow Orchestrator。"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
import inspect
import json
import os
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Protocol, Sequence

from business_service.channel.models import ChannelBindingRuntime, WorkflowChannelPolicy
from business_service.channel.health_store import ChannelBindingHealthStore
from business_logic.workflow import WorkflowRunResult, WorkflowStageResult
from business_service.conversation.config import TelegramEntryConfig, resolve_entry_config
from business_service.conversation.health import (
    ChannelHealthReporter,
    get_channel_health_reporter,
    set_channel_health_reporter,
)
from business_service.conversation.models import ConversationServiceResult
from business_service.conversation.primitives import AdapterBuilder
from business_service.conversation.runtime_gateway import (
    AsyncAckReservation,
    AsyncResultHandle as RuntimeAsyncResultHandle,
    AsyncResultHandleFactory,
    EnqueueFailedError,
    RuntimeGateway,
    RuntimeDispatchOutcome,
    set_task_queue_accessors,
)
from business_service.pipeline.service import AsyncPipelineNodeService
from foundational_service.contracts import toolcalls
from foundational_service.contracts.telegram import (
    behavior_telegram_inbound as contracts_telegram_inbound,
    behavior_telegram_outbound as contracts_telegram_outbound,
)
from foundational_service.persist.task_envelope import RetryState, TaskEnvelope, TaskStatus
from foundational_service.persist.worker import TaskRuntime
from project_utility.context import ContextBridge
from project_utility.db.redis import get_async_redis

log = logging.getLogger("business_service.conversation.service")

RAW_PAYLOAD_LIMIT_BYTES = int(os.getenv("TELEGRAM_RAW_PAYLOAD_MAX_BYTES", "262144"))
_ASYNC_ACK_TTL_SECONDS = int(os.getenv("TELEGRAM_ASYNC_ACK_TIMEOUT_SECONDS", "86400") or "86400")
_PIPELINE_GUARD_DECISION_TTL_SECONDS = int(os.getenv("PIPELINE_GUARD_DECISION_TTL_SECONDS", "3600") or "3600")

_CHANNEL_BINDING_PROVIDER: Optional["ChannelBindingProvider"] = None
_BINDING_REFRESH_TIMEOUT_SECONDS = float(os.getenv("TELEGRAM_BINDING_REFRESH_TIMEOUT", "1.0"))
_BINDING_FALLBACK_FLAG = os.getenv("TELEGRAM_BINDING_FALLBACK_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
_PIPELINE_GUARD_FACTORY: Optional[Callable[[], Optional["PipelineGuardService"]]] = None


class ChannelBindingProvider(Protocol):
    async def get_active_binding(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        ...

    async def refresh(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        ...


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
    chat_id: Optional[str] = None


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
        context: Optional[_ConversationContext] = None,
        resolver: Optional[Callable[[Mapping[str, Any]], Any]] = None,
    ) -> None:
        handle = runtime_handle
        if handle is None and runtime is not None and waiter is not None and task_id is not None:
            handle = RuntimeAsyncResultHandle(runtime=runtime, waiter=waiter, task_id=task_id)
        self._handle = handle
        self._task_id = task_id or (handle.task_id if handle is not None else "")
        self.context: Optional[_ConversationContext] = context
        self._resolver = resolver

    def bind(
        self,
        *,
        context: _ConversationContext,
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
    async def evaluate(self, context: _ConversationContext, workflow_id: Optional[str]) -> PipelineGuardDecision:
        ...


class _DefaultPipelineGuardService:
    async def evaluate(self, context: _ConversationContext, workflow_id: Optional[str]) -> PipelineGuardDecision:
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

    async def evaluate(self, context: _ConversationContext, workflow_id: Optional[str]) -> PipelineGuardDecision:
        node_decision = await self._evaluate_pipeline_node(context)
        if node_decision is not None:
            return node_decision
        return await self.fallback.evaluate(context, workflow_id)

    async def _evaluate_pipeline_node(self, context: _ConversationContext) -> Optional[PipelineGuardDecision]:
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

    async def process_update(self, update: Mapping[str, Any], *, policy: Mapping[str, Any]) -> ConversationServiceResult:
        request_id = ContextBridge.request_id()
        inbound = contracts_telegram_inbound(dict(update), policy)
        telemetry = dict(inbound.get("telemetry", {}))
        binding_provider = self.binding_provider or _CHANNEL_BINDING_PROVIDER
        binding_runtime = await self._get_binding_runtime(binding_provider)

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

        context = self._build_context(update, policy, inbound, request_id, telemetry)
        delegator_result = await self._maybe_dispatch_agent_delegator(context, inbound)
        if delegator_result is not None:
            return delegator_result

        if binding_runtime is None:
            log.warning(
                "telegram.binding.unavailable",
                extra={"request_id": request_id, "update_type": telemetry.get("update_type")},
            )
            fallback_runtime = self._maybe_use_policy_fallback(context)
            if fallback_runtime is None:
                version_hint = self._binding_version_hint(binding_provider)
                self._set_binding_snapshot(context, workflow_id=None, version=version_hint, status="missing")
                return self._build_binding_missing_result(context)
            binding_runtime = fallback_runtime

        self._apply_binding_entry_config(context, binding_runtime.policy)
        if not self._is_chat_allowed(context, binding_runtime.policy):
            log.warning(
                "telegram.binding.chat_not_allowed",
                extra={
                    "chat_id": context.chat_id,
                    "workflow_id": binding_runtime.workflow_id,
                },
            )
            self._schedule_health_error("telegram", binding_runtime.workflow_id, "chat_not_allowed")
            self._set_binding_snapshot(
                context,
                workflow_id=binding_runtime.workflow_id,
                version=binding_runtime.version,
                status="blocked",
                fallback=binding_runtime.version < 0,
            )
            return self._build_binding_missing_result(context)
        self._set_binding_snapshot(
            context,
            workflow_id=binding_runtime.workflow_id,
            version=binding_runtime.version,
            fallback=binding_runtime.version < 0,
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
            return self._build_guard_block_result(context, guard_decision, binding_runtime.workflow_id)

        workflow_id = binding_runtime.workflow_id
        workflow_status = "ready"
        pending_reason: Optional[str] = None


        envelope = self._build_task_envelope(
            context,
            workflow_id=workflow_id,
            workflow_status=workflow_status,
            pending_reason=pending_reason,
        )
        wait_timeout = self._resolve_wait_timeout(context.entry_config, context.policy)
        await self._record_health_snapshot(context, workflow_id=workflow_id)

        reservation = await self._reserve_async_task(context, envelope)
        if not reservation.is_new:
            log.info(
                "telegram.queue.duplicate_message",
                extra={
                    "idempotency_key": reservation.idempotency_key,
                    "task_id": reservation.task_id,
                    "chat_id": context.chat_id,
                },
            )
            return self._build_async_ack_result(
                context,
                envelope,
                None,
                telemetry_hint={"queue_status": "duplicate"},
                task_id_override=reservation.task_id,
                duplicate=True,
                idempotency_key=reservation.idempotency_key,
            )

        expects_result = bool(workflow_id)
        try:
            outcome = await self.runtime_gateway.dispatch(
                envelope=envelope,
                expects_result=expects_result,
                wait_for_result=context.entry_config.wait_for_result,
                wait_timeout=wait_timeout,
            )
        except EnqueueFailedError as exc:
            log.exception(
                "telegram.queue.enqueue_failed",
                extra={"task_id": envelope.task_id, "error": str(exc.error)},
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

        if outcome.status == "completed" and outcome.result_payload is not None:
            return self._build_response_from_worker_payload(context, outcome.result_payload)
        wrapped_handle = self._wrap_async_handle(outcome.handle, context, task_id=envelope.task_id)
        if outcome.status == "timeout":
            log.warning(
                "telegram.task_result_timeout",
                extra={"task_id": envelope.task_id, "timeout_seconds": wait_timeout},
            )
            await self._record_async_pending(context, envelope)
            return self._build_async_ack_result(
                context,
                envelope,
                wrapped_handle,
                telemetry_hint={"queue_status": "timeout"},
                text_override=context.entry_config.degraded_text,
                idempotency_key=reservation.idempotency_key,
            )
        if outcome.status == "async_ack":
            await self._record_async_pending(context, envelope)
            return self._build_async_ack_result(
                context,
                envelope,
                wrapped_handle,
                telemetry_hint={"queue_status": "async"},
                idempotency_key=reservation.idempotency_key,
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
        metadata_section = dict(core_envelope.get("metadata") or {})
        tokens_budget = policy.get("tokens_budget") or {
            "per_call_max_tokens": 3000,
            "per_flow_max_tokens": 6000,
        }
        entry_config = resolve_entry_config(policy)
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
            chat_id=str(metadata_section["chat_id"]) if metadata_section.get("chat_id") is not None else None,
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

    def _build_binding_missing_result(self, context: _ConversationContext) -> ConversationServiceResult:
        telemetry_extra = {"workflow_status": "missing", "bindingFallback": False}
        workflow_id = self._extract_policy_workflow(context.policy)
        self._schedule_health_error("telegram", workflow_id, "workflow_missing")
        missing_text = (
            context.entry_config.manual_review_text
            if context.entry_config.manual_guard
            else context.entry_config.workflow_missing_text
        )
        return self._build_static_response(
            context,
            text=missing_text,
            status="ignored",
            mode="ignored",
            intent="workflow_missing",
            audit_reason="workflow_missing",
            error_hint="workflow_missing",
            telemetry_extra=telemetry_extra,
        )

    def _maybe_use_policy_fallback(self, context: _ConversationContext) -> Optional[ChannelBindingRuntime]:
        if not _BINDING_FALLBACK_FLAG:
            return None
        entrypoints = context.policy.get("entrypoints")
        if not isinstance(entrypoints, Mapping):
            return None
        telegram_entry = entrypoints.get("telegram")
        if not isinstance(telegram_entry, Mapping):
            return None
        workflow_id = telegram_entry.get("workflow_id") or telegram_entry.get("workflowId")
        if not workflow_id:
            return None
        now = datetime.now(timezone.utc)
        policy = WorkflowChannelPolicy(
            workflow_id=str(workflow_id),
            channel="telegram",
            encrypted_bot_token="__fallback__",
            bot_token_mask="__fallback__",
            webhook_url=str(telegram_entry.get("webhook_url") or telegram_entry.get("webhookUrl") or ""),
            wait_for_result=bool(telegram_entry.get("wait_for_result", True)),
            workflow_missing_message=str(
                telegram_entry.get("workflow_missing_text") or telegram_entry.get("workflowMissingText") or DEFAULT_WORKFLOW_MISSING_MESSAGE
            ),
            timeout_message=str(
                telegram_entry.get("timeout_message") or telegram_entry.get("timeoutMessage") or DEFAULT_TIMEOUT_MESSAGE
            ),
            metadata={},
            updated_by="binding_fallback",
            updated_at=now,
            secret_version=0,
        )
        runtime = ChannelBindingRuntime(
            workflow_id=str(workflow_id),
            channel="telegram",
            policy=policy,
            version=-1,
        )
        log.error(
            "telegram.binding.policy_fallback_active",
            extra={"workflow_id": runtime.workflow_id},
        )
        return runtime

    @staticmethod
    def _set_binding_snapshot(
        context: _ConversationContext,
        *,
        workflow_id: Optional[str],
        version: Optional[int],
        status: Optional[str] = None,
        fallback: bool = False,
    ) -> None:
        snapshot = dict(context.telemetry.get("binding") or {})
        snapshot["workflow_id"] = workflow_id
        snapshot["version"] = version if version is not None else snapshot.get("version", -1)
        if fallback:
            snapshot["fallback"] = True
        if status:
            snapshot["status"] = status
        context.telemetry["binding"] = snapshot

    def _binding_version_hint(self, provider: Optional[ChannelBindingProvider]) -> Optional[int]:
        if provider is None:
            return None
        get_state = getattr(provider, "get_state", None)
        if callable(get_state):
            try:
                state = get_state("telegram")
            except TypeError:
                try:
                    state = get_state()
                except Exception:
                    state = None
            if state is not None:
                return getattr(state, "version", None)
        snapshot_fn = getattr(provider, "snapshot", None)
        if callable(snapshot_fn):
            try:
                snapshot = snapshot_fn()
            except TypeError:
                snapshot = snapshot_fn("telegram")
            if isinstance(snapshot, Mapping):
                data = snapshot.get("telegram")
                if isinstance(data, Mapping):
                    version = data.get("version")
                    if isinstance(version, int):
                        return version
        return None

    @staticmethod
    def _is_chat_allowed(context: _ConversationContext, policy: WorkflowChannelPolicy) -> bool:
        metadata = policy.metadata if isinstance(policy.metadata, Mapping) else {}
        allowed = metadata.get("allowedChatIds")
        if not isinstance(allowed, (list, tuple, set)):
            return True
        allowed_ids = {str(item) for item in allowed if item not in {None, ""}}
        if not allowed_ids:
            return True
        if context.chat_id is None:
            return False
        return str(context.chat_id) in allowed_ids

    @staticmethod
    def _apply_binding_entry_config(context: _ConversationContext, policy: WorkflowChannelPolicy) -> None:
        context.entry_config = resolve_entry_config(
            context.policy,
            binding_policy=policy,
            defaults=context.entry_config,
        )

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

    async def _maybe_dispatch_agent_delegator(
        self,
        context: _ConversationContext,
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
            return self._build_static_response(
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
        context: _ConversationContext,
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
        return self._build_static_response(
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

    @staticmethod
    def _format_ack_text(template: str, task_id: str) -> str:
        safe_template = template or ""
        safe_task_id = task_id or "pending"
        try:
            return safe_template.format(task_id=safe_task_id)
        except Exception:
            return safe_template

    def _wrap_async_handle(
        self,
        handle: Optional[RuntimeAsyncResultHandle | AsyncResultHandle],
        context: _ConversationContext,
        *,
        task_id: Optional[str],
    ) -> Optional[AsyncResultHandle]:
        if handle is None:
            return None
        resolver = lambda payload: self._build_response_from_worker_payload(context, payload)
        if isinstance(handle, AsyncResultHandle):
            return handle.bind(context=context, resolver=resolver)
        return AsyncResultHandle(runtime_handle=handle, context=context, resolver=resolver, task_id=task_id)

    def _build_async_ack_result(
        self,
        context: _ConversationContext,
        envelope: TaskEnvelope,
        handle: Optional[AsyncResultHandle],
        *,
        telemetry_hint: Optional[Mapping[str, Any]] = None,
        text_override: Optional[str] = None,
        task_id_override: Optional[str] = None,
        duplicate: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> ConversationServiceResult:
        template = text_override or context.entry_config.async_ack_text
        task_id = task_id_override or envelope.task_id
        ack_text = self._format_ack_text(template, task_id)
        telemetry_extra = {"task_id": task_id, "queue_mode": "async"}
        if telemetry_hint:
            telemetry_extra.update(telemetry_hint)
        if duplicate:
            telemetry_extra.setdefault("queue_status", "duplicate")
        async_payload: Dict[str, Any] = {
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
        self._schedule_health_error("telegram", envelope.payload.get("workflowId"), "enqueue_failed")
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
        pending_text = (
            context.entry_config.manual_review_text
            if context.entry_config.manual_guard
            else context.entry_config.workflow_missing_text
        )
        telemetry_extra = {
            "workflow_status": "pending",
            "queue_status": "workflow_pending",
            "task_id": envelope.task_id,
        }
        agent_response_extra = {"task_id": envelope.task_id, "dispatch": "workflow_pending"}
        agent_request_extra = {"task_id": envelope.task_id}
        return self._build_static_response(
            context,
            text=pending_text,
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
        context: _ConversationContext,
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

    async def _reserve_async_task(self, context: _ConversationContext, envelope: TaskEnvelope) -> AsyncAckReservation:
        if context.entry_config.wait_for_result:
            return AsyncAckReservation(is_new=True, task_id=envelope.task_id)
        factory = self.async_handle_factory
        idempotency_key = str(envelope.context.get("idempotencyKey") or "")
        if not factory:
            return AsyncAckReservation(
                is_new=True,
                task_id=envelope.task_id,
                idempotency_key=idempotency_key or None,
            )
        return await factory.reserve(idempotency_key=idempotency_key or None, task_id=envelope.task_id)

    async def _record_async_pending(self, context: _ConversationContext, envelope: TaskEnvelope) -> None:
        factory = self.async_handle_factory
        if factory is None or context.chat_id is None:
            return
        await factory.track_pending(chat_id=context.chat_id, task_id=envelope.task_id)

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
        context: _ConversationContext,
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
        context: _ConversationContext,
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

    def _build_guard_block_result(
        self,
        context: _ConversationContext,
        decision: PipelineGuardDecision,
        workflow_id: Optional[str],
    ) -> ConversationServiceResult:
        telemetry_extra = {
            "guard_status": "blocked",
            "queue_status": "guard_blocked",
        }
        if decision.profile:
            telemetry_extra["guard_profile"] = decision.profile
        error_hint = decision.reason or "llm_blocked"
        self._schedule_health_error("telegram", workflow_id, "guard_blocked")
        return self._build_static_response(
            context,
            text=context.entry_config.manual_review_text,
            status="handled",
            mode="manual",
            intent="pipeline_guard_blocked",
            audit_reason="llm_blocked",
            error_hint=error_hint,
            telemetry_extra=telemetry_extra,
        )


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
    "set_channel_binding_health_store",
    "set_pipeline_service_factory",
    "AsyncResultHandle",
    "PipelineNodeGuardService",
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



