from __future__ import annotations

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from business_service.pipeline.repository import AsyncMongoPipelineNodeRepository
from business_service.pipeline.service import AsyncPipelineNodeService
from business_service.prompt.repository import AsyncMongoPromptRepository
from business_service.prompt.service import PromptService
from business_service.workflow import (
    AsyncStageRepository,
    AsyncStageService,
    AsyncToolRepository,
    AsyncToolService,
    AsyncWorkflowRepository,
    AsyncWorkflowService,
    WorkflowObservabilityService,
)
from business_service.channel.repository import AsyncWorkflowChannelRepository
from business_service.channel.service import WorkflowChannelService
from foundational_service.persist.observability import WorkflowRunReadRepository

from . import get_mongo_database


# --- Mongo collections ----------------------------------------------------


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


async def get_coverage_history_collection(
    database: AsyncIOMotorDatabase = Depends(get_mongo_database),
) -> AsyncIOMotorCollection:
    return database["workflow_run_coverage"]


# --- Repositories ---------------------------------------------------------


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


async def get_workflow_channel_repository(
    collection: AsyncIOMotorCollection = Depends(get_workflow_channel_collection),
) -> AsyncWorkflowChannelRepository:
    return AsyncWorkflowChannelRepository(collection)


async def get_workflow_run_repository(
    collection: AsyncIOMotorCollection = Depends(get_workflow_run_collection),
) -> WorkflowRunReadRepository:
    return WorkflowRunReadRepository(collection)


# --- Services -------------------------------------------------------------


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


async def get_workflow_channel_service(
    repository: AsyncWorkflowChannelRepository = Depends(get_workflow_channel_repository),
    workflow_repository: AsyncWorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowChannelService:
    return WorkflowChannelService(repository=repository, workflow_repository=workflow_repository)


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
