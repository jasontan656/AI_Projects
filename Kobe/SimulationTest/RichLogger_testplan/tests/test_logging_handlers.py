"""Logging initialization tests for RichLogger.

Validates idempotent RichHandler install, env precedence, and file handler format.
"""

from __future__ import annotations

import importlib
import logging
import os
import tempfile
import unittest


def _reset_logger_module():
    mod = importlib.import_module("Kobe.SharedUtility.RichLogger.logger")
    return importlib.reload(mod)


class TestLoggingHandlers(unittest.TestCase):
    def setUp(self) -> None:
        # Clean env and reset module singletons
        for k in ("LOG_LEVEL", "RICH_LOG_LEVEL"):
            os.environ.pop(k, None)
        self.logger_mod = _reset_logger_module()

    def test_single_rich_handler_installed(self) -> None:
        self.logger_mod.init_logging(level="DEBUG")
        root = logging.getLogger()
        rich_handlers = [
            h for h in root.handlers if h.__class__.__name__ == "RichHandler"
        ]
        self.assertEqual(len(rich_handlers), 1)
        self.assertEqual(root.getEffectiveLevel(), logging.DEBUG)

    def test_env_precedence(self) -> None:
        # RICH_LOG_LEVEL applies when LOG_LEVEL is not set
        os.environ["RICH_LOG_LEVEL"] = "ERROR"
        self.logger_mod = _reset_logger_module()
        self.logger_mod.init_logging()  # no level arg
        root = logging.getLogger()
        self.assertEqual(root.getEffectiveLevel(), logging.ERROR)

        # LOG_LEVEL overrides RICH_LOG_LEVEL
        os.environ["LOG_LEVEL"] = "WARNING"
        self.logger_mod = _reset_logger_module()
        self.logger_mod.init_logging()  # no level arg
        root = logging.getLogger()
        self.assertEqual(root.getEffectiveLevel(), logging.WARNING)

    def test_file_handler_utf8_and_format(self) -> None:
        # Reset module to allow re-installing handlers with logfile
        self.logger_mod = _reset_logger_module()
        with tempfile.TemporaryDirectory() as td:
            log_path = os.path.join(td, "test.log")
            self.logger_mod.init_logging(level="INFO", logfile=log_path)

            log = logging.getLogger("test.logger")
            log.info("hello world")

            with open(log_path, "r", encoding="utf-8") as f:
                line = f.readline().strip()
            # Expected columns: time | LEVEL | logger name | message
            self.assertIn(" | ", line)
            self.assertGreaterEqual(line.count(" | "), 3)
            self.assertIn("hello world", line)

            # Ensure file handler is released so temp dir can be cleaned up on Windows
            logging.shutdown()
