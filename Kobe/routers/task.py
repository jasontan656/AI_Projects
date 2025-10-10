#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Task orchestration API endpoints.

Contracts:
- POST /task/start -> {"task_id": str}
- GET  /task/status/{task_id} -> {"task_id", "state", "ready"}
- GET  /task/result/{task_id} -> {"task_id", "state", "result"?}

Notes:
- Uses Celery with RabbitMQ broker per BackendConstitution.
- Result backend is optional (Redis); disabled by default unless env enables it.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException  # 使用第三方库类 APIRouter/HTTPException 作为路由与错误响应（libraries）
from fastapi.responses import JSONResponse  # 使用第三方库类 JSONResponse 构造 JSON 返回体（libraries）
from pydantic import BaseModel, Field  # 保留导入以供类型提示/一致性（libraries）

from Kobe.SharedUtility.TaskQueue.app import app as celery_app  # 使用同仓模块导入 Celery 应用实例（modules）
from Kobe.SharedUtility.TaskQueue import tasks as tq  # 使用同仓模块别名 tq 引用任务函数（modules）
from Kobe.SharedUtility.TaskQueue.schemas import TaskStart, TaskStatus, TaskResult  # 使用同仓模块的数据模型（modules）


router = APIRouter(prefix="/task", tags=["task"])  # 创建任务相关路由器，统一前缀 /task（libraries）


@router.post("/start", response_model=Dict[str, str])
def start_task(req: TaskStart) -> JSONResponse:  # 声明 POST /task/start 端点，返回 {task_id}（libraries/modules）
    """Start a Celery task according to the requested task kind.

    Returns just a `task_id`. Clients should poll /task/status for progression.
    """
    if req.task == "demo_long_io":  # 比较 req.task 是否为 'demo_long_io'；进入分支 Branch（Branch）
        async_result = tq.demo_long_io.apply_async(
            kwargs={
                "duration_sec": req.duration_sec or 2,
                "fail_rate": req.fail_rate or 0.0,
                "payload": req.payload or {},
            }
        )  # 在对象 tq.demo_long_io 上调用方法 apply_async 异步投递任务（method call）
    elif req.task == "demo_sharded_job":  # 另一路由到分片任务；进入分支 Branch（Branch）
        if not req.shard_key:  # 校验必填字段（Branch）
            raise HTTPException(status_code=400, detail="shard_key is required for demo_sharded_job")  # 抛出 HTTP 400（libraries）
        async_result = tq.demo_sharded_job.apply_async(
            kwargs={
                "shard_key": req.shard_key,
                "payload": req.payload or {},
            }
        )  # 在对象 tq.demo_sharded_job 上调用方法 apply_async 异步投递（method call）
    else:  # pragma: no cover - validated by model regex
        raise HTTPException(status_code=400, detail="Unsupported task")

    return JSONResponse({"task_id": async_result.id})  # 使用 JSONResponse 返回任务 id（libraries）


@router.get("/status/{task_id}", response_model=TaskStatus)
def get_status(task_id: str) -> JSONResponse:  # 声明 GET /task/status/{task_id}；返回标准状态（libraries/modules）
    """Return normalized task state for the given task id."""
    result = celery_app.AsyncResult(task_id)  # 在对象 celery_app 上调用方法 AsyncResult 获取任务句柄（method call）
    # Standard Celery states (subset): PENDING, STARTED, RETRY, SUCCESS, FAILURE
    state = str(result.state)  # 使用 python 内置函数 str 归一化状态为字符串（builtins）
    ready = bool(result.ready())  # 在对象 result 上调用方法 ready() 判断是否就绪；再用 bool 归一化（method call/builtins）
    return JSONResponse(TaskStatus(task_id=task_id, state=state, ready=ready).model_dump())  # 使用 Pydantic 模型 model_dump 生成字典（libraries/modules）


@router.get("/result/{task_id}", response_model=TaskResult)
def get_result(task_id: str) -> JSONResponse:  # 声明 GET /task/result/{task_id}；可选返回结果（libraries/modules）
    """Return task result when available; otherwise return current state.

    If result backend is disabled, state will still be returned.
    """
    result = celery_app.AsyncResult(task_id)  # 再次获取任务句柄（method call）
    state = str(result.state)  # 归一化状态字符串（builtins）
    if result.successful():  # 在对象 result 上调用方法 successful() 判断是否成功（method call）
        return JSONResponse(TaskResult(task_id=task_id, state=state, result=result.result).model_dump())  # 成功时返回结果（libraries/modules）
    # Not ready or failed; expose only state
    return JSONResponse(TaskResult(task_id=task_id, state=state).model_dump(), status_code=202)  # 未就绪返回 202 并仅暴露状态（libraries/modules）
