"""
Centralised filesystem path helpers for Rise services.

Relocated from `shared_utility.config.paths` to the project utility layer and updated to work with
the repository's `src/` layout.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_MARKERS = ("src", "config", "AI_WorkSpace")


def get_repo_root() -> Path:
    """Return the absolute path to the Rise repository root."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if all((parent / marker).exists() for marker in _REPO_MARKERS):
            return parent
    # Fallback: ascend from src/project_utility/config/paths.py to repository root.
    return current.parents[3]


def get_log_root() -> Path:
    """Return the base directory where all runtime logs must live."""

    override = os.getenv("KOBE_LOG_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return get_repo_root() / "var" / "logs"


__all__ = ["get_repo_root", "get_log_root"]
