from __future__ import annotations

"""HTTP routes for workflow definitions."""

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status

from business_service.workflow import AsyncWorkflowService, AsyncStageService
from interface_entry.http.dependencies import get_workflow_service, get_stage_service
from interface_entry.http.responses import ApiMeta, ApiResponse
from interface_entry.http.security import ActorContext, get_actor_context
from interface_entry.http.workflows.dto import WorkflowRequest, WorkflowResponse
from project_utility.context import ContextBridge

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("", response_model=ApiResponse[Sequence[WorkflowResponse]])
async def list_workflows(service: AsyncWorkflowService = Depends(get_workflow_service)) -> ApiResponse[Sequence[WorkflowResponse]]:
    workflows = await service.list()
    data = [
        WorkflowResponse(
            workflowId=workflow.workflow_id,
            name=workflow.name,
            description=workflow.description,
            stageIds=list(workflow.stage_ids),
            metadata=workflow.metadata,
            version=workflow.version,
            updatedAt=workflow.updated_at,
            updatedBy=workflow.updated_by,
        )
        for workflow in workflows
    ]
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[WorkflowResponse])
async def create_workflow(
    payload: WorkflowRequest,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    stage_service: AsyncStageService = Depends(get_stage_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[WorkflowResponse]:
    stage_ids = payload.stageIds or []
    missing = await _validate_stage_ids(stage_service, stage_ids)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "WORKFLOW_STAGE_MISSING",
                "message": "Unknown stage ids",
                "missing": missing,
            },
        )
    workflow = await workflow_service.create(payload.model_dump(), actor.actor_id)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = WorkflowResponse(
        workflowId=workflow.workflow_id,
        name=workflow.name,
        description=workflow.description,
        stageIds=list(workflow.stage_ids),
        metadata=workflow.metadata,
        version=workflow.version,
        updatedAt=workflow.updated_at,
        updatedBy=workflow.updated_by,
    )
    return ApiResponse(data=data, meta=meta)


@router.put("/{workflow_id}", response_model=ApiResponse[WorkflowResponse])
async def update_workflow(
    workflow_id: str,
    payload: WorkflowRequest,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    stage_service: AsyncStageService = Depends(get_stage_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[WorkflowResponse]:
    stage_ids = payload.stageIds or []
    missing = await _validate_stage_ids(stage_service, stage_ids)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "WORKFLOW_STAGE_MISSING",
                "message": "Unknown stage ids",
                "missing": missing,
            },
        )
    try:
        workflow = await workflow_service.update(workflow_id, payload.model_dump(exclude_unset=True), actor.actor_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow definition not found"},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = WorkflowResponse(
        workflowId=workflow.workflow_id,
        name=workflow.name,
        description=workflow.description,
        stageIds=list(workflow.stage_ids),
        metadata=workflow.metadata,
        version=workflow.version,
        updatedAt=workflow.updated_at,
        updatedBy=workflow.updated_by,
    )
    return ApiResponse(data=data, meta=meta)


@router.delete("/{workflow_id}", status_code=status.HTTP_200_OK, response_model=ApiResponse[dict[str, str]])
async def delete_workflow(
    workflow_id: str,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[dict[str, str]]:
    try:
        await workflow_service.delete(workflow_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow definition not found"},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data={"status": "deleted", "workflowId": workflow_id}, meta=meta)


async def _validate_stage_ids(stage_service: AsyncStageService, stage_ids: Sequence[str]) -> Sequence[str]:
    if not stage_ids:
        return ()
    existing = await stage_service.get_many(stage_ids)
    existing_ids = {stage.stage_id for stage in existing}
    missing = [stage_id for stage_id in stage_ids if stage_id not in existing_ids]
    return missing
