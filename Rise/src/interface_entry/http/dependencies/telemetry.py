from __future__ import annotations

import logging
from typing import Optional, Tuple

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection
from redis.asyncio import Redis

from business_service.channel.coverage_status import CoverageStatusService
from business_service.workflow import StageRepository, WorkflowRepository
from foundational_service.persist.observability import WorkflowRunReadRepository
from foundational_service.persist.rabbit_bridge import RabbitConfig, RabbitPublisher
from foundational_service.persist.redis_queue import RedisTaskQueue
from foundational_service.persist.storage import WorkflowRunStorage
from foundational_service.persist.worker import (
    TaskResultBroker,
    TaskRuntime,
    TaskSubmitter,
    WorkflowTaskProcessor,
)
from foundational_service.persist.workflow_summary_repository import WorkflowSummaryRepository
from interface_entry.runtime.workflow_executor import OrchestratorWorkflowExecutor
from project_utility.db.mongo import get_mongo_database as get_sync_mongo_database
from project_utility.db.redis import get_async_redis
from interface_entry.runtime.capabilities import service_unavailable_error
from foundational_service.telemetry.coverage_recorder import get_coverage_test_event_recorder

from . import (
    _capabilities,
    _first_unavailable,
    _require_capability,
    get_async_redis_client,
    get_mongo_client,
    get_settings,
)
from .workflow import get_coverage_history_collection


log = logging.getLogger("interface_entry.dependencies.telemetry")

_rabbit_publisher: Optional[RabbitPublisher] = None
_rabbit_publisher_initialized = False
_workflow_summary_repository: Optional[WorkflowSummaryRepository] = None
_task_runtime: Optional[TaskRuntime] = None


async def get_coverage_status_service(
    redis_client: Redis = Depends(get_async_redis_client),
    history_collection: AsyncIOMotorCollection = Depends(get_coverage_history_collection),
) -> CoverageStatusService:
    recorder = get_coverage_test_event_recorder()
    return CoverageStatusService(
        redis_client=redis_client,
        history_collection=history_collection,
        event_recorder=recorder,
    )


def get_workflow_summary_repository() -> WorkflowSummaryRepository:
    global _workflow_summary_repository
    if _workflow_summary_repository is None:
        settings = get_settings()
        redis_client = get_async_redis()
        database = get_sync_mongo_database()
        _workflow_summary_repository = WorkflowSummaryRepository(
            redis_client=redis_client,
            mongo_database=database,
            max_entries=settings.workflow_summary_max_entries,
            ttl_seconds=settings.workflow_summary_ttl_seconds,
        )
    return _workflow_summary_repository


def _get_rabbit_publisher() -> Optional[RabbitPublisher]:
    global _rabbit_publisher_initialized, _rabbit_publisher
    if _rabbit_publisher_initialized:
        return _rabbit_publisher
    _rabbit_publisher_initialized = True
    try:
        config = RabbitConfig.from_env()
    except RuntimeError:
        _rabbit_publisher = None
        return None
    _rabbit_publisher = RabbitPublisher(config)
    return _rabbit_publisher


class DisabledTaskSubmitter:
    """Submitter that rejects enqueued tasks when runtime is disabled."""

    def __init__(self, capability: str, detail: Optional[str] = None) -> None:
        self._capability = capability
        self._detail = detail

    async def submit(self, envelope: object) -> None:  # pragma: no cover - passthrough to HTTP layer
        raise service_unavailable_error(self._capability, detail=self._detail)


class DisabledTaskRuntime:
    """Placeholder runtime to keep call-sites consistent when queueing is offline."""

    def __init__(self, capability: str, detail: Optional[str] = None) -> None:
        self.capability = capability
        self.detail = detail
        self.queue = None
        self.results = TaskResultBroker()
        self.submitter = DisabledTaskSubmitter(capability, detail)

    async def start(self) -> None:  # pragma: no cover - no-op
        return

    async def stop(self) -> None:  # pragma: no cover - no-op
        return


def _runtime_blockers() -> Tuple[str, ...]:
    return ("redis", "rabbitmq")


def get_task_runtime() -> TaskRuntime | DisabledTaskRuntime:
    global _task_runtime
    blocked = _first_unavailable(_runtime_blockers())
    if blocked:
        detail: Optional[str] = None
        if _capabilities:
            state = _capabilities.get_state(blocked)
            detail = state.detail if state else None
        return DisabledTaskRuntime(blocked, detail)
    if _task_runtime is None:
        redis_client = get_async_redis()
        sync_database = get_sync_mongo_database()
        workflow_repo = WorkflowRepository(sync_database["workflows"])
        stage_repo = StageRepository(sync_database["workflow_stages"])
        summary_repo = get_workflow_summary_repository()
        executor = OrchestratorWorkflowExecutor(
            workflow_repository=workflow_repo,
            stage_repository=stage_repo,
            summary_repository=summary_repo,
        )
        processor = WorkflowTaskProcessor(workflow_executor=executor)
        storage = WorkflowRunStorage(sync_database)
        queue = RedisTaskQueue(redis_client)
        _task_runtime = TaskRuntime(
            queue=queue,
            processor=processor,
            storage=storage,
            rabbit_publisher=_get_rabbit_publisher(),
        )
    return _task_runtime


def get_task_runtime_if_enabled() -> Optional[TaskRuntime]:
    blocked = _first_unavailable(_runtime_blockers())
    if blocked:
        return None
    return _task_runtime


def get_task_submitter() -> TaskSubmitter:
    return get_task_runtime().submitter


def get_task_queue() -> RedisTaskQueue:
    _require_capability("redis", hard=True)
    runtime = get_task_runtime()
    if isinstance(runtime, DisabledTaskRuntime):
        raise service_unavailable_error("redis")
    return runtime.queue  # type: ignore[return-value]


def get_task_results() -> TaskResultBroker:
    _require_capability("redis", hard=True)
    runtime = get_task_runtime()
    if isinstance(runtime, DisabledTaskRuntime):
        raise service_unavailable_error("redis")
    return runtime.results


async def shutdown_task_runtime() -> None:
    global _task_runtime
    if _task_runtime is None:
        return
    await _task_runtime.stop()
    _task_runtime = None


def reset_telemetry_dependencies() -> None:
    global _task_runtime, _workflow_summary_repository, _rabbit_publisher, _rabbit_publisher_initialized
    _task_runtime = None
    _workflow_summary_repository = None
    if _rabbit_publisher is not None:
        try:
            _rabbit_publisher.close()  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - defensive cleanup
            pass
    _rabbit_publisher = None
    _rabbit_publisher_initialized = False
