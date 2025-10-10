#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lightweight settings loader for TaskQueue.

Reads from process environment (optionally preloaded by python-dotenv in main).
No external dependency on pydantic-settings to keep bootstrap minimal.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)  # 使用标准库函数 os.getenv 读取环境变量 name；可能返回 None（libraries）
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}  # 使用字符串方法 strip/lower 与集合成员测试解析布尔（builtins）


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))  # 使用 python 内置函数 int 将环境变量转换为整数（builtins）
    except Exception:
        return default


@dataclass(frozen=True)
class Settings:
    # Broker & backends
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")  # 使用环境变量 RABBITMQ_URL，缺省为本地 guest（libraries）
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")  # 使用环境变量 REDIS_URL，缺省第 0 库（libraries）
    enable_result_backend: bool = _get_bool("ENABLE_RESULT_BACKEND", False)  # 使用模块函数 _get_bool 解析布尔开关（modules）

    # Celery worker & message semantics
    default_queue: str = os.getenv("CELERY_DEFAULT_QUEUE", "q.tasks.default")  # 默认队列名（assignment）
    sharded_queue: str = os.getenv("CELERY_SHARDED_QUEUE", "q.tasks.sharded")  # 分片队列名（assignment）
    dlx_name: str = os.getenv("CELERY_DLX", "dlx.tasks")  # 死信交换机名（assignment）
    dlq_name: str = os.getenv("CELERY_DLQ", "q.tasks.dlq")  # 死信队列名（assignment）
    prefetch: int = _get_int("CELERY_PREFETCH", 1)  # Worker 预取数（modules）
    time_limit: int = _get_int("CELERY_TASK_TIME_LIMIT", 300)  # 硬超时秒数（modules）
    soft_time_limit: int = _get_int("CELERY_TASK_SOFT_TIME_LIMIT", 270)  # 软超时秒数（modules）


def load_settings() -> Settings:
    return Settings()  # 使用模块类 Settings 构造不可变配置实例并返回（modules）
