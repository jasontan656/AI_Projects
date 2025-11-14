#!/usr/bin/env python3
from __future__ import annotations

"""
Rotate telemetry JSONL mirrors with optional dry-run support.

Usage:
    python scripts/rotate_telemetry.sh --dry-run
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from project_utility.config.paths import get_log_root


def _rotate(*, dry_run: bool) -> int:
    log_root = get_log_root().resolve()
    telemetry_path = log_root / "telemetry.jsonl"
    if not telemetry_path.exists():
        print(f"[rotate] telemetry file not found at {telemetry_path}")
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = log_root / f"telemetry-{timestamp}.jsonl"
    print(f"[rotate] would move {telemetry_path} -> {archive_path}")

    if dry_run:
        return 0

    telemetry_path.replace(archive_path)
    telemetry_path.touch()
    print(f"[rotate] rotation complete; new file created at {telemetry_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Rotate telemetry JSONL mirrors.")
    parser.add_argument("--dry-run", action="store_true", help="Only print intended actions.")
    args = parser.parse_args()
    return _rotate(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
