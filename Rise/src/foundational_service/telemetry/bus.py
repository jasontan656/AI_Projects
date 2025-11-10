
"""Telemetry bus that subscribes to TelemetryEmitter events and renders Rich views."""

from __future__ import annotations

import atexit
import json
import threading
import time
from io import StringIO
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence

try:  # pragma: no cover - optional dependency already installed in runtime images
    from rich.console import Console  # type: ignore[import]
    from rich.panel import Panel  # type: ignore[import]
    from rich.rule import Rule  # type: ignore[import]
    from rich.syntax import Syntax  # type: ignore[import]
    from rich.table import Table  # type: ignore[import]
    from rich.tree import Tree  # type: ignore[import]
except ImportError:  # pragma: no cover
    Console = None  # type: ignore[assignment]
    Panel = None  # type: ignore[assignment]
    Rule = None  # type: ignore[assignment]
    Syntax = None  # type: ignore[assignment]
    Table = None  # type: ignore[assignment]
    Tree = None  # type: ignore[assignment]

from project_utility.telemetry import register_listener, unregister_listener

_LEVEL_ORDER = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}
_DEFAULT_FILTERS = (
    "http.",
    "telegram.",
    "capability.",
    "queue.",
    "workflow.",
    "tools.",
)
_ALERT_WINDOW_SECONDS = 60.0


def _preview(value: Any, length: int = 200) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."


def _should_emit(level: str, threshold: str) -> bool:
    return _LEVEL_ORDER.get(level, 20) >= _LEVEL_ORDER.get(threshold, 20)


class TelemetryConsoleSubscriber:
    """Subscribe to TelemetryEmitter events and render them with Rich."""

    def __init__(self, *, config: Mapping[str, Any]) -> None:
        telemetry_cfg = dict(config.get("telemetry", {}))
        console_cfg = dict(telemetry_cfg.get("console", {}))
        self._enabled = bool(telemetry_cfg.get("enabled", False))
        self._console_level = str(console_cfg.get("level", "info")).lower()
        self._prompt_preview = int(console_cfg.get("prompt_preview_chars", 280))
        self._state_keys = tuple(console_cfg.get("state_snapshot_keys", ()))
        filters = console_cfg.get("filters")
        if isinstance(filters, Sequence):
            self._filters = tuple(str(item).strip() for item in filters if str(item).strip())
        else:
            self._filters = _DEFAULT_FILTERS
        self._highlight_latency = console_cfg.get("highlight_latency_threshold_ms", 1500)
        self._highlight_token = console_cfg.get("highlight_token_threshold", 4000)
        self._show_cost = bool(console_cfg.get("show_cost", True))
        self._show_annotations = bool(console_cfg.get("show_annotations", True))
        self._alert_window = float(console_cfg.get("alert_window_seconds", _ALERT_WINDOW_SECONDS))
        self._alert_cache: MutableMapping[str, float] = {}

        self._console = self._build_console(console_cfg)
        self._mirror_console, self._mirror_file = self._build_mirror(console_cfg)
        self._listener_registered = False
        self._lock = threading.RLock()

        if self._mirror_file is not None:
            atexit.register(self._mirror_file.close)

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if not self._enabled or self._listener_registered:
            return
        register_listener(self._handle_event)
        self._listener_registered = True

    def stop(self) -> None:
        if not self._listener_registered:
            return
        unregister_listener(self._handle_event)
        self._listener_registered = False
        self._flush_mirror()

    def __enter__(self) -> TelemetryConsoleSubscriber:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.stop()

    # ------------------------------------------------------------------ render logic
    def _handle_event(self, event: Mapping[str, Any]) -> None:
        if not self._enabled:
            return
        event_type = str(event.get("event_type") or "")
        if self._filters and not any(event_type.startswith(prefix) for prefix in self._filters):
            return
        level = str(event.get("level", "info")).lower()
        if not _should_emit(level, self._console_level):
            return
        masked_event = self._mask_sensitive(event)
        with self._lock:
            self._render_event(masked_event)

    def _render_event(self, event: Mapping[str, Any]) -> None:
        if self._console is None or Table is None or Panel is None:  # pragma: no cover
            print(json.dumps(event, ensure_ascii=False, indent=2))
            return

        event_type = str(event.get("event_type") or "")
        level = str(event.get("level") or "info").upper()
        header_style = {
            "DEBUG": "dim",
            "INFO": "bold cyan",
            "WARNING": "yellow",
            "ERROR": "bold red",
            "CRITICAL": "bold white on red",
        }.get(level, "white")
        self._print(Rule(f"{level} • {event_type}", style=header_style))

        if event_type.startswith("workflow.stage"):
            self._render_workflow_stage(event)
        elif event_type.startswith("workflow."):
            self._render_workflow_event(event)
        elif event_type.startswith("queue."):
            self._render_queue_event(event)
        elif event_type.startswith("http."):
            self._render_http_event(event)
        elif event_type.startswith("telegram."):
            self._render_telegram_event(event)
        else:
            self._render_generic_event(event)

        if self._should_alert(event):
            self._render_alert(event)

        self._print(" ")
        self._flush_mirror()

    # ------------------------------------------------------------------ section renderers
    def _render_workflow_stage(self, event: Mapping[str, Any]) -> None:
        payload = event.get("payload") or {}
        perf = payload.get("performance") or {}
        result = payload.get("result") or {}
        prompt_preview = payload.get("prompt_text") or result.get("prompt_text")
        duration = perf.get("latency_ms_total") or perf.get("latency_ms")
        tokens = perf.get("token_total")
        table = Table(show_header=False, expand=True)
        table.add_column("Field", style="bold cyan", no_wrap=True)
        table.add_column("Value")
        table.add_row("workflow_id", str(event.get("workflow_id") or "-"))
        table.add_row("stage", str(event.get("stage") or event.get("payload", {}).get("stage")))
        if duration is not None:
            highlight = "red" if self._highlight_latency and duration > self._highlight_latency else ""
            value = f"[{highlight}]{duration} ms[/]" if highlight else f"{duration} ms"
            table.add_row("latency", value)
        if tokens is not None:
            highlight = "yellow" if self._highlight_token and tokens > self._highlight_token else ""
            value = f"[{highlight}]{tokens}[/]" if highlight else str(tokens)
            table.add_row("tokens", value)
        status = result.get("status") or result.get("schema_valid")
        if status is not None:
            table.add_row("status", str(status))
        if self._show_cost and payload.get("cost"):
            cost = payload["cost"]
            price = cost.get("pricing_usd")
            if price is not None:
                table.add_row("price_usd", f"${price:.6f}")
            if cost.get("model"):
                table.add_row("model", str(cost["model"]))
        self._print(table)

        if prompt_preview:
            self._print(
                Panel(
                    _preview(prompt_preview, self._prompt_preview),
                    title="prompt",
                    border_style="magenta",
                )
            )
        output_excerpt = result.get("output_excerpt") or payload.get("reply_text")
        if output_excerpt:
            self._print(
                Panel(
                    _preview(output_excerpt, self._prompt_preview),
                    title="output",
                    border_style="green",
                )
            )

    def _render_workflow_event(self, event: Mapping[str, Any]) -> None:
        payload = event.get("payload") or {}
        tree = Tree(f"workflow {event.get('workflow_id') or '-'}")
        for key in ("stage", "actor", "status", "reason"):
            if payload.get(key):
                tree.add(f"{key}: {payload[key]}")
        if payload.get("missing_stages"):
            tree.add(f"missing_stages: {payload['missing_stages']}")
        self._print(tree)

    def _render_queue_event(self, event: Mapping[str, Any]) -> None:
        payload = event.get("payload") or {}
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Field")
        table.add_column("Value", overflow="fold")
        for field in ("task_id", "workflow_id", "attempt", "status", "result"):
            value = payload.get(field) or event.get(field)
            if value is not None:
                table.add_row(field, _preview(value, 200))
        if payload.get("latency_ms") is not None:
            table.add_row("latency_ms", str(payload["latency_ms"]))
        self._print(table)

    def _render_http_event(self, event: Mapping[str, Any]) -> None:
        payload = event.get("payload") or {}
        table = Table(show_header=True, header_style="bold green")
        table.add_column("path")
        table.add_column("method")
        table.add_column("status")
        table.add_column("latency")
        table.add_row(
            payload.get("path") or "-",
            payload.get("method") or "-",
            str(payload.get("status_code") or event.get("status_code") or "-"),
            f"{payload.get('latency_ms', '-')} ms",
        )
        self._print(table)
        if payload.get("error"):
            self._print(
                Panel(
                    _preview(payload["error"], self._prompt_preview),
                    title="http.error",
                    border_style="red",
                )
            )

    def _render_telegram_event(self, event: Mapping[str, Any]) -> None:
        payload = event.get("payload") or {}
        table = Table(show_header=False, expand=True)
        table.add_column("Field", style="bold blue", no_wrap=True)
        table.add_column("Value", overflow="fold")
        table.add_row("chat_id", str(payload.get("chat_id") or "-"))
        if payload.get("latency_ms") is not None:
            table.add_row("latency_ms", str(payload["latency_ms"]))
        if payload.get("retries") is not None:
            table.add_row("retries", str(payload["retries"]))
        if payload.get("error"):
            table.add_row("error", _preview(payload["error"], 200))
        if payload.get("prompt_text"):
            self._print(
                Panel(
                    _preview(payload["prompt_text"], self._prompt_preview),
                    title="prompt",
                    border_style="cyan",
                )
            )
        if payload.get("reply_text"):
            self._print(
                Panel(
                    _preview(payload["reply_text"], self._prompt_preview),
                    title="reply",
                    border_style="green",
                )
            )
        self._print(table)

    def _render_generic_event(self, event: Mapping[str, Any]) -> None:
        payload = json.dumps(event, ensure_ascii=False, indent=2)
        if Syntax is None or Panel is None:  # pragma: no cover
            self._print(payload)
            return
        self._print(Panel(Syntax(payload, "json"), title="event", border_style="dim"))

    def _render_alert(self, event: Mapping[str, Any]) -> None:
        payload = event.get("payload") or {}
        summary = {
            "event_type": event.get("event_type"),
            "level": event.get("level"),
            "request_id": event.get("request_id"),
            "workflow_id": event.get("workflow_id"),
            "status_code": payload.get("status_code"),
            "error": payload.get("error") or payload.get("error_hint"),
        }
        text = json.dumps(summary, ensure_ascii=False, indent=2)
        if Panel is None:  # pragma: no cover
            self._print(f"[ALERT] {text}")
            return
        self._print(Panel(Syntax(text, "json"), title="ALERT", border_style="bold red"))

    # ------------------------------------------------------------------ helpers
    def _mask_sensitive(self, event: Mapping[str, Any]) -> Mapping[str, Any]:
        sensitive = event.get("sensitive") or []
        payload = dict(event.get("payload") or {})
        masked = dict(event)
        masked["payload"] = payload
        for key in sensitive:
            value = payload.get(key)
            if isinstance(value, str):
                payload[key] = _preview(value, 160)
            elif value is not None:
                payload[key] = str(value)
        return masked

    def _should_alert(self, event: Mapping[str, Any]) -> bool:
        level = str(event.get("level") or "info").lower()
        if _LEVEL_ORDER.get(level, 20) < _LEVEL_ORDER["warning"]:
            return False
        payload = event.get("payload") or {}
        key = f"{event.get('event_type')}:{payload.get('status_code')}:{event.get('workflow_id')}"
        now = time.monotonic()
        last = self._alert_cache.get(key, 0.0)
        if now - last < self._alert_window:
            return False
        self._alert_cache[key] = now
        return True

    def _print(self, obj: Any) -> None:
        if self._console is not None:
            self._console.print(obj)
            if self._mirror_console is not None and self._mirror_file is not None:
                self._mirror_console.print(obj)
        else:  # pragma: no cover - fallback when Rich is missing
            print(obj)

    def _flush_mirror(self) -> None:
        if self._mirror_console is None or self._mirror_file is None:
            return
        buffer = getattr(self._mirror_console, "file", None)
        if not isinstance(buffer, StringIO):
            return
        text = buffer.getvalue()
        if text:
            self._mirror_file.write(text)
            self._mirror_file.flush()
            buffer.seek(0)
            buffer.truncate(0)

    @staticmethod
    def _build_console(console_cfg: Mapping[str, Any]) -> Optional[Console]:
        if Console is None:  # pragma: no cover
            return None
        kwargs = {
            "force_terminal": bool(console_cfg.get("force_terminal", True)),
            "width": int(console_cfg.get("width", 120)),
            "highlight": bool(console_cfg.get("highlight", False)),
            "markup": bool(console_cfg.get("markup", True)),
            "soft_wrap": bool(console_cfg.get("soft_wrap", True)),
        }
        color_system = console_cfg.get("color_system")
        if color_system:
            kwargs["color_system"] = color_system
        legacy_windows = console_cfg.get("legacy_windows")
        if legacy_windows is not None:
            kwargs["legacy_windows"] = bool(legacy_windows)
        return Console(**kwargs)

    @staticmethod
    def _build_mirror(console_cfg: Mapping[str, Any]) -> tuple[Optional[Console], Optional[Any]]:
        mirror_path = console_cfg.get("mirror_path")
        if not mirror_path or Console is None:
            return None, None

        path = Path(str(mirror_path))
        path.parent.mkdir(parents=True, exist_ok=True)
        mirror_file = path.open("a", encoding="utf-8", buffering=1)
        buffer = StringIO()
        mirror_console = Console(
            file=buffer,
            force_terminal=False,
            color_system=None,
            highlight=False,
            markup=False,
            soft_wrap=True,
            width=int(console_cfg.get("width", 120)),
        )
        return mirror_console, mirror_file


def build_console_subscriber(config: Mapping[str, Any]) -> TelemetryConsoleSubscriber:
    """
    Helper that instantiates and starts a console subscriber using the given telemetry config.
    """

    subscriber = TelemetryConsoleSubscriber(config=config)
    subscriber.start()
    return subscriber


__all__ = ["TelemetryConsoleSubscriber", "build_console_subscriber"]
