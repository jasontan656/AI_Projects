from __future__ import annotations

"""HTTP routes for tool definitions."""

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status

from business_service.workflow import AsyncToolService
from interface_entry.http.dependencies import get_tool_service
from interface_entry.http.responses import ApiMeta, ApiResponse
from interface_entry.http.security import ActorContext, get_actor_context
from interface_entry.http.tools.dto import ToolRequest, ToolResponse
from project_utility.context import ContextBridge

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=ApiResponse[Sequence[ToolResponse]])
async def list_tools(service: AsyncToolService = Depends(get_tool_service)) -> ApiResponse[Sequence[ToolResponse]]:
    tools = await service.list()
    data = [
        ToolResponse(
            toolId=tool.tool_id,
            name=tool.name,
            description=tool.description,
            promptSnippet=tool.prompt_snippet,
            metadata=tool.metadata,
            version=tool.version,
            updatedAt=tool.updated_at,
            updatedBy=tool.updated_by,
        )
        for tool in tools
    ]
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[ToolResponse])
async def create_tool(
    payload: ToolRequest,
    service: AsyncToolService = Depends(get_tool_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[ToolResponse]:
    tool = await service.create(payload.model_dump(), actor.actor_id)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = ToolResponse(
        toolId=tool.tool_id,
        name=tool.name,
        description=tool.description,
        promptSnippet=tool.prompt_snippet,
        metadata=tool.metadata,
        version=tool.version,
        updatedAt=tool.updated_at,
        updatedBy=tool.updated_by,
    )
    return ApiResponse(data=data, meta=meta)


@router.put("/{tool_id}", response_model=ApiResponse[ToolResponse])
async def update_tool(
    tool_id: str,
    payload: ToolRequest,
    service: AsyncToolService = Depends(get_tool_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[ToolResponse]:
    try:
        tool = await service.update(tool_id, payload.model_dump(exclude_unset=True), actor.actor_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TOOL_NOT_FOUND", "message": "Tool definition not found"},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = ToolResponse(
        toolId=tool.tool_id,
        name=tool.name,
        description=tool.description,
        promptSnippet=tool.prompt_snippet,
        metadata=tool.metadata,
        version=tool.version,
        updatedAt=tool.updated_at,
        updatedBy=tool.updated_by,
    )
    return ApiResponse(data=data, meta=meta)


@router.delete("/{tool_id}", status_code=status.HTTP_200_OK, response_model=ApiResponse[dict[str, str]])
async def delete_tool(
    tool_id: str,
    service: AsyncToolService = Depends(get_tool_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[dict[str, str]]:
    try:
        await service.delete(tool_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TOOL_NOT_FOUND", "message": "Tool definition not found"},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data={"status": "deleted", "toolId": tool_id}, meta=meta)
