from __future__ import annotations

"""Workflow observability helpers (logs, variables, tools, SSE streaming)."""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from business_service.workflow.models import WorkflowDefinition
from business_service.workflow.repository import AsyncStageRepository, AsyncToolRepository, AsyncWorkflowRepository
from foundational_service.persist.observability import WorkflowRunReadRepository

__all__ = [
    "WorkflowLogRecord",
    "WorkflowLogPage",
    "WorkflowObservabilityService",
    "WorkflowVariableEntry",
    "WorkflowVariablesPayload",
    "WorkflowToolsPayload",
    "WorkflowAccessError",
    "WorkflowLogQuery",
]

VARIABLE_ENTRY_LIMIT = 200


@dataclass(slots=True)
class WorkflowLogRecord:
    task_id: str
    stage_id: Optional[str]
    stage_name: Optional[str]
    level: str
    message: str
    metadata: Mapping[str, Any]
    timestamp: datetime
    cursor: str


@dataclass(slots=True)
class WorkflowLogPage:
    workflow_id: str
    items: Sequence[WorkflowLogRecord]
    next_cursor: Optional[str]
    warnings: Sequence[str]


@dataclass(slots=True)
class WorkflowVariableEntry:
    name: str
    type: str
    value: Any


@dataclass(slots=True)
class WorkflowVariablesPayload:
    workflow_id: str
    task_id: Optional[str]
    variables: Sequence[WorkflowVariableEntry]
    warnings: Sequence[str]


@dataclass(slots=True)
class WorkflowToolsPayload:
    workflow_id: str
    tools: Sequence[Mapping[str, Any]]
    source: str


@dataclass(slots=True)
class WorkflowLogQuery:
    limit: int
    since: Optional[datetime]
    cursor: Optional[str]
    task_id: Optional[str]


class WorkflowAccessError(PermissionError):
    """Raised when workflow is missing or actor has no access."""


class WorkflowObservabilityService:
    def __init__(
        self,
        *,
        workflow_repository: AsyncWorkflowRepository,
        stage_repository: AsyncStageRepository,
        tool_repository: AsyncToolRepository,
        run_repository: WorkflowRunReadRepository,
        poll_interval_seconds: float = 3.0,
        heartbeat_interval_seconds: float = 30.0,
    ) -> None:
        self._workflow_repository = workflow_repository
        self._stage_repository = stage_repository
        self._tool_repository = tool_repository
        self._run_repository = run_repository
        self._poll_interval_seconds = poll_interval_seconds
        self._heartbeat_interval_seconds = heartbeat_interval_seconds

    async def stream_logs(self, workflow_id: str, *, actor_id: Optional[str]) -> AsyncIterator[str]:
        workflow = await self._require_workflow(workflow_id, actor_id)
        seen: List[str] = []
        last_emit = datetime.now(timezone.utc)
        try:
            while True:
                page = await self.list_logs(
                    workflow.workflow_id,
                    WorkflowLogQuery(limit=100, since=None, cursor=None, task_id=None),
                    actor_id=actor_id,
                )
                for record in reversed(page.items):
                    if record.cursor in seen:
                        continue
                    seen.append(record.cursor)
                    if len(seen) > 500:
                        seen = seen[-250:]
                    payload = {
                        "workflowId": workflow.workflow_id,
                        "taskId": record.task_id,
                        "stageId": record.stage_id,
                        "stageName": record.stage_name,
                        "level": record.level,
                        "message": record.message,
                        "metadata": record.metadata,
                        "timestamp": record.timestamp.isoformat(),
                        "cursor": record.cursor,
                    }
                    last_emit = datetime.now(timezone.utc)
                    yield self._format_sse("workflow.log", payload)
                now = datetime.now(timezone.utc)
                if (now - last_emit).total_seconds() >= self._heartbeat_interval_seconds:
                    last_emit = now
                    yield self._format_sse(
                        "heartbeat",
                        {
                            "workflowId": workflow.workflow_id,
                            "timestamp": now.isoformat(),
                            "seen": len(seen),
                        },
                    )
                await asyncio.sleep(self._poll_interval_seconds)
        except asyncio.CancelledError:
            raise

    async def list_logs(self, workflow_id: str, query: WorkflowLogQuery, *, actor_id: Optional[str]) -> WorkflowLogPage:
        await self._require_workflow(workflow_id, actor_id)
        runs: Sequence[Mapping[str, Any]]
        if query.task_id:
            doc = await self._run_repository.get_by_task(workflow_id, query.task_id)
            runs = (doc,) if doc else ()
        else:
            task_limit = max(10, min(50, query.limit * 2))
            runs = await self._run_repository.list_runs(
                workflow_id,
                limit_tasks=task_limit,
                since=query.since,
            )
        flattened = self._flatten_logs(runs)
        start_index = 0
        if query.cursor:
            try:
                start_index = next(i + 1 for i, item in enumerate(flattened) if item.cursor == query.cursor)
            except StopIteration:
                start_index = 0
        end_index = min(len(flattened), start_index + query.limit)
        page_items = flattened[start_index:end_index]
        next_cursor = flattened[end_index].cursor if end_index < len(flattened) else None
        warnings: List[str] = []
        if not runs:
            warnings.append("NO_EXECUTION")
        elif not page_items:
            warnings.append("CURSOR_EXHAUSTED")
        return WorkflowLogPage(workflow_id=workflow_id, items=page_items, next_cursor=next_cursor, warnings=warnings)

    async def get_variables(
        self,
        workflow_id: str,
        *,
        task_id: Optional[str],
        actor_id: Optional[str],
    ) -> WorkflowVariablesPayload:
        await self._require_workflow(workflow_id, actor_id)
        if task_id:
            run = await self._run_repository.get_by_task(workflow_id, task_id)
        else:
            run = await self._run_repository.get_latest(workflow_id)
        if run is None:
            return WorkflowVariablesPayload(workflow_id=workflow_id, task_id=None, variables=(), warnings=("NO_EXECUTION",))
        variables: List[WorkflowVariableEntry] = []
        warnings: List[str] = []
        selected_task = str(run.get("task_id"))
        final_text = self._nested_get(run, ("result", "finalText")) or ""
        variables.append(WorkflowVariableEntry(name="taskId", type="string", value=selected_task))
        variables.append(WorkflowVariableEntry(name="workflowId", type="string", value=workflow_id))
        variables.append(WorkflowVariableEntry(name="finalText", type="string", value=final_text))
        telemetry = self._nested_get(run, ("result", "telemetry")) or {}
        for key, value in telemetry.items():
            variables.append(WorkflowVariableEntry(name=f"telemetry.{key}", type=self._infer_type(value), value=value))
        payload_snapshot = run.get("payload_snapshot") or {}
        for key, value in payload_snapshot.get("metadata", {}).items():
            variables.append(WorkflowVariableEntry(name=f"metadata.{key}", type=self._infer_type(value), value=value))
        core_envelope = payload_snapshot.get("coreEnvelope") or {}
        for key, value in core_envelope.items():
            variables.append(WorkflowVariableEntry(name=f"coreEnvelope.{key}", type=self._infer_type(value), value=value))
        if len(variables) > VARIABLE_ENTRY_LIMIT:
            warnings.append("VARIABLES_TRUNCATED")
            variables = variables[:VARIABLE_ENTRY_LIMIT]
        return WorkflowVariablesPayload(workflow_id=workflow_id, task_id=selected_task, variables=variables, warnings=tuple(warnings))

    async def list_tools(self, workflow_id: str, *, actor_id: Optional[str]) -> WorkflowToolsPayload:
        workflow = await self._require_workflow(workflow_id, actor_id)
        metadata_tools = workflow.metadata.get("tools")
        if isinstance(metadata_tools, list) and metadata_tools:
            sanitized = [self._sanitize_tool_metadata(item) for item in metadata_tools]
            return WorkflowToolsPayload(workflow_id=workflow_id, tools=sanitized, source="metadata")
        stages = await self._stage_repository.get_many(workflow.stage_ids)
        tool_ids: List[str] = []
        for stage in stages:
            tool_ids.extend(stage.tool_ids)
        unique_ids = list(dict.fromkeys(tool_ids))
        if not unique_ids:
            return WorkflowToolsPayload(workflow_id=workflow_id, tools=(), source="definition")
        tool_defs = await self._tool_repository.get_many(unique_ids)
        tools = [
            {
                "toolId": tool.tool_id,
                "name": tool.name,
                "kind": tool.metadata.get("kind", "custom"),
                "config": tool.metadata,
                "promptSnippet": tool.prompt_snippet,
            }
            for tool in tool_defs
        ]
        return WorkflowToolsPayload(workflow_id=workflow_id, tools=tools, source="registry")

    async def _require_workflow(self, workflow_id: str, actor_id: Optional[str]) -> WorkflowDefinition:
        workflow = await self._workflow_repository.get(workflow_id)
        if workflow is None:
            raise WorkflowAccessError(workflow_id)
        # ACL hooks can be added here leveraging actor_id and workflow metadata.
        return workflow

    def _flatten_logs(self, runs: Sequence[Mapping[str, Any]]) -> List[WorkflowLogRecord]:
        items: List[WorkflowLogRecord] = []
        for doc in runs:
            task_id = str(doc.get("task_id"))
            updated_at: datetime = doc.get("updated_at") or doc.get("created_at") or datetime.now(timezone.utc)
            stage_results: Sequence[Mapping[str, Any]] = self._nested_get(doc, ("result", "stageResults")) or ()
            if not stage_results:
                cursor = f"{task_id}#final"
                message = self._nested_get(doc, ("result", "finalText")) or ""
                metadata = {"telemetry": self._nested_get(doc, ("result", "telemetry"))}
                items.append(
                    WorkflowLogRecord(
                        task_id=task_id,
                        stage_id=None,
                        stage_name=None,
                        level="info",
                        message=message,
                        metadata=metadata,
                        timestamp=updated_at,
                        cursor=cursor,
                    )
                )
                continue
            for index, stage in enumerate(stage_results):
                cursor = f"{task_id}#{index}"
                metadata = {
                    "promptUsed": stage.get("promptUsed"),
                    "usage": stage.get("usage"),
                }
                items.append(
                    WorkflowLogRecord(
                        task_id=task_id,
                        stage_id=stage.get("stageId"),
                        stage_name=stage.get("name"),
                        level="info",
                        message=str(stage.get("outputText") or ""),
                        metadata=metadata,
                        timestamp=updated_at,
                        cursor=cursor,
                    )
                )
        items.sort(key=lambda record: record.timestamp, reverse=True)
        return items

    @staticmethod
    def _sanitize_tool_metadata(raw: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "name": raw.get("name"),
            "kind": raw.get("kind") or raw.get("type") or "custom",
            "config": raw.get("config") or {},
            "description": raw.get("description"),
        }

    @staticmethod
    def _infer_type(value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, Mapping):
            return "object"
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return "array"
        return "string"

    @staticmethod
    def _nested_get(data: Mapping[str, Any], path: Tuple[str, ...]) -> Any:
        cursor: Any = data
        for key in path:
            if not isinstance(cursor, Mapping):
                return None
            cursor = cursor.get(key)
            if cursor is None:
                return None
        return cursor

    @staticmethod
    def _format_sse(event: str, payload: Mapping[str, Any]) -> str:
        body = json.dumps(payload, ensure_ascii=False)
        return f"event: {event}\ndata: {body}\n\n"
