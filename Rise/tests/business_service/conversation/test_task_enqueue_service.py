from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping, Optional

import pytest

from business_service.conversation.config import TelegramEntryConfig, TelegramRuntimeMode
from business_service.conversation.context_factory import ConversationContext
from business_service.conversation.runtime_gateway import AsyncAckReservation, RuntimeDispatchOutcome
from business_service.conversation.task_enqueue_service import TaskEnqueueService


@dataclass(slots=True)
class _StubGateway:
    outcome: RuntimeDispatchOutcome
    calls: list[Mapping[str, Any]]

    def __init__(self, outcome: RuntimeDispatchOutcome) -> None:
        self.outcome = outcome
        self.calls = []

    async def dispatch(
        self,
        *,
        envelope,
        expects_result: bool,
        wait_for_result: bool,
        wait_timeout: Optional[float],
    ) -> RuntimeDispatchOutcome:
        self.calls.append(
            {
                "expects_result": expects_result,
                "wait_for_result": wait_for_result,
                "wait_timeout": wait_timeout,
                "task_id": envelope.task_id,
            }
        )
        return self.outcome


class _DuplicateFactory:
    async def reserve(self, *, idempotency_key: Optional[str], task_id: str) -> AsyncAckReservation:
        return AsyncAckReservation(
            is_new=False,
            task_id="dupe-task",
            idempotency_key=idempotency_key,
            duplicate=True,
        )


def _build_context(
    locale: Optional[str] = "en",
    policy: Optional[Mapping[str, Any]] = None,
    entry_config: Optional[TelegramEntryConfig] = None,
) -> ConversationContext:
    telemetry = {}
    if locale:
        telemetry["binding"] = {"locale": locale}
    return ConversationContext(
        update={},
        policy=policy or {"wait_timeout_seconds": 15},
        request_id="req-123",
        inbound={"metadata": {}},
        core_envelope={"metadata": {"chat_id": "5112"}},
        legacy_envelope={},
        logging_payload={},
        telemetry=telemetry,
        user_text="hello",
        history_chunks=(),
        tokens_budget={},
        entry_config=entry_config or TelegramEntryConfig(),
        channel_payload={},
        raw_payload_meta={},
        chat_id="5112",
    )


@pytest.mark.asyncio
async def test_task_enqueue_includes_locale_metadata() -> None:
    gateway = _StubGateway(RuntimeDispatchOutcome(envelope=None, status="pending"))
    service = TaskEnqueueService(runtime_gateway=gateway, async_handle_factory=None)
    context = _build_context()

    result = await service.dispatch(
        context,
        workflow_id="wf-locale",
        workflow_status="ready",
        pending_reason=None,
    )

    assert result.wait_timeout == 15
    assert result.envelope.payload["metadata"]["locale"] == "en"
    assert result.envelope.context["locale"] == "en"
    assert result.envelope.context["channel"] == "telegram"
    assert gateway.calls[0]["wait_timeout"] == 15


@pytest.mark.asyncio
async def test_task_enqueue_duplicate_short_circuits_dispatch() -> None:
    gateway = _StubGateway(RuntimeDispatchOutcome(envelope=None, status="pending"))
    factory = _DuplicateFactory()
    service = TaskEnqueueService(runtime_gateway=gateway, async_handle_factory=factory)
    context = _build_context(
        policy={},
        entry_config=TelegramEntryConfig(mode=TelegramRuntimeMode.ASYNC),
    )

    result = await service.dispatch(
        context,
        workflow_id="wf-duplicate",
        workflow_status="ready",
        pending_reason=None,
    )

    assert result.duplicate is True
    assert result.outcome is None
    assert gateway.calls == []
