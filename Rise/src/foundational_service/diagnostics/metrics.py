"""Telemetry metrics helpers for foundational bootstrap flows."""

from __future__ import annotations

from typing import TypedDict

__all__ = ["MetricsSnapshot", "default_metrics_state"]


class MetricsSnapshot(TypedDict, total=False):
    telegram_updates_total: int
    telegram_inbound_total: int
    telegram_ignored_total: int
    telegram_streaming_failures: int
    telegram_placeholder_latency_sum: float
    telegram_placeholder_latency_count: int
    webhook_signature_failures: int
    webhook_rtt_ms_sum: float
    webhook_rtt_ms_count: int
    last_webhook_latency_ms: float


def default_metrics_state() -> MetricsSnapshot:
    """Return a fresh metrics snapshot with zeroed counters."""

    return MetricsSnapshot(
        telegram_updates_total=0,
        telegram_inbound_total=0,
        telegram_ignored_total=0,
        telegram_streaming_failures=0,
        telegram_placeholder_latency_sum=0.0,
        telegram_placeholder_latency_count=0,
        webhook_signature_failures=0,
        webhook_rtt_ms_sum=0.0,
        webhook_rtt_ms_count=0,
        last_webhook_latency_ms=0.0,
    )
