from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

import pytest

from business_service.conversation.config import TelegramEntryConfig
from business_service.conversation.context_factory import ConversationContext
from business_service.conversation.primitives import AdapterBuilder
from business_service.conversation.response_builder import ResponseBuilder
from foundational_service.persist.task_envelope import TaskEnvelope


class _StubAdapterBuilder(AdapterBuilder):
    def build_contract(
        self,
        update: Mapping[str, Any],
        *,
        core_bundle: Mapping[str, Any],
        agent_request: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:
        chat_id = core_bundle.get("core_envelope", {}).get("metadata", {}).get("chat_id", "c1")
        return {"inbound": {"reply_to_message_id": None}, "outbound": {"chat_id": chat_id}}

    def finalize_contract(
        self,
        contract: MutableMapping[str, Any],
        *,
        chunk_metrics,
        response_text: str,
        streaming_mode: str,
    ) -> MutableMapping[str, Any]:
        outbound = contract["outbound"]
        outbound["text"] = response_text
        outbound["stream"] = streaming_mode
        return outbound


def _context_with_locale(locale: str, localization: Mapping[str, Any]) -> ConversationContext:
    return ConversationContext(
        update={},
        policy={"localization": localization},
        request_id="req-localized",
        inbound={"telemetry": {}, "metadata": {}},
        core_envelope={"metadata": {"chat_id": "c1"}},
        legacy_envelope={},
        logging_payload={},
        telemetry={"binding": {"locale": locale}},
        user_text="hi",
        history_chunks=(),
        tokens_budget={},
        entry_config=TelegramEntryConfig(),
        channel_payload={},
        raw_payload_meta={},
        chat_id="c1",
    )


def _new_envelope() -> TaskEnvelope:
    return TaskEnvelope.new(task_type="workflow.execute", payload={"workflowId": "wf"}, context={"idempotencyKey": "idem"})


def _noop_health(*args: Any, **kwargs: Any) -> None:
    return None


def test_async_ack_uses_localized_template() -> None:
    localization = {
        "ack": {
            "en": "Hello {task_id}",
            "zh": "你好 {task_id}",
        },
        "default_locale": "zh",
    }
    context = _context_with_locale("en", localization)
    builder = ResponseBuilder(adapter_builder=_StubAdapterBuilder(), schedule_health_error=_noop_health)
    envelope = _new_envelope()

    result = builder.async_ack(context, envelope, handle=None, template_key="ack")

    assert "Hello" in result.agent_response["text"]
    assert result.agent_response["text"].endswith(envelope.task_id)


def test_degraded_ack_allows_custom_template() -> None:
    localization = {
        "degraded": {"en": "Delayed {task_id}"},
        "ack": {"en": "Queue {task_id}"},
        "default_locale": "en",
    }
    context = _context_with_locale("en", localization)
    builder = ResponseBuilder(adapter_builder=_StubAdapterBuilder(), schedule_health_error=_noop_health)
    envelope = _new_envelope()

    result = builder.async_ack(
        context,
        envelope,
        handle=None,
        template_key="degraded",
        fallback_text="Fallback {task_id}",
    )

    assert result.agent_response["text"].startswith("Delayed")
