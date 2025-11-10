from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Mapping, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from business_service.channel.events import ChannelBindingEvent, CHANNEL_BINDING_TOPIC
from business_service.channel.models import WorkflowChannelPolicy
from business_service.channel.rate_limit import ChannelRateLimiter, RateLimitExceeded
from business_service.channel.service import ChannelValidationError, WorkflowChannelService
from foundational_service.integrations.telegram_client import TelegramClient, TelegramClientError
from foundational_service.persist.observability import WorkflowRunReadRepository
from interface_entry.http.channels.dto import (
    ChannelBindingDetailResponse,
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
    get_channel_binding_registry,
    get_channel_rate_limiter,
    get_telegram_client,
    get_workflow_channel_service,
    get_workflow_run_repository,
)
from interface_entry.http.responses import ApiMeta, ApiResponse
from interface_entry.http.security import ActorContext, get_actor_context
from interface_entry.http.workflows.dto import WorkflowApplyResult, WorkflowStageResult
from project_utility.context import ContextBridge
from project_utility.db.redis import get_async_redis

router = APIRouter(prefix="/api", tags=["channel-bindings"])


@router.get(
    "/channel-bindings/options",
    response_model=ApiResponse[list[ChannelBindingOptionResponse]],
)
async def list_channel_binding_options(
    channel: str = Query(default="telegram"),
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    registry=Depends(get_channel_binding_registry),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[list[ChannelBindingOptionResponse]]:
    _require_actor(actor)
    try:
        options = await registry.get_options(channel)
    except Exception:
        options = await service.list_binding_options(channel)
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
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[ChannelBindingDetailResponse]:
    _require_actor(actor)
    try:
        option = await service.get_binding_view(workflow_id, channel)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "Workflow not found"},
        ) from exc
    data = _binding_detail_response(option)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.put(
    "/channel-bindings/{workflow_id}",
    response_model=ApiResponse[ChannelBindingDetailResponse],
)
async def upsert_channel_binding(
    workflow_id: str,
    payload: ChannelBindingUpsertRequest,
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    registry=Depends(get_channel_binding_registry),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[ChannelBindingDetailResponse]:
    _require_actor(actor)
    channel = payload.channel or "telegram"
    operation = "delete"
    policy: WorkflowChannelPolicy | None = None
    try:
        if payload.enabled:
            config = payload.config
            if config is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"code": "CONFIG_REQUIRED", "message": "config is required when enabled=true"},
                )
            operation = "upsert"
            policy = await service.save_policy(
                workflow_id,
                config.model_dump(),
                actor=actor.actor_id,
                channel=channel,
            )
            await service.set_channel_enabled(workflow_id, channel, enabled=True, actor=actor.actor_id)
        else:
            try:
                await service.delete_policy(workflow_id, channel)
            except KeyError:
                pass
            await service.set_channel_enabled(workflow_id, channel, enabled=False, actor=actor.actor_id)
    except ChannelValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    state = await registry.refresh(channel)
    option = state.options.get(workflow_id) if state else None
    if option is None:
        option = await service.get_binding_view(workflow_id, channel)
    await _publish_binding_event(
        ChannelBindingEvent(
            channel=channel,
            workflow_id=workflow_id,
            operation=operation,
            binding_version=(state.version if state else 0),
            published_version=option.published_version if option else 0,
            enabled=payload.enabled,
            secret_version=policy.secret_version if policy else None,
            actor=actor.actor_id,
        )
    )
    data = _binding_detail_response(option)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.post(
    "/channel-bindings/{workflow_id}/refresh",
    response_model=ApiResponse[ChannelBindingDetailResponse],
)
async def refresh_channel_binding(
    workflow_id: str,
    channel: str = Query(default="telegram"),
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    registry=Depends(get_channel_binding_registry),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[ChannelBindingDetailResponse]:
    _require_actor(actor)
    state = await registry.refresh(channel)
    option = state.options.get(workflow_id) if state else None
    if option is None:
        option = await service.get_binding_view(workflow_id, channel)
    await _publish_binding_event(
        ChannelBindingEvent(
            channel=channel,
            workflow_id=workflow_id,
            operation="refresh",
            binding_version=state.version if state else 0,
            published_version=option.published_version if option else 0,
            enabled=option.is_enabled if option else False,
            secret_version=option.policy.secret_version if option and option.policy else None,
            actor=actor.actor_id,
        )
    )
    data = _binding_detail_response(option)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.get("/workflow-channels/{workflow_id}", response_model=ApiResponse[WorkflowChannelResponse])
async def get_workflow_channel(
    workflow_id: str,
    channel: str = Query(default="telegram"),
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    actor: ActorContext = Depends(get_actor_context),
) -> ApiResponse[WorkflowChannelResponse]:
    _require_actor(actor)
    try:
        policy = await service.get_policy(workflow_id, channel)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHANNEL_POLICY_NOT_FOUND", "message": "Channel configuration not found"},
        ) from exc
    data = _policy_to_response(policy)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.put("/workflow-channels/{workflow_id}", response_model=ApiResponse[WorkflowChannelResponse])
async def save_workflow_channel(
    workflow_id: str,
    payload: WorkflowChannelRequest,
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    actor: ActorContext = Depends(get_actor_context),
    channel: str = Query(default="telegram"),
    registry=Depends(get_channel_binding_registry),
) -> ApiResponse[WorkflowChannelResponse]:
    _require_actor(actor)
    try:
        policy = await service.save_policy(
            workflow_id,
            payload.model_dump(),
            actor=actor.actor_id,
            channel=channel,
        )
    except ChannelValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    await service.set_channel_enabled(workflow_id, channel, enabled=True, actor=actor.actor_id)
    state = await registry.refresh(channel)
    option = state.options.get(workflow_id) if state else None
    await _publish_binding_event(
        ChannelBindingEvent(
            channel=channel,
            workflow_id=workflow_id,
            operation="upsert",
            binding_version=state.version if state else 0,
            published_version=option.published_version if option else 0,
            enabled=True,
            secret_version=policy.secret_version,
            actor=actor.actor_id,
        )
    )
    data = _policy_to_response(policy)
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data=data, meta=meta)


@router.delete("/workflow-channels/{workflow_id}", status_code=status.HTTP_200_OK, response_model=ApiResponse[dict[str, str]])
async def delete_workflow_channel(
    workflow_id: str,
    channel: str = Query(default="telegram"),
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    actor: ActorContext = Depends(get_actor_context),
    registry=Depends(get_channel_binding_registry),
) -> ApiResponse[dict[str, str]]:
    _require_actor(actor)
    try:
        await service.delete_policy(workflow_id, channel)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHANNEL_POLICY_NOT_FOUND", "message": "Channel configuration not found"},
        ) from exc
    await service.set_channel_enabled(workflow_id, channel, enabled=False, actor=actor.actor_id)
    state = await registry.refresh(channel)
    await _publish_binding_event(
        ChannelBindingEvent(
            channel=channel,
            workflow_id=workflow_id,
            operation="delete",
            binding_version=state.version if state else 0,
            published_version=0,
            enabled=False,
            secret_version=None,
            actor=actor.actor_id,
        )
    )
    meta = ApiMeta(requestId=ContextBridge.request_id())  # type: ignore[arg-type]
    return ApiResponse(data={"status": "deleted", "workflowId": workflow_id}, meta=meta)


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
    telegram_client: TelegramClient = Depends(get_telegram_client),
    rate_limiter: ChannelRateLimiter = Depends(get_channel_rate_limiter),
    actor: ActorContext = Depends(get_actor_context),
    run_repository: WorkflowRunReadRepository = Depends(get_workflow_run_repository),
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
    start_time = datetime.now(timezone.utc)
    token = service.decrypt_token(policy)
    text = payload.payloadText or "Rise workflow channel test message."
    start = perf_counter()
    telegram_message_id = None
    error_code = None
    try:
        result = await telegram_client.send_message(
            token,
            chat_id=payload.chatId,
            text=text,
            parse_mode=None,
            trace_id=trace_id,
        )
        telegram_message_id = str(result.get("message_id")) if result else None
        status_value = "success"
    except TelegramClientError as exc:
        status_value = "failed"
        error_code = exc.code
    duration_ms = int((perf_counter() - start) * 1000)
    workflow_result: Optional[WorkflowApplyResult] = None
    warnings: list[str] = []
    if payload.waitForResult and status_value == "success":
        workflow_result = await _await_workflow_result(
            run_repository,
            workflow_id=payload.workflowId,
            since=start_time,
        )
        if workflow_result is None:
            warnings.append("WORKFLOW_RESULT_TIMEOUT")
    if error_code:
        warnings.append(error_code)
    data = TelegramTestResponse(
        status=status_value,
        responseTimeMs=duration_ms,
        telegramMessageId=telegram_message_id,
        errorCode=error_code,
        traceId=trace_id,
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


async def _await_workflow_result(
    run_repository: WorkflowRunReadRepository,
    *,
    workflow_id: str,
    since: datetime,
    timeout_seconds: float = 20.0,
    poll_interval: float = 2.0,
) -> Optional[WorkflowApplyResult]:
    deadline = perf_counter() + timeout_seconds
    while perf_counter() < deadline:
        runs = await run_repository.list_runs(workflow_id, since=since)
        for doc in runs:
            result_payload = doc.get("result")
            updated_at = doc.get("updated_at") or doc.get("created_at") or since
            if result_payload and updated_at >= since:
                return _convert_run_result(result_payload)
        await asyncio.sleep(poll_interval)
    return None


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
        publishedVersion=option.published_version,
        bindingUpdatedAt=option.updated_at,
        bindingUpdatedBy=option.updated_by,
        health=_binding_health_from_metadata(option.health),
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


async def _publish_binding_event(event: ChannelBindingEvent) -> None:
    redis = get_async_redis()
    await redis.publish(CHANNEL_BINDING_TOPIC, event.dumps())
