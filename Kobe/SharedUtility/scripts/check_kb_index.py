#!/usr/bin/env python
"""CLI entrypoint for KnowledgeBase pipeline validation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from SharedUtility.Contracts.behavior_contract import behavior_kb_pipeline


def load_config(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid pipeline config JSON: {exc}") from exc
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate KnowledgeBase index pipeline")
    parser.add_argument("--config", type=Path, default=Path("KnowledgeBase/kb_pipeline.json"), help="Pipeline configuration JSON")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root (default: cwd)")
    args = parser.parse_args()

    config_path = args.config if args.config.is_absolute() else args.repo_root / args.config
    if not config_path.exists():
        raise SystemExit(f"pipeline config not found: {config_path}")

    config = load_config(config_path)
    result = behavior_kb_pipeline(config=config, repo_root=args.repo_root)
    report = result.get("kb_pipeline_report", {})
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

