from __future__ import annotations
import json
import logging
from typing import Any, Mapping

from .console_handler import build_console_handler
from .file_handler import (
    build_app_file_handler,
    build_error_file_handler,
    build_module_file_handler,
)


class RichLoggerManager:
    _root_logger: logging.Logger | None = None

    @classmethod
    def bootstrap(
        cls,
        *,
        console_level: int = logging.DEBUG,
        console_kwargs: Mapping[str, Any] | None = None,
    ) -> logging.Logger:
        if cls._root_logger:
            return cls._root_logger
        logger = logging.getLogger("kobe")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(build_console_handler(level=console_level, console_kwargs=console_kwargs))
        logger.addHandler(build_app_file_handler(level=logging.DEBUG))
        logger.addHandler(build_error_file_handler())
        cls._root_logger = logger
        return logger

    @classmethod
    def for_node(
        cls,
        name: str,
        *,
        level: int | None = None,
        console_kwargs: Mapping[str, Any] | None = None,
    ) -> logging.Logger:
        if level is None and console_kwargs is None:
            raise ValueError("for_node() requires level or console_kwargs")
        root = cls.bootstrap()
        logger = logging.getLogger(f"{root.name}.{name}")
        logger.handlers.clear()
        node_level = level if level is not None else root.level
        logger.setLevel(node_level)
        logger.addHandler(build_console_handler(level=node_level, console_kwargs=console_kwargs))
        logger.addHandler(build_app_file_handler(level=node_level))
        logger.addHandler(build_error_file_handler())
        logger.addHandler(build_module_file_handler(name, level=logging.DEBUG))
        logger.propagate = False
        return logger

    @staticmethod
    def debug_json(logger: logging.Logger, *, event: str, payload: Mapping[str, Any] | None = None) -> None:
        data: dict[str, Any] = {"event": event}
        if payload:
            data.update(payload)
        logger.debug(json.dumps(data, ensure_ascii=False))

