"""CLI integration tests for RichLogger.

Runs the module entry with different flags and checks exit codes/output.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    return subprocess.run(
        [sys.executable, "-m", "Kobe.SharedUtility.RichLogger.cli", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


class TestCLI(unittest.TestCase):
    def test_cli_debug_runs(self) -> None:
        proc = _run_cli(["--level", "DEBUG"])
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        # Expect human-formatted output from RichHandler without ANSI when redirected
        self.assertIn("Hello", proc.stdout)

    def test_cli_boom_errors(self) -> None:
        proc = _run_cli(["--boom"])
        self.assertNotEqual(proc.returncode, 0)
        # Rich traceback may render to stdout or stderr depending on environment
        combined = (proc.stdout + "\n" + proc.stderr).lower()
        self.assertIn("runtimeerror", combined)
