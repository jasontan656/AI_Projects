from __future__ import annotations

import importlib
import sys
from pathlib import Path

_SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if _SRC_PATH.exists():
    src_str = str(_SRC_PATH)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

_module = importlib.import_module("src.one_off")
globals().update({k: v for k, v in _module.__dict__.items() if not k.startswith("__")})
app = getattr(_module, "app", None)

sys.modules[__name__] = _module
