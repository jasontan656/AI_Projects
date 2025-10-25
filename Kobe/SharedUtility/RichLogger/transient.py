from __future__ import annotations

import traceback
from typing import Optional

from .logger import RichLoggerManager


def log_transient_retry(
    logger,
    *,
    stage: str,
    attempt: int,
    max_attempts: int,
    exc: BaseException,
    extra_message: Optional[str] = None,
) -> None:
    """统一记录瞬时网络抖动的重试日志。

    - 终端：输出一行简洁的提示，便于快速识别。
    - 文件：保留完整堆栈信息，方便排查细节。
    """

    short_reason = f"{exc.__class__.__name__}: {exc}"
    if extra_message:
        short_reason = f"{short_reason} | {extra_message}"

    logger.warning(
        "[transient] 网络抖动，正在重试（%s 第 %s/%s 次）：%s",
        stage,
        attempt,
        max_attempts,
        short_reason,
    )

    stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.debug("Transient retry detail (仅记录在文件日志中):\n%s", stack)


__all__ = ["log_transient_retry"]
