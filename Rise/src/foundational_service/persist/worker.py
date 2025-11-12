from __future__ import annotations

"""Task worker implementation that bridges Redis streams and workflow execution."""

import asyncio
import socket
from typing import Any, Awaitable, Callable, Dict, List, Mapping, MutableMapping, Optional, Sequence
from uuid import uuid4

from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from business_logic.workflow import WorkflowExecutionContext, WorkflowOrchestrator, WorkflowRunResult
from business_service.workflow import StageRepository, WorkflowRepository
from project_utility.context import ContextBridge
from project_utility.telemetry import emit as telemetry_emit
from foundational_service.persist.workflow_summary_repository import WorkflowSummaryRepository

from .rabbit_bridge import RabbitPublisher
from .redis_queue import RedisTaskQueue, StreamTask
from .retry_scheduler import RetryScheduler
from .storage import WorkflowRunStorage
from .task_envelope import TaskEnvelope, TaskStatus

__all__ = [
    "RetryTask",
    "SuspendTask",
    "TaskResultBroker",
    "TaskRuntime",
    "TaskSubmitter",
    "TaskWorker",
    "WorkflowTaskProcessor",
]

class RetryTask(RuntimeError):
    def __init__(self, reason: str, *, delay: float = 30.0, error: Optional[str] = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.delay = delay
        self.error = error


class SuspendTask(RuntimeError):
    def __init__(self, reason: str, *, error: Optional[str] = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.error = error


class TaskResultBroker:
    def __init__(self) -> None:
        self._waiters: MutableMapping[str, List[asyncio.Future]] = {}
        self._lock = asyncio.Lock()

    async def register(self, task_id: str) -> asyncio.Future:
        future = asyncio.get_running_loop().create_future()
        async with self._lock:
            self._waiters.setdefault(task_id, []).append(future)
        return future

    async def discard(self, task_id: str, future: asyncio.Future) -> None:
        async with self._lock:
            futures = self._waiters.get(task_id)
            if not futures:
                return
            if future in futures:
                futures.remove(future)
            if not futures:
                self._waiters.pop(task_id, None)

    async def publish(self, task_id: str, payload: Mapping[str, Any]) -> None:
        async with self._lock:
            futures = self._waiters.pop(task_id, [])
        for future in futures:
            if not future.done():
                future.set_result(payload)


def _emit_worker_event(
    event_type: str,
    *,
    level: str = "info",
    envelope: Optional[TaskEnvelope] = None,
    payload: Optional[Mapping[str, Any]] = None,
    **fields: Any,
) -> None:
    data = dict(payload or {})
    workflow_id = None
    request_id = None
    if envelope:
        data.setdefault("task_id", envelope.task_id)
        data.setdefault("task_type", envelope.type)
        workflow_id = envelope.payload.get("workflowId") or envelope.context.get("workflowId")
        request_id = envelope.context.get("requestId")
    telemetry_emit(
        event_type,
        level=level,
        workflow_id=workflow_id,
        request_id=request_id,
        payload=data,
        **fields,
    )


class WorkflowTaskProcessor:
    def __init__(
        self,
        *,
        workflow_repository: WorkflowRepository,
        stage_repository: StageRepository,
        summary_repository: WorkflowSummaryRepository,
        backoff_curve: Optional[Sequence[float]] = None,
    ) -> None:
        self._workflow_repository = workflow_repository
        self._stage_repository = stage_repository
        self._orchestrator: Optional[WorkflowOrchestrator] = None
        self._summary_repository = summary_repository
        self._backoff_curve = backoff_curve or (15.0, 30.0, 60.0, 120.0, 180.0)

    async def process(self, envelope: TaskEnvelope) -> Mapping[str, Any]:
        workflow_id = str(envelope.payload.get("workflowId") or "")
        if not workflow_id:
            raise SuspendTask("workflow_id_missing", error="workflowId is required")
        trace_id = envelope.context.get("traceId") or envelope.task_id
        ContextBridge.set_request_id(trace_id)
        try:
            core_envelope = dict(envelope.payload.get("coreEnvelope") or {})
            context = WorkflowExecutionContext(
                workflow_id=workflow_id,
                request_id=envelope.context.get("requestId", envelope.task_id),
                user_text=str(envelope.payload.get("userText", "")),
                history_chunks=tuple(envelope.payload.get("historyChunks") or ()),
                policy=dict(envelope.payload.get("policy") or {}),
                core_envelope=core_envelope,
                telemetry=self._build_telemetry(envelope),
                metadata=core_envelope.get("metadata"),
                inbound=core_envelope.get("inbound"),
            )
            run_result = await self._get_orchestrator().execute(context)
        except ServerSelectionTimeoutError as exc:
            raise RetryTask(
                "mongo_unavailable",
                delay=self.retry_delay(envelope.retry.count),
                error=str(exc),
            ) from exc
        except KeyError as exc:
            raise SuspendTask("workflow_configuration_missing", error=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - guard orchestrator soft failures
            raise RetryTask(
                "workflow_execution_failed",
                delay=self.retry_delay(envelope.retry.count),
                error=str(exc),
            ) from exc
        finally:
            ContextBridge.clear()
        return self._serialize_result(run_result)

    def _get_orchestrator(self) -> WorkflowOrchestrator:
        if self._orchestrator is None:
            self._orchestrator = WorkflowOrchestrator(
                workflow_repository=self._workflow_repository,
                stage_repository=self._stage_repository,
                summary_repository=self._summary_repository,
            )
        return self._orchestrator

    def _serialize_result(self, run_result: WorkflowRunResult) -> Mapping[str, Any]:
        stage_results = [
            {
                "stageId": result.stage_id,
                "name": result.name,
                "promptUsed": result.prompt_used,
                "outputText": result.output_text,
                "usage": result.raw_response.get("usage"),
            }
            for result in run_result.stage_results
        ]
        payload: Dict[str, Any] = {
            "finalText": run_result.final_text,
            "stageResults": stage_results,
            "telemetry": dict(run_result.telemetry),
        }
        return payload

    def _build_telemetry(self, envelope: TaskEnvelope) -> MutableMapping[str, Any]:
        telemetry = dict(envelope.payload.get("telemetry") or {})
        telemetry.setdefault("taskId", envelope.task_id)
        telemetry.setdefault("source", envelope.payload.get("source", "http"))
        return telemetry

    def retry_delay(self, attempt: int) -> float:
        curve = self._backoff_curve
        if attempt < len(curve):
            return curve[attempt]
        return curve[-1]


class TaskWorker:
    def __init__(
        self,
        *,
        queue: RedisTaskQueue,
        processor: WorkflowTaskProcessor,
        storage: WorkflowRunStorage,
        results: TaskResultBroker,
        group_name: Optional[str] = None,
        poll_interval: float = 1.5,
        max_batch: int = 5,
        claim_idle_ms: int = 30000,
    ) -> None:
        self._queue = queue
        self._processor = processor
        self._storage = storage
        self._results = results
        self._group_name = group_name or queue.group_name
        self._poll_interval = poll_interval
        self._max_batch = max_batch
        self._claim_idle_ms = claim_idle_ms
        self._consumer_id = f"{socket.gethostname()}:{uuid4().hex[:6]}"
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        await self._queue.ensure_group()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="task-worker")
        telemetry_emit(
            "queue.worker_start",
            payload={"consumer": self._consumer_id, "group": self._group_name},
        )

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
            telemetry_emit(
                "queue.worker_stop",
                payload={"consumer": self._consumer_id, "group": self._group_name},
            )

    async def _run_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                await self._claim_pending()
                batch = await self._queue.read_group(self._consumer_id, count=self._max_batch, block_ms=int(self._poll_interval * 1000))
                if not batch:
                    continue
                for item in batch:
                    await self._process_item(item)
        except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
            raise
        except Exception:  # pragma: no cover - keep worker alive after unexpected errors
            telemetry_emit(
                "queue.worker_loop_error",
                level="error",
                payload={"consumer": self._consumer_id},
            )
            await asyncio.sleep(self._poll_interval)
            if not self._stop_event.is_set():
                self._task = None
                await self.start()
                return

    async def _claim_pending(self) -> None:
        claimed = await self._queue.auto_claim(
            self._consumer_id,
            min_idle_ms=self._claim_idle_ms,
            count=self._max_batch,
        )
        for item in claimed:
            await self._process_item(item)

    async def _process_item(self, item: StreamTask) -> None:
        envelope = item.envelope
        await self._queue.mark_processing(envelope, stream_id=item.stream_id)
        try:
            result = await self._processor.process(envelope)
            envelope.set_result(result)
            await self._persist_result(envelope, item.stream_id)
            await self._queue.mark_completed(envelope, stream_id=item.stream_id)
            await self._results.publish(
                envelope.task_id,
                {"status": TaskStatus.COMPLETED.value, "result": result},
            )
        except RetryTask as exc:
            await self._handle_retry(envelope, item.stream_id, exc)
        except SuspendTask as exc:
            await self._queue.mark_suspended(envelope, stream_id=item.stream_id, error=exc.error or exc.reason)
            await self._results.publish(
                envelope.task_id,
                {"status": TaskStatus.SUSPENDED.value, "error": exc.error or exc.reason},
            )
        except Exception as exc:  # pragma: no cover - guard loop from unexpected handler failures
            _emit_worker_event(
                "queue.worker_unhandled_error",
                level="error",
                envelope=envelope,
                payload={"error": str(exc)},
            )
            await self._handle_retry(
                envelope,
                item.stream_id,
                RetryTask(
                    "handler_failure",
                    delay=self._processor.retry_delay(envelope.retry.count),
                    error=str(exc),
                ),
            )

    async def _handle_retry(self, envelope: TaskEnvelope, stream_id: str, exc: RetryTask) -> None:
        scheduled = await self._queue.mark_retry(
            envelope,
            stream_id=stream_id,
            delay_seconds=max(1.0, exc.delay),
            error=exc.error or exc.reason,
        )
        _emit_worker_event(
            "queue.task_retry",
            level="warning",
            envelope=envelope,
            payload={"reason": exc.reason, "delay": exc.delay, "scheduled": scheduled},
        )
        if not scheduled:
            await self._results.publish(
                envelope.task_id,
                {"status": TaskStatus.SUSPENDED.value, "error": exc.error or exc.reason},
            )

    async def _persist_result(self, envelope: TaskEnvelope, stream_id: str) -> None:
        try:
            self._storage.upsert_result(envelope=envelope, result=envelope.result or {})
        except PyMongoError as exc:
            raise RetryTask(
                "mongo_write_failed",
                delay=self._processor.retry_delay(envelope.retry.count),
                error=str(exc),
            ) from exc


class TaskSubmitter:
    def __init__(self, queue: RedisTaskQueue, rabbit_publisher: Optional[RabbitPublisher] = None) -> None:
        self._queue = queue
        self._rabbit_publisher = rabbit_publisher

    async def submit(self, envelope: TaskEnvelope) -> TaskEnvelope:
        await self._queue.enqueue(envelope)
        if self._rabbit_publisher is not None:
            try:
                await self._rabbit_publisher.publish_task(envelope)
            except Exception as exc:  # pragma: no cover - mirrored channel best effort
                _emit_worker_event(
                    "queue.submitter.rabbit_mirror_failed",
                    level="warning",
                    envelope=envelope,
                    payload={"error": str(exc)},
                )
        return envelope


class TaskRuntime:
    def __init__(
        self,
        *,
        queue: RedisTaskQueue,
        processor: WorkflowTaskProcessor,
        storage: WorkflowRunStorage,
        rabbit_publisher: Optional[RabbitPublisher] = None,
    ) -> None:
        self.queue = queue
        self.results = TaskResultBroker()
        self.submitter = TaskSubmitter(queue, rabbit_publisher=rabbit_publisher)
        self.worker = TaskWorker(
            queue=queue,
            processor=processor,
            storage=storage,
            results=self.results,
        )
        self.scheduler = RetryScheduler(queue)
        self._rabbit_publisher = rabbit_publisher
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        if self._rabbit_publisher is not None:
            await self._rabbit_publisher.start()
        await self.queue.healthcheck()
        await self.scheduler.start()
        await self.worker.start()
        self._started = True

    async def stop(self) -> None:
        if not self._started:
            return
        await self.scheduler.stop()
        await self.worker.stop()
        if self._rabbit_publisher is not None:
            await self._rabbit_publisher.close()
        self._started = False


