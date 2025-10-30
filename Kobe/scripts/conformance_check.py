"""
Conformance checker enforcing 02 requirements.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from core.prompt_registry import PromptRegistry

DOC_ID = "02"
DOC_COMMIT = "28a8d3a"
REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_FILES = [
    REPO_ROOT / "app.py",
    REPO_ROOT / "core" / "schema.py",
    REPO_ROOT / "core" / "adapters.py",
    REPO_ROOT / "core" / "context.py",
    REPO_ROOT / "TelegramBot" / "runtime.py",
    REPO_ROOT / "TelegramBot" / "routes.py",
    REPO_ROOT / "TelegramBot" / "handlers" / "message.py",
    REPO_ROOT / "TelegramBot" / "adapters" / "telegram.py",
    REPO_ROOT / "TelegramBot" / "adapters" / "response.py",
    REPO_ROOT / "Contracts" / "behavior_contract.py",
    REPO_ROOT / "Contracts" / "toolcalls.py",
    REPO_ROOT / "Contracts" / "auto_discovery.schema.json",
    REPO_ROOT / "Contracts" / "core_envelope.schema.json",
    REPO_ROOT / "Contracts" / "output.schema.json",
    REPO_ROOT / "Contracts" / "asset_report.schema.json",
    REPO_ROOT / "Contracts" / "telegram_adapter.schema.json",
    REPO_ROOT / "Contracts" / "agent_request.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "aiogram_bootstrap.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "asset_transition.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "core_envelope.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "telegram_adapter.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "webhook_service.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "agents_bridge.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "layout_tree.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "top_entry.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "agent_generic.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "agency_compose.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "budget.schema.json",
    REPO_ROOT / "Contracts" / "prompts" / "strings.schema.json",
    REPO_ROOT / "Config" / "runtime_policy.json",
    REPO_ROOT / "scripts" / "check_anchors.py",
    REPO_ROOT / "scripts" / "ci" / "fs_guard.py",
]
SAMPLE_DIR = REPO_ROOT / "WorkPlan" / "Samples"
OUTPUT_REPORT = REPO_ROOT / "WorkPlan" / "conformance.report.json"

def fingerprint(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def ensure_generated_tags() -> list[str]:
    missing: list[str] = []
    tag = f"{DOC_ID}@{DOC_COMMIT}"
    for file in GENERATED_FILES:
        text = file.read_text(encoding="utf-8")
        if tag not in text:
            missing.append(str(file.relative_to(REPO_ROOT)))
    return missing


def ensure_prompts() -> list[str]:
    try:
        PromptRegistry(REPO_ROOT / "Config")
    except ValueError as exc:
        return [str(exc)]
    return []


def ensure_samples() -> list[str]:
    violations: list[str] = []
    if not SAMPLE_DIR.exists():
        return ["WorkPlan/Samples missing"]
    core_samples = list(SAMPLE_DIR.glob("core_envelope_sample_*.json"))
    if len(core_samples) < 3:
        violations.append("CoreEnvelope golden samples < 3")
    counter_samples = list(SAMPLE_DIR.glob("core_envelope_counter_*.json"))
    if len(counter_samples) < 2:
        violations.append("CoreEnvelope counter samples < 2")
    asset_samples = list(SAMPLE_DIR.glob("asset_report_sample_*.json"))
    if len(asset_samples) < 3:
        violations.append("Asset report golden samples < 3")
    asset_counter = list(SAMPLE_DIR.glob("asset_report_counter_*.json"))
    if len(asset_counter) < 2:
        violations.append("Asset report counter samples < 2")
    return violations


def ensure_output_schema() -> list[str]:
    from jsonschema import Draft202012Validator

    schema_path = REPO_ROOT / "Contracts" / "output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    sample = {
        "agent_output": {
            "chat_id": "1001",
            "text": "Echo",
            "parse_mode": "MarkdownV2",
            "status_code": 200,
            "error_hint": "",
        }
    }
    Draft202012Validator(schema).validate(sample)
    return []


def build_fingerprints(files: Iterable[Path]) -> dict[str, str]:
    return {str(path.relative_to(REPO_ROOT)): fingerprint(path) for path in files}


def main() -> int:
    missing = ensure_generated_tags()
    violations = []
    violations.extend(ensure_prompts())
    violations.extend(ensure_samples())
    violations.extend(ensure_output_schema())

    status = 100 if not missing and not violations else 0
    report = {
        "doc_id": DOC_ID,
        "doc_commit": DOC_COMMIT,
        "conformance": status,
        "missing": missing,
        "violations": violations,
        "fingerprints": build_fingerprints(GENERATED_FILES),
    }
    OUTPUT_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if status == 100 else 1


if __name__ == "__main__":
    raise SystemExit(main())

