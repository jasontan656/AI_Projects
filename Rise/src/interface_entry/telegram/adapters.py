"""
Telegram inbound adapter that normalises updates into the contract expected by WorkPlan/15.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from foundational_service.contracts.telegram import build_core_schema, core_to_agent_request

ADAPTER_VERSION = "v1.1.0"


def _extract_text(update: Dict[str, Any]) -> str:
    message = update.get("message") or update
    text = message.get("text") or message.get("caption") or update.get("text") or ""
    return text


def _extract_language(update: Dict[str, Any], core_envelope: Dict[str, Any]) -> Optional[str]:
    message = update.get("message") or update
    metadata = core_envelope.get("metadata", {})
    language = (
        message.get("from", {}).get("language_code")
        or message.get("chat", {}).get("language_code")
        or update.get("language_code")
        or metadata.get("language")
    )
    return language


def _extract_reply_to_bot(update: Dict[str, Any]) -> bool:
    container = update.get("message") or update
    reply = container.get("reply_to_message") or {}
    from_user = reply.get("from", {})
    return bool(from_user.get("is_bot"))


def _extract_thread_id(update: Dict[str, Any], core_envelope: Dict[str, Any]) -> Optional[int]:
    message = update.get("message") or update
    metadata = core_envelope.get("metadata", {})
    thread_id = message.get("message_thread_id")
    if thread_id is None:
        thread_id = metadata.get("thread_id")
    try:
        return int(thread_id) if thread_id is not None else None
    except (TypeError, ValueError):
        return None


def _build_inbound(update: Dict[str, Any], core_envelope: Dict[str, Any]) -> Dict[str, Any]:
    message = update.get("message") or update
    chat = message.get("chat") or update.get("chat") or {}
    inbound: Dict[str, Any] = {
        "message_id": int(message.get("message_id", 0)),
        "chat_id": int(chat.get("id", 0)),
        "text": _extract_text(update),
        "reply_to_bot": _extract_reply_to_bot(update),
    }
    thread_id = _extract_thread_id(update, core_envelope)
    if thread_id is not None:
        inbound["thread_id"] = thread_id
    language = _extract_language(update, core_envelope)
    if language:
        inbound["language_code"] = language
    reply_to_message = message.get("reply_to_message")
    if reply_to_message and reply_to_message.get("message_id"):
        inbound["reply_to_message_id"] = int(reply_to_message["message_id"])
    return inbound


def _build_agent_bridge(agent_request: Dict[str, Any]) -> Dict[str, Any]:
    agent_bridge: Dict[str, Any] = {
        "prompt": agent_request.get("prompt", ""),
        "convo_id": agent_request.get("convo_id", ""),
        "language": agent_request.get("language", ""),
    }
    if agent_request.get("intent_hint"):
        agent_bridge["intent_hint"] = agent_request["intent_hint"]
    if agent_request.get("tokens_budget"):
        agent_bridge["tokens_budget"] = dict(agent_request["tokens_budget"])
    if agent_request.get("tokens_usage") is not None:
        agent_bridge["tokens_usage"] = int(agent_request["tokens_usage"])
    if agent_request.get("tokens_usage_threshold") is not None:
        agent_bridge["tokens_usage_threshold"] = int(agent_request["tokens_usage_threshold"])
    return agent_bridge


def _build_outbound(core_envelope: Dict[str, Any]) -> Dict[str, Any]:
    metadata = core_envelope.get("metadata", {})
    chat_id = metadata.get("chat_id")
    outbound: Dict[str, Any] = {
        "chat_id": int(chat_id) if chat_id else 0,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
        "streaming_buffer": [],
    }
    return outbound


def telegram_update_to_core(
    update: Dict[str, Any],
    *,
    core_bundle: Optional[Dict[str, Any]] = None,
    agent_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Normalise a Telegram update into the adapter contract sections.

    If core_bundle/agent_request are not provided they will be derived via core adapters.
    """
    core_bundle = core_bundle or build_core_schema(update, channel="telegram")
    core_envelope = dict(core_bundle.get("core_envelope", {}))
    agent_request = agent_request or core_to_agent_request(core_bundle)

    return {
        "adapter_version": ADAPTER_VERSION,
        "inbound": _build_inbound(update, core_envelope),
        "agent_bridge": _build_agent_bridge(agent_request),
        "outbound": _build_outbound(core_envelope),
    }


def append_streaming_buffer(contract: Dict[str, Any], buffer: Iterable[Dict[str, Any]]) -> None:
    """
    Populate streaming_buffer with chunk metadata.
    """
    streaming = []
    for item in buffer:
        streaming.append(
            {
                "chunk_index": int(item.get("chunk_index", 0)),
                "char_count": int(item.get("char_count", 0)),
                "planned_delay_ms": float(item.get("planned_delay_ms", 0.0)),
            }
        )
    contract.setdefault("outbound", {})["streaming_buffer"] = streaming


__all__ = ["telegram_update_to_core", "append_streaming_buffer"]


