#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Baseline Celery tasks used by the initial setup.

Showcases long-running I/O and a sharded job pattern with retries.
Names are generic to serve as reusable templates.
"""

from __future__ import annotations

import random
import time
from typing import Any, Dict

from .app import app


@app.task(  # 在对象 app 上调用方法 task 注册 Celery 任务；启用重试/指数退避/抖动（method call）
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
)
def long_io(self, duration_sec: int = 2, fail_rate: float = 0.0, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:  # 使用函数定义声明任务入口并返回字典（builtins）
    """Simulate long I/O with optional transient errors.

    Args:
        duration_sec: seconds to sleep to mimic I/O
        fail_rate:   probability in [0,1] to raise a transient error
        payload:     arbitrary payload returned in the result
    """
    payload = payload or {}  # 使用赋值把空字典作为默认负载绑定到变量 payload（assignment）

    # Random transient failure to exercise retries
    if fail_rate > 0 and random.random() < fail_rate:  # 使用第三方库函数 random.random 产生 [0,1) 随机数并与阈值比较（libraries）
        raise RuntimeError("transient downstream error")  # 抛出异常；由装饰器配置触发自动重试（control）

    time.sleep(max(0, int(duration_sec)))  # 使用标准库函数 time.sleep 休眠指定秒数；确保非负（libraries/builtins）
    return {
        "kind": "long_io",
        "slept": int(duration_sec),
        "payload": payload,
    }


@app.task(  # 注册分片示例任务；最大重试 3 次（method call）
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def sharded_job(self, shard_key: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:  # 使用函数定义声明任务入口（builtins）
    """Simulate a small sharded job using a deterministic shard key.

    This is a single-task demo; full frontier/lease orchestration is a later step.
    """
    payload = payload or {}  # 使用赋值把空字典作为默认负载（assignment）
    shard_hash = hash(shard_key)  # 使用 python 内置函数 hash 计算分片键哈希（builtins）
    partition = shard_hash % 8  # 使用取模运算把哈希映射到 8 个分区（builtins）
    # Do pseudo work
    time.sleep(1)  # 模拟一小段 I/O（libraries）
    return {
        "kind": "sharded_job",
        "shard_key": shard_key,
        "partition": int(partition),
        "payload": payload,
    }
