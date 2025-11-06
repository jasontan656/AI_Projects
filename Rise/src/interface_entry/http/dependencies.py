from __future__ import annotations

"""FastAPI dependency graph and lifespan helpers."""

import asyncio
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncIterator, Optional

from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from business_service.pipeline.repository import AsyncMongoPipelineNodeRepository
from business_service.pipeline.service import AsyncPipelineNodeService
from business_service.workflow import (
    AsyncStageRepository,
    AsyncStageService,
    AsyncToolRepository,
    AsyncToolService,
    AsyncWorkflowRepository,
    AsyncWorkflowService,
)
from business_service.prompt.repository import AsyncMongoPromptRepository
from business_service.prompt.service import PromptService


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
        yield
    finally:
        clear_cached_dependencies()
