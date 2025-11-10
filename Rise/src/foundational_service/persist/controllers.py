from __future__ import annotations

"""Internal FastAPI router for inspecting the task queue runtime."""

from typing import Callable, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, status

from .worker import TaskRuntime

__all__ = ["build_task_admin_router"]


def build_task_admin_router(runtime_provider: Callable[[], Optional[TaskRuntime]]) -> APIRouter:
    router = APIRouter(prefix="/internal/tasks", tags=["internal-tasks"])

    def _runtime_dependency() -> TaskRuntime:
        runtime = runtime_provider()
        if runtime is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="task runtime unavailable")
        return runtime

    @router.get("/stats")
    async def queue_stats(runtime: TaskRuntime = Depends(_runtime_dependency)) -> dict:
        stats = await runtime.queue.get_stats()
        return stats

    @router.get("/suspended")
    async def list_suspended(runtime: TaskRuntime = Depends(_runtime_dependency)) -> Sequence[dict]:
        envelopes = await runtime.queue.list_suspended(limit=100)
        return [envelope.to_public_dict() for envelope in envelopes]

    @router.post("/{task_id}/resume")
    async def resume_task(task_id: str, runtime: TaskRuntime = Depends(_runtime_dependency)) -> dict:
        envelope = await runtime.queue.resume_task(task_id)
        if envelope is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"status": "queued", "taskId": task_id}

    @router.delete("/{task_id}")
    async def drop_task(task_id: str, runtime: TaskRuntime = Depends(_runtime_dependency)) -> dict:
        deleted = await runtime.queue.drop_task(task_id)
        if not deleted:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="task not found")
        return {"status": "deleted", "taskId": task_id}

    @router.get("/{task_id}")
    async def inspect_task(task_id: str, runtime: TaskRuntime = Depends(_runtime_dependency)) -> dict:
        envelope = await runtime.queue.get_task(task_id)
        if envelope is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="task not found")
        return envelope.to_public_dict()

    return router
