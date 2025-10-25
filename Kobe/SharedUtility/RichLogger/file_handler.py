from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
MODULES_DIR = LOG_DIR / "modules"
APP_LOG_PATH = LOG_DIR / "app.log"
ERROR_LOG_PATH = LOG_DIR / "error.log"


def _ensure_log_dir() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    MODULES_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR


def build_app_file_handler(level: int = logging.DEBUG) -> logging.Handler:
    _ensure_log_dir()
    handler = RotatingFileHandler(
        APP_LOG_PATH, mode="a", encoding="utf-8", maxBytes=50 * 1024 * 1024, backupCount=5
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    return handler


def build_error_file_handler() -> logging.Handler:
    _ensure_log_dir()
    handler = RotatingFileHandler(
        ERROR_LOG_PATH, mode="a", encoding="utf-8", maxBytes=50 * 1024 * 1024, backupCount=5
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    return handler


def build_module_file_handler(module_name: str, level: int = logging.DEBUG) -> logging.Handler:
    """Per-module rotating file handler: logs/modules/{module}.log.

    DEBUG 级别用于记录 rawdata（调用方把原始 JSON 作为 message 写入）。
    """
    _ensure_log_dir()
    safe = (
        module_name.replace(":", ".")
        .replace("/", ".")
        .replace("\\", ".")
        .replace(" ", "_")
    )
    path = MODULES_DIR / f"{safe}.log"
    handler = RotatingFileHandler(
        path, mode="a", encoding="utf-8", maxBytes=50 * 1024 * 1024, backupCount=5
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    return handler

