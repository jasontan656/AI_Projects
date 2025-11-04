"""State management primitives for foundational bootstrap flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from aiogram import Bot, Dispatcher

__all__ = [
    "BootstrapState",
    "get_bootstrap_state",
    "set_bootstrap_state",
    "get_bootstrap_context",
    "set_bootstrap_context",
    "clear_bootstrap_state",
    "resolve_repo_root",
]


@dataclass(slots=True)
class BootstrapState:
    """Hold aiogram components needed throughout the runtime."""

    bot: Bot
    dispatcher: Dispatcher
    router: Dispatcher
    repo_root: Path
    redis_url: Optional[str] = None


_BOOTSTRAP_STATE: Optional[BootstrapState] = None
_BOOTSTRAP_CONTEXT: Dict[str, Any] = {}


def set_bootstrap_state(state: BootstrapState) -> None:
    """Persist the active bootstrap state for later reuse."""

    global _BOOTSTRAP_STATE
    _BOOTSTRAP_STATE = state


def set_bootstrap_context(context: Mapping[str, Any]) -> None:
    """Persist bootstrap metadata (policy, telemetry, etc.)."""

    _BOOTSTRAP_CONTEXT.clear()
    _BOOTSTRAP_CONTEXT.update(dict(context))


def get_bootstrap_state() -> BootstrapState:
    """Return the current bootstrap state or raise if unavailable."""

    if _BOOTSTRAP_STATE is None:
        raise RuntimeError("bootstrap state not initialised")
    return _BOOTSTRAP_STATE


def get_bootstrap_context() -> Dict[str, Any]:
    """Return a copy of the bootstrap context dictionary."""

    return dict(_BOOTSTRAP_CONTEXT)


def clear_bootstrap_state() -> None:
    """Reset cached bootstrap state and context."""

    global _BOOTSTRAP_STATE
    _BOOTSTRAP_STATE = None
    _BOOTSTRAP_CONTEXT.clear()


def resolve_repo_root(fallback: Optional[Path | str] = None) -> Path:
    """Determine the repository root based on state or filesystem."""

    if _BOOTSTRAP_STATE is not None:
        return _BOOTSTRAP_STATE.repo_root
    if fallback is not None:
        return Path(fallback).resolve()
    return Path(__file__).resolve().parents[4]
