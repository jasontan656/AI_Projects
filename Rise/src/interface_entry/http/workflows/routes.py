from __future__ import annotations

"""HTTP routes for workflow definitions and execution.

注意：这些接口服务于 Admin Panel / 后端工具链，是内部配置面板的一部分，不属于外部用户输入。
因此它们直接暴露 REST API 供内部调用即可，不需要接入外部入口的 Redis/RabbitMQ 兜底机制。
真正的外部输入（Telegram bot、未来的聊天渠道等）必须走统一封包→队列→Worker 的底座。
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from business_service.channel.coverage_status import CoverageStatusService, WorkflowCoverageStatus
from business_service.prompt.repository import AsyncMongoPromptRepository
from business_service.workflow import AsyncWorkflowService, AsyncStageService, WorkflowObservabilityService
from business_service.workflow.models import WorkflowDefinition, PromptBinding as DomainPromptBinding
from business_service.workflow.repository import WorkflowVersionConflict
from business_service.workflow.observability import (
    WorkflowAccessError,
    WorkflowLogQuery,
    WorkflowLogPage,
    WorkflowToolsPayload,
    WorkflowVariablesPayload,
)
from foundational_service.persist.task_envelope import RetryState, TaskEnvelope, TaskStatus
from foundational_service.persist.worker import TaskRuntime, TaskSubmitter
from interface_entry.http.dependencies.workflow import (
    get_workflow_service,
    get_stage_service,
    get_workflow_observability_service,
    get_prompt_repository,
)
from interface_entry.http.dependencies.telemetry import (
    get_task_runtime,
    get_task_submitter,
    get_coverage_status_service,
)
from interface_entry.http.responses import ApiMeta, ApiResponse
from interface_entry.http.security import ActorContext, get_actor_context
from interface_entry.http.workflows.dto import (
    PromptBinding as PromptBindingDTO,
    TaskRetryMetadata,
    WorkflowApplyRequest,
    WorkflowApplyResponse,
    WorkflowApplyResult,
    WorkflowCoverageStatusResponse,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowPublishMeta,
    WorkflowStageResult,
    WorkflowLogItem,
    WorkflowLogListResponse,
    WorkflowVariablesResponse,
    WorkflowVariableEntry,
    WorkflowToolsResponse,
    WorkflowToolDescriptor,
    WorkflowPublishRequest,
    WorkflowRollbackRequest,
    WorkflowPublishRecord,
    CoverageTestRequest,
)
from project_utility.context import ContextBridge
from foundational_service.telemetry.coverage_recorder import get_coverage_test_event_recorder

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("", response_model=ApiResponse[Sequence[WorkflowResponse]])
async def list_workflows(
    service: AsyncWorkflowService = Depends(get_workflow_service),
    coverage_service: CoverageStatusService = Depends(get_coverage_status_service),
) -> ApiResponse[Sequence[WorkflowResponse]]:
    workflows = await service.list()
    coverage_map: dict[str, WorkflowCoverageStatus] = {}
    if workflows:
        coverage_results = await asyncio.gather(
            *(coverage_service.get_status(workflow.workflow_id) for workflow in workflows)
        )
        coverage_map = {workflow.workflow_id: status for workflow, status in zip(workflows, coverage_results)}
    data = [
        _to_workflow_response(workflow, coverage=coverage_map.get(workflow.workflow_id)) for workflow in workflows
    ]
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.get("/{workflow_id}", response_model=ApiResponse[WorkflowResponse])
async def get_workflow(
    workflow_id: str,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    coverage_service: CoverageStatusService = Depends(get_coverage_status_service),
) -> ApiResponse[WorkflowResponse]:
    workflow = await workflow_service.get(workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow definition not found"},
        )
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    coverage = await coverage_service.get_status(workflow.workflow_id)
    data = _to_workflow_response(workflow, coverage=coverage)
    return ApiResponse(data=data, meta=meta)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[WorkflowResponse])
async def create_workflow(
    payload: WorkflowRequest,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    stage_service: AsyncStageService = Depends(get_stage_service),
    prompt_repository: AsyncMongoPromptRepository = Depends(get_prompt_repository),
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
    prompt_missing = await _validate_prompt_bindings(prompt_repository, payload.promptBindings or ())
    if prompt_missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "WORKFLOW_PROMPT_MISSING",
                "message": "Unknown prompt ids",
                "missing": prompt_missing,
            },
        )
    workflow = await workflow_service.create(payload.model_dump(), actor.actor_id)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = _to_workflow_response(workflow)
    return ApiResponse(data=data, meta=meta)


@router.put("/{workflow_id}", response_model=ApiResponse[WorkflowResponse])
async def update_workflow(
    workflow_id: str,
    payload: WorkflowRequest,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    stage_service: AsyncStageService = Depends(get_stage_service),
    prompt_repository: AsyncMongoPromptRepository = Depends(get_prompt_repository),
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
    prompt_missing = await _validate_prompt_bindings(prompt_repository, payload.promptBindings or ())
    if prompt_missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "WORKFLOW_PROMPT_MISSING",
                "message": "Unknown prompt ids",
                "missing": prompt_missing,
            },
        )
    if payload.version is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "WORKFLOW_VERSION_REQUIRED",
                "message": "version is required for workflow updates",
            },
        )
    try:
        workflow = await workflow_service.update(
            workflow_id,
            payload.model_dump(exclude_unset=True),
            expected_version=payload.version,
            actor=actor.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow definition not found"},
        ) from exc
    except WorkflowVersionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WORKFLOW_VERSION_CONFLICT", "message": "Workflow version mismatch"},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = _to_workflow_response(workflow)
    return ApiResponse(data=data, meta=meta)


@router.post("/{workflow_id}/publish", response_model=ApiResponse[WorkflowResponse])
async def publish_workflow(
    workflow_id: str,
    payload: WorkflowPublishRequest,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    stage_service: AsyncStageService = Depends(get_stage_service),
    prompt_repository: AsyncMongoPromptRepository = Depends(get_prompt_repository),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[WorkflowResponse]:
    workflow = await workflow_service.get(workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow definition not found"},
        )
    stage_missing = await _validate_stage_ids(stage_service, workflow.stage_ids)
    if stage_missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "WORKFLOW_STAGE_MISSING", "message": "Unknown stage ids", "missing": stage_missing},
        )
    prompt_missing = await _validate_prompt_bindings(prompt_repository, workflow.prompt_bindings)
    if prompt_missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "WORKFLOW_PROMPT_MISSING", "message": "Unknown prompt ids", "missing": prompt_missing},
        )
    if payload.targetVersion is not None and payload.targetVersion != workflow.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WORKFLOW_VERSION_CONFLICT",
                "message": f"Expected version {payload.targetVersion}, current {workflow.version}",
            },
        )
    try:
        updated = await workflow_service.publish(
            workflow,
            actor=actor.actor_id,
            comment=payload.comment,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WORKFLOW_PUBLISH_INVALID", "message": str(exc)},
        ) from exc
    except WorkflowVersionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WORKFLOW_VERSION_CONFLICT", "message": "Workflow version mismatch"},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = _to_workflow_response(updated)
    return ApiResponse(data=data, meta=meta)


@router.post(
    "/{workflow_id}/tests/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[WorkflowCoverageStatusResponse],
)
async def trigger_workflow_tests(
    workflow_id: str,
    payload: CoverageTestRequest,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    coverage_service: CoverageStatusService = Depends(get_coverage_status_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[WorkflowCoverageStatusResponse]:
    workflow = await workflow_service.get(workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow definition not found"},
        )
    scenarios = list(payload.scenarios) or ["golden_path"]
    coverage = await coverage_service.mark_status(
        workflow_id,
        status="pending",
        scenarios=scenarios,
        mode=payload.mode,
        actor_id=actor.actor_id,
        metadata={"trigger": "manual"},
    )
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = _to_coverage_response(coverage)
    return ApiResponse(data=data, meta=meta)


@router.get(
    "/{workflow_id}/tests/stream",
)
async def stream_workflow_tests(
    workflow_id: str,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    actor: ActorContext = Depends(get_actor_context),
) -> StreamingResponse:
    workflow = await workflow_service.get(workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow definition not found"},
        )
    # Ensure actor context is evaluated for auditing purposes.
    _ = actor.actor_id
    recorder = get_coverage_test_event_recorder()
    return StreamingResponse(recorder.stream(workflow.workflow_id), media_type="text/event-stream")


@router.post("/{workflow_id}/rollback", response_model=ApiResponse[WorkflowResponse])
async def rollback_workflow(
    workflow_id: str,
    payload: WorkflowRollbackRequest,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[WorkflowResponse]:
    workflow = await workflow_service.get(workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow definition not found"},
        )
    try:
        updated = await workflow_service.rollback(
            workflow,
            target_version=payload.targetVersion,
            actor=actor.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_VERSION_NOT_FOUND", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WORKFLOW_ROLLBACK_INVALID", "message": str(exc)},
        ) from exc
    except WorkflowVersionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WORKFLOW_VERSION_CONFLICT", "message": "Workflow version mismatch"},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    data = _to_workflow_response(updated)
    return ApiResponse(data=data, meta=meta)


@router.delete("/{workflow_id}", status_code=status.HTTP_200_OK, response_model=ApiResponse[dict[str, str]])
async def delete_workflow(
    workflow_id: str,
    workflow_service: AsyncWorkflowService = Depends(get_workflow_service),
    actor: ActorContext = Depends(get_actor_context),
    force: bool = Query(default=False),
) -> ApiResponse[dict[str, str]]:
    try:
        await workflow_service.delete(workflow_id, force=force)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow definition not found"},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WORKFLOW_DELETE_FORBIDDEN", "message": str(exc)},
        ) from exc
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data={"status": "deleted", "workflowId": workflow_id}, meta=meta)


@router.post("/apply", response_model=ApiResponse[WorkflowApplyResponse], status_code=status.HTTP_202_ACCEPTED)
async def apply_workflow(
    payload: WorkflowApplyRequest,
    response: Response,
    submitter: TaskSubmitter = Depends(get_task_submitter),
    runtime: TaskRuntime = Depends(get_task_runtime),
) -> ApiResponse[WorkflowApplyResponse]:
    request_id = ContextBridge.request_id()
    envelope = _build_envelope_from_request(payload, request_id)
    waiter = None
    if payload.waitForResult:
        waiter = await runtime.results.register(envelope.task_id)
    await submitter.submit(envelope)
    broker_message: Optional[Mapping[str, Any]] = None
    if payload.waitForResult and waiter is not None:
        try:
            broker_message = await asyncio.wait_for(waiter, timeout=payload.waitTimeoutSeconds)
        except asyncio.TimeoutError:
            await runtime.results.discard(envelope.task_id, waiter)
    snapshot = await runtime.queue.get_task(envelope.task_id)
    data = _build_task_response(snapshot or envelope, broker_message)
    response.status_code = status.HTTP_200_OK if data.status == TaskStatus.COMPLETED.value else status.HTTP_202_ACCEPTED
    meta = ApiMeta(requestId=request_id)  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.get("/tasks/{task_id}", response_model=ApiResponse[WorkflowApplyResponse])
async def get_task_status(task_id: str, runtime: TaskRuntime = Depends(get_task_runtime)) -> ApiResponse[WorkflowApplyResponse]:
    envelope = await runtime.queue.get_task(task_id)
    if envelope is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": "Task not found"},
        )
    data = _build_task_response(envelope)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.get("/{workflow_id}/logs/stream")
async def stream_workflow_logs(
    workflow_id: str,
    actor: ActorContext = Depends(get_actor_context),
    observability: WorkflowObservabilityService = Depends(get_workflow_observability_service),
) -> StreamingResponse:
    try:
        stream = observability.stream_logs(workflow_id, actor_id=actor.actor_id)
    except WorkflowAccessError as exc:  # pragma: no cover - passthrough to HTTP layer
        raise _workflow_access_http_error(workflow_id) from exc
    return StreamingResponse(stream, media_type="text/event-stream")


@router.get(
    "/{workflow_id}/logs",
    response_model=ApiResponse[WorkflowLogListResponse],
)
async def list_workflow_logs(
    workflow_id: str,
    limit: int = Query(50, ge=1, le=200),
    since: Optional[datetime] = Query(default=None),
    cursor: Optional[str] = Query(default=None),
    task_id: Optional[str] = Query(default=None, alias="taskId"),
    actor: ActorContext = Depends(get_actor_context),
    observability: WorkflowObservabilityService = Depends(get_workflow_observability_service),
) -> ApiResponse[WorkflowLogListResponse]:
    query = WorkflowLogQuery(
        limit=limit,
        since=_ensure_timezone(since),
        cursor=cursor,
        task_id=task_id,
    )
    try:
        page = await observability.list_logs(workflow_id, query, actor_id=actor.actor_id)
    except WorkflowAccessError as exc:
        raise _workflow_access_http_error(workflow_id) from exc
    data = _to_log_response(page)
    meta = ApiMeta(requestId=ContextBridge.request_id(), warnings=list(page.warnings))  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.get(
    "/{workflow_id}/variables",
    response_model=ApiResponse[WorkflowVariablesResponse],
)
async def get_workflow_variables(
    workflow_id: str,
    task_id: Optional[str] = Query(default=None, alias="taskId"),
    actor: ActorContext = Depends(get_actor_context),
    observability: WorkflowObservabilityService = Depends(get_workflow_observability_service),
) -> ApiResponse[WorkflowVariablesResponse]:
    try:
        payload = await observability.get_variables(workflow_id, task_id=task_id, actor_id=actor.actor_id)
    except WorkflowAccessError as exc:
        raise _workflow_access_http_error(workflow_id) from exc
    data = _to_variables_response(payload)
    meta = ApiMeta(requestId=ContextBridge.request_id(), warnings=list(payload.warnings))  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.get(
    "/{workflow_id}/tools",
    response_model=ApiResponse[WorkflowToolsResponse],
)
async def list_workflow_tools(
    workflow_id: str,
    actor: ActorContext = Depends(get_actor_context),
    observability: WorkflowObservabilityService = Depends(get_workflow_observability_service),
) -> ApiResponse[WorkflowToolsResponse]:
    try:
        payload = await observability.list_tools(workflow_id, actor_id=actor.actor_id)
    except WorkflowAccessError as exc:
        raise _workflow_access_http_error(workflow_id) from exc
    data = _to_tools_response(payload)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


def _build_envelope_from_request(payload: WorkflowApplyRequest, request_id: str) -> TaskEnvelope:
    core_envelope = dict(payload.coreEnvelope or {})
    if payload.chatId:
        metadata = dict(core_envelope.get("metadata") or {})
        metadata["chat_id"] = str(payload.chatId)
        core_envelope["metadata"] = metadata
    history_chunks = [str(item) for item in payload.history]
    telemetry = dict(payload.telemetry or {})
    metadata = dict(payload.metadata or {})
    channel = telemetry.get("channel") or metadata.get("channel") or "http"
    telemetry["channel"] = channel
    telemetry.setdefault("requestId", request_id)

    chat_id = payload.chatId or metadata.get("chat_id") or _extract_chat_id(core_envelope)
    if not chat_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CHAT_ID_REQUIRED", "message": "chatId 或 metadata.chat_id 必填"},
        )
    metadata["chat_id"] = str(chat_id)
    metadata.setdefault("source", metadata.get("source") or "http-api")

    payload_map = {
        "workflowId": payload.workflowId,
        "userText": payload.userText,
        "historyChunks": history_chunks,
        "policy": dict(payload.policy or {}),
        "coreEnvelope": core_envelope,
        "telemetry": telemetry,
        "metadata": metadata,
        "source": channel,
    }
    context = {
        "idempotencyKey": payload.idempotencyKey
        or _build_idempotency_key(channel=channel, workflow_id=payload.workflowId, chat_id=str(chat_id)),
        "traceId": request_id,
        "user": dict(payload.user or {}),
        "requestId": request_id,
    }
    retry_state = RetryState(count=0, max=payload.retryMax)
    return TaskEnvelope.new(task_type="workflow.execute", payload=payload_map, context=context, retry=retry_state)


def _extract_chat_id(core_envelope: Mapping[str, Any]) -> Optional[str]:
    metadata = core_envelope.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    chat_id = metadata.get("chat_id")
    if chat_id is None:
        return None
    return str(chat_id)


def _build_idempotency_key(*, channel: str, workflow_id: str, chat_id: str) -> str:
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    return f"{channel}:{workflow_id}:{chat_id}:{timestamp}"


def _build_task_response(
    envelope: TaskEnvelope,
    broker_message: Optional[Mapping[str, Any]] = None,
) -> WorkflowApplyResponse:
    status_value = broker_message.get("status") if broker_message else envelope.status.value
    result_payload = broker_message.get("result") if broker_message else envelope.result
    retry_meta = TaskRetryMetadata(
        count=envelope.retry.count,
        max=envelope.retry.max,
        nextAttemptAt=envelope.retry.next_attempt_at or None,
    )
    apply_result = None
    if result_payload:
        apply_result = WorkflowApplyResult(
            finalText=str(result_payload.get("finalText", "")),
            stageResults=[
                WorkflowStageResult(
                    stageId=str(stage.get("stageId", "")),
                    name=str(stage.get("name", "")),
                    promptUsed=stage.get("promptUsed"),
                    outputText=str(stage.get("outputText", "")),
                    usage=stage.get("usage"),
                )
                for stage in result_payload.get("stageResults", [])
            ],
            telemetry=dict(result_payload.get("telemetry") or {}),
        )
    return WorkflowApplyResponse(
        taskId=envelope.task_id,
        status=str(status_value),
        result=apply_result,
        retry=retry_meta,
        error=envelope.error,
    )


def _ensure_timezone(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _workflow_access_http_error(workflow_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "WORKFLOW_NOT_ACCESSIBLE",
            "message": f"workflow '{workflow_id}' is not accessible or does not exist",
        },
    )


def _to_log_response(page: WorkflowLogPage) -> WorkflowLogListResponse:
    items = [
        WorkflowLogItem(
            taskId=record.task_id,
            stageId=record.stage_id,
            stageName=record.stage_name,
            level=record.level,
            message=record.message,
            metadata=record.metadata,
            timestamp=record.timestamp,
            cursor=record.cursor,
        )
        for record in page.items
    ]
    return WorkflowLogListResponse(workflowId=page.workflow_id, items=items, nextCursor=page.next_cursor)


def _to_variables_response(payload: WorkflowVariablesPayload) -> WorkflowVariablesResponse:
    variables = [
        WorkflowVariableEntry(name=item.name, type=item.type, value=item.value) for item in payload.variables
    ]
    return WorkflowVariablesResponse(workflowId=payload.workflow_id, taskId=payload.task_id, variables=variables)


def _to_tools_response(payload: WorkflowToolsPayload) -> WorkflowToolsResponse:
    tools = [
        WorkflowToolDescriptor(
            toolId=item.get("toolId"),
            name=item.get("name"),
            kind=item.get("kind"),
            config=item.get("config") or {},
            description=item.get("description"),
            promptSnippet=item.get("promptSnippet"),
        )
        for item in payload.tools
    ]
    return WorkflowToolsResponse(workflowId=payload.workflow_id, source=payload.source, tools=tools)


def _to_workflow_response(
    workflow: WorkflowDefinition,
    coverage: Optional[WorkflowCoverageStatus] = None,
) -> WorkflowResponse:
    prompt_bindings = [
        PromptBindingDTO(nodeId=binding.node_id, promptId=binding.prompt_id) for binding in workflow.prompt_bindings
    ]
    publish_history = [
        WorkflowPublishRecord.model_validate(record.to_document())
        for record in workflow.publish_history
    ]
    publish_meta = WorkflowPublishMeta(
        status=workflow.status,
        version=workflow.version,
        publishedVersion=workflow.published_version,
        pendingChanges=workflow.pending_changes,
    )
    return WorkflowResponse(
        workflowId=workflow.workflow_id,
        name=workflow.name,
        description=workflow.description,
        stageIds=list(workflow.stage_ids),
        metadata=workflow.metadata,
        nodeSequence=list(workflow.node_sequence),
        promptBindings=prompt_bindings,
        strategy=workflow.strategy,
        status=workflow.status,
        version=workflow.version,
        publishedVersion=workflow.published_version,
        pendingChanges=workflow.pending_changes,
        historyChecksum=workflow.history_checksum,
        publishHistory=publish_history,
        publishMeta=publish_meta,
        updatedAt=workflow.updated_at,
        updatedBy=workflow.updated_by,
        testCoverage=_to_coverage_response(coverage),
    )


def _to_coverage_response(
    coverage: Optional[WorkflowCoverageStatus],
) -> Optional[WorkflowCoverageStatusResponse]:
    if coverage is None:
        return None
    return WorkflowCoverageStatusResponse(
        status=coverage.status,
        updatedAt=coverage.updated_at,
        scenarios=list(coverage.scenarios),
        mode=coverage.mode,
        lastRunId=coverage.last_run_id,
        lastError=coverage.last_error,
        actorId=coverage.actor_id,
    )


async def _validate_prompt_bindings(
    prompt_repository: AsyncMongoPromptRepository,
    bindings: Sequence[PromptBindingDTO] | Sequence[DomainPromptBinding],
) -> Sequence[str]:
    if not bindings:
        return ()
    missing: list[str] = []
    unique_ids: list[str] = []
    for binding in bindings:
        prompt_id = binding.promptId if isinstance(binding, PromptBindingDTO) else binding.prompt_id
        prompt_id = prompt_id or ""
        if not prompt_id:
            missing.append(prompt_id)
            continue
        if prompt_id not in unique_ids:
            unique_ids.append(prompt_id)
    for prompt_id in unique_ids:
        doc = await prompt_repository.get(prompt_id)
        if doc is None:
            missing.append(prompt_id)
    return missing


async def _validate_stage_ids(stage_service: AsyncStageService, stage_ids: Sequence[str]) -> Sequence[str]:
    if not stage_ids:
        return ()
    existing = await stage_service.get_many(stage_ids)
    existing_ids = {stage.stage_id for stage in existing}
    missing = [stage_id for stage_id in stage_ids if stage_id not in existing_ids]
    return missing
