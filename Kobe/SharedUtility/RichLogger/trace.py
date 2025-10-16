from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Mapping
from contextvars import ContextVar

from .logger import RichLoggerManager


_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def ensure_trace_id(existing: str | None = None) -> str:
    """Return existing trace id or generate a new one and store in contextvar."""
    trace_id = existing or _trace_id_var.get() or uuid.uuid4().hex
    _trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> str | None:
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    _trace_id_var.set(trace_id)


class LoggingProgressReporter:
    """Structured progress reporter that writes to project logger with a trace id."""

    def __init__(self, node_name: str, level: int = logging.DEBUG) -> None:
        self.logger = RichLoggerManager.for_node(node_name, level=level)
        self.node_name = node_name

    def _log(self, event: str, payload: Mapping[str, Any] | None = None, level: int = logging.DEBUG) -> None:
        data = {
            "trace_id": get_trace_id(),
            "event": event,
            "node": self.node_name,
        }
        if payload:
            data.update(payload)
        message = json.dumps(data, ensure_ascii=False)
        if level >= logging.ERROR:
            self.logger.error(message)
        elif level >= logging.INFO:
            self.logger.info(message)
        else:
            self.logger.debug(message)

    # High-level helpers
    def on_request_start(self, method: str, path: str) -> None:
        self._log("request.start", {"method": method, "path": path})

    def on_request_end(self, method: str, path: str, status: int) -> None:
        self._log("request.end", {"method": method, "path": path, "status": status})

    def on_agent_start(self, user_input: str) -> None:
        self._log("agent.start", {"input_preview": user_input[:120]})

    def on_agent_end(self, tool_calls: int, total_tokens: int) -> None:
        self._log("agent.end", {"tool_calls": tool_calls, "total_tokens": total_tokens})

    def on_llm_tokens(self, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
        self._log(
            "llm.usage",
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
        )

    def on_tool_start(self, name: str, args: Mapping[str, Any]) -> None:
        self._log("tool.start", {"name": name, "args_preview": str(args)[:200]})

    def on_tool_end(self, name: str, output_size: int) -> None:
        self._log("tool.end", {"name": name, "output_size": output_size})

    def on_error(self, error: str) -> None:
        self._log("error", {"error": error}, level=logging.ERROR)


def get_progress_reporter(node_name: str, level: int = logging.DEBUG) -> LoggingProgressReporter:
    return LoggingProgressReporter(node_name=node_name, level=level)


