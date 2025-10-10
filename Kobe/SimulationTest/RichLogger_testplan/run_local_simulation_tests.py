"""Local RunAll-style orchestrator for Simulation Testing.

Implements a minimal subset of the SimulationTestingConstitution:
- Sequentially runs unit tests, CLI demo, and stress test for the RichLogger entry.
- Writes artifacts under SimulationTest/RichLogger_testplan.md/{results,logs}.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

from Kobe.SharedUtility.RichLogger import init_logging


# Use the workspace directory created by the plan (without .md suffix)
ARTIFACT_BASE = Path("D:/AI_Projects/Kobe/SimulationTest/RichLogger_testplan")
RESULTS_DIR = ARTIFACT_BASE / "results"
LOGS_DIR = ARTIFACT_BASE / "logs"


def _run(cmd: list[str], description: str = "") -> int:
    """Run command with live terminal output, return only exit code."""
    if description:
        print(f"\n{'='*70}")
        print(f"Running: {description}")
        print(f"{'='*70}")
    # Remove PIPE capture to show live output in terminal
    proc = subprocess.run(cmd)
    if description:
        print(f"{'='*70}")
        print(f"Completed: {description} (exit code: {proc.returncode})")
        print(f"{'='*70}\n")
    return proc.returncode


def run_unit_tests() -> dict:
    code = _run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "Kobe/SimulationTest/RichLogger_testplan/tests",
            "-p",
            "test_*.py",
            "-v",  # verbose mode for better visibility
        ],
        "Unit Tests"
    )
    return {"name": "unittest", "returncode": code}


def run_cli_demo() -> dict:
    code = _run(
        [
            sys.executable,
            "-m",
            "Kobe.SharedUtility.RichLogger.cli",
            "--level",
            "DEBUG",
        ],
        "CLI Demo"
    )
    return {"name": "cli_demo", "returncode": code}


def run_stress() -> dict:
    code = _run(
        [sys.executable, "-m", "Kobe.SimulationTest.RichLogger_testplan.tests.stress_richlogger"],
        "Stress Test"
    )
    return {"name": "stress", "returncode": code}


def run_progress_tests() -> dict:
    code = _run(
        [
            sys.executable,
            "-m",
            "unittest",
            "Kobe.SimulationTest.RichLogger_testplan.tests.test_progress_live_updates",
            "-v",
        ],
        "Progress Bar Tests (Live Updates)"
    )
    return {"name": "progress", "returncode": code}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local simulation tests")
    parser.add_argument("--entry", default="richlogger", help="entry module name")
    parser.add_argument(
        "--scenario",
        default="all",
        help="scenario name (all/cli/console/logging/traceback/progress)",
    )
    parser.add_argument("--all", action="store_true", help="run all stages")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # File logging per constitution
    init_logging(level="INFO", logfile=str(LOGS_DIR / "debug.log"))
    logging.getLogger(__name__).info(
        "Starting local simulation tests",
        extra={"entry": args.entry, "scenario": args.scenario, "all": args.all},
    )

    report: dict[str, object] = {"stages": []}

    def record(stage: dict) -> None:
        report["stages"].append(stage)

    if args.all or args.scenario in {"all", "console", "logging", "traceback"}:
        record(run_unit_tests())
    if args.all or args.scenario in {"all", "cli"}:
        record(run_cli_demo())
    if args.all or args.scenario in {"all", "logging"}:
        record(run_stress())
    if args.all or args.scenario in {"all", "progress"}:
        record(run_progress_tests())

    (RESULTS_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Ensure error log file exists for consumers expecting it in artifacts
    (LOGS_DIR / "error.log").touch(exist_ok=True)
    logging.getLogger(__name__).info("Simulation tests complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
