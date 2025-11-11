from __future__ import annotations

import argparse
import logging
import os
from typing import Optional

from fastapi import FastAPI

from interface_entry.bootstrap.application_builder import (
    TelegramWebhookUnavailableError,
    configure_application,
    perform_clean_startup,
)

log = logging.getLogger("interface_entry.app")

CLI_DESCRIPTION = "Rise Telegram service"

app: Optional[FastAPI] = None


def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="Rise Telegram Bridge", version="1.0.0")
    configure_application(fastapi_app)
    return fastapi_app


def configure_arg_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--clean",
        action="store_true",
        help="启动前清空日志、runtime_state 目录，并重置 Redis 与 MongoDB 数据库",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="绑定主机地址 (默认 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="监听端口 (默认 8000)",
    )


def handle_cli(args: argparse.Namespace) -> None:
    global app  # type: ignore[assignment]
    try:
        if getattr(args, "clean", False):
            perform_clean_startup()
        app = create_app()
    except TelegramWebhookUnavailableError as exc:
        log.critical("Startup aborted: %s", exc)
        raise

    import uvicorn

    uvicorn.run(
        app,
        host=getattr(args, "host", "0.0.0.0"),
        port=getattr(args, "port", int(os.getenv("PORT", "8000"))),
        log_config=None,
    )


try:
    app = create_app()
except TelegramWebhookUnavailableError as exc:
    log.critical("Startup aborted: %s", exc)
    raise
