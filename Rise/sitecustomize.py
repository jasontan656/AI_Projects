"""Ensure the repository's `src/` directory is importable when running scripts locally."""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

_SRC_PATH = Path(__file__).resolve().parent / "src"
if _SRC_PATH.exists():
    src_str = str(_SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

_suppressed_warnings = [
    ("aiohttp.client", ResourceWarning, "Unclosed client session"),
    ("aio_pika", RuntimeWarning, "coroutine 'RobustConnection.close' was never awaited"),
]
_warn_logger = logging.getLogger("project_utility.warnings")
for module_name, category, message in _suppressed_warnings:
    warnings.filterwarnings("once", category=category, message=message, module=module_name)
    _warn_logger.info(
        "warning.suppressed",
        extra={"module": module_name, "category": category.__name__, "message": message},
    )
