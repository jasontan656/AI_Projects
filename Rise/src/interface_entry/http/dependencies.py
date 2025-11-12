from __future__ import annotations

"""FastAPI dependency graph and lifespan helpers."""

import asyncio
import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncIterator, Optional

from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from business_service.channel.command_service import ChannelBindingCommandService
from business_service.channel.rate_limit import ChannelRateLimiter
from business_service.channel.registry import ChannelBindingRegistry
from business_service.channel.repository import AsyncWorkflowChannelRepository
from business_service.channel.service import WorkflowChannelService
from business_service.channel.test_runner import ChannelBindingTestRunner
from business_service.pipeline.repository import AsyncMongoPipelineNodeRepository
from business_service.pipeline.service import AsyncPipelineNodeService
from business_service.workflow import (
    AsyncStageRepository,
    AsyncStageService,
    AsyncToolRepository,
    AsyncToolService,
    AsyncWorkflowRepository,
    AsyncWorkflowService,
    WorkflowObservabilityService,
)
from business_service.prompt.repository import AsyncMongoPromptRepository
from business_service.prompt.service import PromptService
from business_service.workflow import StageRepository, WorkflowRepository
from foundational_service.integrations.telegram_client import TelegramClient
from foundational_service.persist.redis_queue import RedisTaskQueue
from foundational_service.persist.storage import WorkflowRunStorage
from foundational_service.persist.observability import WorkflowRunReadRepository
from foundational_service.persist.worker import (
    TaskResultBroker,
    TaskRuntime,
    TaskSubmitter,
    WorkflowTaskProcessor,
)
from foundational_service.persist.rabbit_bridge import RabbitConfig, RabbitPublisher
from foundational_service.persist.workflow_summary_repository import WorkflowSummaryRepository
from project_utility.db.mongo import get_mongo_database as get_sync_mongo_database
from project_utility.db.redis import get_async_redis
from interface_entry.runtime.capabilities import CapabilityRegistry, service_unavailable_error


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="allow",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    mongodb_uri: str = Field(..., alias="MONGODB_URI")
    mongodb_database: str = Field(..., alias="MONGODB_DATABASE")
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    app_env: str = Field(default="development", alias="APP_ENV")
    workflow_summary_ttl_seconds: Optional[int] = Field(default=3600, alias="WORKFLOW_SUMMARY_TTL_SECONDS")
    workflow_summary_max_entries: int = Field(default=20, alias="WORKFLOW_SUMMARY_MAX_ENTRIES")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return application settings loaded from environment / .env."""

    return AppSettings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_mongo_client() -> AsyncIOMotorClient:
    """Return a cached AsyncIOMotorClient."""

    settings = get_settings()
    return AsyncIOMotorClient(settings.mongodb_uri, tz_aware=True)


async def get_mongo_database(
    client: AsyncIOMotorClient = Depends(get_mongo_client),
) -> AsyncIOMotorDatabase:
    """Resolve Mongo database from cached client."""

    _require_capability("mongo", hard=True)
    settings = get_settings()
    return client[settings.mongodb_database]


async def get_prompt_collection(
    database: AsyncIOMotorDatabase = Depends(get_mongo_database),
) -> AsyncIOMotorCollection:
    return database["prompts"]


async def get_pipeline_collection(
    database: AsyncIOMotorDatabase = Depends(get_mongo_database),
) -> AsyncIOMotorCollection:
    return database["pipeline_nodes"]


async def get_tool_collection(
    database: AsyncIOMotorDatabase = Depends(get_mongo_database),
) -> AsyncIOMotorCollection:
    return database["workflow_tools"]


async def get_stage_collection(
    database: AsyncIOMotorDatabase = Depends(get_mongo_database),
) -> AsyncIOMotorCollection:
    return database["workflow_stages"]


async def get_workflow_collection(
    database: AsyncIOMotorDatabase = Depends(get_mongo_database),
) -> AsyncIOMotorCollection:
    return database["workflows"]


async def get_workflow_run_collection(
    database: AsyncIOMotorDatabase = Depends(get_mongo_database),
) -> AsyncIOMotorCollection:
    return database["workflow_runs"]


async def get_workflow_channel_collection(
    database: AsyncIOMotorDatabase = Depends(get_mongo_database),
) -> AsyncIOMotorCollection:
    return database["workflow_channels"]


async def get_prompt_repository(
    collection: AsyncIOMotorCollection = Depends(get_prompt_collection),
) -> AsyncMongoPromptRepository:
    return AsyncMongoPromptRepository(collection)


async def get_pipeline_repository(
    collection: AsyncIOMotorCollection = Depends(get_pipeline_collection),
) -> AsyncMongoPipelineNodeRepository:
    return AsyncMongoPipelineNodeRepository(collection)


async def get_tool_repository(
    collection: AsyncIOMotorCollection = Depends(get_tool_collection),
) -> AsyncToolRepository:
    return AsyncToolRepository(collection)


async def get_stage_repository(
    collection: AsyncIOMotorCollection = Depends(get_stage_collection),
) -> AsyncStageRepository:
    return AsyncStageRepository(collection)


async def get_workflow_repository(
    collection: AsyncIOMotorCollection = Depends(get_workflow_collection),
) -> AsyncWorkflowRepository:
    return AsyncWorkflowRepository(collection)


async def get_workflow_run_repository(
    collection: AsyncIOMotorCollection = Depends(get_workflow_run_collection),
) -> WorkflowRunReadRepository:
    return WorkflowRunReadRepository(collection)


async def get_workflow_channel_repository(
    collection: AsyncIOMotorCollection = Depends(get_workflow_channel_collection),
) -> AsyncWorkflowChannelRepository:
    return AsyncWorkflowChannelRepository(collection)


async def get_prompt_service(
    repository: AsyncMongoPromptRepository = Depends(get_prompt_repository),
) -> PromptService:
    return PromptService(repository=repository)


async def get_pipeline_service(
    repository: AsyncMongoPipelineNodeRepository = Depends(get_pipeline_repository),
) -> AsyncPipelineNodeService:
    return AsyncPipelineNodeService(repository=repository)


async def get_tool_service(
    repository: AsyncToolRepository = Depends(get_tool_repository),
) -> AsyncToolService:
    return AsyncToolService(repository=repository)


async def get_stage_service(
    repository: AsyncStageRepository = Depends(get_stage_repository),
) -> AsyncStageService:
    return AsyncStageService(repository=repository)


async def get_workflow_service(
    repository: AsyncWorkflowRepository = Depends(get_workflow_repository),
) -> AsyncWorkflowService:
    return AsyncWorkflowService(repository=repository)


async def get_workflow_observability_service(
    workflow_repository: AsyncWorkflowRepository = Depends(get_workflow_repository),
    stage_repository: AsyncStageRepository = Depends(get_stage_repository),
    tool_repository: AsyncToolRepository = Depends(get_tool_repository),
    run_repository: WorkflowRunReadRepository = Depends(get_workflow_run_repository),
) -> WorkflowObservabilityService:
    return WorkflowObservabilityService(
        workflow_repository=workflow_repository,
        stage_repository=stage_repository,
        tool_repository=tool_repository,
        run_repository=run_repository,
    )


async def get_workflow_channel_service(
    repository: AsyncWorkflowChannelRepository = Depends(get_workflow_channel_repository),
    workflow_repository: AsyncWorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowChannelService:
    return WorkflowChannelService(repository=repository, workflow_repository=workflow_repository)


_task_runtime: Optional[TaskRuntime] = None
_capabilities: Optional[CapabilityRegistry] = None
_rabbit_publisher: Optional[RabbitPublisher] = None
_rabbit_publisher_initialized = False
_channel_rate_limiter: Optional[ChannelRateLimiter] = None
_channel_binding_test_runner: Optional[ChannelBindingTestRunner] = None
_telegram_client: Optional[TelegramClient] = None
_channel_binding_registry: Optional[ChannelBindingRegistry] = None
_workflow_summary_repository: Optional[WorkflowSummaryRepository] = None


def set_capability_registry(registry: CapabilityRegistry) -> None:
    global _capabilities
    _capabilities = registry


def _require_capability(name: str, *, hard: bool = True) -> None:
    if _capabilities is None:
        return
    _capabilities.require(name, hard=hard)


def _first_unavailable(names: tuple[str, ...]) -> Optional[str]:
    if _capabilities is None:
        return None
    for name in names:
        if not _capabilities.is_available(name):
            return name
    return None


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


def get_task_runtime() -> TaskRuntime | DisabledTaskRuntime:
    global _task_runtime
    blocked = _first_unavailable(("redis", "rabbitmq"))
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
        processor = WorkflowTaskProcessor(
            workflow_repository=workflow_repo,
            stage_repository=stage_repo,
            summary_repository=summary_repo,
        )
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
    blocked = _first_unavailable(("redis", "rabbitmq"))
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
    return runtime.queue


def get_task_results() -> TaskResultBroker:
    _require_capability("redis", hard=True)
    runtime = get_task_runtime()
    if isinstance(runtime, DisabledTaskRuntime):
        raise service_unavailable_error("redis")
    return runtime.results


def _resolve_telegram_client(*, require_capability: bool) -> TelegramClient:
    global _telegram_client
    if require_capability:
        _require_capability("telegram", hard=True)
    if _telegram_client is None:
        _telegram_client = TelegramClient()
    return _telegram_client


def get_telegram_client() -> TelegramClient:
    return _resolve_telegram_client(require_capability=True)


def prime_telegram_client() -> TelegramClient:
    """Instantiate a Telegram client without capability enforcement."""

    return _resolve_telegram_client(require_capability=False)


def get_channel_rate_limiter() -> ChannelRateLimiter:
    global _channel_rate_limiter
    if _channel_rate_limiter is None:
        redis_client = get_async_redis()
        _channel_rate_limiter = ChannelRateLimiter(redis_client)
    return _channel_rate_limiter


async def get_channel_binding_test_runner(
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    telegram_client: TelegramClient = Depends(get_telegram_client),
    run_repository: WorkflowRunReadRepository = Depends(get_workflow_run_repository),
) -> ChannelBindingTestRunner:
    global _channel_binding_test_runner
    if _channel_binding_test_runner is None:
        _channel_binding_test_runner = ChannelBindingTestRunner(
            service=service,
            telegram_client=telegram_client,
            run_repository=run_repository,
        )
    return _channel_binding_test_runner


async def get_channel_binding_registry(
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
) -> ChannelBindingRegistry:
    global _channel_binding_registry
    if _channel_binding_registry is None:
        _channel_binding_registry = ChannelBindingRegistry(service=service)
        await _channel_binding_registry.refresh()
    return _channel_binding_registry


def set_channel_binding_registry(registry: ChannelBindingRegistry) -> None:
    global _channel_binding_registry
    _channel_binding_registry = registry


async def get_channel_binding_command_service(
    request: Request,
    registry: ChannelBindingRegistry = Depends(get_channel_binding_registry),
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
) -> ChannelBindingCommandService:
    publisher = getattr(request.app.state, "channel_binding_event_publisher", None)
    return ChannelBindingCommandService(service=service, registry=registry, publisher=publisher)


async def shutdown_task_runtime() -> None:
    global _task_runtime
    if _task_runtime is None:
        return
    await _task_runtime.stop()
    _task_runtime = None


def clear_cached_dependencies() -> None:
    """Clear cached dependency singletons."""

    try:
        client = get_mongo_client()
    except Exception:
        client = None
    else:
        client.close()
    get_mongo_client.cache_clear()
    get_settings.cache_clear()
    global _telegram_client, _channel_rate_limiter, _channel_binding_test_runner
    if _telegram_client is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_telegram_client.aclose())
            else:  # pragma: no cover - cli shutdown path
                loop.run_until_complete(_telegram_client.aclose())
        except Exception:
            pass
        _telegram_client = None
    _channel_rate_limiter = None
    _channel_binding_test_runner = None
    global _channel_binding_registry
    _channel_binding_registry = None
    global _workflow_summary_repository
    _workflow_summary_repository = None


@asynccontextmanager
async def dependency_lifespan(_: Request) -> AsyncIterator[None]:
    """Ensure dependency singletons stay alive during request scope."""

    yield


@asynccontextmanager
async def application_lifespan() -> AsyncIterator[None]:
    """Application lifespan wrapper to manage cached dependencies."""

    # Prime settings/client early so startup failures happen before accepting traffic.
    _ = get_settings()
    _ = get_mongo_client()
    try:
        prime_telegram_client()
    except Exception as exc:  # pragma: no cover - best effort logging
        logging.getLogger("interface_entry.dependency").warning(
            "telegram.client.prime_failed",
            extra={"error": str(exc)},
        )
    runtime: Optional[TaskRuntime] = None
    runtime_enabled = _capabilities is None or (
        _capabilities.is_available("redis") and _capabilities.is_available("rabbitmq")
    )
    if runtime_enabled:
        runtime = get_task_runtime()
        await runtime.start()
    else:
        logging.getLogger("interface_entry.dependency").warning(
            "task_runtime.disabled",
            extra={"reason": "capability_unavailable"},
        )
    try:
        yield
    finally:
        if runtime is not None:
            await shutdown_task_runtime()
        clear_cached_dependencies()
