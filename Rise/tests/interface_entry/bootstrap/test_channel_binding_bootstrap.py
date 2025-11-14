import pytest
from fastapi import FastAPI, HTTPException

from interface_entry.bootstrap import channel_binding_bootstrap as bootstrap


@pytest.mark.asyncio
async def test_start_channel_binding_monitor_handles_unavailable_telegram(monkeypatch):
    """Channel binding monitor should skip startup when Telegram capability is unavailable."""

    app = FastAPI()
    app.state.channel_binding_registry = object()

    monkeypatch.setattr(bootstrap, "_build_channel_binding_service", lambda: object())

    def _raise_http_exception() -> None:
        raise HTTPException(status_code=503, detail={"capability": "telegram"})

    monkeypatch.setattr(bootstrap, "get_telegram_client", _raise_http_exception)

    await bootstrap.start_channel_binding_monitor(app)

    assert getattr(app.state, "channel_binding_monitor", None) is None
