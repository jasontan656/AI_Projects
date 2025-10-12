from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from Kobe.TelegramCuration.services import parse_telegram_export


@pytest.mark.asyncio
async def test_parse_telegram_export_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        await parse_telegram_export("__nope__/missing.html", chat_id="@x")

