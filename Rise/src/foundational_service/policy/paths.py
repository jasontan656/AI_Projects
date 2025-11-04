"""Path helpers scoped for foundational services."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from project_utility.config.paths import get_log_root as _project_log_root
from project_utility.config.paths import get_repo_root as _project_repo_root

__all__ = ["get_repo_root", "get_log_root", "get_shared_config_root"]


def get_repo_root() -> Path:
    """Return the repository root as resolved by project_utility."""

    return _project_repo_root()


def get_log_root() -> Path:
    """Return the shared log root directory."""

    return _project_log_root()


def get_shared_config_root(repo_root: Optional[Path | str] = None) -> Path:
    """Return the shared configuration directory for foundational services."""

    root = Path(repo_root).resolve() if repo_root is not None else get_repo_root()
    return root / "config"
