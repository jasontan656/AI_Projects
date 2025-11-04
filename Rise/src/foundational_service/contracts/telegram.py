"""Telegram adapters bridging channel updates and core envelopes.

Ported from `shared_utility.core.adapters` to live inside the Foundational
Service Layer while maintaining backwards-compatible behaviour.
"""
from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from pydantic import ValidationError

from project_utility.context import ContextBridge
from project_utility.clock import philippine_from_timestamp
from foundational_service.contracts.envelope import (
    CoreEnvelope,
    PayloadTooLarge,
    SchemaValidationError,
)

__all__ = [
    "ChannelNotSupportedError",
    "build_core_schema",
    "call_validate_core_envelope",
    "call_normalize_context_quotes",
    "UnsupportedUpdateError",
    "behavior_core_envelope",
    "behavior_telegram_inbound",
    "behavior_telegram_outbound",
]


class UnsupportedUpdateError(Exception):
    def __init__(self, update_type: str) -> None:
        self.update_type = update_type
        super().__init__(f"unsupported update type: {update_type}")


class ChannelNotSupportedError(RuntimeError):
    """Raised when adapter for the given channel is not available."""


def build_core_schema(update: Dict[str, Any], channel: str) -> Dict[str, Any]:
    if channel != "telegram":
        raise ChannelNotSupportedError(channel)

    message = update.get("message") or update
    chat = message.get("chat", {})
    chat_id = str(chat.get("id") or "")
    if not chat_id:
        raise SchemaValidationError("missing chat_id")

    thread_id_raw = message.get("message_thread_id")
    if thread_id_raw is None:
        thread_id_raw = chat.get("thread_id")
    thread_id = str(thread_id_raw) if thread_id_raw is not None else chat_id
    is_private = chat.get("type") == "private"
    convo_id = chat_id if is_private else f"{chat_id}:{thread_id}"

    timestamp_iso = _to_iso_timestamp(message.get("date"))
    language = (
        message.get("from", {}).get("language_code")
        or chat.get("language_code")
        or update.get("language_code")
        or "zh-CN"
    )
    raw_user_message = message.get("text") or message.get("caption") or update.get("text", "")
    user_message = raw_user_message.strip()

    context_quotes, trimmed = _collect_context_quotes(message, update.get("context_quotes", []))
    attachments = _collect_attachments(message)

    ext_flags = dict(update.get("ext_flags", {}))
    ext_flags.setdefault(
        "reply_to_bot",
        bool(message.get("reply_to_message", {}).get("from", {}).get("is_bot")),
    )
    ext_flags.setdefault("intent_hint", update.get("intent_hint"))
    ext_flags.setdefault("kb_scope", update.get("kb_scope", ext_flags.get("kb_scope", [])))
    ext_flags.setdefault("safety_level", update.get("safety_level", "normal"))

    telemetry = dict(update.get("telemetry", {}))
    telemetry.setdefault("request_id", ContextBridge.request_id())
    telemetry.setdefault("prompt_version", update.get("prompt_version"))
    telemetry.setdefault("doc_commit", update.get("doc_commit"))
    telemetry.setdefault("stage", update.get("stage"))
    if trimmed:
        telemetry.setdefault("core_envelope_trim_total", trimmed)

    envelope = {
        "metadata": {
            "chat_id": chat_id,
            "convo_id": convo_id,
            "channel": "telegram",
            "language": language,
            "timestamp_iso": timestamp_iso,
            "thread_id": thread_id if not is_private else chat_id,
        },
        "payload": {
            "user_message": user_message,
            "context_quotes": context_quotes,
            "attachments": attachments,
            "system_tags": update.get("system_tags", []),
            "message_ts": timestamp_iso,
        },
        "ext_flags": ext_flags,
        "telemetry": telemetry,
        "version": update.get("version", "v1.0.0"),
    }

    model = call_validate_core_envelope(envelope, telemetry=telemetry)
    telemetry_payload = dict(model.telemetry_payload)
    telemetry_payload.setdefault("core_envelope_trim_total", model.trimmed_context_quote_count)
    telemetry_payload.setdefault("core_envelope_attachment_reject_total", 0)
    model.attach_telemetry(telemetry_payload)
    return {
        "core_envelope": model.model_dump(by_alias=True),
        "telemetry": model.telemetry_payload,
    }


def call_validate_core_envelope(
    payload: Dict[str, Any],
    *,
    telemetry: Optional[Dict[str, Any]] = None,
) -> CoreEnvelope:
    started = perf_counter()
    working_payload: Dict[str, Any] = dict(payload)
    if telemetry is not None:
        working_payload["_telemetry"] = dict(telemetry)
    try:
        model = CoreEnvelope.validate_payload(working_payload)
    except PayloadTooLarge:
        raise
    except SchemaValidationError:
        raise
    except ValidationError as exc:  # pragma: no cover - defensive guard
        raise SchemaValidationError(str(exc)) from exc

    telemetry_data = dict(model.telemetry_payload)
    telemetry_data.setdefault("validation_ms", round((perf_counter() - started) * 1000, 3))
    model.attach_telemetry(telemetry_data)
    return model


def call_normalize_context_quotes(quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    trimmed = quotes[-5:]
    normalized: List[Dict[str, Any]] = []
    for quote in trimmed:
        normalized.append(
            {
                "speaker": quote.get("speaker", "user"),
                "excerpt": quote.get("excerpt", ""),
                "role": quote.get("role", "user"),
                "timestamp_iso": quote.get("timestamp_iso") or quote.get("timestamp"),
            }
        )
    return normalized


def _extract_telegram_message(update: Mapping[str, Any]) -> Tuple[Optional[Mapping[str, Any]], str]:
    for key in ("message",):
        message_obj = update.get(key)
        if message_obj is None:
            continue
        if isinstance(message_obj, Mapping):
            return _prune_none_mapping(message_obj), key
        if hasattr(message_obj, "model_dump"):
            payload = getattr(message_obj, "model_dump")()
            if isinstance(payload, Mapping):
                return _prune_none_mapping(payload), key
    return None, "unknown"


def _compose_telegram_update(source: Mapping[str, Any], message_payload: Mapping[str, Any]) -> Dict[str, Any]:
    message_data = _prune_none_mapping(message_payload)
    reply_payload = message_data.get("reply_to_message")
    if reply_payload is None or not isinstance(reply_payload, Mapping):
        message_data.pop("reply_to_message", None)
    if "reply_to_message" not in message_data:
        message_data["reply_to_message"] = {}
    update_id = source.get("update_id")
    composed: Dict[str, Any] = {"message": message_data}
    if update_id is not None:
        composed["update_id"] = update_id
    return composed


def _prune_none_mapping(value: Mapping[str, Any]) -> Dict[str, Any]:
    pruned: Dict[str, Any] = {}
    for key, item in value.items():
        if item is None:
            continue
        if isinstance(item, Mapping):
            pruned[key] = _prune_none_mapping(item)
        elif isinstance(item, list):
            pruned_list = [
                _prune_none_mapping(elem) if isinstance(elem, Mapping) else elem
                for elem in item
                if elem is not None
            ]
            pruned[key] = pruned_list
        else:
            pruned[key] = item
    return pruned


def behavior_core_envelope(update: Mapping[str, Any], *, channel: str = "telegram") -> Dict[str, Any]:
    """Wrap `build_core_schema` with Telegram-specific normalization."""

    if channel != "telegram":
        return build_core_schema(dict(update), channel=channel)

    message_payload, update_type = _extract_telegram_message(update)
    if message_payload is None:
        raise UnsupportedUpdateError(update_type)
    normalized_update = _compose_telegram_update(update, message_payload)
    return build_core_schema(normalized_update, channel=channel)


def behavior_telegram_inbound(
    update: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    message, update_type = _extract_telegram_message(update)
    request_id = ContextBridge.request_id()

    telemetry = {
        "request_id": request_id,
        "update_type": update_type,
        "chat_id": message.get("chat", {}).get("id") if message else None,
    }

    if message is None:
        return {
            "response_status": "ignored",
            "telemetry": telemetry,
            "error_hint": "unsupported_update_type",
            "logging": {
                "event": "telegram.update.ignored",
                "reason": "unsupported_update_type",
            },
        }

    text = (message.get("text") or message.get("caption") or "").strip()
    if not text:
        return {
            "response_status": "ignored",
            "telemetry": telemetry,
            "error_hint": "empty_message",
            "logging": {
                "event": "telegram.update.ignored",
                "reason": "empty_message",
                "chat_id": message.get("chat", {}).get("id"),
            },
        }

    try:
        normalized_update = _compose_telegram_update(update, message)
        core_bundle = build_core_schema(normalized_update, channel="telegram")
    except SchemaValidationError as exc:
        return {
            "response_status": "ignored",
            "telemetry": telemetry,
            "error_hint": str(exc),
            "logging": {
                "event": "telegram.update.schema_violation",
                "error": str(exc),
                "chat_id": message.get("chat", {}).get("id"),
            },
            "prompt_id": "core_schema_violation",
            "prompt_variables": {"error": str(exc)},
        }

    core_envelope = dict(core_bundle.get("core_envelope", {}))
    telemetry.update(core_bundle.get("telemetry", {}))
    metadata = core_envelope.get("metadata", {})
    ext_flags = core_envelope.get("ext_flags", {})
    payload = core_envelope.get("payload", {})

    agent_request = {
        "prompt": payload.get("user_message", ""),
        "convo_id": metadata.get("convo_id", ""),
        "language": metadata.get("language", "zh-CN"),
        "intent_hint": ext_flags.get("intent_hint", ""),
        "kb_scope": ext_flags.get("kb_scope", []),
        "system_tags": payload.get("system_tags", []),
        "request_id": request_id,
        "tokens_usage": payload.get("token_usage"),
    }

    logging_payload = {
        "event": "telegram.update.accepted",
        "chat_id": metadata.get("chat_id"),
        "convo_id": agent_request.get("convo_id"),
        "intent_hint": agent_request.get("intent_hint"),
    }

    return {
        "response_status": "handled",
        "core_envelope": core_envelope,
        "envelope": core_envelope,
        "agent_request": agent_request,
        "telemetry": telemetry,
        "logging": logging_payload,
        "policy_snapshot": {"tokens_budget": policy.get("tokens_budget", {})},
    }


def behavior_telegram_outbound(chunks: Sequence[str], policy: Mapping[str, Any]) -> Dict[str, Any]:
    sanitized = [str(chunk).strip() for chunk in chunks if str(chunk).strip()]
    if not sanitized:
        sanitized = [""]
    total_chars = sum(len(chunk) for chunk in sanitized)
    chunk_metrics = [
        {"chunk_index": index, "char_count": len(chunk), "planned_delay_ms": 1500.0}
        for index, chunk in enumerate(sanitized)
    ]
    return {
        "text": "\n\n".join(sanitized),
        "chunks": sanitized,
        "placeholder": "处理中…",
        "edits": [],
        "metrics": {"chunk_metrics": chunk_metrics, "total_chars": total_chars},
    }


def _to_iso_timestamp(raw: Optional[int]) -> Optional[str]:
    if raw is None:
        return None
    try:
        return philippine_from_timestamp(int(raw)).isoformat()
    except (ValueError, OSError):  # pragma: no cover - invalid input
        return None


def _collect_context_quotes(
    message: Dict[str, Any],
    seed_quotes: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    quotes = list(seed_quotes)
    reply = message.get("reply_to_message")
    if reply:
        quotes.append(
            {
                "speaker": reply.get("from", {}).get("username")
                or reply.get("from", {}).get("first_name", "user"),
                "excerpt": reply.get("text") or reply.get("caption", ""),
                "role": "assistant" if reply.get("from", {}).get("is_bot") else "user",
                "timestamp_iso": _to_iso_timestamp(reply.get("date")),
            }
        )
    normalized = call_normalize_context_quotes(quotes)
    trimmed_count = max(0, len(quotes) - len(normalized))
    return normalized, trimmed_count


def _collect_attachments(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    attachments: List[Dict[str, Any]] = []
    if photos := message.get("photo"):
        photo = photos[-1]
        attachments.append(
            {
                "kind": "image",
                "source": photo.get("file_id", ""),
                "summary": message.get("caption", ""),
                "mime_size_bytes": photo.get("file_size"),
            }
        )
    if document := message.get("document"):
        attachment = {
            "kind": "file",
            "source": document.get("file_id", ""),
            "summary": document.get("file_name"),
            "mime_size_bytes": document.get("file_size"),
        }
        checksum = document.get("file_unique_id")
        if isinstance(checksum, str) and len(checksum) == 64 and all(ch in "0123456789abcdef" for ch in checksum.lower()):
            attachment["checksum_sha256"] = checksum
        attachments.append(attachment)
    if voice := message.get("voice"):
        attachments.append(
            {
                "kind": "voice",
                "source": voice.get("file_id", ""),
                "summary": message.get("text", ""),
                "mime_size_bytes": voice.get("file_size"),
            }
        )
    return attachments[:3]


def _extract_core_envelope(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if "core_envelope" in payload:
        core_envelope = dict(payload["core_envelope"])
        telemetry = dict(payload.get("telemetry", {}))
    else:
        core_envelope = dict(payload)
        telemetry = dict(payload.get("telemetry", {})) if isinstance(payload.get("telemetry"), dict) else {}
    return core_envelope, telemetry


def core_to_agent_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    envelope, telemetry = _extract_core_envelope(payload)
    model = call_validate_core_envelope(envelope, telemetry=telemetry or None)
    return model.to_agent_request()


def to_logging_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    envelope, telemetry = _extract_core_envelope(payload)
    model = call_validate_core_envelope(envelope, telemetry=telemetry or None)
    return model.to_logging_dict()


__all__ = [
    "ChannelNotSupportedError",
    "build_core_schema",
    "call_normalize_context_quotes",
    "call_validate_core_envelope",
    "core_to_agent_request",
    "to_logging_dict",
]

