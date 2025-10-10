from __future__ import annotations

from prometheus_client import Counter, Histogram


chat_requests = Counter(
    "hub_chat_calls_total",
    "Total number of /chat calls",
    labelnames=("module", "stream"),
)

chat_latency = Histogram(
    "hub_chat_latency_seconds",
    "Latency for /chat handling",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

llm_tokens_streamed = Counter(
    "hub_llm_tokens_streamed_total",
    "Tokens streamed over SSE",
)


__all__ = ["chat_requests", "chat_latency", "llm_tokens_streamed"]
