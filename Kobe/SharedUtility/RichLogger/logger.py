from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Callable


_LOGGER_INITIALIZED = False


class _Color:
    RESET = "\x1b[0m"
    DIM = "\x1b[2m"
    BOLD = "\x1b[1m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"


class _ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        color = _Color.BLUE
        if record.levelno >= logging.ERROR:
            color = _Color.RED
        elif record.levelno >= logging.WARNING:
            color = _Color.YELLOW
        elif record.levelno >= logging.INFO:
            color = _Color.GREEN
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        location = f"{record.module}:{record.lineno}"
        msg = super().format(record)
        return f"{_Color.DIM}{ts}{_Color.RESET} {color}{level:<7}{_Color.RESET} {_Color.BOLD}{location}{_Color.RESET} | {msg}"


def init_logging(level: str = "INFO") -> None:
    """
    初始化标准日志系统。

    参数
    - level: 日志级别字符串，默认 INFO。

    约束
    - 使用标准库 logging；控制台输出带颜色与精简上下文；
      如存在环境变量 `LOG_FILE`, 追加一个文件处理器（纯文本格式）。
    """
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    root = logging.getLogger()
    # 将 strata 清空，避免重复添加 handler
    for h in list(root.handlers):
        root.removeHandler(h)

    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(root.level)
    console.setFormatter(_ConsoleFormatter("%(message)s"))
    root.addHandler(console)

    log_file = os.getenv("LOG_FILE")
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(root.level)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(module)s:%(lineno)d | %(message)s"))
        root.addHandler(fh)

    _LOGGER_INITIALIZED = True


def install_traceback() -> None:
    """
    安装统一未捕获异常展示钩子。

    行为
    - 将 sys.excepthook 指向一个包装器：
      * 通过 logging.error 输出异常类型与消息（单行摘要）。
      * 紧随其后输出格式化的 traceback（多行）。
    - 使 CLI/脚本在各处获得一致的异常表现。
    """

    def _hook(exc_type, exc, tb):
        logger = logging.getLogger("RichLogger")
        summary = f"{exc_type.__name__}: {exc}"
        logger.error(summary)
        formatted = "".join(traceback.format_exception(exc_type, exc, tb))
        # 使用换行避免与单行摘要混淆
        for line in formatted.rstrip().splitlines():
            logger.error(line)

    sys.excepthook = _hook


def get_console() -> Callable[[str], None]:
    """返回简易 console 函数：`console(msg)` 等价于 `logging.info(msg)`。

    说明
    - 统一通过 logging 输出，避免 `print` 破坏结构化日志。
    """
    logger = logging.getLogger("console")

    def _console(message: str) -> None:
        logger.info(message)

    return _console

