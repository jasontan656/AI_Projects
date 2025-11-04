"""Runtime policy loading utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from foundational_service.policy.paths import get_shared_config_root

__all__ = ["load_runtime_policy", "RuntimePolicyError"]


class RuntimePolicyError(RuntimeError):
    """Raised when runtime policy cannot be loaded or parsed."""


def load_runtime_policy(
    repo_root: Path | str,
    runtime_policy_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Load the runtime policy JSON file and return its dictionary payload."""

    repo_root_path = Path(repo_root).resolve()
    if runtime_policy_path is not None:
        policy_file = Path(runtime_policy_path)
    else:
        policy_file = get_shared_config_root(repo_root_path) / "runtime_policy.json"

    try:
        raw = policy_file.read_text(encoding="utf-8")
    except FileNotFoundError as exc:  # pragma: no cover - propagate missing policy immediately
        raise RuntimePolicyError(str(exc)) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - invalid policy must fail fast
        raise RuntimePolicyError(f"runtime_policy_invalid_json: {exc}") from exc
