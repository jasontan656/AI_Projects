"""
Validate Prompt Registry coverage against Doc24 mapping (WorkPlan/24.md).

This script ensures that:
- All categories exist in mapping
- Every prompt id listed in mapping exists in loaded registry (Config/prompts.*.yaml)

Exit non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
from core.prompt_registry import PROMPT_REGISTRY


# Mapping aligned with WorkPlan/24.md (Doc24)
DOC24_MAPPING: Dict[str, List[str]] = {
    "system": ["agent_triage_system"],
    "triage": ["agent_triage_system"],
    "summarize": ["telegram_history_summarize"],
    "compose": [
        "agency_compose_body",
        "agency_compose_header",
        "agent_consult_compose",
        "agent_plan_executor",
        "pricing_summary",
    ],
    "clarify": ["telegram_user_clarify"],
    "toolcall": ["telegram_toolcall_error"],
    "refusal": ["agent_refusal_policy", "core_schema_violation"],
    "welcome": ["telegram_welcome"],
    "help": ["telegram_prompt_missing"],
    "rate_limit": ["budget_alert"],
    "ops_alert": [
        "agency_pricing_alert",
        "aiogram_bootstrap_alert",
        "aiogram_bootstrap_status",
        "asset_cleanup_summary",
        "asset_guard_violation",
        "kb_index_missing_agency",
        "kb_index_ready",
        "kb_pipeline_failed",
        "kb_pipeline_success",
        "memory_checksum_mismatch",
        "memory_loader_alert",
        "memory_snapshot_ready",
        "plan_autodiscovery_status",
        "pricing_error",
        "telegram_streaming_error",
        "webhook_register_retry",
        "webhook_signature_fail",
    ],
    "dev_alert": [
        "core_envelope_attachment",
        "core_envelope_gap",
        "core_schema_alert",
        "core_schema_violation",
        "entry_layout_violation",
        "entry_missing_file",
        "kb_routing_conflict",
        "layout_missing_dir",
        "layout_owner_mismatch",
        "plan_alignment_gap",
        "plan_scope_ack",
        "selector_match_debug",
        "slot_missing",
        "slot_validation_error",
    ],
}


def main() -> int:
    missing: Dict[str, List[str]] = {}
    for category, prompt_ids in DOC24_MAPPING.items():
        for pid in prompt_ids:
            if not PROMPT_REGISTRY.has_prompt(pid):
                missing.setdefault(category, []).append(pid)

    if missing:
        sys.stderr.write("Prompt Registry coverage check failed (Doc24).\n")
        for category, ids in missing.items():
            sys.stderr.write(f"  - {category}: missing {', '.join(ids)}\n")
        return 2
    print("Prompt Registry coverage: OK (Doc24)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
