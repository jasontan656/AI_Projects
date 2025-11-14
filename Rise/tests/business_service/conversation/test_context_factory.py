from __future__ import annotations

from typing import Any, Dict

from business_service.conversation.context_factory import ConversationContextFactory


def _build_policy(tokens_budget: Dict[str, Any] | None = None) -> Dict[str, Any]:
    policy: Dict[str, Any] = {}
    if tokens_budget:
        policy["tokens_budget"] = tokens_budget
    return policy


def test_context_factory_builds_complete_context() -> None:
    factory = ConversationContextFactory()
    update = {"message": {"chat": {"id": 42}, "text": "hello world"}}
    policy = _build_policy({"per_call_max_tokens": 111, "per_flow_max_tokens": 222})
    inbound = {
        "core_envelope": {
            "payload": {
                "context_quotes": [{"excerpt": "之前的上下文"}],
                "user_message": "hello world",
            },
            "metadata": {"chat_id": 42},
        },
        "envelope": {"legacy": True},
        "logging": {"correlation": "abc"},
        "telemetry": {"update_type": "message"},
    }
    telemetry = dict(inbound["telemetry"])

    context = factory.build(update, policy, inbound, "req-123", telemetry)

    assert context.chat_id == "42"
    assert context.user_text == "hello world"
    assert context.history_chunks == ("之前的上下文",)
    assert context.logging_payload == {"correlation": "abc"}
    assert context.telemetry is telemetry
    assert context.channel_payload["version"] == "telegram.v1"
    assert context.raw_payload_meta["raw_truncated"] is False


def test_context_factory_honors_payload_limit() -> None:
    factory = ConversationContextFactory(payload_limit_bytes=8)
    update = {"message": {"text": "x" * 32}}
    inbound = {"core_envelope": {"payload": {}, "metadata": {}}, "logging": {}, "telemetry": {}}
    telemetry: Dict[str, Any] = {}

    context = factory.build(update, {}, inbound, "rid", telemetry)

    assert context.channel_payload["rawTruncated"] is True
    assert context.channel_payload["raw"] is None
    assert context.raw_payload_meta["raw_truncated"] is True
