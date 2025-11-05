from __future__ import annotations

"""FastAPI routes for prompt management."""

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status as http_status

from business_service.prompt import PromptService
from interface_entry.http.prompts.dto import (
    PromptListResponse,
    PromptPayload,
    PromptResponse,
    PromptUpdatePayload,
)
from interface_entry.http.dependencies import get_prompt_service
from interface_entry.http.responses import ApiMeta, ApiResponse, PaginationMeta
from interface_entry.http.security import ActorContext, get_actor_context
from foundational_service.contracts.toolcalls import call_record_audit
from project_utility.context import ContextBridge

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("", response_model=ApiResponse[PromptListResponse])
async def list_prompts(
    page: int = 1,
    pageSize: int = 20,
    service: PromptService = Depends(get_prompt_service),
) -> ApiResponse[PromptListResponse]:
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
    prompts, total = await service.list_prompts(page, pageSize)
    items = [_to_response(prompt) for prompt in prompts]
    payload = PromptListResponse(page=page, pageSize=pageSize, total=total, items=items)
    meta = ApiMeta(
        requestId=ContextBridge.request_id(),  # type: ignore[arg-type]
        pagination=PaginationMeta(page=page, pageSize=pageSize, total=total),
    )
    return ApiResponse(data=payload, meta=meta)


@router.post("", response_model=ApiResponse[PromptResponse], status_code=http_status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptPayload,
    background_tasks: BackgroundTasks,
    service: PromptService = Depends(get_prompt_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[PromptResponse]:
    prompt, audit_entry = await service.create_prompt(payload.model_dump(), actor.actor_id)
    background_tasks.add_task(call_record_audit, audit_entry)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=_to_response(prompt), meta=meta)


@router.put("/{prompt_id}", response_model=ApiResponse[PromptResponse])
async def update_prompt(
    prompt_id: str,
    payload: PromptUpdatePayload,
    background_tasks: BackgroundTasks,
    service: PromptService = Depends(get_prompt_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[PromptResponse]:
    if not payload.model_dump(exclude_none=True):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_BODY", "message": "At least one field must be provided"},
        )
    try:
        prompt, audit_entry = await service.update_prompt(
            prompt_id,
            payload.model_dump(exclude_none=True),
            actor.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={"code": "PROMPT_NOT_FOUND", "message": "Prompt not found"},
        ) from exc
    background_tasks.add_task(call_record_audit, audit_entry)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=_to_response(prompt), meta=meta)


@router.delete("/{prompt_id}", status_code=http_status.HTTP_200_OK, response_model=ApiResponse[dict[str, Any] | None])
async def delete_prompt(
    prompt_id: str,
    background_tasks: BackgroundTasks,
    service: PromptService = Depends(get_prompt_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[dict[str, Any] | None]:
    try:
        audit_entry = await service.delete_prompt(prompt_id, actor.actor_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={"code": "PROMPT_NOT_FOUND", "message": "Prompt not found"},
        ) from exc
    background_tasks.add_task(call_record_audit, audit_entry)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=None, meta=meta)


def _to_response(prompt: Any) -> PromptResponse:
    return PromptResponse(
        id=prompt.prompt_id,
        name=prompt.name,
        markdown=prompt.markdown,
        createdAt=prompt.created_at,
        updatedAt=prompt.updated_at,
        version=prompt.version,
        updatedBy=prompt.updated_by,
    )
