"""Load telemetry configuration for UnifiedCS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "SharedUtility").exists() and (parent / "OpenaiAgents").exists():
            return parent
    # Fallback to the immediate project directory (Kobe)
    return current.parents[2]


def _default_config() -> Dict[str, Any]:
    return {
        "telemetry": {
            "enabled": False,
            "iteration_counter": True,
            "console": {
                "handler": "rich",
                "theme": "default",
                "tree": True,
                "prompt_preview_chars": 280,
                "state_snapshot_keys": ["nextStep", "latest_response_id", "guard"],
                "show_state_diff": True,
                "highlight_latency_threshold_ms": 1500,
                "highlight_token_threshold": 4000,
                "show_cost": True,
                "show_annotations": True,
            },
            "jsonl": {
                "enabled": True,
                "path": "SharedUtility/logs/unifiedcs.telemetry.jsonl",
                "ensure_dir": True,
            },
            "redact": {
                "prompt": False,
                "user_input": False,
                "state": False,
                "output": False,
            },
            "pricing": {},
            "events": {
                "stage_start": True,
                "stage_end": True,
                "guard_event": True,
                "cache_event": True,
                "bridge_summary": True,
                "error_event": True,
            },
        }
    }


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_telemetry_config() -> Dict[str, Any]:
    """Load telemetry configuration, merging defaults with YAML overrides."""

    config = _default_config()
    repo_root = _repo_root()

    config_path_env = os.getenv("TELEMETRY_CONFIG")
    if config_path_env:
        config_path = Path(config_path_env)
    else:
        config_path = repo_root / "OpenaiAgents" / "Config" / "telemetry.yaml"

    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            config = _deep_merge(config, data)
        except Exception as exc:  # pragma: no cover - 诊断时需快速暴露问题
            raise RuntimeError(f"Failed to load telemetry config from {config_path}") from exc

    telemetry_cfg = config.get("telemetry", {})
    json_cfg = telemetry_cfg.get("jsonl", {})
    path_str = json_cfg.get("path")
    if path_str:
        json_cfg["path"] = str((repo_root / path_str).resolve())

    config["telemetry"] = telemetry_cfg
    return config


__all__ = ["load_telemetry_config"]
