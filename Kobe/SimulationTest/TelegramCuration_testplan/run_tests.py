#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def check_environment() -> bool:
    try:
        from test_config import TestConfig  # type: ignore
        from utils.service_checker import ServiceChecker  # type: ignore
    except Exception as e:  # noqa: BLE001
        print("[ERROR] Missing dependencies to run environment checks:", e)
        print("Install first: pip install -r requirements.txt")
        return False
    cfg = TestConfig()
    sc = ServiceChecker(cfg)
    status = sc.check_all()
    print("=" * 60)
    print("Environment Check")
    print("=" * 60)
    all_ok = True
    for k in ["fastapi", "mongodb", "redis", "rabbitmq"]:
        v = status.get(k, False)
        mark = "OK" if v else "FAIL"
        print(f"  [{mark}] {k}")
        if k == "fastapi" and not v:
            all_ok = False
    print("=" * 60)
    if not all_ok:
        print("[ERROR] Core service 'fastapi' is not running.")
    return all_ok


def prepare_fixtures() -> None:
    print("\nPreparing fixtures...")
    from test_data.generators.html_generator import TelegramHTMLGenerator

    fixtures_dir = Path("test_data/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    gen = TelegramHTMLGenerator(seed=42)
    small = fixtures_dir / "sample_small.html"
    if not small.exists():
        small.write_text(gen.generate_html(count=18), encoding="utf-8")
        print(f"  Created: {small}")
    empty = fixtures_dir / "sample_empty.html"
    if not empty.exists():
        empty.write_text(gen.generate_html(count=0), encoding="utf-8")
        print(f"  Created: {empty}")
    print("Fixtures ready.\n")


def run_pytest(extra: list[str] | None = None) -> int:
    cmd = [sys.executable, "-m", "pytest", "test_cases/"]
    if extra:
        cmd.extend(extra)
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Executor")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--priority", type=str, help="p0/p1/p2/p3")
    parser.add_argument("--parallel", type=int, help="xdist workers")
    args, unknown = parser.parse_known_args()

    if not check_environment():
        return 1
    if args.check_only:
        return 0

    prepare_fixtures()
    extra = list(unknown)
    if args.priority:
        extra += ["-m", args.priority]
    if args.parallel:
        extra += ["-n", str(args.parallel)]
    return run_pytest(extra)


if __name__ == "__main__":
    raise SystemExit(main())
