from __future__ import annotations

"""Workflow domain services."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional, Sequence, Tuple

from business_service.workflow.models import (
    PromptBinding,
    StageDefinition,
    ToolDefinition,
    WorkflowDefinition,
    WorkflowPublishRecord,
)
from business_service.workflow.repository import (
    AsyncStageRepository,
    AsyncToolRepository,
    AsyncWorkflowHistoryRepository,
    AsyncWorkflowRepository,
    PUBLISH_HISTORY_LIMIT,
    calculate_history_checksum,
)
from project_utility.telemetry import emit as telemetry_emit

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


def _emit_workflow_event(
    event_type: str,
    *,
    level: str = "info",
    workflow: Optional[WorkflowDefinition] = None,
    payload: Optional[Mapping[str, Any]] = None,
    actor: Optional[str] = None,
) -> None:
    data = dict(payload or {})
    workflow_id = data.get("workflow_id")
    if workflow is not None:
        workflow_id = workflow.workflow_id
        data.setdefault("name", workflow.name)
        data.setdefault("status", workflow.status)
        data.setdefault("version", workflow.version)
    telemetry_emit(
        event_type,
        level=level,
        workflow_id=workflow_id,
        payload=data,
        actor=actor,
    )


@dataclass(slots=True)
class AsyncWorkflowService:
    repository: AsyncWorkflowRepository
    history_repository: Optional[AsyncWorkflowHistoryRepository] = None

    async def _load_history_slice(self, workflow: WorkflowDefinition) -> Sequence[WorkflowPublishRecord]:
        if self.history_repository is not None:
            return await self.history_repository.list_history(workflow.workflow_id, limit=PUBLISH_HISTORY_LIMIT)
        return workflow.publish_history

    async def _next_history_state(
        self,
        workflow: WorkflowDefinition,
        new_record: Optional[WorkflowPublishRecord],
    ) -> tuple[Sequence[WorkflowPublishRecord], str]:
        history = list(await self._load_history_slice(workflow))
        if new_record is not None:
            history.append(new_record)
        trimmed = tuple(history[-PUBLISH_HISTORY_LIMIT:])
        checksum = calculate_history_checksum(trimmed)
        return trimmed, checksum

    async def create(self, payload: Mapping[str, Any], actor: Optional[str]) -> WorkflowDefinition:
        workflow = WorkflowDefinition.new(
            name=str(payload["name"]),
            description=str(payload.get("description") or ""),
            stage_ids=payload.get("stageIds") or [],
            metadata=payload.get("metadata") or {},
            node_sequence=payload.get("nodeSequence") or [],
            prompt_bindings=_coerce_prompt_bindings(payload.get("promptBindings")),
            strategy=payload.get("strategy") or {},
            actor=actor,
        )
        created = await self.repository.create(workflow)
        _emit_workflow_event(
            "workflow.create",
            workflow=created,
            payload={"stage_ids": list(created.stage_ids)},
            actor=actor,
        )
        return created

    async def update(
        self,
        workflow_id: str,
        payload: Mapping[str, Any],
        *,
        expected_version: int,
        actor: Optional[str],
    ) -> WorkflowDefinition:
        updates: MutableMapping[str, Any] = {}
        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "description" in payload:
            updates["description"] = str(payload.get("description") or "")
        if "stageIds" in payload:
            updates["stage_ids"] = list(payload.get("stageIds") or [])
        if "metadata" in payload:
            updates["metadata"] = dict(payload.get("metadata") or {})
        if "nodeSequence" in payload:
            updates["node_sequence"] = list(payload.get("nodeSequence") or [])
        if "promptBindings" in payload:
            updates["prompt_bindings"] = [
                binding.to_document() for binding in _coerce_prompt_bindings(payload.get("promptBindings"))
            ]
        if "strategy" in payload:
            updates["strategy"] = dict(payload.get("strategy") or {})
        updates["updated_by"] = actor
        updated = await self.repository.update(
            workflow_id,
            updates,
            expected_version=expected_version,
            status="draft",
            pending_changes=True,
        )
        _emit_workflow_event(
            "workflow.update",
            workflow=updated,
            payload={"changes": list(updates.keys())},
            actor=actor,
        )
        return updated

    async def delete(self, workflow_id: str, *, force: bool = False) -> None:
        workflow = await self.repository.get(workflow_id)
        if workflow is None:
            raise KeyError(workflow_id)
        if workflow.status == "published" and not force:
            raise ValueError("cannot delete published workflow without force=true")
        deleted = await self.repository.delete(workflow_id)
        if deleted is None:
            raise KeyError(workflow_id)

    async def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return await self.repository.get(workflow_id)

    async def list(self) -> Sequence[WorkflowDefinition]:
        return await self.repository.list_workflows()

    async def publish(
        self,
        workflow: WorkflowDefinition,
        *,
        actor: Optional[str],
        comment: Optional[str],
    ) -> WorkflowDefinition:
        if workflow.status == "published" and not workflow.pending_changes:
            raise ValueError(f"workflow '{workflow.workflow_id}' has no pending changes")
        history_slice = await self._load_history_slice(workflow)
        snapshot = workflow.to_document()
        previous_snapshot = history_slice[-1].snapshot if history_slice else None
        publish_record = WorkflowPublishRecord(
            version=workflow.version + 1,
            action="publish",
            actor=actor,
            comment=comment,
            timestamp=_now_utc(),
            snapshot=_build_publish_snapshot(snapshot),
            diff=_build_diff(snapshot, previous_snapshot),
        )
        _, history_checksum = await self._next_history_state(workflow, publish_record)
        updated = await self.repository.update(
            workflow.workflow_id,
            {},
            expected_version=workflow.version,
            status="published",
            pending_changes=False,
            published_version=workflow.version + 1,
            publish_record=publish_record,
            history_checksum=history_checksum,
        )
        if self.history_repository is not None:
            await self.history_repository.append(workflow.workflow_id, publish_record)
        _emit_workflow_event(
            "workflow.publish",
            workflow=updated,
            payload={"comment": comment},
            actor=actor,
        )
        return updated

    async def rollback(
        self,
        workflow: WorkflowDefinition,
        *,
        target_version: int,
        actor: Optional[str],
    ) -> WorkflowDefinition:
        if target_version >= workflow.version:
            raise ValueError("target version must be less than current version")
        history_slice = await self._load_history_slice(workflow)
        target_history = _find_publish_record(history_slice, target_version)
        if target_history is None:
            raise KeyError(f"workflow '{workflow.workflow_id}' version '{target_version}' not found")
        snapshot = dict(target_history.snapshot)
        updates: MutableMapping[str, Any] = {
            "name": snapshot.get("name", workflow.name),
            "description": snapshot.get("description", workflow.description),
            "stage_ids": snapshot.get("stageIds", list(workflow.stage_ids)),
            "metadata": snapshot.get("metadata", workflow.metadata),
            "node_sequence": snapshot.get("nodeSequence", list(workflow.node_sequence)),
            "prompt_bindings": snapshot.get("promptBindings", [binding.to_document() for binding in workflow.prompt_bindings]),
            "strategy": snapshot.get("strategy", workflow.strategy),
            "updated_by": actor,
        }
        publish_record = WorkflowPublishRecord(
            version=workflow.version + 1,
            action="rollback",
            actor=actor,
            comment=f"rollback to v{target_version}",
            timestamp=_now_utc(),
            snapshot=_build_publish_snapshot(snapshot),
            diff={"rollbackToVersion": target_version},
        )
        _, history_checksum = await self._next_history_state(workflow, publish_record)
        updated = await self.repository.update(
            workflow.workflow_id,
            updates,
            expected_version=workflow.version,
            status="published",
            pending_changes=False,
            published_version=workflow.version + 1,
            publish_record=publish_record,
            history_checksum=history_checksum,
        )
        if self.history_repository is not None:
            await self.history_repository.append(workflow.workflow_id, publish_record)
        _emit_workflow_event(
            "workflow.rollback",
            workflow=updated,
            payload={"target_version": target_version},
            actor=actor,
        )
        return updated


def _coerce_prompt_bindings(raw: Optional[Sequence[Any]]) -> Tuple[PromptBinding, ...]:
    if not raw:
        return ()
    bindings: list[PromptBinding] = []
    for item in raw:
        if isinstance(item, PromptBinding):
            bindings.append(item)
            continue
        node_id = ""
        prompt_id = ""
        if isinstance(item, Mapping):
            node_id = str(item.get("nodeId") or item.get("node_id") or "")
            prompt_id = str(item.get("promptId") or item.get("prompt_id") or "")
        else:
            telemetry_emit(
                "workflow.prompt_binding.invalid_type",
                level="warning",
                payload={"payload": str(item)},
            )
        bindings.append(PromptBinding(node_id=node_id, prompt_id=prompt_id))
    return tuple(bindings)


def _build_publish_snapshot(document: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "name": document.get("name"),
        "description": document.get("description"),
        "stageIds": list(document.get("stage_ids") or document.get("stageIds") or []),
        "metadata": dict(document.get("metadata") or {}),
        "nodeSequence": list(document.get("node_sequence") or document.get("nodeSequence") or []),
        "promptBindings": [
            {"nodeId": item.get("node_id") or item.get("nodeId"), "promptId": item.get("prompt_id") or item.get("promptId")}
            for item in document.get("prompt_bindings") or document.get("promptBindings") or []
        ],
        "strategy": dict(document.get("strategy") or {}),
    }


def _build_diff(current: Mapping[str, Any], previous: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    if previous is None:
        return {"changedFields": ["initial"]}
    diffs: MutableMapping[str, Any] = {}
    monitored_keys = ["stageIds", "nodeSequence", "promptBindings", "strategy", "metadata"]
    for key in monitored_keys:
        current_value = current.get(key)
        previous_value = previous.get(key)
        if current_value != previous_value:
            diffs[key] = {
                "before": previous_value,
                "after": current_value,
            }
    if not diffs:
        return {"changedFields": []}
    return diffs


def _find_publish_record(history: Sequence[WorkflowPublishRecord], version: int) -> Optional[WorkflowPublishRecord]:
    for record in history:
        if record.version == version:
            return record
    return None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)
