from __future__ import annotations

"""Task enqueue orchestration extracted from Telegram conversation service."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from business_service.conversation.config import TelegramEntryConfig
from business_service.conversation.context_factory import ConversationContext
from business_service.conversation.runtime_gateway import (
    AsyncAckReservation,
    AsyncResultHandleFactory,
    EnqueueFailedError,
    RuntimeDispatchOutcome,
    RuntimeGateway,
)
from foundational_service.persist.task_envelope import RetryState, TaskEnvelope
from project_utility.context import ContextBridge


@dataclass(slots=True)
class TaskDispatchResult:
    envelope: TaskEnvelope
    reservation: AsyncAckReservation
    wait_timeout: float
    outcome: Optional[RuntimeDispatchOutcome] = None
    duplicate: bool = False


class TaskEnqueueDispatchError(RuntimeError):
    def __init__(self, envelope: TaskEnvelope, error: Exception) -> None:
        super().__init__("task_enqueue_failed")
        self.envelope = envelope
        self.error = error


class TaskEnqueueService:
    """Builds envelopes, handles async dedupe, and dispatches to the runtime gateway."""

    def __init__(
        self,
        *,
        runtime_gateway: RuntimeGateway,
        async_handle_factory: Optional[AsyncResultHandleFactory],
        channel: str = "telegram",
    ) -> None:
        self._runtime_gateway = runtime_gateway
        self._async_handle_factory = async_handle_factory
        self._channel = channel

    async def dispatch(
        self,
        context: ConversationContext,
        *,
        workflow_id: Optional[str],
        workflow_status: str,
        pending_reason: Optional[str],
    ) -> TaskDispatchResult:
        envelope = self._build_task_envelope(
            context,
            workflow_id=workflow_id,
            workflow_status=workflow_status,
            pending_reason=pending_reason,
        )
        reservation = await self._reserve_async_task(context, envelope)
        wait_timeout = self._resolve_wait_timeout(context.entry_config, context.policy)
        if not reservation.is_new:
            return TaskDispatchResult(
                envelope=envelope,
                reservation=reservation,
                wait_timeout=wait_timeout,
                duplicate=True,
            )
        try:
            outcome = await self._runtime_gateway.dispatch(
                envelope=envelope,
                expects_result=bool(workflow_id),
                wait_for_result=context.entry_config.wait_for_result,
                wait_timeout=wait_timeout,
            )
        except EnqueueFailedError as exc:  # pragma: no cover - gateway errors handled upstream
            raise TaskEnqueueDispatchError(envelope, exc.error) from exc
        return TaskDispatchResult(
            envelope=envelope,
            reservation=reservation,
            wait_timeout=wait_timeout,
            outcome=outcome,
        )

    async def track_pending(self, context: ConversationContext, envelope: TaskEnvelope) -> None:
        factory = self._async_handle_factory
        if factory is None or context.chat_id is None:
            return
        await factory.track_pending(chat_id=context.chat_id, task_id=envelope.task_id)

    def _build_task_envelope(
        self,
        context: ConversationContext,
        *,
        workflow_id: Optional[str],
        workflow_status: str,
        pending_reason: Optional[str],
    ) -> TaskEnvelope:
        core_envelope = dict(context.core_envelope)
        metadata = dict(core_envelope.get("metadata") or {})
        chat_id = metadata.get("chat_id")
        if not chat_id:
            raise RuntimeError("chat_id_missing")

        telemetry = dict(context.telemetry)
        telemetry.setdefault("channel", self._channel)
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
        locale = self._determine_locale(context.policy, telemetry)
        if locale:
            payload_metadata.setdefault("locale", locale)

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
            "source": self._channel,
            "channelPayload": dict(context.channel_payload),
        }
        if pending_reason:
            payload["pendingReason"] = pending_reason
        idempotency_key = self._build_idempotency_key(
            channel=self._channel,
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
            "channel": self._channel,
        }
        if locale:
            task_context["locale"] = locale
        retry_max = int(context.policy.get("retry_max") or 3)
        retry_state = RetryState(count=0, max=retry_max)
        return TaskEnvelope.new(task_type="workflow.execute", payload=payload, context=task_context, retry=retry_state)

    async def _reserve_async_task(self, context: ConversationContext, envelope: TaskEnvelope) -> AsyncAckReservation:
        if context.entry_config.wait_for_result:
            return AsyncAckReservation(is_new=True, task_id=envelope.task_id)
        factory = self._async_handle_factory
        idempotency_key = str(envelope.context.get("idempotencyKey") or "")
        if not factory:
            return AsyncAckReservation(
                is_new=True,
                task_id=envelope.task_id,
                idempotency_key=idempotency_key or None,
            )
        return await factory.reserve(idempotency_key=idempotency_key or None, task_id=envelope.task_id)

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
    def _determine_locale(policy: Mapping[str, Any], telemetry: Mapping[str, Any]) -> Optional[str]:
        binding_snapshot = telemetry.get("binding")
        if isinstance(binding_snapshot, Mapping):
            locale = binding_snapshot.get("locale")
            if isinstance(locale, str) and locale.strip():
                return locale.strip().lower()
        localization = policy.get("localization")
        if isinstance(localization, Mapping):
            default_locale = localization.get("default_locale") or localization.get("defaultLocale")
            if isinstance(default_locale, str) and default_locale.strip():
                return default_locale.strip().lower()
        return None

    @staticmethod
    def _extract_message_id(update: Mapping[str, Any]) -> Optional[str]:
        message = update.get("message")
        if not isinstance(message, Mapping):
            return None
        message_id = message.get("message_id")
        if message_id is None:
            return None
        return str(message_id)


__all__ = ["TaskEnqueueService", "TaskDispatchResult", "TaskEnqueueDispatchError"]
