from __future__ import annotations

"""FastAPI routes for pipeline node storage."""

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status as http_status

from business_service.pipeline.repository import DuplicateNodeNameError
from business_service.pipeline.service import AsyncPipelineNodeService
from interface_entry.http.dependencies.workflow import get_pipeline_service
from interface_entry.http.pipeline_nodes.dto import (
    PipelineNodeListResponse,
    PipelineNodeRequest,
    PipelineNodeResponse,
    PipelineNodeSnapshot,
    PipelineNodeUpdateRequest,
)
from interface_entry.http.responses import ApiMeta, ApiResponse, PaginationMeta
from interface_entry.http.security import ActorContext, get_actor_context
from foundational_service.contracts.toolcalls import call_record_audit
from project_utility.context import ContextBridge

router = APIRouter(prefix="/api/pipeline-nodes", tags=["pipeline-nodes"])


@router.post(
    "",
    response_model=ApiResponse[PipelineNodeResponse],
    status_code=http_status.HTTP_201_CREATED,
)
async def create_pipeline_node(
    payload: PipelineNodeRequest,
    background_tasks: BackgroundTasks,
    service: AsyncPipelineNodeService = Depends(get_pipeline_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[PipelineNodeResponse]:
    try:
        node, audit_entry = await service.create_node(payload.model_dump(), actor.actor_id)
    except DuplicateNodeNameError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail={"code": "NODE_NAME_CONFLICT", "message": str(exc)},
        ) from exc
    background_tasks.add_task(call_record_audit, audit_entry)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=_to_response(node), meta=meta)


@router.put(
    "/{node_id}",
    response_model=ApiResponse[PipelineNodeResponse],
)
async def update_pipeline_node(
    node_id: str,
    payload: PipelineNodeUpdateRequest,
    background_tasks: BackgroundTasks,
    service: AsyncPipelineNodeService = Depends(get_pipeline_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[PipelineNodeResponse]:
    try:
        node, audit_entry = await service.update_node(
            node_id,
            payload.model_dump(exclude_none=True),
            actor.actor_id,
        )
    except DuplicateNodeNameError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail={"code": "NODE_NAME_CONFLICT", "message": str(exc)},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={"code": "NODE_NOT_FOUND", "message": "Pipeline node not found"},
        ) from exc
    background_tasks.add_task(call_record_audit, audit_entry)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=_to_response(node), meta=meta)


@router.get(
    "",
    response_model=ApiResponse[PipelineNodeListResponse],
)
async def list_pipeline_nodes(
    pipelineId: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
    service: AsyncPipelineNodeService = Depends(get_pipeline_service),
) -> ApiResponse[PipelineNodeListResponse]:
    if page < 1:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_PAGE", "message": "page must be greater than or equal to 1"},
        )
    if pageSize <= 0 or pageSize > 100:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_PAGE_SIZE", "message": "pageSize must be within 1..100"},
        )
    nodes, total = await service.list_nodes(pipelineId, status, page, pageSize)
    items = [_to_response(node) for node in nodes]
    payload = PipelineNodeListResponse(page=page, pageSize=pageSize, total=total, items=items)
    meta = ApiMeta(
        requestId=ContextBridge.request_id(),  # type: ignore[arg-type]
        pagination=PaginationMeta(page=page, pageSize=pageSize, total=total),
    )
    return ApiResponse(data=payload, meta=meta)


@router.delete(
    "/{node_id}",
    status_code=http_status.HTTP_200_OK,
    response_model=ApiResponse[dict[str, Any] | None],
)
async def delete_pipeline_node(
    node_id: str,
    background_tasks: BackgroundTasks,
    service: AsyncPipelineNodeService = Depends(get_pipeline_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[dict[str, Any] | None]:
    try:
        audit_entry = await service.delete_node(node_id, actor.actor_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={"code": "NODE_NOT_FOUND", "message": "Pipeline node not found"},
        ) from exc
    background_tasks.add_task(call_record_audit, audit_entry)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=None, meta=meta)


def _to_response(node: Any) -> PipelineNodeResponse:
    snapshot = _to_snapshot(node)
    return PipelineNodeResponse(**snapshot.model_dump(), latestSnapshot=snapshot)


def _to_snapshot(node: Any) -> PipelineNodeSnapshot:
    return PipelineNodeSnapshot(
        id=node.node_id,
        name=node.name,
        allowLLM=node.allow_llm,
        systemPrompt=node.system_prompt,
        pipelineId=node.pipeline_id,
        status=node.status,
        strategy=dict(node.strategy or {}),
        createdAt=node.created_at,
        clientCreatedAt=node.client_created_at,
        updatedAt=node.updated_at,
        version=node.version,
        updatedBy=node.updated_by,
    )
