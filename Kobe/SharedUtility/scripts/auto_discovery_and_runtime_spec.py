"""Auto-Discovery 仓库锚点扫描与全局运行参数加载。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence, TypedDict

TITLE: str = "Auto-Discovery 仓库锚点扫描 与 全局运行参数"


class AutoDiscoveryReport(TypedDict, total=False):
    repo_root: str
    existing_dirs: Sequence[str]
    missing_dirs: Sequence[str]
    status: str
    actions: Sequence[str]
    env_files: Sequence[str]
    notes: str
    duration_ms: float


class DeterminismConfig(TypedDict):
    temperature: float
    top_p: float
    seed: int


class TokenBudgetConfig(TypedDict):
    per_call_max_tokens: int
    per_flow_max_tokens: int
    summary_threshold_tokens: int


class VersioningConfig(TypedDict):
    prompt_version: str
    doc_commit: str


class PIIRedactionRule(TypedDict, total=False):
    field: str
    mask: str
    policy: str


class FingerprintsConfig(TypedDict):
    prompt_fingerprint: str
    output_schema_id: str


class GlobalRuntimePolicy(TypedDict):
    determinism: DeterminismConfig
    token_budget: TokenBudgetConfig
    output_mode: str
    versioning: VersioningConfig
    pii_redaction: Sequence[PIIRedactionRule]
    fingerprints: FingerprintsConfig


TOKENS_BUDGET_KEYS: tuple[str, ...] = (
    "per_call_max_tokens",
    "per_flow_max_tokens",
    "summary_threshold_tokens",
)

METADATA_FIELDS: tuple[str, ...] = ("chat_id", "convo_id", "channel", "language")
LANGUAGE_PATTERN: str = r"^[a-z]{2}(-[A-Z]{2})?$"

TELEMETRY_FIELDS: tuple[str, ...] = (
    "request_id",
    "trace_id",
    "latency_ms",
    "validation_ms",
    "status_code",
    "error_hint",
)


def scan_repo(repo_root: Path, expected_dirs: Sequence[str]) -> AutoDiscoveryReport:
    existing: list[str] = []
    missing: list[str] = []
    for name in expected_dirs:
        candidate = repo_root / name
        if candidate.exists():
            existing.append(name)
        else:
            missing.append(name)
    status = "ready" if not missing else "needs_setup"
    actions = (
        ["app.py created; core/Config/Contracts present (placeholders)"]
        if status == "ready"
        else ["create missing directories"]
    )
    return {
        "repo_root": str(repo_root),
        "existing_dirs": existing,
        "missing_dirs": missing,
        "status": status,
        "actions": actions,
        "env_files": [".env"],
        "notes": "OpenaiAgents/, TelegramAPI/, Tests/ 当前为空占位；仅用于后续重建",
    }


def load_global_runtime_policy(policy: Mapping[str, Any]) -> GlobalRuntimePolicy:
    determinism_raw = policy.get("determinism", {})
    determinism = DeterminismConfig(
        temperature=float(determinism_raw.get("temperature", 0.0)),
        top_p=float(determinism_raw.get("top_p", 1.0)),
        seed=int(determinism_raw.get("seed", 0)),
    )
    if determinism["temperature"] != 0 or determinism["top_p"] != 1:
        raise ValueError("determinism must remain temperature=0, top_p=1")

    token_budget_raw = policy.get("token_budget") or policy.get("tokens_budget", {})
    token_budget = TokenBudgetConfig(
        per_call_max_tokens=int(token_budget_raw.get("per_call_max_tokens", 0)),
        per_flow_max_tokens=int(token_budget_raw.get("per_flow_max_tokens", 0)),
        summary_threshold_tokens=int(token_budget_raw.get("summary_threshold_tokens", 0)),
    )
    for key in TOKENS_BUDGET_KEYS:
        if token_budget[key] <= 0:
            raise ValueError(f"token_budget.{key} must be positive")

    output_mode = str(policy.get("output_mode", "markdown-structured"))
    if output_mode not in {"markdown-structured", "strict-json"}:
        raise ValueError(f"unsupported output_mode: {output_mode}")

    versioning_raw = policy.get("versioning", {})
    versioning = VersioningConfig(
        prompt_version=str(versioning_raw.get("prompt_version", "")),
        doc_commit=str(versioning_raw.get("doc_commit", "")),
    )

    pii_rules = [
        PIIRedactionRule(
            field=str(rule.get("field", "")),
            mask=str(rule.get("mask", "")) if rule.get("mask") else "",
            policy=str(rule.get("policy", "")) if rule.get("policy") else "",
        )
        for rule in policy.get("pii_redaction", [])
    ]

    fingerprints_raw = policy.get("fingerprints", {})
    fingerprints = FingerprintsConfig(
        prompt_fingerprint=str(fingerprints_raw.get("prompt_fingerprint", "")),
        output_schema_id=str(fingerprints_raw.get("output_schema_id", "")),
    )

    return GlobalRuntimePolicy(
        determinism=determinism,
        token_budget=token_budget,
        output_mode=output_mode,
        versioning=versioning,
        pii_redaction=pii_rules,
        fingerprints=fingerprints,
    )
