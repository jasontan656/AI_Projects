from __future__ import annotations

import sys
import types

import pytest

# Stub cryptography.fernet to avoid optional dependency imports during tests.
fernet_module = types.ModuleType("cryptography.fernet")
fernet_module.Fernet = object
fernet_module.InvalidToken = Exception
sys.modules.setdefault("cryptography", types.ModuleType("cryptography"))
sys.modules["cryptography.fernet"] = fernet_module

from interface_entry.http import dependencies
from interface_entry.http.dependencies.channel import (
    get_telegram_client,
    prime_telegram_client,
    reset_channel_dependencies,
)
from interface_entry.http.dependencies.telemetry import (
    DisabledTaskRuntime,
    get_task_runtime,
    reset_telemetry_dependencies,
)
from interface_entry.http.dependencies.workflow import get_prompt_collection


@pytest.mark.asyncio
async def test_get_prompt_collection_resolves_named_collection() -> None:
    class DummyDatabase(dict):
        def __getitem__(self, name: str):
            return f"collection:{name}"

    result = await get_prompt_collection(DummyDatabase())

    assert result == "collection:prompts"


def test_prime_telegram_client_caches_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyClient:
        def __init__(self) -> None:
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True

    monkeypatch.setattr("interface_entry.http.dependencies.channel.TelegramClient", DummyClient)

    try:
        first = prime_telegram_client()
        second = get_telegram_client()
        assert first is second
    finally:
        reset_channel_dependencies()


def test_get_task_runtime_returns_disabled_when_capability_missing() -> None:
    class DummyRegistry:
        def require(self, name: str, *, hard: bool = True) -> None:  # pragma: no cover - noop
            return

        def is_available(self, name: str) -> bool:
            return name != "redis"

        def get_state(self, name: str):
            return types.SimpleNamespace(detail="offline")

    dependencies.set_capability_registry(DummyRegistry())  # type: ignore[arg-type]
    try:
        runtime = get_task_runtime()
        assert isinstance(runtime, DisabledTaskRuntime)
    finally:
        dependencies.set_capability_registry(None)  # type: ignore[arg-type]
        reset_telemetry_dependencies()
