#!/usr/bin/env python
"""Generate KnowledgeBase snapshot metadata."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def collect_sources(source: Path) -> List[str]:
    entries: List[str] = []
    if not source.exists():
        return entries
    for item in sorted(source.rglob("*.yaml")):
        try:
            entries.append(str(item.relative_to(source)))
        except ValueError:
            entries.append(str(item))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate KB snapshot")
    parser.add_argument("--source", type=Path, default=Path("KnowledgeBase"), help="KnowledgeBase root")
    parser.add_argument("--output", type=Path, help="Snapshot output path")
    args = parser.parse_args()

    source = args.source
    snapshot: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "files": collect_sources(source),
    }
    output_path = args.output
    if output_path is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = Path("OpenaiAgents/UnifiedCS/memory/snapshots") / f"{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
