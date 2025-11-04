"""
Context utilities for request-id propagation across async boundaries.

Migrated from the legacy `shared_utility.core.context` module to provide a stable surface in the
project utility layer.
"""

from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass
from typing import Optional

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


@dataclass(slots=True)
class ContextBridge:
    """ContextVar-backed helper that guarantees a request identifier is always available."""

    @staticmethod
    def request_id() -> str:
        rid = _request_id.get()
        if not rid:
            rid = ContextBridge.set_request_id()
        return rid

    @staticmethod
    def set_request_id(value: Optional[str] = None) -> str:
        rid = value or uuid.uuid4().hex
        _request_id.set(rid)
        return rid

    @staticmethod
    def clear() -> None:
        _request_id.set("")


__all__ = ["ContextBridge"]
