from __future__ import annotations

"""Background scheduler that re-enqueues tasks whose retry timestamp has arrived."""

import asyncio
from typing import Optional

from .redis_queue import RedisTaskQueue
from .task_envelope import TaskEnvelope
from project_utility.telemetry import emit as telemetry_emit

__all__ = ["RetryScheduler"]


class RetryScheduler:
    def __init__(
        self,
        queue: RedisTaskQueue,
        *,
        poll_interval: float = 5.0,
        batch_size: int = 20,
    ) -> None:
        self._queue = queue
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="retry-scheduler")
        telemetry_emit("queue.retry_scheduler_start", payload={"poll_interval": self._poll_interval})

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
            telemetry_emit("queue.retry_scheduler_stop")

    async def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    await self._drain_due_tasks()
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval)
                except asyncio.TimeoutError:
                    continue
                except Exception:  # pragma: no cover - keep scheduler alive after unexpected errors
                    telemetry_emit(
                        "queue.retry_scheduler_error",
                        level="error",
                        payload={},
                    )
                    await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:  # pragma: no cover - cooperative cancellation path
            raise

    async def _drain_due_tasks(self) -> None:
        batch = await self._queue.fetch_due_retries(self._batch_size)
        if not batch:
            return
        for envelope in batch:
            telemetry_emit(
                "queue.retry_scheduler_enqueue",
                level="info",
                workflow_id=envelope.payload.get("workflowId"),
                request_id=envelope.context.get("requestId"),
                payload={"task_id": envelope.task_id, "retry_count": envelope.retry.count},
            )
            await self._queue.enqueue_existing(envelope)
