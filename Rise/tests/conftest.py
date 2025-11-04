from __future__ import annotations

import sys
import types
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Provide minimal aiogram stubs where required by foundational bootstrap utilities.
if "aiogram" not in sys.modules:
    aiogram_module = types.ModuleType("aiogram")

    class _DummyBot:  # pragma: no cover - shim for optional imports
        pass

    class _DummyDispatcher:  # pragma: no cover - shim for optional imports
        def __init__(self) -> None:
            self.workflow_data = {}

    setattr(aiogram_module, "Bot", _DummyBot)
    setattr(aiogram_module, "Dispatcher", _DummyDispatcher)
    sys.modules["aiogram"] = aiogram_module
