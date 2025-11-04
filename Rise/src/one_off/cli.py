from __future__ import annotations

import runpy
import sys
from dataclasses import asdict
from typing import List

try:  # pragma: no cover
    import typer  # type: ignore[import]
except ImportError:  # pragma: no cover
    from . import _typer_stub as typer

from .registry import SCRIPTS, ScriptMetadata

app = typer.Typer(help="One-off utility commands.")


def _invoke_script(meta: ScriptMetadata, extra_args: List[str]) -> None:
    argv_backup = sys.argv[:]
    sys.argv = [meta.command, *extra_args]
    try:
        runpy.run_module(meta.module, run_name="__main__")
    finally:
        sys.argv = argv_backup


def _build_command(meta: ScriptMetadata) -> None:
    def callback(args: List[str] = typer.Argument(None, nargs=-1, help="Arguments passed to the script.")) -> None:
        typer.echo(f"[one-off] {meta.command}: {meta.summary} (owner={meta.owner}, danger={meta.danger_level})")
        _invoke_script(meta, list(args or []))

    app.command(name=meta.command, help=meta.summary)(callback)  # type: ignore[arg-type]


@app.command("list")
def list_commands() -> None:
    """List available one-off utility commands."""

    from rich.console import Console  # type: ignore[import]
    from rich.table import Table  # type: ignore[import]

    table = Table(title="One-off Utilities")
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Summary")
    table.add_column("Owner")
    table.add_column("Group")
    table.add_column("Danger")

    for meta in SCRIPTS:
        table.add_row(meta.command, meta.summary, meta.owner, meta.group, meta.danger_level)

    Console().print(table)


@app.command("show")
def show_metadata(command: str) -> None:
    """Show metadata for a specific command."""

    meta = next((item for item in SCRIPTS if item.command == command), None)
    if meta is None:
        raise typer.BadParameter(f"Unknown command '{command}'")

    from rich.console import Console  # type: ignore[import]
    from rich.panel import Panel  # type: ignore[import]

    description = "\n".join(f"{key}: {value}" for key, value in asdict(meta).items())
    Console().print(Panel(description, title=f"one_off::{meta.command}"))


for entry in SCRIPTS:
    _build_command(entry)
