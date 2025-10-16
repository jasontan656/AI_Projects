"""
Bridge logger endpoint and helper.
Purpose: accept mirrored events and append NDJSON lines to app log.
This avoids console logging conflicts and keeps boundary logs simple.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


LOG_DIR = Path(__file__).resolve().parents[1] / "SharedUtility" / "RichLogger" / "logs"
APP_LOG_PATH = LOG_DIR / "app.log"


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _append_ndjson_line(record: Dict[str, Any]) -> None:
    _ensure_log_dir()
    # Ensure minimal size and valid JSON per line
    with APP_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


async def emit_bridge_event(event: Dict[str, Any]) -> None:
    """Non-blocking helper used internally to mirror events to file."""
    record = {
        "ts": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        **event,
    }
    # File IO kept synchronous but scheduled in default loop executor
    await asyncio.get_running_loop().run_in_executor(None, _append_ndjson_line, record)


router = APIRouter()


@router.post("/bridge/log")
async def bridge_log(request: Request) -> JSONResponse:
    """Accept any JSON and append as NDJSON with timestamp (internal use)."""
    body = await request.json()
    await emit_bridge_event({"event": "bridge.log", **(body if isinstance(body, dict) else {"body": body})})
    return JSONResponse({"ok": True})


