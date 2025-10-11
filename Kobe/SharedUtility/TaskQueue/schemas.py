#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pydantic v3 models for TaskQueue API payloads."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TaskStart(BaseModel):
    task: str = Field(pattern=r"^[a-z0-9_:.]{1,64}$")  # 通用 slug：小写字母/数字/下划线/冒号/点，长度 1-64
    duration_sec: int | None = Field(default=2, ge=0)  # 使用 Field 指定默认值与非负下界（libraries）
    fail_rate: float | None = Field(default=0.0, ge=0.0, le=1.0)  # 使用 Field 指定 0-1 闭区间（libraries）
    shard_key: str | None = None  # 使用赋值把可选分片键绑定到模型字段（assignment）
    payload: Dict[str, Any] | None = None  # 使用赋值把任意负载绑定到模型字段（assignment）


class TaskStatus(BaseModel):
    task_id: str  # 任务 ID（assignment）
    state: str  # 标准状态：PENDING/STARTED/RETRY/SUCCESS/FAILURE（assignment）
    ready: bool  # 是否就绪（assignment）


class TaskResult(BaseModel):
    task_id: str  # 任务 ID（assignment）
    state: str  # 当前状态（assignment）
    result: Optional[Any] = None  # 结果可为空；未就绪时省略（assignment）
