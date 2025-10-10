"""Console configuration tests for RichLogger.

Covers env/option merging, idempotency, and basic attributes.
"""

from __future__ import annotations

import importlib
import os
import unittest


class TestConsoleOptions(unittest.TestCase):
    def setUp(self) -> None:  # reset console module to clear singleton
        # Import submodule directly so we can reload its module-level singletons
        self.console_mod = importlib.import_module(
            "Kobe.SharedUtility.RichLogger.console"
        )
        importlib.reload(self.console_mod)

        # Clean related env vars between tests
        for k in ("RICH_NO_COLOR", "RICH_THEME", "RICH_WIDTH"):
            os.environ.pop(k, None)

    def test_no_color_via_options(self) -> None:
        c = self.console_mod.init_console({"no_color": True, "theme": "default"})
        self.assertTrue(getattr(c, "no_color", False))
        # Idempotency: second call returns the same instance
        c2 = self.console_mod.init_console({})
        self.assertIs(c, c2)

    def test_env_overrides_and_width(self) -> None:
        os.environ["RICH_NO_COLOR"] = "1"
        os.environ["RICH_THEME"] = "high_contrast"
        os.environ["RICH_WIDTH"] = "100"

        c = self.console_mod.init_console({})
        self.assertTrue(getattr(c, "no_color", False))
        # Width is an optional argument; rich Console stores it as .width
        # Only assert it’s either None or our requested width to avoid platform quirks
        if getattr(c, "width", None) is not None:
            self.assertEqual(c.width, 100)

