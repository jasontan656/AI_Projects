from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace


tracer = trace.get_tracer(__name__)


@contextmanager
def span(name: str) -> Iterator[None]:
    with tracer.start_as_current_span(name):
        yield


__all__ = ["span", "tracer"]

