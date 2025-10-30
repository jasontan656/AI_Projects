"""
Minimal tracing helpers for Kobe services.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, Optional

log = logging.getLogger("kobe.trace")


@dataclass(slots=True)
class TraceSpan:
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    _start: float = field(init=False, default=0.0)

    async def __aenter__(self) -> "TraceSpan":
        self._start = perf_counter()
        log.info(
            "trace.start",
            extra={
                "span": self.name,
                **self.attributes,
            },
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        duration_ms = round((perf_counter() - self._start) * 1000, 3)
        payload: Dict[str, Any] = {
            "span": self.name,
            "duration_ms": duration_ms,
            **self.attributes,
        }
        if exc is not None:
            payload.setdefault("error", str(exc))
        log.info("trace.end", extra=payload)
        return False

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value


def trace_span(name: str, **attributes: Any) -> TraceSpan:
    """
    Create an asynchronous trace span context manager.

    Usage:
        async with trace_span("telegram.webhook", request_id=req_id) as span:
            span.set_attribute("status_code", 200)
    """
    return TraceSpan(name=name, attributes=dict(attributes))

