"""Telemetry bus with Rich console + JSONL sinks."""

from __future__ import annotations

import atexit
import json
import logging
import threading
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, TextIO, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from project_utility.clock import philippine_iso


def _utc_now_iso() -> str:
    return philippine_iso()


class _JsonlWriter:
    def __init__(self, path: str, ensure_dir: bool) -> None:
        self._path = Path(path)
        if ensure_dir:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, event: Mapping[str, Any]) -> None:
        payload = json.dumps(event, ensure_ascii=False)
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(payload + "\n")


def _preview(value: Optional[str], length: int) -> str:
    if not value:
        return ""
    if len(value) <= length:
        return value
    return value[: length - 3] + "..."


class RichTelemetryConsole:
    def __init__(self, console_cfg: Mapping[str, Any]) -> None:
        self._console_cfg = console_cfg
        self._logger = logging.getLogger("UnifiedCS.telemetry.console")

        mirror_path_cfg = console_cfg.get("mirror_path")
        self._mirror_file: Optional[TextIO] = None
        self._mirror_path: Optional[Path] = None
        self._mirror_buffer: Optional[StringIO] = None
        if mirror_path_cfg:
            mirror_path_obj = Path(str(mirror_path_cfg))
            try:
                mirror_path_obj.parent.mkdir(parents=True, exist_ok=True)
                self._mirror_file = mirror_path_obj.open("a", encoding="utf-8", buffering=1)
                atexit.register(self._mirror_file.close)
                self._mirror_path = mirror_path_obj
            except Exception:
                self._logger.exception(
                    "telemetry.console_mirror_open_failed",
                    extra={"path": str(mirror_path_cfg)},
                )
                self._mirror_file = None
                self._mirror_path = None
                mirror_path_obj = None

        console_kwargs: Dict[str, Any] = {
            "force_terminal": bool(console_cfg.get("force_terminal", True)),
            "width": int(console_cfg.get("width", 120)),
            "highlight": bool(console_cfg.get("highlight", False)),
            "markup": bool(console_cfg.get("markup", True)),
            "soft_wrap": bool(console_cfg.get("soft_wrap", True)),
        }
        color_system = console_cfg.get("color_system")
        if color_system:
            console_kwargs["color_system"] = color_system
        style = console_cfg.get("style")
        if style:
            console_kwargs["style"] = style
        legacy_windows = console_cfg.get("legacy_windows")
        if legacy_windows is not None:
            console_kwargs["legacy_windows"] = bool(legacy_windows)
        self._console = Console(**console_kwargs)
        self._mirror_console: Optional[Console] = None
        if self._mirror_file is not None:
            self._mirror_buffer = StringIO()
            mirror_kwargs: Dict[str, Any] = {
                "file": self._mirror_buffer,
                "force_terminal": False,
                "color_system": None,
                "width": console_kwargs.get("width"),
                "highlight": False,
                "markup": bool(console_cfg.get("markup", True)),
                "soft_wrap": bool(console_cfg.get("soft_wrap", True)),
                "emoji": False,
            }
            self._mirror_console = Console(**mirror_kwargs)
        self._console_encoding_failed = False
        self._prompt_preview_chars = int(console_cfg.get("prompt_preview_chars", 280))
        self._state_keys = list(console_cfg.get("state_snapshot_keys", []))
        self._latency_threshold = console_cfg.get("highlight_latency_threshold_ms", 1500)
        self._token_threshold = console_cfg.get("highlight_token_threshold", 4000)
        self._show_cost = bool(console_cfg.get("show_cost", True))
        self._show_annotations = bool(console_cfg.get("show_annotations", True))
        self._show_prompt_full = bool(console_cfg.get("show_prompt_full", True))
        self._show_state_snapshot_full = bool(console_cfg.get("show_state_snapshot_full", True))
        self._show_output_full = bool(console_cfg.get("show_output_full", True))

    def _print(self, *args: Any, **kwargs: Any) -> None:
        try:
            self._console.print(*args, **kwargs)
        except UnicodeEncodeError:
            if not self._console_encoding_failed:
                self._console_encoding_failed = True
                self._logger.warning(
                    "telemetry.console_encoding_unsupported",
                    extra={"encoding": getattr(self._console.file, "encoding", None)},
                )
        except Exception:
            self._logger.exception("telemetry.console_print_failed")
        if self._mirror_console is not None and self._mirror_file is not None and self._mirror_buffer is not None:
            self._mirror_console.print(*args, **kwargs)
            text = self._mirror_buffer.getvalue()
            if text:
                self._mirror_file.write(text)
            self._mirror_buffer.seek(0)
            self._mirror_buffer.truncate(0)

    def render(self, event: Mapping[str, Any]) -> None:
        event_type = event.get("event_type")
        stage_id = event.get("stage_id") or "-"
        header = f"{event_type} • stage={stage_id} • request={event.get('request_id')}"
        self._print(Rule(header))
        if event_type == "StageStart":
            self._render_stage_start(event)
        elif event_type == "StageEnd":
            self._render_stage_end(event)
        elif event_type == "GuardEvent":
            self._render_guard_event(event)
        elif event_type == "CacheEvent":
            self._render_cache_event(event)
        elif event_type == "BridgeSummary":
            self._render_bridge_summary(event)
        elif event_type == "ErrorEvent":
            self._render_error(event)
        else:
            self._print(Panel(json.dumps(event, ensure_ascii=False, indent=2)))
        self._print()
        self._flush_mirror()


    def _render_stage_start(self, event: Mapping[str, Any]) -> None:
        payload = event.get("payload", {})
        user_input = payload.get("user_input") or {}
        prompt = payload.get("prompt") or {}
        state_snapshot = payload.get("state_snapshot") or {}
        iteration = event.get("iteration")

        table = Table.grid(padding=(0, 2))
        table.add_row("[bold]Iteration[/]", str(iteration))
        if user_input.get("raw"):
            table.add_row("[bold cyan]User[/]", _preview(user_input.get("raw"), 400))
        cache_hash = prompt.get("cache_prefix_hash") if prompt else None
        if cache_hash:
            table.add_row("[bold yellow]Cache Prefix[/]", cache_hash)
        if prompt and not self._show_prompt_full:
            body_preview = _preview(prompt.get("body_preview"), self._prompt_preview_chars)
            table.add_row("[bold magenta]Prompt[/]", body_preview)
        if self._state_keys and state_snapshot and not self._show_state_snapshot_full:
            lines = []
            for key in self._state_keys:
                if key in state_snapshot:
                    lines.append(f"{key}: {state_snapshot[key]!r}")
            if lines:
                table.add_row("[bold green]State[/]", "\n".join(lines))

        self._print(table)

        if self._show_prompt_full and prompt:
            base_system = prompt.get("base_system")
            template = prompt.get("stage_prompt_template") or prompt.get("stage_prompt")
            compiled_prompt = prompt.get("compiled_prompt") or template
            compiled_input = prompt.get("compiled_input")
            store_plan = prompt.get("store_plan")

            sections = []
            if base_system:
                sections.append((base_system, "Base System Prompt", "markdown"))
            if template:
                sections.append((template, "Stage Prompt Template", "markdown"))
            if compiled_prompt and compiled_prompt != template:
                sections.append((compiled_prompt, "Compiled Prompt", "markdown"))
            if compiled_input:
                sections.append((compiled_input, "Compiled Input", "json"))
            if store_plan:
                sections.append(
                    (json.dumps(store_plan, ensure_ascii=False, indent=2), "Store Plan", "json")
                )

            for content, title, language in sections:
                if content:
                    self._print(self._syntax_panel(content, title, language=language))

        if self._show_state_snapshot_full:
            formatted = json.dumps(payload.get("state_snapshot") or {}, ensure_ascii=False, indent=2)
            if formatted and formatted != "{}":
                self._print(self._syntax_panel(formatted, "State Snapshot", language="json"))

    def _render_stage_end(self, event: Mapping[str, Any]) -> None:
        payload = event.get("payload", {})
        perf = payload.get("performance") or {}
        result = payload.get("result") or {}
        cost = payload.get("cost") or {}
        state_diff = payload.get("state_diff") or {}
        annotations = result.get("annotations") or []

        metrics = Table(title="Performance", show_header=True, header_style="bold")
        metrics.add_column("Metric")
        metrics.add_column("Value", justify="right")

        latency = perf.get("latency_ms_total")
        if latency is not None:
            style = "red" if self._latency_threshold and latency > self._latency_threshold else ""
            metrics.add_row("latency_ms_total", f"[{style}]{latency}[/]" if style else str(latency))

        provider_latency = perf.get("latency_ms_provider")
        if provider_latency is not None:
            metrics.add_row("latency_ms_provider", str(provider_latency))

        token_in = perf.get("token_in")
        token_out = perf.get("token_out")
        token_total = perf.get("token_total") or ((token_in or 0) + (token_out or 0))
        if token_in is not None:
            metrics.add_row("token_in", str(token_in))
        if token_out is not None:
            metrics.add_row("token_out", str(token_out))
        if token_total:
            style = "yellow" if self._token_threshold and token_total > self._token_threshold else ""
            metrics.add_row("token_total", f"[{style}]{token_total}[/]" if style else str(token_total))

        cache = "hit" if perf.get("cache_hit") else "miss"
        metrics.add_row("cache", cache)

        if self._show_cost and cost:
            metrics.add_row("model", str(cost.get("model", "")))
            pricing = cost.get("pricing_usd")
            if pricing is not None:
                metrics.add_row("price_usd", f"${pricing:.6f}")

        output_excerpt = result.get("output_excerpt")
        status = "✅ valid" if result.get("schema_valid", True) else "⚠️ invalid"
        body_table = Table.grid(expand=True)
        body_table.add_row("[bold]Result[/]", status)
        if output_excerpt:
            body_table.add_row("[bold purple]Output[/]", _preview(output_excerpt, 400))
        if annotations and self._show_annotations:
            body_table.add_row("[bold orange1]Annotations[/]", ", ".join(annotations))

        if state_diff:
            diff_lines = []
            for key, diff in state_diff.items():
                old = diff.get("old")
                new = diff.get("new")
                diff_lines.append(f"{key}: {old!r} → {new!r}")
            if diff_lines:
                body_table.add_row("[bold green]State diff[/]", "\n".join(diff_lines))

        tree = Tree("StageEnd")
        tree.add(metrics)
        tree.add(body_table)
        self._print(tree)

        if self._show_output_full:
            output_excerpt = result.get("output_excerpt")
            if output_excerpt:
                self._print(self._syntax_panel(output_excerpt, "Stage Output", language="json"))

    def _render_guard_event(self, event: Mapping[str, Any]) -> None:
        guard = event.get("payload", {}).get("guard", {})
        status = str(guard.get("status") or "")
        table = Table(
            show_header=False,
            box=box.MINIMAL_DOUBLE_HEAD,
            expand=True,
        )
        table.add_column("Field", style="bold blue", no_wrap=True)
        table.add_column("Value", overflow="fold")
        table.add_row("status", status or "-")
        table.add_row("action", str(guard.get("action")))
        stage = guard.get("stage")
        if stage:
            table.add_row("stage", str(stage))
        reason = guard.get("reason")
        if reason and reason != "load":
            table.add_row("reason", str(reason))
        prev_val = guard.get("violations_prev")
        curr_val = guard.get("violations")
        display_val = str(curr_val)
        try:
            prev_int = int(prev_val) if prev_val is not None else None
            curr_int = int(curr_val) if curr_val is not None else None
        except (TypeError, ValueError):
            prev_int = prev_val
            curr_int = curr_val
        if prev_val is not None and prev_int != curr_int:
            display_val = f"{prev_val} -> {curr_val}"
        table.add_row("violations", display_val)
        locked_until = guard.get("locked_until")
        if locked_until:
            table.add_row("locked_until", str(locked_until))
        message = guard.get("message")
        border_style = "red" if status.lower() == "locked" else "yellow"
        panel = Panel(table, title="GuardEvent", subtitle=message or "", border_style=border_style)
        self._print(panel)

    def _render_cache_event(self, event: Mapping[str, Any]) -> None:
        cache = event.get("payload", {}).get("cache", {})
        table = Table(
            title="CacheEvent",
            show_header=False,
            box=box.MINIMAL_DOUBLE_HEAD,
            expand=True,
        )
        table.add_column("Field", style="bold blue")
        table.add_column("Value", overflow="fold")
        table.add_row("operation", str(cache.get("op", "")))
        table.add_row("path", str(cache.get("path", "")))
        summary = cache.get("summary")
        if summary:
            summary_text = json.dumps(summary, ensure_ascii=False, indent=2)
            if len(summary_text) <= 200:
                table.add_row("summary", summary_text)
                summary_text = None
            self._print(table)
            if summary_text:
                self._print(self._syntax_panel(summary_text, "Cache Summary", language="json"))
            return
        self._print(table)

    def _render_bridge_summary(self, event: Mapping[str, Any]) -> None:
        summary = event.get("payload", {}).get("summary", {})
        table = Table(title="BridgeSummary", show_header=True, header_style="bold cyan")
        table.add_column("Field")
        table.add_column("Value", justify="right")
        for key in ("mode", "tokens_total", "token_in", "token_out", "latency_ms_total"):
            if key in summary:
                table.add_row(key, str(summary[key]))
        if self._show_cost and summary.get("pricing_usd") is not None:
            table.add_row("price_usd", f"${summary['pricing_usd']:.6f}")
        chunks = summary.get("chunks") or []
        if chunks:
            table.add_row("chunks[0]", _preview(str(chunks[0]), 400))
        self._print(table)

    def _render_error(self, event: Mapping[str, Any]) -> None:
        payload = event.get("payload", {})
        panel = Panel(
            payload.get("message", ""),
            title="ErrorEvent",
            border_style="bold red",
        )
        self._print(panel)

    def _syntax_panel(self, text: str, title: str, language: str = "markdown") -> Panel:
        syntax = Syntax(text, language, theme="monokai", line_numbers=False, word_wrap=True)
        return Panel(syntax, title=title, expand=False)

    def _flush_mirror(self) -> None:
        if self._mirror_file is not None:
            self._mirror_file.flush()

class TelemetryBus:
    """Central dispatcher for telemetry events."""

    def __init__(self, *, config: Mapping[str, Any]) -> None:
        telemetry_cfg = config.get("telemetry", {})
        self._cfg = telemetry_cfg
        self._enabled = bool(telemetry_cfg.get("enabled", False))
        self._events_cfg = telemetry_cfg.get("events", {})
        self._pricing_cfg = telemetry_cfg.get("pricing", {})
        self._iteration_enabled = bool(telemetry_cfg.get("iteration_counter", True))
        self._iterations: Dict[Tuple[str, str], int] = {}
        self._lock = threading.Lock()
        self._logger = logging.getLogger("UnifiedCS.telemetry")

        console_cfg = telemetry_cfg.get("console", {})
        handler = console_cfg.get("handler", "rich")
        self._console_sink: Optional[RichTelemetryConsole]
        if self._enabled and handler == "rich":
            self._console_sink = RichTelemetryConsole(console_cfg)
        else:
            self._console_sink = None

        json_cfg = telemetry_cfg.get("jsonl", {})
        if self._enabled and json_cfg.get("enabled", True):
            self._jsonl_writer = _JsonlWriter(
                path=json_cfg.get("path"),
                ensure_dir=bool(json_cfg.get("ensure_dir", True)),
            )
        else:
            self._jsonl_writer = None

    # --------------------------------------------------------------------- API

    def emit_stage_start(
        self,
        *,
        request_id: str,
        convo_id: str,
        session_id: str,
        stage_id: str,
        user_input: Optional[Mapping[str, Any]] = None,
        prompt: Optional[Mapping[str, Any]] = None,
        state_snapshot: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> int:
        if not self._should_emit("stage_start"):
            return 0
        iteration = self._next_iteration(convo_id, session_id)
        payload = {
            "user_input": user_input or {},
            "prompt": prompt or {},
            "state_snapshot": state_snapshot or {},
        }
        event = self._build_event(
            "StageStart",
            request_id=request_id,
            convo_id=convo_id,
            session_id=session_id,
            stage_id=stage_id,
            iteration=iteration,
            payload=payload,
            metadata=metadata,
        )
        self._dispatch(event)
        return iteration

    def emit_stage_end(
        self,
        *,
        request_id: str,
        convo_id: str,
        session_id: str,
        stage_id: str,
        iteration: Optional[int],
        model: Optional[str],
        performance: Mapping[str, Any],
        result: Mapping[str, Any],
        state_diff: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if not self._should_emit("stage_end"):
            return
        actual_iteration = iteration if iteration is not None else self._current_iteration(convo_id, session_id)
        perf = dict(performance or {})
        tokens_in = perf.get("token_in")
        tokens_out = perf.get("token_out")
        token_total = perf.get("token_total")
        if token_total is None and tokens_in is not None and tokens_out is not None:
            perf["token_total"] = tokens_in + tokens_out

        cost = self._calculate_cost(model=model, performance=perf)
        payload = {
            "performance": perf,
            "result": result,
            "cost": cost,
            "state_diff": state_diff or {},
        }
        event = self._build_event(
            "StageEnd",
            request_id=request_id,
            convo_id=convo_id,
            session_id=session_id,
            stage_id=stage_id,
            iteration=actual_iteration,
            payload=payload,
            metadata=metadata,
        )
        self._dispatch(event)

    def emit_guard_event(
        self,
        *,
        request_id: str,
        convo_id: str,
        session_id: str,
        guard_payload: Mapping[str, Any],
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if not self._should_emit("guard_event"):
            return
        event = self._build_event(
            "GuardEvent",
            request_id=request_id,
            convo_id=convo_id,
            session_id=session_id,
            stage_id=None,
            iteration=self._current_iteration(convo_id, session_id),
            payload={"guard": guard_payload},
            metadata=metadata,
        )
        self._dispatch(event)

    def emit_cache_event(
        self,
        *,
        request_id: str,
        convo_id: str,
        session_id: str,
        cache_payload: Mapping[str, Any],
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if not self._should_emit("cache_event"):
            return
        event = self._build_event(
            "CacheEvent",
            request_id=request_id,
            convo_id=convo_id,
            session_id=session_id,
            stage_id=None,
            iteration=self._current_iteration(convo_id, session_id),
            payload={"cache": cache_payload},
            metadata=metadata,
        )
        self._dispatch(event)

    def emit_bridge_summary(
        self,
        *,
        request_id: str,
        convo_id: str,
        session_id: str,
        summary: Mapping[str, Any],
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if not self._should_emit("bridge_summary"):
            return
        event = self._build_event(
            "BridgeSummary",
            request_id=request_id,
            convo_id=convo_id,
            session_id=session_id,
            stage_id=None,
            iteration=self._current_iteration(convo_id, session_id),
            payload={"summary": summary},
            metadata=metadata,
        )
        self._dispatch(event)

    def emit_error_event(
        self,
        *,
        request_id: str,
        convo_id: str,
        session_id: str,
        message: str,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if not self._should_emit("error_event"):
            return
        event = self._build_event(
            "ErrorEvent",
            request_id=request_id,
            convo_id=convo_id,
            session_id=session_id,
            stage_id=None,
            iteration=self._current_iteration(convo_id, session_id),
            payload={"message": message},
            metadata=metadata,
        )
        self._dispatch(event)

    # ------------------------------------------------------------------ helpers

    def _should_emit(self, key: str) -> bool:
        if not self._enabled:
            return False
        return bool(self._events_cfg.get(key, True))

    def _next_iteration(self, convo_id: str, session_id: str) -> int:
        if not self._iteration_enabled:
            return 0
        key = (convo_id, session_id)
        with self._lock:
            value = self._iterations.get(key, -1) + 1
            self._iterations[key] = value
            return value

    def _current_iteration(self, convo_id: str, session_id: str) -> int:
        if not self._iteration_enabled:
            return 0
        key = (convo_id, session_id)
        return self._iterations.get(key, 0)

    def _calculate_cost(self, *, model: Optional[str], performance: Mapping[str, Any]) -> Mapping[str, Any]:
        model_key = model or ""
        pricing_cfg = self._pricing_cfg.get(model_key, {})
        prompt_rate = pricing_cfg.get("prompt")
        completion_rate = pricing_cfg.get("completion")
        prompt_tokens = performance.get("token_in") or performance.get("prompt_tokens")
        completion_tokens = performance.get("token_out") or performance.get("completion_tokens")

        total_cost = None
        if prompt_rate is not None and prompt_tokens is not None:
            total_cost = (prompt_tokens * prompt_rate)
        if completion_rate is not None and completion_tokens is not None:
            total_cost = (total_cost or 0.0) + (completion_tokens * completion_rate)

        return {
            "model": model,
            "pricing_usd": total_cost,
        }

    def _build_event(
        self,
        event_type: str,
        *,
        request_id: str,
        convo_id: str,
        session_id: str,
        stage_id: Optional[str],
        iteration: Optional[int],
        payload: Mapping[str, Any],
        metadata: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        event = {
            "timestamp": _utc_now_iso(),
            "event_type": event_type,
            "request_id": request_id,
            "convo_id": convo_id,
            "session_id": session_id,
            "stage_id": stage_id,
            "iteration": iteration,
            "payload": payload,
            "metadata": dict(metadata or {}),
        }
        return event

    def _dispatch(self, event: Mapping[str, Any]) -> None:
        if self._console_sink is not None:
            try:
                self._console_sink.render(event)
            except Exception:  # pragma: no cover - console telemetry failures must not block primary flow
                self._logger.exception("telemetry.console_render_failed", extra={"event_type": event.get("event_type")})

        if self._jsonl_writer is not None:
            try:
                self._jsonl_writer.write(event)
            except Exception:
                self._logger.exception("telemetry.jsonl_write_failed")

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(json.dumps(event, ensure_ascii=False))


__all__ = ["TelemetryBus", "RichTelemetryConsole"]
