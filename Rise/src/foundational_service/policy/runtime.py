"""Runtime policy loading utilities."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from foundational_service.policy.paths import get_shared_config_root

__all__ = ["load_runtime_policy", "RuntimePolicyError"]

DEFAULT_RUNTIME_POLICY: Dict[str, Any] = {
    "determinism": {
        "temperature": 0,
        "top_p": 1,
        "seed": 20251027,
    },
    "output_mode": "markdown-structured",
    "versioning": {
        "prompt_version": "idx-v2",
        "doc_commit": "28a8d3a",
    },
    "pii_redaction": [
        {"field": "email", "mask": "***@***"},
        {"field": "phone", "mask": "***-****"},
        {"field": "id_number", "policy": "hash(sha256)"},
    ],
    "fingerprints": {
        "prompt_fingerprint": "8625086d0db1507b379f48d0547fb11053ebce40c984a1bd69177e11dfa2a6bb",
        "output_schema_id": "rise/contracts/output.schema.json@v1",
    },
    "policy": {
        "refusal_strategy": {
            "priority": ["safety", "contract", "budget", "rate_limit", "other"],
            "rules": {
                "safety": {
                    "on": ["safety_triggered", "policy_violation", "pii_detected"],
                    "action": "refuse",
                    "audit_log": True,
                },
                "contract": {
                    "on": ["output_validation_failed", "schema_mismatch", "drift_exceeded"],
                    "action": "repair_then_refuse_if_unfixable",
                    "max_repairs": 1,
                },
                "budget": {
                    "on": ["token_budget_exceeded", "summary_required"],
                    "action": "summarize_or_error",
                },
                "rate_limit": {
                    "on": ["rate_limited"],
                    "action": "retry_with_backoff",
                    "backoff_ms": [200, 400, 800],
                },
                "other": {
                    "on": ["other_error"],
                    "action": "escalate",
                },
            },
        },
    },
    "provider_capabilities": {
        "OpenAI.Responses": {
            "supports_seed": True,
            "supports_json_mode": True,
            "supports_function_call": True,
            "max_input_tokens": 200000,
            "notes": "优先使用；strict JSON 建议配合 schema 约束",
        },
        "OpenAI.ChatCompletions": {
            "supports_seed": True,
            "supports_json_mode": True,
            "supports_function_call": True,
            "max_input_tokens": 128000,
        },
        "Anthropic.Messages": {
            "supports_seed": False,
            "supports_json_mode": "partial",
            "supports_function_call": "tool_use",
            "max_input_tokens": 200000,
            "notes": "seed 不稳定时需放宽 drift 容忍或改用结构化提示",
        },
        "Custom": {
            "supports_seed": "unknown",
            "supports_json_mode": "unknown",
            "supports_function_call": "unknown",
            "max_input_tokens": "unknown",
        },
    },
    "nondeterminism": {
        "allow_without_seed": False,
        "drift_tolerance_tokens": 1,
        "assert_output_contract": True,
    },
    "generated-from": "30@28a8d3a",
    "tokens_budget": {
        "per_call_max_tokens": 3000,
        "per_flow_max_tokens": 6000,
        "summary_threshold_tokens": 2200,
    },
}


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
        try:
            raw = policy_file.read_text(encoding="utf-8")
        except FileNotFoundError as exc:  # pragma: no cover
            raise RuntimePolicyError(str(exc)) from exc
    else:
        policy_file = get_shared_config_root(repo_root_path) / "runtime_policy.json"
        if policy_file.exists():
            raw = policy_file.read_text(encoding="utf-8")
        else:
            return deepcopy(DEFAULT_RUNTIME_POLICY)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - invalid policy must fail fast
        raise RuntimePolicyError(f"runtime_policy_invalid_json: {exc}") from exc
