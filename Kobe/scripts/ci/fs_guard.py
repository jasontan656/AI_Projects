"""
Legacy asset guard per WorkPlan 11 (资产拆解与迁移).

generated-from: 11@local-dev
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


DOC_ID = "11"
DOC_COMMIT = "local-dev"

# Relative paths (case sensitive) that must remain removed/preserved according to WorkPlan 11.
REMOVED_DIRECTORIES = [
    Path("TelegramBot/legacy"),
    Path("config"),
]
PRESERVED_MODULES = [
    Path("OpenaiAgents"),
    Path("KnowledgeBase"),
    Path("SharedUtility"),
]


def _exists_exact(repo_root: Path, rel_path: Path) -> bool:
    """Case-sensitive existence check for the given relative path."""
    current = repo_root
    for part in rel_path.parts:
        try:
            entries = {p.name: p for p in current.iterdir()}
        except FileNotFoundError:
            return False
        if part not in entries:
            return False
        current = entries[part]
    return True


def _format_report_path(rel_path: Path) -> str:
    return f"Kobe/{rel_path.as_posix()}"


def scan_assets(repo_root: Path) -> Dict[str, List[str]]:
    repo_root = repo_root.resolve()
    removed: List[str] = []
    preserved: List[str] = []

    for rel in REMOVED_DIRECTORIES:
        if _exists_exact(repo_root, rel):
            removed.append(_format_report_path(rel))

    for rel in PRESERVED_MODULES:
        if _exists_exact(repo_root, rel):
            preserved.append(_format_report_path(rel))

    status = "violation" if removed else "clean"
    return {
        "doc_id": DOC_ID,
        "generated_from": f"{DOC_ID}@{DOC_COMMIT}",
        "removed": removed,
        "preserved": preserved,
        "status": status,
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    result = scan_assets(repo_root)
    output_path = repo_root / "WorkPlan" / "asset_report.json"
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 1 if result["status"] == "violation" else 0


if __name__ == "__main__":
    raise SystemExit(main())
