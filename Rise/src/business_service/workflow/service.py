from __future__ import annotations

"""Workflow domain services."""

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple

from business_service.workflow.models import StageDefinition, ToolDefinition, WorkflowDefinition
from business_service.workflow.repository import (
    AsyncStageRepository,
    AsyncToolRepository,
    AsyncWorkflowRepository,
)

__all__ = [
    "AsyncToolService",
    "AsyncStageService",
    "AsyncWorkflowService",
]


@dataclass(slots=True)
class AsyncToolService:
    repository: AsyncToolRepository

    async def create(self, payload: Mapping[str, Any], actor: Optional[str]) -> ToolDefinition:
        tool = ToolDefinition.new(
            name=str(payload["name"]),
            description=str(payload.get("description") or ""),
            prompt_snippet=str(payload.get("promptSnippet") or ""),
            metadata=payload.get("metadata") or {},
            actor=actor,
        )
        return await self.repository.create(tool)

    async def update(self, tool_id: str, payload: Mapping[str, Any], actor: Optional[str]) -> ToolDefinition:
        updates: dict[str, Any] = {}
        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "description" in payload:
            updates["description"] = str(payload.get("description") or "")
        if "promptSnippet" in payload:
            updates["prompt_snippet"] = str(payload.get("promptSnippet") or "")
        if "metadata" in payload:
            updates["metadata"] = dict(payload.get("metadata") or {})
        updates["updated_by"] = actor
        return await self.repository.update(tool_id, updates)

    async def delete(self, tool_id: str) -> None:
        deleted = await self.repository.delete(tool_id)
        if deleted is None:
            raise KeyError(tool_id)

    async def get(self, tool_id: str) -> Optional[ToolDefinition]:
        return await self.repository.get(tool_id)

    async def list(self) -> Sequence[ToolDefinition]:
        return await self.repository.list_tools()


@dataclass(slots=True)
class AsyncStageService:
    repository: AsyncStageRepository

    async def create(self, payload: Mapping[str, Any], actor: Optional[str]) -> StageDefinition:
        stage = StageDefinition.new(
            name=str(payload["name"]),
            prompt_template=str(payload["promptTemplate"]),
            description=str(payload.get("description") or ""),
            tool_ids=payload.get("toolIds") or [],
            metadata=payload.get("metadata") or {},
            actor=actor,
        )
        return await self.repository.create(stage)

    async def update(self, stage_id: str, payload: Mapping[str, Any], actor: Optional[str]) -> StageDefinition:
        updates: dict[str, Any] = {}
        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "promptTemplate" in payload:
            updates["prompt_template"] = str(payload["promptTemplate"])
        if "description" in payload:
            updates["description"] = str(payload.get("description") or "")
        if "toolIds" in payload:
            updates["tool_ids"] = list(payload.get("toolIds") or [])
        if "metadata" in payload:
            updates["metadata"] = dict(payload.get("metadata") or {})
        updates["updated_by"] = actor
        return await self.repository.update(stage_id, updates)

    async def delete(self, stage_id: str) -> None:
        deleted = await self.repository.delete(stage_id)
        if deleted is None:
            raise KeyError(stage_id)

    async def get(self, stage_id: str) -> Optional[StageDefinition]:
        return await self.repository.get(stage_id)

    async def list(self) -> Sequence[StageDefinition]:
        return await self.repository.list_stages()

    async def get_many(self, stage_ids: Sequence[str]) -> Sequence[StageDefinition]:
        if not stage_ids:
            return ()
        return await self.repository.get_many(stage_ids)


@dataclass(slots=True)
class AsyncWorkflowService:
    repository: AsyncWorkflowRepository

    async def create(self, payload: Mapping[str, Any], actor: Optional[str]) -> WorkflowDefinition:
        workflow = WorkflowDefinition.new(
            name=str(payload["name"]),
            description=str(payload.get("description") or ""),
            stage_ids=payload.get("stageIds") or [],
            metadata=payload.get("metadata") or {},
            actor=actor,
        )
        return await self.repository.create(workflow)

    async def update(self, workflow_id: str, payload: Mapping[str, Any], actor: Optional[str]) -> WorkflowDefinition:
        updates: dict[str, Any] = {}
        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "description" in payload:
            updates["description"] = str(payload.get("description") or "")
        if "stageIds" in payload:
            updates["stage_ids"] = list(payload.get("stageIds") or [])
        if "metadata" in payload:
            updates["metadata"] = dict(payload.get("metadata") or {})
        updates["updated_by"] = actor
        return await self.repository.update(workflow_id, updates)

    async def delete(self, workflow_id: str) -> None:
        deleted = await self.repository.delete(workflow_id)
        if deleted is None:
            raise KeyError(workflow_id)

    async def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return await self.repository.get(workflow_id)

    async def list(self) -> Sequence[WorkflowDefinition]:
        return await self.repository.list_workflows()
