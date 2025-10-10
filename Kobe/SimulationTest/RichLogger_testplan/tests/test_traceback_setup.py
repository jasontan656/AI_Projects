"""Traceback installation smoke test.

Ensures install_traceback wires to the shared Console and does not raise.
"""

from __future__ import annotations

import importlib
import unittest


class TestTracebackSetup(unittest.TestCase):
    def test_install_traceback_runs(self) -> None:
        tb_mod = importlib.import_module(
            "Kobe.SharedUtility.RichLogger.traceback_setup"
        )
        importlib.reload(tb_mod)
        # Should not raise
        tb_mod.install_traceback(show_locals=True, width=80, theme=None)

