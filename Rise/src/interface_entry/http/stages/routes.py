from __future__ import annotations

"""HTTP routes for stage definitions."""

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status

from business_service.workflow import AsyncStageService
from interface_entry.http.dependencies.workflow import get_stage_service
from interface_entry.http.responses import ApiMeta, ApiResponse
from interface_entry.http.security import ActorContext, get_actor_context
from interface_entry.http.stages.dto import StageRequest, StageResponse
from project_utility.context import ContextBridge

router = APIRouter(prefix="/api/stages", tags=["stages"])


@router.get("", response_model=ApiResponse[Sequence[StageResponse]])
async def list_stages(service: AsyncStageService = Depends(get_stage_service)) -> ApiResponse[Sequence[StageResponse]]:
    stages = await service.list()
    data = [
        StageResponse(
            stageId=stage.stage_id,
            name=stage.name,
            description=stage.description,
            promptTemplate=stage.prompt_template,
            toolIds=list(stage.tool_ids),
            metadata=stage.metadata,
            version=stage.version,
            updatedAt=stage.updated_at,
            updatedBy=stage.updated_by,
        )
        for stage in stages
    ]
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[StageResponse])
async def create_stage(
    payload: StageRequest,
    service: AsyncStageService = Depends(get_stage_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[StageResponse]:
    stage = await service.create(payload.model_dump(), actor.actor_id)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = StageResponse(
        stageId=stage.stage_id,
        name=stage.name,
        description=stage.description,
        promptTemplate=stage.prompt_template,
        toolIds=list(stage.tool_ids),
        metadata=stage.metadata,
        version=stage.version,
        updatedAt=stage.updated_at,
        updatedBy=stage.updated_by,
    )
    return ApiResponse(data=data, meta=meta)


@router.put("/{stage_id}", response_model=ApiResponse[StageResponse])
async def update_stage(
    stage_id: str,
    payload: StageRequest,
    service: AsyncStageService = Depends(get_stage_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[StageResponse]:
    try:
        stage = await service.update(stage_id, payload.model_dump(exclude_unset=True), actor.actor_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STAGE_NOT_FOUND", "message": "Stage definition not found"},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = StageResponse(
        stageId=stage.stage_id,
        name=stage.name,
        description=stage.description,
        promptTemplate=stage.prompt_template,
        toolIds=list(stage.tool_ids),
        metadata=stage.metadata,
        version=stage.version,
        updatedAt=stage.updated_at,
        updatedBy=stage.updated_by,
    )
    return ApiResponse(data=data, meta=meta)


@router.delete("/{stage_id}", status_code=status.HTTP_200_OK, response_model=ApiResponse[dict[str, str]])
async def delete_stage(
    stage_id: str,
    service: AsyncStageService = Depends(get_stage_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[dict[str, str]]:
    try:
        await service.delete(stage_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STAGE_NOT_FOUND", "message": "Stage definition not found"},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data={"status": "deleted", "stageId": stage_id}, meta=meta)
