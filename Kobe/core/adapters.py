"""
Core adapters bridging channel updates and CoreEnvelope.

The adapters expose functions used by contracts and runtime components to
construct, validate, and log CoreEnvelope instances aligned with
WorkPlan 13.
"""
from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from core.context import ContextBridge
from core.schema import CoreEnvelope, PayloadTooLarge, SchemaValidationError


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


def _to_iso_timestamp(raw: Optional[int]) -> Optional[str]:
    if raw is None:
        return None
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc).isoformat()
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
