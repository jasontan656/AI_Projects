from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Optional, Sequence, Tuple

from business_service.conversation.config import TelegramEntryConfig, resolve_entry_config

RAW_PAYLOAD_LIMIT_BYTES = int(os.getenv("TELEGRAM_RAW_PAYLOAD_MAX_BYTES", "262144"))


@dataclass(slots=True)
class ConversationContext:
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


class ConversationContextFactory:
    """Builds ConversationContext instances from inbound Telegram payloads."""

    def __init__(self, *, payload_limit_bytes: Optional[int] = None) -> None:
        self.payload_limit_bytes = payload_limit_bytes or RAW_PAYLOAD_LIMIT_BYTES

    def build(
        self,
        update: Mapping[str, Any],
        policy: Mapping[str, Any],
        inbound: Mapping[str, Any],
        request_id: str,
        telemetry: MutableMapping[str, Any],
    ) -> ConversationContext:
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

        return ConversationContext(
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

    def _build_channel_payload(self, update: Mapping[str, Any]) -> Tuple[Mapping[str, Any], Mapping[str, Any]]:
        serialized = json.dumps(update, ensure_ascii=False, separators=(",", ":"))
        encoded = serialized.encode("utf-8")
        size = len(encoded)
        truncated = size > self.payload_limit_bytes
        payload: dict[str, Any] = {
            "version": "telegram.v1",
            "rawSizeBytes": size,
            "rawTruncated": truncated,
        }
        if truncated:
            payload["raw"] = None
            payload["rawPreview"] = serialized[: self.payload_limit_bytes]
        else:
            payload["raw"] = json.loads(serialized)
        meta = {"raw_size_bytes": size, "raw_truncated": truncated}
        return payload, meta


__all__ = ["ConversationContext", "ConversationContextFactory"]
