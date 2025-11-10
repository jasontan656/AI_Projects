"""
Structured logging helpers backed by Rich.

This module centralises the logging bootstrap previously defined in
`shared_utility.logging.rich_config`. It provides `configure_logging()` alongside helper handlers
that render structured console output, rotating files, and alert panels.
"""

from __future__ import annotations

import atexit
import logging
import os
import shutil
import sys
import threading
import time
import traceback
import zipfile
from collections import OrderedDict
from contextlib import suppress
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from project_utility.config.paths import get_log_root
from project_utility.telemetry import setup_telemetry

_SYNC_LOG_FILENAME = "current.log"
_INFO_LOG_FILENAME = "rise-info.log"
_ERROR_LOG_FILENAME = "rise-error.log"
_ARCHIVE_DIRNAME = "archive"
_GITKEEP = ".gitkeep"

_workspace_lock = threading.RLock()
_workspace_initialized = False
_workspace_finalized = False
_workspace_root: Optional[Path] = None
_archive_dir: Optional[Path] = None
_sync_log_path: Optional[Path] = None
_atexit_registered = False
_workspace_notes: List[Tuple[int, str, Dict[str, Any]]] = []


def _record_workspace_note(level: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    _workspace_notes.append((level, message, extra or {}))


def _flush_workspace_notes() -> None:
    if not _workspace_notes:
        return
    logger = logging.getLogger("project_utility.logging")
    for level, message, extra in list(_workspace_notes):
        logger.log(level, message, extra=extra)
    _workspace_notes.clear()


def _runtime_shutting_down() -> bool:
    """
    Detect whether the interpreter or workspace teardown has begun, so console handlers can stop.
    """

    return _workspace_finalized or getattr(logging, "_shutdown", False)

_SYNC_CONTEXT_FIELDS = (
    "request_id",
    "convo_id",
    "chat_id",
    "task_id",
)

_WARNING_SUMMARIES = {
    "task_runtime.disabled": "任务队列降级，Redis 未连接",
}


def _resolve_warning_summary(record: logging.LogRecord) -> Optional[str]:
    message = record.getMessage()
    return _WARNING_SUMMARIES.get(message)


_ALERT_SUPPRESSION: Dict[str, Dict[str, Any]] = {}
_ALERT_WINDOW_SECONDS = 60.0

try:
    from rich.console import Console  # type: ignore[import]
    from rich.logging import RichHandler  # type: ignore[import]
    from rich.text import Text  # type: ignore[import]
except ImportError:  # pragma: no cover
    RichHandler = None  # type: ignore[assignment]
    Console = None  # type: ignore[assignment]
    Text = None  # type: ignore[assignment]


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
            if _runtime_shutting_down():
                return
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


class _RichAlertHandler(logging.Handler):
    EXTRA_FIELDS = (
        "request_id",
        "convo_id",
        "chat_id",
        "capability",
        "router",
        "status_code",
        "error",
    )

    def __init__(self, console: Console) -> None:  # type: ignore[type-arg]
        super().__init__(level=logging.WARNING)
        self._console = console
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if _runtime_shutting_down():
                return
            key = self._build_alert_key(record)
            suppressed = self._register_alert(key)
            if suppressed is None:
                return
            message = self.format(record)
            summary = _resolve_warning_summary(record)
            if summary:
                message = f"{message} | {summary}"
            if suppressed > 0:
                message = f"{message} (+{suppressed} suppressed)"
            metadata = self._collect_metadata(record)
            line = Text()
            line.append(datetime.utcnow().strftime("%H:%M:%S"), style="dim")
            line.append(" ")
            line.append(f"{record.levelname:<8}", style="bold yellow" if record.levelno >= logging.WARNING else "bold red")
            line.append(" ")
            line.append(f"[{record.name}]", style="bold white")
            line.append(" ")
            line.append(message, style="yellow" if record.levelno >= logging.WARNING else "red")
            if metadata:
                line.append(" :: ", style="dim")
                line.append(" ".join(metadata))
            self._console.print(line)
        except Exception:
            self.handleError(record)

    def _collect_metadata(self, record: logging.LogRecord) -> List[str]:
        pairs: List[str] = []
        for field in self.EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value not in (None, "", []):
                pairs.append(f"{field}={value}")
        return pairs

    def _build_alert_key(self, record: logging.LogRecord) -> str:
        return "|".join(
            str(part)
            for part in (
                record.name,
                record.getMessage(),
                getattr(record, "capability", ""),
                getattr(record, "request_id", ""),
            )
        )

    def _register_alert(self, key: str) -> Optional[int]:
        now = time.time()
        entry = _ALERT_SUPPRESSION.get(key)
        if entry and now - entry["ts"] < _ALERT_WINDOW_SECONDS:
            entry["count"] += 1
            return None
        suppressed = entry["count"] if entry else 0
        _ALERT_SUPPRESSION[key] = {"ts": now, "count": 0}
        return suppressed


class _MaxLevelFilter(logging.Filter):
    """
    Filter that allows records up to the provided maximum level (inclusive).
    """

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self._max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self._max_level


class SyncLogHandler(logging.Handler):
    """
    Mirror log lines into `current.log` so external watchers can tail startup progress.
    """

    def __init__(self, path: Path) -> None:
        super().__init__(level=logging.INFO)
        self._path = path

    def emit(self, record: logging.LogRecord) -> None:
        if self._path is None:
            return
        try:
            message = self.format(record)
            line = f"{datetime.utcnow().isoformat()}Z {record.levelname:<8} {record.name} :: {message}"
            with _workspace_lock:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as stream:
                    stream.write(line + "\n")
        except Exception:
            self.handleError(record)


def _iter_log_root_entries(root: Path) -> List[Path]:
    entries: List[Path] = []
    if not root.exists():
        return entries
    for child in root.iterdir():
        if child.name in {_ARCHIVE_DIRNAME, _GITKEEP}:
            continue
        entries.append(child)
    return entries


def _next_archive_path() -> Path:
    archive_dir = _archive_dir or (_workspace_root or get_log_root()) / _ARCHIVE_DIRNAME
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    candidate = archive_dir / f"{stamp}.zip"
    counter = 1
    while candidate.exists():
        counter += 1
        candidate = archive_dir / f"{stamp}-{counter}.zip"
    return candidate


def _archive_entries(entries: Sequence[Path]) -> Optional[Path]:
    files = [entry for entry in entries if entry.is_file()]
    if not files:
        return None
    archive_path = _next_archive_path()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            try:
                archive.write(file_path, arcname=file_path.name)
            except FileNotFoundError:
                continue
    return archive_path


def _safe_remove_path(target: Path) -> Optional[str]:
    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return None
    except Exception as exc:  # pragma: no cover - filesystem specific
        fallback = target.with_name(f"{target.name}.stale")
        with suppress(Exception):
            target.rename(fallback)
        return repr(exc)


def _clear_log_root(root: Path) -> List[Tuple[str, str]]:
    errors: List[Tuple[str, str]] = []
    for entry in _iter_log_root_entries(root):
        error = _safe_remove_path(entry)
        if error:
            errors.append((str(entry), error))
    (root / _ARCHIVE_DIRNAME).mkdir(parents=True, exist_ok=True)
    return errors


def initialize_log_workspace(*, log_root: Optional[Path] = None) -> Path:
    """
    Prepare `var/logs` for a fresh runtime session.
    Archives the previous run, clears stray files, and seeds current.log.
    """

    global _workspace_initialized, _workspace_root, _archive_dir, _sync_log_path
    with _workspace_lock:
        if _workspace_initialized and _workspace_root:
            return _workspace_root

        root = (log_root or get_log_root()).resolve()
        root.mkdir(parents=True, exist_ok=True)
        archive_dir = root / _ARCHIVE_DIRNAME
        archive_dir.mkdir(parents=True, exist_ok=True)

        entries = _iter_log_root_entries(root)
        archive_error: Optional[str] = None
        archive_path: Optional[Path] = None
        if entries:
            try:
                archive_path = _archive_entries(entries)
            except Exception as exc:  # pragma: no cover - filesystem dependent
                archive_error = repr(exc)
                _record_workspace_note(
                    logging.WARNING,
                    "log_workspace.archive_failed",
                    {"phase": "startup", "error": archive_error},
                )
        cleanup_errors = _clear_log_root(root)

        sync_log = root / _SYNC_LOG_FILENAME
        sync_log.write_text("", encoding="utf-8")
        banner_lines: List[str] = []
        if archive_path:
            _record_workspace_note(
                logging.INFO,
                "log_workspace.archived",
                {"phase": "startup", "path": str(archive_path)},
            )
        if archive_error:
            banner_lines.append(f"[workspace] archive_failed: {archive_error}")
        for failed_path, error in cleanup_errors:
            banner_lines.append(f"[workspace] cleanup_failed: {failed_path} :: {error}")
            _record_workspace_note(
                logging.WARNING,
                "log_workspace.cleanup_failed",
                {"phase": "startup", "path": failed_path, "error": error},
            )
        if banner_lines:
            sync_log.write_text("\n".join(banner_lines) + "\n", encoding="utf-8")

        _workspace_initialized = True
        _workspace_root = root
        _archive_dir = archive_dir
        _sync_log_path = sync_log

        global _atexit_registered
        if not _atexit_registered:
            atexit.register(finalize_log_workspace)
            _atexit_registered = True

        return root


def finalize_log_workspace(*, reason: str = "shutdown") -> None:
    """Flush logging handlers and optionally clean runtime logs."""

    global _workspace_finalized
    with _workspace_lock:
        if _workspace_finalized:
            return
        root = _workspace_root or get_log_root()
        entries = _iter_log_root_entries(root)
        logging.shutdown()
        archive_path: Optional[Path] = None
        if entries:
            try:
                archive_path = _archive_entries(entries)
            except Exception as exc:  # pragma: no cover - filesystem dependent
                _record_workspace_note(
                    logging.WARNING,
                    "log_workspace.archive_failed",
                    {"phase": reason, "error": repr(exc)},
                )
        cleanup_mode_raw = (os.getenv("LOG_CLEANUP_MODE", "purge") or "purge").strip().lower()
        cleanup_mode = cleanup_mode_raw if cleanup_mode_raw in ("purge", "retain") else "purge"
        if cleanup_mode_raw not in ("purge", "retain"):
            cleanup_mode = "purge"
            _record_workspace_note(
                logging.WARNING,
                "log_workspace.cleanup_mode_invalid",
                {"phase": reason, "mode": cleanup_mode_raw},
            )
        if cleanup_mode == "purge":
            for entry in entries:
                error = _safe_remove_path(entry)
                if error:
                    _record_workspace_note(
                        logging.WARNING,
                        "log_workspace.cleanup_failed",
                        {"phase": reason, "path": str(entry), "error": error},
                    )
        if archive_path:
            _record_workspace_note(
                logging.INFO,
                "log_workspace.archived",
                {"phase": reason, "path": str(archive_path)},
            )
        _workspace_finalized = True

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


def _collect_record_extras(
    record: logging.LogRecord,
    extra_keys: Sequence[str],
) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    extras: List[Tuple[str, str]] = []
    for key in extra_keys:
        value = getattr(record, key, None)
        if value in (None, "", [], {}, ()):
            continue
        extras.append((key, str(value)))
    error = getattr(record, "error", None)
    if error is not None:
        error = str(error)
    return extras, error


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
    root = (log_root or get_log_root()).resolve()
    initialize_log_workspace(log_root=root)
    setup_telemetry(log_root=root)

    handlers = _build_rich_console_handlers()
    info_log_path = root / _INFO_LOG_FILENAME
    error_log_path = root / _ERROR_LOG_FILENAME
    handlers.append(_build_rotating_file_handler(info_log_path))
    handlers.append(_build_error_file_handler(error_log_path))
    if _sync_log_path is not None:
        handlers.append(SyncLogHandler(_sync_log_path))

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

    _flush_workspace_notes()

    return configured


__all__ = ["configure_logging", "finalize_log_workspace", "initialize_log_workspace"]
