from __future__ import annotations

"""Telegram conversation entry configuration helpers."""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional

from business_service.channel.models import (
    DEFAULT_TIMEOUT_MESSAGE,
    DEFAULT_WORKFLOW_MISSING_MESSAGE,
    WorkflowChannelPolicy,
)

__all__ = [
    "TelegramRuntimeMode",
    "TelegramEntryConfig",
    "load_default_entry_config",
    "resolve_entry_config",
]

DEFAULT_ASYNC_ACK_TEXT = (
    "We received your request and placed it in queue. Task ID: {task_id}. "
    "Natanggap namin ang iyong request at nasa pila na ito. Task ID: {task_id}."
)
DEFAULT_ENQUEUE_FAILURE_TEXT = (
    "The service is busy. Please try again shortly. "
    "Abala ang serbisyo ngayon; pakiulit maya-maya. Task ID: {task_id}."
)
DEFAULT_ASYNC_FAILURE_TEXT = (
    "Processing encountered an issue. We will retry and notify you shortly. Task ID: {task_id}. "
    "Nagka-aberya sa pagproseso. Susubukan naming muli at ipapaalam sa iyo. Task ID: {task_id}."
)
DEFAULT_DEGRADED_TEXT = (
    "Channel switched to async due to load. Expect a delayed reply. "
    "Lumipat sa async mode ang channel dahil sa dami ng request; mangyaring maghintay."
)
DEFAULT_MANUAL_REVIEW_TEXT = (
    "Expect manual review before completion. "
    "Dadaan muna sa manwal na pagsusuri bago matapos."
)


class TelegramRuntimeMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"


@dataclass(slots=True)
class TelegramEntryConfig:
    mode: TelegramRuntimeMode = TelegramRuntimeMode.SYNC
    async_ack_text: str = DEFAULT_ASYNC_ACK_TEXT
    enqueue_failure_text: str = DEFAULT_ENQUEUE_FAILURE_TEXT
    workflow_missing_text: str = DEFAULT_WORKFLOW_MISSING_MESSAGE
    async_failure_text: str = DEFAULT_ASYNC_FAILURE_TEXT
    degraded_text: str = DEFAULT_DEGRADED_TEXT
    manual_review_text: str = DEFAULT_MANUAL_REVIEW_TEXT
    wait_timeout_seconds: Optional[float] = None
    manual_guard: bool = False

    @property
    def wait_for_result(self) -> bool:
        return self.mode == TelegramRuntimeMode.SYNC


def load_default_entry_config() -> TelegramEntryConfig:
    """Load defaults from environment to allow operator override."""

    env_mode = os.getenv("TELEGRAM_RUNTIME_MODE", TelegramRuntimeMode.SYNC.value).strip().lower()
    mode = TelegramRuntimeMode.SYNC if env_mode != TelegramRuntimeMode.ASYNC.value else TelegramRuntimeMode.ASYNC
    wait_timeout = _coerce_float(os.getenv("TELEGRAM_WAIT_TIMEOUT_SECONDS"))
    return TelegramEntryConfig(
        mode=mode,
        async_ack_text=os.getenv("TELEGRAM_ASYNC_ACK_TEXT", DEFAULT_ASYNC_ACK_TEXT),
        enqueue_failure_text=os.getenv("TELEGRAM_ENQUEUE_FAILURE_TEXT", DEFAULT_ENQUEUE_FAILURE_TEXT),
        workflow_missing_text=os.getenv("TELEGRAM_WORKFLOW_MISSING_TEXT", DEFAULT_WORKFLOW_MISSING_MESSAGE),
        async_failure_text=os.getenv("TELEGRAM_ASYNC_FAILURE_TEXT", DEFAULT_ASYNC_FAILURE_TEXT),
        degraded_text=os.getenv("TELEGRAM_DEGRADED_TEXT", DEFAULT_DEGRADED_TEXT),
        manual_review_text=os.getenv("TELEGRAM_MANUAL_REVIEW_TEXT", DEFAULT_MANUAL_REVIEW_TEXT),
        wait_timeout_seconds=wait_timeout,
    )


def resolve_entry_config(
    policy: Mapping[str, Any],
    *,
    binding_policy: Optional[WorkflowChannelPolicy] = None,
    defaults: Optional[TelegramEntryConfig] = None,
) -> TelegramEntryConfig:
    """Merge policy entrypoints + binding overrides into a resolved config."""

    base = defaults or load_default_entry_config()
    entry = _extract_entry(policy)
    metadata = binding_policy.metadata if binding_policy and isinstance(binding_policy.metadata, Mapping) else {}

    manual_guard = _coerce_bool(
        entry.get("manual_guard"),
        _coerce_bool(metadata.get("manual_guard"), base.manual_guard),
    )
    wait_timeout = _coerce_float(entry.get("wait_timeout_seconds"))
    if wait_timeout is None:
        wait_timeout = base.wait_timeout_seconds

    mode = _resolve_mode(entry, binding_policy, base.mode)

    async_ack_text = _coerce_text(entry.get("async_ack_text"), base.async_ack_text)
    async_ack_text = _coerce_text(metadata.get("async_ack_text"), async_ack_text)

    enqueue_failure_text = _coerce_text(entry.get("enqueue_failure_text"), base.enqueue_failure_text)
    enqueue_failure_text = _coerce_text(metadata.get("enqueue_failure_text"), enqueue_failure_text)

    workflow_missing_text = _coerce_text(
        entry.get("workflow_missing_text"),
        base.workflow_missing_text,
    )
    if binding_policy:
        workflow_missing_text = _coerce_text(binding_policy.workflow_missing_message, workflow_missing_text)

    async_failure_text = _coerce_text(entry.get("async_failure_text"), base.async_failure_text)
    if binding_policy:
        async_failure_text = _coerce_text(binding_policy.timeout_message, async_failure_text)

    degraded_text = _coerce_text(entry.get("degraded_text"), base.degraded_text)
    degraded_text = _coerce_text(metadata.get("degraded_text"), degraded_text)

    manual_review_text = _coerce_text(entry.get("manual_review_text"), base.manual_review_text)

    return TelegramEntryConfig(
        mode=mode,
        async_ack_text=async_ack_text,
        enqueue_failure_text=enqueue_failure_text,
        workflow_missing_text=workflow_missing_text,
        async_failure_text=async_failure_text,
        degraded_text=degraded_text,
        manual_review_text=manual_review_text,
        wait_timeout_seconds=wait_timeout,
        manual_guard=manual_guard,
    )


def _resolve_mode(
    entry: Mapping[str, Any],
    binding_policy: Optional[WorkflowChannelPolicy],
    fallback: TelegramRuntimeMode,
) -> TelegramRuntimeMode:
    explicit_mode = entry.get("mode")
    if isinstance(explicit_mode, str):
        coerced = explicit_mode.strip().lower()
        if coerced == TelegramRuntimeMode.ASYNC.value:
            return TelegramRuntimeMode.ASYNC
        if coerced == TelegramRuntimeMode.SYNC.value:
            return TelegramRuntimeMode.SYNC
    if "wait_for_result" in entry:
        return TelegramRuntimeMode.SYNC if _coerce_bool(entry.get("wait_for_result"), True) else TelegramRuntimeMode.ASYNC
    if binding_policy is not None:
        return TelegramRuntimeMode.SYNC if binding_policy.wait_for_result else TelegramRuntimeMode.ASYNC
    return fallback


def _extract_entry(policy: Mapping[str, Any]) -> Mapping[str, Any]:
    entrypoints = policy.get("entrypoints")
    if isinstance(entrypoints, Mapping):
        telegram_entry = entrypoints.get("telegram")
        if isinstance(telegram_entry, Mapping):
            return telegram_entry
    return {}


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"false", "0", "off", "no"}:
            return False
        if lowered in {"true", "1", "on", "yes"}:
            return True
    if value is None:
        return default
    return bool(value)


def _coerce_text(value: Any, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return default


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
