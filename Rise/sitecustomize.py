"""Ensure the repository's `src/` directory is importable when running scripts locally."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_PATH = Path(__file__).resolve().parent / "src"
if _SRC_PATH.exists():
    src_str = str(_SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
