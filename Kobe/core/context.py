"""
Context utilities for Kobe runtime.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass
from typing import Optional


_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


@dataclass(slots=True)
class ContextBridge:
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

