"""Non-TTY behavior tests for CLI output.

Ensures redirected output does not include ANSI escape sequences.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest


ANSI_RE = re.compile(r"\x1b\[")


class TestNonTTY(unittest.TestCase):
    def test_redirected_has_no_ansi(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "out.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "Kobe.SharedUtility.RichLogger.cli",
                        "--level",
                        "INFO",
                        "--no-color",
                        "--theme",
                        "high_contrast",
                    ],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            self.assertEqual(proc.returncode, 0)
            with open(out_path, "r", encoding="utf-8") as rf:
                text = rf.read()
            self.assertIsNone(ANSI_RE.search(text))
