"""Helpers for loading interface entry manifests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from project_utility.config.paths import get_repo_root


def _default_manifest(repo_root: Path) -> Dict[str, Any]:
    return {
        "version": "v1.2.0",
        "app_py": str(repo_root / "app.py"),
        "infra": [str(repo_root / "src/interface_entry/bootstrap/app.py")],
        "core": [
            str(repo_root / "src/foundational_service/contracts/envelope.py"),
            str(repo_root / "src/foundational_service/contracts/telegram.py"),
            str(repo_root / "src/project_utility/context.py"),
        ],
        "telegrambot": [
            str(repo_root / "src/interface_entry/telegram/runtime.py"),
            str(repo_root / "src/interface_entry/telegram/routes.py"),
            str(repo_root / "src/interface_entry/telegram/handlers.py"),
            str(repo_root / "src/interface_entry/telegram/adapters.py"),
        ],
    }


def load_top_entry_manifest() -> Dict[str, Any]:
    repo_root = get_repo_root()
    manifest_path = repo_root / "WorkPlan" / "top_entry_manifest.json"
    if manifest_path.exists():
        raw = manifest_path.read_text(encoding="utf-8")
        normalized = raw.replace("{REPO_ROOT}", str(repo_root))
        return json.loads(normalized)
    return _default_manifest(repo_root)


def load_doc_context() -> Dict[str, str]:
    doc_id = os.getenv("DOC_ID", "WorkPlan/top_entry_manifest.json")
    doc_commit = os.getenv("DOC_COMMIT", "unknown")
    return {"doc_id": doc_id, "doc_commit": doc_commit}


__all__ = ["load_top_entry_manifest", "load_doc_context"]
