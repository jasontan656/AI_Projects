from __future__ import annotations

"""Telemetry emitter built on top of structlog + Rich/JSONL sinks."""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence

try:
    from rich.console import Console  # type: ignore[import]
    from rich.table import Table  # type: ignore[import]
    from rich.text import Text  # type: ignore[import]
except ImportError:  # pragma: no cover
    Console = None  # type: ignore[assignment]
    Table = None  # type: ignore[assignment]
    Text = None  # type: ignore[assignment]

try:
    import structlog
except ImportError:  # pragma: no cover
    structlog = None  # type: ignore[assignment]

from project_utility.config.paths import get_log_root

_CONSOLE_LEVEL = os.getenv("TELEMETRY_CONSOLE_LEVEL", "info").lower()
_FILE_LEVEL = os.getenv("TELEMETRY_FILE_LEVEL", "debug").lower()
_LEVEL_ORDER = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}
_EVENT_FILTERS = tuple(filter(None, (os.getenv("TELEMETRY_EVENT_FILTER") or "").split(",")))
_LISTENER_LOCK = threading.Lock()
_LISTENERS: list[Callable[[Mapping[str, Any]], None]] = []


def _should_emit(level: str, threshold: str) -> bool:
    return _LEVEL_ORDER.get(level, 20) >= _LEVEL_ORDER.get(threshold, 20)


def _passes_filter(event_type: str) -> bool:
    if not _EVENT_FILTERS:
        return True
    return any(event_type.startswith(filter_value.strip()) for filter_value in _EVENT_FILTERS)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview_text(value: str, *, length: int = 200) -> str:
    if len(value) <= length:
        return value
    return value[: length - 3] + "..."


class _JsonlSink:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: Mapping[str, Any]) -> None:
        payload = json.dumps(event, ensure_ascii=False)
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(payload + "\n")


class _ConsoleSink:
    def __init__(self) -> None:
        self._console: Optional[Console] = Console() if Console is not None else None

    def write(self, event: Mapping[str, Any]) -> None:
        if self._console is None or Table is None or Text is None:  # pragma: no cover
            print(self._format_plain(event))
            return
        table = Table.grid(padding=(0, 1))
        level = event.get("level", "info").upper()
        style = {
            "DEBUG": "dim",
            "INFO": "bold cyan",
            "WARNING": "yellow",
            "ERROR": "bold red",
            "CRITICAL": "bold white on red",
        }.get(level, "white")
        header = Text(f"[{level}] {event.get('event_type')}", style=style)
        table.add_row(header, Text(event.get("timestamp", ""), style="dim"))
        summary = []
        for key in ("request_id", "workflow_id", "stage", "span_id"):
            if event.get(key):
                summary.append(f"{key}={event[key]}")
        payload = event.get("payload") or {}
        if payload.get("latency_ms") is not None:
            summary.append(f"latency={payload['latency_ms']}ms")
        if payload.get("status_code") is not None:
            summary.append(f"status={payload['status_code']}")
        table.add_row(" ".join(summary) or "-")
        preview_entries = []
        for name in ("prompt_text", "reply_text", "error_hint", "error"):
            value = payload.get(name)
            if isinstance(value, str) and value:
                preview_entries.append(f"{name}={_preview_text(value, length=160)}")
        if preview_entries:
            table.add_row("\n".join(preview_entries))
        self._console.print(table)

    @staticmethod
    def _format_plain(event: Mapping[str, Any]) -> str:
        core = f"[{event.get('level', 'info').upper()}] {event.get('event_type')} :: {event.get('timestamp')}"
        parts: list[str] = []
        for key in ("request_id", "workflow_id", "stage"):
            if event.get(key):
                parts.append(f"{key}={event[key]}")
        payload = event.get("payload") or {}
        if payload:
            parts.append(json.dumps(payload, ensure_ascii=False))
        return f"{core} {' '.join(parts)}"


class TelemetryEmitter:
    def __init__(self) -> None:
        self._jsonl_sink: Optional[_JsonlSink] = None
        self._console_sink = _ConsoleSink()
        self._structured_logger = structlog.get_logger("rise.telemetry") if structlog else None
        self._lock = threading.Lock()

    def configure(self, *, log_root: Optional[Path] = None) -> None:
        root = (log_root or get_log_root()).resolve()
        path = root / "telemetry.jsonl"
        self._jsonl_sink = _JsonlSink(path)
        if structlog:
            structlog.configure(
                processors=[
                    structlog.processors.TimeStamper(fmt="%Y-%m-%dT%H:%M:%S.%fZ"),
                    structlog.processors.add_log_level,
                    structlog.processors.dict_tracebacks,
                    structlog.processors.JSONRenderer(ensure_ascii=False),
                ],
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )

    def emit(
        self,
        event_type: str,
        *,
        level: str = "info",
        payload: Optional[Mapping[str, Any]] = None,
        sensitive: Optional[Sequence[str]] = None,
        **fields: Any,
    ) -> None:
        event_level = level.lower()
        event: Dict[str, Any] = {
            "event_type": event_type,
            "level": event_level,
            "timestamp": _now_iso(),
            **fields,
        }
        payload_dict = dict(payload or {})
        event["payload"] = payload_dict
        event["sensitive"] = list(dict.fromkeys(sensitive or []))
        if not _passes_filter(event_type):
            return
        if self._should_write_file(event_level):
            self._write_file_event(event, payload_dict)
        if self._should_write_console(event_level):
            masked_event = dict(event)
            masked_event["payload"] = self._mask_payload(payload_dict, masked_event.get("sensitive", []))
            self._console_sink.write(masked_event)
        self._notify_listeners(event)

    def _write_file_event(self, event: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
        sink = self._jsonl_sink
        if sink is None:
            self.configure()
            sink = self._jsonl_sink
        if sink is None:  # pragma: no cover
            return
        sink.write(event)
        if self._structured_logger:
            self._structured_logger.info(event["event_type"], **event)

    @staticmethod
    def _should_write_console(level: str) -> bool:
        return _should_emit(level, _CONSOLE_LEVEL)

    @staticmethod
    def _should_write_file(level: str) -> bool:
        return _should_emit(level, _FILE_LEVEL)

    @staticmethod
    def _mask_payload(payload: Mapping[str, Any], sensitive: Sequence[str]) -> Mapping[str, Any]:
        if not sensitive:
            return payload
        masked: Dict[str, Any] = dict(payload)
        for key in sensitive:
            value = payload.get(key)
            if isinstance(value, str):
                masked[key] = _preview_text(value, length=160)
            elif value is not None:
                masked[key] = str(value)
        return masked

    def _notify_listeners(self, event: Mapping[str, Any]) -> None:
        with _LISTENER_LOCK:
            listeners = list(_LISTENERS)
        if not listeners:
            return
        snapshot = json.loads(json.dumps(event, ensure_ascii=False))
        for callback in listeners:
            try:
                callback(snapshot)
            except Exception:
                continue


_EMITTER: Optional[TelemetryEmitter] = None
_LOCK = threading.Lock()


def get_telemetry() -> TelemetryEmitter:
    global _EMITTER
    if _EMITTER is None:
        with _LOCK:
            if _EMITTER is None:
                _EMITTER = TelemetryEmitter()
    return _EMITTER


def setup_telemetry(log_root: Optional[Path] = None) -> None:
    emitter = get_telemetry()
    emitter.configure(log_root=log_root)


def emit(event_type: str, **kwargs: Any) -> None:
    get_telemetry().emit(event_type, **kwargs)


def register_listener(callback: Callable[[Mapping[str, Any]], None]) -> None:
    with _LISTENER_LOCK:
        if callback not in _LISTENERS:
            _LISTENERS.append(callback)


def unregister_listener(callback: Callable[[Mapping[str, Any]], None]) -> None:
    with _LISTENER_LOCK:
        if callback in _LISTENERS:
            _LISTENERS.remove(callback)


__all__ = ["emit", "get_telemetry", "setup_telemetry", "register_listener", "unregister_listener"]
