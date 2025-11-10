"""
Minimal tracing helpers for Rise services.

Ported from `shared_utility.core.tracing` to keep instrumentation utilities within the project
utility layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict

from project_utility.telemetry import emit as telemetry_emit


@dataclass(slots=True)
class TraceSpan:
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    _start: float = field(init=False, default=0.0)

    async def __aenter__(self) -> "TraceSpan":
        self._start = perf_counter()
        telemetry_emit(
            "trace.start",
            level="debug",
            span=self.name,
            payload={"attributes": dict(self.attributes)},
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
            payload["error"] = str(exc)
        telemetry_emit("trace.end", level="debug", span=self.name, payload=payload, sensitive=["error"])
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


__all__ = ["TraceSpan", "trace_span"]
