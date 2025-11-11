from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from business_service.channel.command_service import ChannelBindingCommandService
from business_service.channel.models import WorkflowChannelPolicy
from business_service.channel.rate_limit import ChannelRateLimiter, RateLimitExceeded
from business_service.channel.service import ChannelValidationError, WorkflowChannelService
from business_service.channel.test_runner import ChannelBindingTestRunner
from foundational_service.integrations.telegram_client import TelegramClient, TelegramClientError
from foundational_service.persist.observability import WorkflowRunReadRepository
from interface_entry.http.channels.dto import (
    ChannelBindingDetailResponse,
    ChannelBindingDiagnosticsResponse,
    ChannelBindingOptionResponse,
    ChannelBindingUpsertRequest,
    ChannelBindingHealth,
    TelegramChannelMetadata,
    TelegramHealthResponse,
    TelegramTestRequest,
    TelegramTestResponse,
    WorkflowChannelRequest,
    WorkflowChannelResponse,
)
from interface_entry.http.dependencies import (
    get_channel_binding_command_service,
    get_channel_binding_registry,
    get_channel_rate_limiter,
    get_telegram_client,
    get_workflow_channel_service,
    get_workflow_run_repository,
    get_channel_binding_test_runner,
)
from interface_entry.http.responses import ApiMeta, ApiResponse
from interface_entry.http.security import ActorContext, get_actor_context
from interface_entry.http.workflows.dto import WorkflowApplyResult, WorkflowStageResult
from project_utility.context import ContextBridge
from project_utility.db.mongo import get_mongo_database
from project_utility.db.redis import get_async_redis

from foundational_service.messaging.channel_binding_event_publisher import (
    DEADLETTER_COLLECTION,
    EVENT_QUEUE_KEY,
)

router = APIRouter(prefix="/api", tags=["channel-bindings"])


def _reject_legacy_endpoint() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={"code": "LEGACY_ENDPOINT_DISABLED", "message": "Use /api/channel-bindings/* endpoints"},
    )



@router.get(
    "/channel-bindings/options",
    response_model=ApiResponse[list[ChannelBindingOptionResponse]],
)
async def list_channel_binding_options(
    channel: str = Query(default="telegram"),
    commands: ChannelBindingCommandService = Depends(get_channel_binding_command_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[list[ChannelBindingOptionResponse]]:
    _require_actor(actor)
    options = await commands.list_options(channel)
    data = [_binding_option_to_response(option) for option in options]
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.get(
    "/channel-bindings/{workflow_id}",
    response_model=ApiResponse[ChannelBindingDetailResponse],
)
async def get_channel_binding(
    workflow_id: str,
    channel: str = Query(default="telegram"),
    commands: ChannelBindingCommandService = Depends(get_channel_binding_command_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[ChannelBindingDetailResponse]:
    _require_actor(actor)
    try:
        option = await commands.get_binding(workflow_id, channel)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow not found"},
        ) from exc
    data = _binding_detail_response(option)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.get(
    "/channel-bindings/diagnostics",
    response_model=ApiResponse[ChannelBindingDiagnosticsResponse],
)
async def get_channel_binding_diagnostics(
    channel: str = Query(default="telegram"),
    registry=Depends(get_channel_binding_registry),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[ChannelBindingDiagnosticsResponse]:
    _require_actor(actor)
    state = registry.get_state(channel)
    if state is None:
        await registry.refresh(channel)
        state = registry.get_state(channel)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "CHANNEL_STATE_UNAVAILABLE", "message": "Channel registry unavailable"},
        )
    redis = get_async_redis()
    queue_length = await redis.llen(EVENT_QUEUE_KEY)

    def _count_deadletters() -> int:
        db = get_mongo_database()
        return db[DEADLETTER_COLLECTION].count_documents({})

    deadletter_count = await asyncio.to_thread(_count_deadletters)
    data = ChannelBindingDiagnosticsResponse(
        channel=channel,
        version=state.version,
        activeWorkflowId=state.active.workflow_id if state.active else None,
        optionCount=len(state.options),
        lastRefreshAt=state.refreshed_at,
        queueLength=queue_length,
        deadletterCount=deadletter_count,
    )
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.put(
    "/channel-bindings/{workflow_id}",
    response_model=ApiResponse[ChannelBindingDetailResponse],
)
async def upsert_channel_binding(
    workflow_id: str,
    payload: ChannelBindingUpsertRequest,
    commands: ChannelBindingCommandService = Depends(get_channel_binding_command_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[ChannelBindingDetailResponse]:
    _require_actor(actor)
    channel = payload.channel or "telegram"
    if payload.enabled and payload.config is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CONFIG_REQUIRED", "message": "config is required when enabled=true"},
        )
    try:
        outcome = await commands.upsert_binding(
            workflow_id,
            channel=channel,
            enabled=payload.enabled,
            config=payload.config.model_dump() if payload.config else None,
            actor=actor.actor_id,
        )
    except ChannelValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    data = _binding_detail_response(outcome.option)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    meta.warnings.extend(outcome.warnings)
    return ApiResponse(data=data, meta=meta)


@router.post(
    "/channel-bindings/{workflow_id}/refresh",
    response_model=ApiResponse[ChannelBindingDetailResponse],
)
async def refresh_channel_binding(
    workflow_id: str,
    channel: str = Query(default="telegram"),
    commands: ChannelBindingCommandService = Depends(get_channel_binding_command_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[ChannelBindingDetailResponse]:
    _require_actor(actor)
    outcome = await commands.refresh_binding(
        workflow_id,
        channel=channel,
        actor=actor.actor_id,
    )
    data = _binding_detail_response(outcome.option)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    meta.warnings.extend(outcome.warnings)
    return ApiResponse(data=data, meta=meta)


@router.get("/workflow-channels/{workflow_id}", response_model=ApiResponse[WorkflowChannelResponse])
async def get_workflow_channel(
    workflow_id: str,
    channel: str = Query(default="telegram"),
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[WorkflowChannelResponse]:
    _require_actor(actor)
    _reject_legacy_endpoint()


@router.put("/workflow-channels/{workflow_id}", response_model=ApiResponse[WorkflowChannelResponse])
async def save_workflow_channel(
    workflow_id: str,
    payload: WorkflowChannelRequest,
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    actor: ActorContext = Depends(get_actor_context),
    channel: str = Query(default="telegram"),
) -> ApiResponse[WorkflowChannelResponse]:
    _require_actor(actor)
    _reject_legacy_endpoint()


@router.delete("/workflow-channels/{workflow_id}", status_code=status.HTTP_200_OK, response_model=ApiResponse[dict[str, str]])
async def delete_workflow_channel(
    workflow_id: str,
    channel: str = Query(default="telegram"),
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[dict[str, str]]:
    _require_actor(actor)
    _reject_legacy_endpoint()


@router.get("/channels/telegram/health", response_model=ApiResponse[TelegramHealthResponse])
async def telegram_health_check(
    workflow_id: str = Query(..., alias="workflowId"),
    include_metrics: bool = Query(default=False, alias="includeMetrics"),
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    telegram_client: TelegramClient = Depends(get_telegram_client),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[TelegramHealthResponse]:
    _require_actor(actor)
    try:
        policy = await service.get_policy(workflow_id, "telegram")
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHANNEL_POLICY_NOT_FOUND", "message": "Channel configuration not found"},
        ) from exc
    trace_id = ContextBridge.request_id()
    status_value = "up"
    error_message = None
    metrics: dict[str, Any] = {}
    error_code = None
    last_checked_at = datetime.now(timezone.utc)
    token = service.decrypt_token(policy)
    try:
        bot_info = await telegram_client.get_bot_info(token, trace_id=trace_id)
        webhook_info = await telegram_client.get_webhook_info(token, trace_id=trace_id)
        metrics["bot"] = bot_info
        metrics["webhook"] = webhook_info
        target_url = policy.webhook_url.rstrip("/")
        actual_url = str(webhook_info.get("url") or "").rstrip("/")
        if target_url and actual_url and target_url != actual_url:
            status_value = "degraded"
            error_message = "Webhook URL mismatch"
    except TelegramClientError as exc:
        status_value = "unknown"
        error_message = exc.message
        error_code = exc.code
        metrics = {"errorCode": exc.code}
    if not include_metrics:
        metrics = {}
    data = TelegramHealthResponse(
        status=status_value,
        lastCheckedAt=last_checked_at,
        lastError=error_message,
        metrics=metrics,
    )
    await service.record_health_snapshot(
        workflow_id,
        "telegram",
        status=status_value,
        detail={"error": error_message, "errorCode": error_code} if error_message or error_code else {},
        checked_at=last_checked_at,
    )
    warnings = [error_code] if error_code else []
    meta = ApiMeta(requestId=trace_id, warnings=warnings)  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.post("/channels/telegram/test", response_model=ApiResponse[TelegramTestResponse])
async def telegram_test_message(
    payload: TelegramTestRequest,
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    rate_limiter: ChannelRateLimiter = Depends(get_channel_rate_limiter),
    actor: ActorContext = Depends(get_actor_context),
    test_runner: ChannelBindingTestRunner = Depends(get_channel_binding_test_runner),
) -> ApiResponse[TelegramTestResponse]:
    _require_actor(actor)
    try:
        await rate_limiter.check(payload.workflowId)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "CHANNEL_TEST_RATE_LIMIT",
                "message": "Rate limit exceeded",
                "retryAfterSeconds": exc.retry_after,
            },
        ) from exc
    try:
        policy = await service.get_policy(payload.workflowId, "telegram")
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHANNEL_POLICY_NOT_FOUND", "message": "Channel configuration not found"},
        ) from exc
    trace_id = payload.correlationId or ContextBridge.request_id()
    text = payload.payloadText or "Rise workflow channel test message."
    outcome = await test_runner.run_test(
        workflow_id=payload.workflowId,
        policy=policy,
        chat_id=payload.chatId,
        payload_text=text,
        wait_for_result=payload.waitForResult,
        trace_id=trace_id,
    )
    warnings = list(outcome.warnings)
    workflow_result: Optional[WorkflowApplyResult] = None
    if outcome.workflow_result is not None:
        workflow_result = _convert_run_result(outcome.workflow_result)
    data = TelegramTestResponse(
        status=outcome.status,
        responseTimeMs=outcome.duration_ms,
        telegramMessageId=outcome.telegram_message_id,
        errorCode=outcome.error_code,
        traceId=outcome.trace_id,
        workflowResult=workflow_result,
    )
    meta = ApiMeta(requestId=trace_id, warnings=warnings)  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


def _policy_to_response(policy: WorkflowChannelPolicy) -> WorkflowChannelResponse:
    return WorkflowChannelResponse(
        workflowId=policy.workflow_id,
        channel=policy.channel,
        webhookUrl=policy.webhook_url,
        waitForResult=policy.wait_for_result,
        workflowMissingMessage=policy.workflow_missing_message,
        timeoutMessage=policy.timeout_message,
        metadata=TelegramChannelMetadata.model_validate(policy.metadata),
        maskedBotToken=policy.masked_token,
        secretVersion=policy.secret_version,
        updatedAt=policy.updated_at,
        updatedBy=policy.updated_by,
    )


def _require_actor(actor: ActorContext) -> None:
    if not actor.actor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "Actor context required"},
        )


def _convert_run_result(payload: Mapping[str, Any]) -> WorkflowApplyResult:
    stage_results = [
        WorkflowStageResult(
            stageId=str(stage.get("stageId", "")),
            name=str(stage.get("name", "")),
            promptUsed=stage.get("promptUsed"),
            outputText=str(stage.get("outputText", "")),
            usage=stage.get("usage"),
        )
        for stage in payload.get("stageResults", [])
    ]
    return WorkflowApplyResult(
        finalText=str(payload.get("finalText", "")),
        stageResults=stage_results,
        telemetry=dict(payload.get("telemetry") or {}),
    )


def _binding_option_to_response(option) -> ChannelBindingOptionResponse:
    return ChannelBindingOptionResponse(
        workflowId=option.workflow_id,
        workflowName=option.workflow_name,
        channel=option.channel,
        status=option.status,
        isChannelEnabled=option.is_enabled,
        isBound=option.is_bound,
        publishedVersion=option.published_version,
        bindingUpdatedAt=option.updated_at,
        bindingUpdatedBy=option.updated_by,
        health=_binding_health_from_metadata(option.health),
        killSwitch=option.kill_switch,
    )


def _binding_detail_response(option) -> ChannelBindingDetailResponse:
    summary = _binding_option_to_response(option)
    policy = _policy_to_response(option.policy) if option.policy else None
    return ChannelBindingDetailResponse(**summary.model_dump(), policy=policy)


def _binding_health_from_metadata(metadata: Mapping[str, Any]) -> ChannelBindingHealth:
    if not metadata:
        return ChannelBindingHealth()
    status_value = str(metadata.get("status") or "unknown")
    last_checked_raw = metadata.get("lastCheckedAt")
    detail = metadata.get("detail")
    if isinstance(detail, Mapping):
        detail_payload = dict(detail)
    else:
        detail_payload = {
            key: value
            for key, value in metadata.items()
            if key not in {"status", "lastCheckedAt"}
        }
    return ChannelBindingHealth(
        status=status_value,
        lastCheckedAt=_parse_timestamp(last_checked_raw),
        detail=detail_payload,
    )


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


