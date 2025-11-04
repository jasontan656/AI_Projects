"""Contract toolcall helpers for the Foundational Service Layer.

Provides Markdown escaping, webhook signature verification, layout guards,
knowledge-base snapshot helpers, and other shared functions used across the
Rise orchestration pipeline.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Optional, Sequence

import yaml

logger = logging.getLogger("rise.toolcalls")


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #


class LayoutMismatch(Exception):
    """Raised when the layout tree differs, enabling detailed reporting."""

    def __init__(
        self,
        diff: str,
        *,
        prompt_id: Optional[str] = None,
        prompt_variables: Optional[Mapping[str, Any]] = None,
        layout_report: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(diff or "layout mismatch")
        self.diff = diff
        self.prompt_id = prompt_id
        self.prompt_variables = dict(prompt_variables) if prompt_variables else None
        self.layout_report = dict(layout_report) if layout_report else None


class MemoryMissError(KeyError):
    """Raised when a requested MemorySnapshot slot is missing."""

    def __init__(self, slot: str) -> None:
        super().__init__(slot)
        self.slot = slot


# --------------------------------------------------------------------------- #
# Markdown / logging helpers
# --------------------------------------------------------------------------- #

_MDV2_SPECIALS = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")


def call_md_escape(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters with backslashes."""
    if not text:
        return ""
    return _MDV2_SPECIALS.sub(r"\\\1", text)


async def call_send_placeholder(bot: Any, chat_id: str, text: str) -> int:
    """Send a placeholder message and return the resulting message_id."""
    if not hasattr(bot, "send_message"):
        raise RuntimeError("bot 实例缺少 send_message 方法")
    message = await bot.send_message(chat_id=chat_id, text=text, parse_mode="MarkdownV2")
    message_id = getattr(message, "message_id", None)
    if message_id is None:
        raise RuntimeError("send_message 未返回 message_id")
    return int(message_id)


def call_prepare_logging(
    core_bundle: Mapping[str, Any],
    runtime_policy: Mapping[str, Any],
    telemetry: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Compose a structured logging payload for consistent output fields."""
    core_envelope = core_bundle.get("core_envelope", {})
    metadata = core_envelope.get("metadata", {})
    payload = core_envelope.get("payload", {})
    ext_flags = core_envelope.get("ext_flags", {})
    versioning = runtime_policy.get("versioning", {})
    tokens_budget = runtime_policy.get("tokens_budget") or runtime_policy.get("token_budget") or {}

    return {
        "request_id": telemetry.get("request_id"),
        "chat_id": metadata.get("chat_id"),
        "convo_id": metadata.get("convo_id"),
        "language": metadata.get("language"),
        "intent_hint": ext_flags.get("intent_hint"),
        "kb_scope": ext_flags.get("kb_scope"),
        "status_code": telemetry.get("status_code"),
        "error_hint": telemetry.get("error_hint"),
        "signature_status": telemetry.get("signature_status"),
        "prompt_version": versioning.get("prompt_version"),
        "doc_commit": versioning.get("doc_commit"),
        "tokens_budget": tokens_budget,
        "message_length": len(str(payload.get("user_message", ""))),
    }


def call_emit_schema_alert(error: str, channel: str) -> None:
    """Emit a schema alert log entry."""
    logger.warning("schema.alert", extra={"channel": channel, "error": error})


def call_validate_output(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate and normalise the agent output payload."""
    agent_output = payload.get("agent_output")
    if not isinstance(agent_output, Mapping):
        raise ValueError("agent_output 缺失或类型错误")

    chat_id = agent_output.get("chat_id")
    if chat_id is None:
        raise ValueError("agent_output.chat_id 缺失")
    text = agent_output.get("text", "")
    status_code = int(agent_output.get("status_code", 200))

    normalized = {
        "chat_id": chat_id,
        "text": str(text),
        "parse_mode": agent_output.get("parse_mode", "MarkdownV2"),
        "status_code": status_code,
        "error_hint": agent_output.get("error_hint", ""),
    }
    return {"agent_output": normalized}


def call_record_audit(entry: Mapping[str, Any]) -> None:
    """Record an audit event (currently logged, extendable later)."""
    logger.info("audit.record", extra=dict(entry))


def call_validate_telegram_adapter_contract(contract: Mapping[str, Any]) -> None:
    """Ensure the Telegram adapter contract carries the required fields."""
    if not isinstance(contract, Mapping):
        raise ValueError("adapter contract must be mapping")
    if "inbound" not in contract or "outbound" not in contract:
        raise ValueError("adapter contract missing inbound/outbound section")
    inbound = contract["inbound"]
    outbound = contract["outbound"]
    if not isinstance(inbound, Mapping):
        raise ValueError("inbound section must be mapping")
    if not isinstance(outbound, MutableMapping):
        raise ValueError("outbound section must be mutable mapping")
    if "chat_id" not in outbound:
        raise ValueError("outbound.chat_id missing")


def call_verify_signature(headers: Mapping[str, str], secret: str) -> bool:
    """Compare the webhook header token with the configured secret."""
    provided = (headers.get("X-Telegram-Bot-Api-Secret-Token") or "").strip()
    expected = (secret or "").strip()
    return bool(expected) and provided == expected


# --------------------------------------------------------------------------- #
# Memory snapshot helpers
# --------------------------------------------------------------------------- #


def call_mem_read(
    slot: str,
    selectors: Mapping[str, Any],
    *,
    snapshot: Mapping[str, Sequence[Mapping[str, Any]]],
) -> Mapping[str, Any]:
    """Read a slot from the snapshot and optionally filter by keywords."""
    records = snapshot.get(slot)
    if not records:
        raise MemoryMissError(slot)

    keywords: Iterable[str] = selectors.get("keywords") or selectors.get("terms") or []
    normalized_keywords = [str(term).lower() for term in keywords if term]

    def _match(record: Mapping[str, Any]) -> bool:
        if not normalized_keywords:
            return True
        content = str(record.get("content", "")).lower()
        return any(keyword in content for keyword in normalized_keywords)

    snippets = [dict(record) for record in records if isinstance(record, Mapping) and _match(record)]
    if not snippets:
        raise MemoryMissError(slot)
    return {"slot": slot, "snippets": snippets, "match_count": len(snippets)}


# --------------------------------------------------------------------------- #
# Selector and slot validation
# --------------------------------------------------------------------------- #


def call_validate_slot(slot: Mapping[str, Any]) -> None:
    """Validate that a slot definition carries required fields."""
    if not isinstance(slot, Mapping):
        raise ValueError("slot must be mapping")
    name = slot.get("slot")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("slot.slot 必须为非空字符串")
    slot_type = slot.get("type", "text")
    if slot_type not in {"text", "rich_text", "json"}:
        raise ValueError(f"unsupported slot.type: {slot_type}")
    content = slot.get("content")
    if content is None:
        raise ValueError("slot.content 缺失")


def call_match_selectors(core_envelope: Mapping[str, Any], selectors: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Match selectors to the user message and return simple scores."""
    if isinstance(core_envelope.get("payload"), Mapping):
        user_message = str(core_envelope["payload"].get("user_message", "")).lower()
    else:
        user_message = str(core_envelope.get("user_message", "")).lower()

    matched_slots: list[Mapping[str, Any]] = []
    scores: list[Mapping[str, Any]] = []

    for selector in selectors:
        if not isinstance(selector, Mapping):
            continue
        slot_name = selector.get("slot")
        if not slot_name:
            continue
        terms = selector.get("keywords") or selector.get("terms") or selector.get("values") or []
        if isinstance(terms, str):
            terms = [terms]
        normalized_terms = [str(term).lower() for term in terms if term]

        score = 0
        for term in normalized_terms:
            if term and term in user_message:
                score += 1

        regex_pattern = selector.get("regex")
        if isinstance(regex_pattern, str) and regex_pattern:
            try:
                if re.search(regex_pattern, user_message, re.IGNORECASE):
                    score += 1
            except re.error as exc:
                logger.debug("selector.regex.invalid", extra={"slot": slot_name, "error": str(exc)})

        if score > 0:
            matched_slots.append({"slot": slot_name, "score": score})
            scores.append({"slot": slot_name, "score": score, "terms": normalized_terms})

    return {"matched_slots": matched_slots, "scores": scores}


# --------------------------------------------------------------------------- #
# Layout guard / tree comparison
# --------------------------------------------------------------------------- #


def call_scan_tree(root: Path, depth: int = 2) -> str:
    """Generate a lightweight textual directory tree."""
    root = Path(root).resolve()
    lines = [f"{root.name}/"]
    entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    for index, path in enumerate(entries):
        prefix = "└── " if index == len(entries) - 1 else "├── "
        if path.is_dir() and depth > 1:
            lines.append(f"{prefix}{path.name}/")
            sub_entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            for sub_index, sub in enumerate(sub_entries):
                sub_prefix = "└── " if sub_index == len(sub_entries) - 1 else "├── "
                lines.append(f"    {sub_prefix}{sub.name}")
        else:
            lines.append(f"{prefix}{path.name}")
    return "\n".join(lines)


def call_compare_tree(expected: str, actual: str) -> str:
    """Return an explanation when layout trees do not match."""
    return "" if expected.strip() == actual.strip() else "layout tree mismatch"


# --------------------------------------------------------------------------- #
# Knowledge-base index loading (legacy behaviour)
# --------------------------------------------------------------------------- #


def call_load_org_index(path: str, loader: Optional[Callable[[str], Mapping[str, Any]]] = None) -> Mapping[str, Any]:
    if loader is not None:
        return loader(path)
    index_path = Path(path)
    if not index_path.exists():
        raise FileNotFoundError(path)
    data: Mapping[str, Any] = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    return data


def call_load_agency_index(path: str, loader: Optional[Callable[[str], Mapping[str, Any]]] = None) -> Mapping[str, Any]:
    if loader is not None:
        return loader(path)
    index_path = Path(path)
    if not index_path.exists():
        raise FileNotFoundError(path)
    data: Mapping[str, Any] = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    return data


def call_build_snapshot(org_index: Mapping[str, Any], agency_indexes: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
    digest = sha256(json.dumps(org_index, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    for key in sorted(agency_indexes):
        digest.update(json.dumps(agency_indexes[key], ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return {
        "org_metadata": org_index.get("org_metadata", {}),
        "routing_table": org_index.get("routing_table", []),
        "agencies": agency_indexes,
        "created_at": org_index.get("created_at", ""),
        "checksum": f"sha256::{digest.hexdigest()}",
    }


__all__ = [
    "LayoutMismatch",
    "MemoryMissError",
    "call_build_snapshot",
    "call_compare_tree",
    "call_emit_schema_alert",
    "call_load_agency_index",
    "call_load_org_index",
    "call_match_selectors",
    "call_md_escape",
    "call_mem_read",
    "call_prepare_logging",
    "call_record_audit",
    "call_send_placeholder",
    "call_validate_output",
    "call_validate_slot",
    "call_validate_telegram_adapter_contract",
    "call_verify_signature",
]
