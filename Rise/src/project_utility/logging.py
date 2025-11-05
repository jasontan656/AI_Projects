"""
Structured logging helpers backed by Rich.

This module centralises the logging bootstrap previously defined in
`shared_utility.logging.rich_config`. It provides `configure_logging()` alongside helper handlers
that render structured console output, rotating files, and alert panels.
"""

from __future__ import annotations

import logging
import traceback
from collections import OrderedDict
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from project_utility.config.paths import get_log_root

try:
    from rich.console import Console  # type: ignore[import]
    from rich.logging import RichHandler  # type: ignore[import]
    from rich.panel import Panel  # type: ignore[import]
    from rich.text import Text  # type: ignore[import]
except ImportError:  # pragma: no cover
    RichHandler = None  # type: ignore[assignment]
    Console = None  # type: ignore[assignment]
    Panel = None  # type: ignore[assignment]
    Text = None  # type: ignore[assignment]


class _MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int) -> None:
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level


_LOG_RECORD_BASE_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "asctime",
    "color_message",
}


def _stringify_extra(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return repr(value)


def _collect_record_extras(
    record: logging.LogRecord,
    include: Sequence[str],
) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    items: "OrderedDict[str, str]" = OrderedDict()
    for key in include:
        value = record.__dict__.get(key)
        if value in (None, "", [], {}, ()):  # pragma: no cover - defensive
            continue
        items[key] = _stringify_extra(value)
    for key, value in record.__dict__.items():
        if key in _LOG_RECORD_BASE_FIELDS or key in items or key == "message":
            continue
        if value in (None, "", [], {}, ()):  # pragma: no cover - defensive
            continue
        items[key] = _stringify_extra(value)
    error_text = items.pop("error", None)
    return list(items.items()), error_text


class _RichAlertHandler(logging.Handler):
    def __init__(self, console: Console) -> None:  # type: ignore[type-arg]
        super().__init__(level=logging.WARNING)
        self._console = console

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            metadata_lines: List[str] = []
            for key in ("request_id", "convo_id", "chat_id", "error", "status_code"):
                value = getattr(record, key, None)
                if value not in (None, "", []):
                    metadata_lines.append(f"{key}: {value}")
            body_parts = metadata_lines + [message]
            if Text is not None and Panel is not None:
                body = Text("\\n".join(body_parts))
                border_style = "yellow" if record.levelno == logging.WARNING else "red"
                title = f"{record.levelname} · {record.name}"
                panel = Panel(body, title=title, border_style=border_style, expand=False)
                self._console.print(panel)
            else:  # pragma: no cover
                border = "WARNING" if record.levelno == logging.WARNING else "ERROR"
                formatted = " | ".join(body_parts)
                self._console.print(f"[{border}]{record.levelname} {record.name}[/] {formatted}")
        except Exception:
            self.handleError(record)


class _RichConsoleHandler(logging.Handler):
    LEVEL_STYLES = {
        logging.DEBUG: "dim",
        logging.INFO: "bold cyan",
    }
    EXTRA_KEYS = (
        "step",
        "phase",
        "pending_updates",
        "decision",
        "webhook_url",
        "redis_enabled",
        "router",
        "timeout_seconds",
        "default_selected",
        "status_code",
        "latency_ms",
    )

    def __init__(self, console: Console) -> None:  # type: ignore[type-arg]
        super().__init__(level=logging.INFO)
        self._console = console
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.WARNING:
            return
        try:
            message = self.format(record)
            segments = _extract_console_segments(record, message, self.EXTRA_KEYS)
            level_style = self.LEVEL_STYLES.get(record.levelno, "white")

            text = Text()
            text.append(segments.timestamp, style="dim")
            text.append(" ")
            text.append(f"{record.levelname:<8}", style=level_style)
            text.append(" ")
            text.append(f"[{record.name}]", style="bold white")
            text.append(" ")
            text.append(segments.message)

            _append_tree_metadata(text, segments.extras, segments.error)
            self._console.print(text)
        except Exception:
            self.handleError(record)


class _ConsoleSegments:
    __slots__ = ("timestamp", "message", "extras", "error")

    def __init__(
        self,
        timestamp: str,
        message: str,
        extras: List[Tuple[str, str]],
        error: Optional[str],
    ) -> None:
        self.timestamp = timestamp
        self.message = message
        self.extras = extras
        self.error = error


def _extract_console_segments(
    record: logging.LogRecord,
    message: str,
    extra_keys: Tuple[str, ...],
) -> _ConsoleSegments:
    timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    extras, error = _collect_record_extras(record, extra_keys)
    if record.exc_info:
        error = "".join(traceback.format_exception(*record.exc_info)).rstrip()
    elif record.stack_info:
        error = record.stack_info.rstrip()
    return _ConsoleSegments(timestamp, message, extras, error)


class _ConsolePlainFormatter(logging.Formatter):
    EXTRA_KEYS = _RichConsoleHandler.EXTRA_KEYS

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        extras, error = _collect_record_extras(record, self.EXTRA_KEYS)
        extra_str = " ".join(f"{key}={value}" for key, value in extras)
        error_suffix = f" :: {error}" if error else ""
        return f"{message} {extra_str}{error_suffix}".strip()


def _append_tree_metadata(
    target: Text,
    extras: Sequence[Tuple[str, str]],
    error: Optional[str],
) -> None:
    if not extras and error is None:
        return

    indent = "    "
    entries: List[Tuple[str, str, Optional[str]]] = [(key, value, "white") for key, value in extras]
    if error is not None:
        entries.append(("error", error, "italic red"))

    total = len(entries)
    for index, (key, value, value_style) in enumerate(entries):
        connector = "└──" if index == total - 1 else "├──"
        continuation_prefix = indent + ("│   " if connector != "└──" else "    ") + "    "
        formatted_value = value.replace("\n", f"\n{continuation_prefix}")

        target.append("\n")
        target.append(indent, style="dim")
        target.append(connector, style="dim")
        target.append(" ", style="dim")
        target.append(f"{key}: ", style="dim")
        target.append(formatted_value, style=value_style or "white")


def _build_rich_console_handlers() -> List[logging.Handler]:
    if RichHandler is None or Console is None or Text is None:  # pragma: no cover
        return []
    console = Console()
    console_handler = _RichConsoleHandler(console)
    alert_handler = _RichAlertHandler(console)
    alert_handler.setFormatter(logging.Formatter("%(message)s"))
    return [console_handler, alert_handler]


def _build_rotating_file_handler(path: Path) -> logging.Handler:
    handler = RotatingFileHandler(
        path,
        maxBytes=2 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(_MaxLevelFilter(logging.INFO))
    return handler


def _build_error_file_handler(path: Path) -> logging.Handler:
    handler = RotatingFileHandler(
        path,
        maxBytes=2 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    handler.setLevel(logging.WARNING)
    return handler


def configure_logging(
    *,
    log_root: Optional[Path] = None,
    extra_loggers: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, logging.Logger]:
    """
    Configure structured logging for Rise services.

    Returns a mapping of logger names to configured logger instances. Callers can tweak behaviour by
    passing `extra_loggers` with logger-specific levels or handlers.
    """

    logging.captureWarnings(True)
    root = log_root or get_log_root()
    root.mkdir(parents=True, exist_ok=True)

    handlers = _build_rich_console_handlers()
    info_log_path = root / "rise-info.log"
    error_log_path = root / "rise-error.log"
    handlers.append(_build_rotating_file_handler(info_log_path))
    handlers.append(_build_error_file_handler(error_log_path))

    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
    )

    configured: Dict[str, logging.Logger] = {}
    for name, options in (extra_loggers or {}).items():
        logger = logging.getLogger(name)
        if "level" in options:
            logger.setLevel(options["level"])
        for handler in options.get("handlers", []):
            logger.addHandler(handler)
        configured[name] = logger

    return configured


__all__ = ["configure_logging"]
