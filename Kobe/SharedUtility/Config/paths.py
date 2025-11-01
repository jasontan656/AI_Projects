"""Centralized filesystem path helpers for Kobe services."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_MARKERS = ("SharedUtility", "OpenaiAgents")


def get_repo_root() -> Path:
    """Return the absolute path to the Kobe repository root."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if all((parent / marker).exists() for marker in _REPO_MARKERS):
            return parent
    # Fallback: assume SharedUtility/Config/..../.. layout
    return current.parents[2]


def get_log_root() -> Path:
    """Return the base directory where all runtime logs must live."""

    override = os.getenv("KOBE_LOG_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return get_repo_root() / "SharedUtility" / "logs"


__all__ = ["get_repo_root", "get_log_root"]
