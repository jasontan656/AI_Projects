"""Load telemetry configuration for UnifiedCS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

from project_utility.config.paths import get_log_root, get_repo_root


def _default_config() -> Dict[str, Any]:
    return {
        "telemetry": {
            "enabled": False,
            "iteration_counter": True,
            "console": {
                "handler": "rich",
                "force_terminal": True,
                "width": 120,
                "highlight": False,
                "markup": True,
                "soft_wrap": True,
                "legacy_windows": False,
                "theme": "default",
                "tree": True,
                "prompt_preview_chars": 280,
                "state_snapshot_keys": ["nextStep", "latest_response_id", "guard"],
                "show_state_diff": True,
                "highlight_latency_threshold_ms": 1500,
                "highlight_token_threshold": 4000,
                "show_cost": True,
                "show_annotations": True,
                "mirror_path": str((get_log_root() / "unifiedcs.console.log").resolve()),
            },
            "jsonl": {
                "enabled": True,
                "path": str((get_log_root() / "unifiedcs.telemetry.jsonl").resolve()),
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
    repo_root = get_repo_root()

    config_path_env = os.getenv("TELEMETRY_CONFIG")
    if config_path_env:
        config_path = Path(config_path_env)
    else:
        config_path = repo_root / "openai_agents" / "Config" / "telemetry.yaml"

    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            config = _deep_merge(config, data)
        except Exception as exc:  # pragma: no cover - surface config issues quickly during diagnostics
            raise RuntimeError(f"Failed to load telemetry config from {config_path}") from exc

    telemetry_cfg = config.get("telemetry", {})
    json_cfg = telemetry_cfg.get("jsonl", {})
    path_str = json_cfg.get("path")
    if path_str:
        json_path = Path(path_str)
        if not json_path.is_absolute():
            json_path = (repo_root / json_path).resolve()
        json_cfg["path"] = str(json_path)
    else:
        json_cfg["path"] = str((get_log_root() / "unifiedcs.telemetry.jsonl").resolve())

    console_cfg = telemetry_cfg.get("console", {})
    mirror_path = console_cfg.get("mirror_path")
    if mirror_path:
        mirror_obj = Path(str(mirror_path))
        if not mirror_obj.is_absolute():
            mirror_obj = (repo_root / mirror_obj).resolve()
        console_cfg["mirror_path"] = str(mirror_obj)
    elif "mirror_path" not in console_cfg:
        console_cfg["mirror_path"] = str((get_log_root() / "unifiedcs.console.log").resolve())

    config["telemetry"] = telemetry_cfg
    return config


__all__ = ["load_telemetry_config"]
