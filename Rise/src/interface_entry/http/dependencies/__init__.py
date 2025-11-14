from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncIterator, Optional, Tuple

from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import Redis

from project_utility.db.redis import get_async_redis
from interface_entry.runtime.capabilities import CapabilityRegistry

log = logging.getLogger("interface_entry.dependencies")


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


_capabilities: Optional[CapabilityRegistry] = None


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


async def get_async_redis_client() -> Redis:
    _require_capability("redis", hard=True)
    return get_async_redis()


def set_capability_registry(registry: CapabilityRegistry) -> None:
    global _capabilities
    _capabilities = registry


def _require_capability(name: str, *, hard: bool = True) -> None:
    if _capabilities is None:
        return
    _capabilities.require(name, hard=hard)


def _first_unavailable(names: Tuple[str, ...]) -> Optional[str]:
    if _capabilities is None:
        return None
    for name in names:
        if not _capabilities.is_available(name):
            return name
    return None


@asynccontextmanager
async def dependency_lifespan(_: Request) -> AsyncIterator[None]:
    """Keep dependency singletons alive during request scope."""

    yield


@asynccontextmanager
async def application_lifespan() -> AsyncIterator[None]:
    """Application lifespan wrapper to manage cached dependencies."""

    from .channel import prime_telegram_client
    from .telemetry import get_task_runtime, shutdown_task_runtime

    _ = get_settings()
    _ = get_mongo_client()
    try:
        prime_telegram_client()
    except Exception as exc:  # pragma: no cover - best-effort logging
        log.warning("telegram.client.prime_failed", extra={"error": str(exc)})
    runtime = None
    runtime_enabled = _capabilities is None or (
        _capabilities.is_available("redis") and _capabilities.is_available("rabbitmq")
    )
    if runtime_enabled:
        runtime = get_task_runtime()
        await runtime.start()
    else:
        log.warning(
            "task_runtime.disabled",
            extra={"reason": "capability_unavailable"},
        )
    try:
        yield
    finally:
        if runtime is not None:
            await shutdown_task_runtime()
        clear_cached_dependencies()


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
    from .channel import reset_channel_dependencies
    from .telemetry import reset_telemetry_dependencies

    reset_channel_dependencies()
    reset_telemetry_dependencies()


# --------------------------------------------------------------------------
# Re-export domain-specific dependency helpers
# --------------------------------------------------------------------------

from .workflow import (  # noqa: E402
    get_stage_collection,
    get_stage_repository,
    get_stage_service,
    get_tool_collection,
    get_tool_repository,
    get_tool_service,
    get_pipeline_collection,
    get_pipeline_repository,
    get_pipeline_service,
    get_prompt_collection,
    get_prompt_repository,
    get_prompt_service,
    get_workflow_collection,
    get_workflow_repository,
    get_workflow_service,
    get_workflow_observability_service,
    get_workflow_run_collection,
    get_workflow_run_repository,
    get_workflow_channel_collection,
    get_workflow_channel_repository,
    get_workflow_channel_service,
)
from .channel import (  # noqa: E402
    get_channel_binding_command_service,
    get_channel_binding_registry,
    get_channel_binding_test_runner,
    get_channel_rate_limiter,
    get_telegram_client,
    prime_telegram_client,
    set_channel_binding_registry,
)
from .telemetry import (  # noqa: E402
    DisabledTaskRuntime,
    DisabledTaskSubmitter,
    get_coverage_status_service,
    get_task_queue,
    get_task_results,
    get_task_runtime,
    get_task_runtime_if_enabled,
    get_task_submitter,
    get_workflow_summary_repository,
    reset_telemetry_dependencies,
    shutdown_task_runtime,
)

__all__ = [
    "AppSettings",
    "application_lifespan",
    "clear_cached_dependencies",
    "dependency_lifespan",
    "get_async_redis_client",
    "get_mongo_client",
    "get_mongo_database",
    "get_settings",
    "set_capability_registry",
    # workflow exports
    "get_stage_collection",
    "get_stage_repository",
    "get_stage_service",
    "get_tool_collection",
    "get_tool_repository",
    "get_tool_service",
    "get_pipeline_collection",
    "get_pipeline_repository",
    "get_pipeline_service",
    "get_prompt_collection",
    "get_prompt_repository",
    "get_prompt_service",
    "get_workflow_collection",
    "get_workflow_repository",
    "get_workflow_service",
    "get_workflow_observability_service",
    "get_workflow_run_collection",
    "get_workflow_run_repository",
    "get_workflow_channel_collection",
    "get_workflow_channel_repository",
    "get_workflow_channel_service",
    # channel exports
    "get_channel_binding_command_service",
    "get_channel_binding_registry",
    "get_channel_binding_test_runner",
    "get_channel_rate_limiter",
    "get_telegram_client",
    "prime_telegram_client",
    "set_channel_binding_registry",
    # telemetry exports
    "DisabledTaskRuntime",
    "DisabledTaskSubmitter",
    "get_coverage_status_service",
    "get_task_queue",
    "get_task_results",
    "get_task_runtime",
    "get_task_runtime_if_enabled",
    "get_task_submitter",
    "get_workflow_summary_repository",
    "shutdown_task_runtime",
]
