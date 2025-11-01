"""
Layout guard CLI aligned with 02.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
# Ensure repository root is available for absolute imports
REPO_ROOT = Path(__file__).resolve().parents[2]
repo_root_str = str(REPO_ROOT)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)

from SharedUtility.Contracts.behavior_contract import behavior_layout_guard
from SharedUtility.Contracts.toolcalls import LayoutMismatch


def main() -> int:
    repo_root = REPO_ROOT
    manifest_path = repo_root / "WorkPlan" / "layout_manifest.json"
    if not manifest_path.exists():
        sys.stderr.write("layout_manifest.json missing\n")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_tree = manifest.get("tree", "")
    ownership = manifest.get("ownership", {})
    try:
        result = behavior_layout_guard(repo_root, expected_tree, ownership)
    except LayoutMismatch as exc:
        diff = exc.diff or ""
        if diff:
            sys.stderr.write(diff + "\n")
        prompt_id = getattr(exc, "prompt_id", None)
        prompt_variables = getattr(exc, "prompt_variables", None)
        if prompt_id and prompt_variables:
            sys.stderr.write(f"{prompt_id}:{prompt_variables}\n")
        layout_report = getattr(exc, "layout_report", None)
        if layout_report:
            layout_report.setdefault("doc_id", manifest.get("doc_id", "unknown"))
            layout_report.setdefault("verified_with", "scripts/layout/check_layout.py")
            print(json.dumps(layout_report, ensure_ascii=False, indent=2))
        return 1

    diff = result.get("diff")
    if diff:
        sys.stderr.write(diff + "\n")
        return 1
    layout_report = result.get("layout_report", {})
    layout_report.setdefault("doc_id", manifest.get("doc_id", "unknown"))
    layout_report.setdefault("verified_with", "scripts/layout/check_layout.py")
    print(json.dumps(layout_report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


