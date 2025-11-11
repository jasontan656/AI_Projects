from __future__ import annotations

"""Periodic channel binding refresh & health monitor."""

import asyncio
import contextlib
import logging
from datetime import datetime, timezone
from typing import Mapping, Optional

from business_service.channel.events import (
    ChannelBindingEvent,
    ChannelBindingHealthEvent,
)
from business_service.channel.registry import ChannelBindingRegistry
from business_service.channel.service import WorkflowChannelService
from business_service.channel.health_store import ChannelBindingHealthStore
from business_service.channel.test_runner import ChannelBindingTestRunner
from foundational_service.integrations.telegram_client import TelegramClient, TelegramClientError
from foundational_service.messaging.channel_binding_event_publisher import ChannelBindingEventPublisher
from foundational_service.persist.observability import WorkflowRunReadRepository
from project_utility.context import ContextBridge
from project_utility.telemetry import emit as telemetry_emit


class ChannelBindingMonitor:
    def __init__(
        self,
        *,
        service: WorkflowChannelService,
        registry: ChannelBindingRegistry,
        telegram_client: TelegramClient,
        publisher: ChannelBindingEventPublisher | None = None,
        health_store: ChannelBindingHealthStore | None = None,
        run_repository: WorkflowRunReadRepository | None = None,
        channel: str = "telegram",
        interval_seconds: float = 600.0,
    ) -> None:
        self._service = service
        self._registry = registry
        self._telegram_client = telegram_client
        self._publisher = publisher
        self._health_store = health_store
        self._test_runner = (
            ChannelBindingTestRunner(
                service=service,
                telegram_client=telegram_client,
                run_repository=run_repository,
            )
            if run_repository is not None
            else None
        )
        self._channel = channel
        self._interval = interval_seconds
        self._task: Optional[asyncio.Task[None]] = None
        self._stopped = asyncio.Event()
        self._logger = logging.getLogger("channel_binding.monitor")

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name="channel-binding-monitor")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        try:
            while not self._stopped.is_set():
                await self._monitor_once()
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=self._interval)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise

    async def _monitor_once(self) -> None:
        options = await self._service.list_binding_options(self._channel)
        refresh_required = False
        for option in options:
            if not option.policy:
                continue
            status, detail = await self._evaluate_health(option)
            checked_at = datetime.now(timezone.utc)
            await self._service.record_health_snapshot(
                option.workflow_id,
                self._channel,
                status=status,
                detail=detail,
                checked_at=checked_at,
            )
            await self._publish_health_event(option, status, detail, checked_at)
            if status == "down" and option.is_enabled:
                await self._activate_kill_switch(option, detail)
            refresh_required = True
        if refresh_required:
            await self._registry.refresh(self._channel)

    async def _publish_health_event(self, option, status: str, detail: dict, checked_at: datetime) -> None:
        if self._publisher is None:
            return
        state = self._registry.get_state(self._channel)
        version = state.version if state else 0
        event = ChannelBindingHealthEvent(
            channel=self._channel,
            workflow_id=option.workflow_id,
            status=status,
            detail={
                "detail": detail,
                "bindingVersion": version,
                "publishedVersion": option.published_version or 0,
            },
            checked_at=checked_at.isoformat(),
        )
        await self._publisher.publish_health(event)

    async def _evaluate_health(self, option) -> tuple[str, dict]:
        policy = option.policy
        webhook_status, webhook_detail = await self._probe_webhook(policy)
        internal_status, internal_detail = await self._probe_internal_test(option)
        error_status, error_detail = await self._evaluate_error_counters(option)
        status = self._reduce_status((webhook_status, internal_status, error_status))
        detail = {
            "webhook": {"status": webhook_status, "detail": webhook_detail},
            "internalTest": {"status": internal_status, "detail": internal_detail},
            "errorCounters": {"status": error_status, "detail": error_detail},
        }
        if status == "ok" and self._health_store:
            await self._health_store.reset(self._channel, option.workflow_id)
        return status, detail

    async def _probe_webhook(self, policy) -> tuple[str, dict]:
        token = self._service.decrypt_token(policy)
        trace_id = ContextBridge.request_id() or ContextBridge.set_request_id()
        expected_url = (policy.webhook_url or "").rstrip("/")
        try:
            webhook_info = await self._telegram_client.get_webhook_info(token, trace_id=trace_id)
            actual_url = str(webhook_info.get("url") or "").rstrip("/")
            detail = {
                "expectedUrl": expected_url,
                "actualUrl": actual_url,
            }
            if expected_url and actual_url and expected_url != actual_url:
                telemetry_emit(
                    "channel.binding.health",
                    level="warning",
                    request_id=trace_id,
                    payload={"workflow_id": policy.workflow_id, "detail": detail},
                )
                return "degraded", detail
            return "ok", detail
        except TelegramClientError as exc:
            detail = {"error": str(exc), "code": exc.code}
            telemetry_emit(
                "channel.binding.health_error",
                level="error",
                request_id=trace_id,
                payload={"workflow_id": policy.workflow_id, "detail": detail},
            )
            return "down", detail

    async def _probe_internal_test(self, option) -> tuple[str, dict]:
        policy = option.policy
        metadata = policy.metadata if isinstance(policy.metadata, Mapping) else {}
        probe_chat_id = None
        health_meta = metadata.get("health")
        if isinstance(health_meta, Mapping):
            probe_chat_id = health_meta.get("probeChatId")
        if not probe_chat_id:
            allowed = metadata.get("allowedChatIds")
            if isinstance(allowed, (list, tuple)) and allowed:
                probe_chat_id = str(allowed[0])
        if not probe_chat_id:
            return "unknown", {"reason": "missing_probe_chat"}
        if self._test_runner is None:
            return "unknown", {"reason": "test_runner_unavailable"}
        trace_id = ContextBridge.request_id() or ContextBridge.set_request_id()
        outcome = await self._test_runner.run_test(
            workflow_id=option.workflow_id,
            policy=policy,
            chat_id=probe_chat_id,
            payload_text=f"[monitor] binding probe {option.workflow_id}",
            wait_for_result=True,
            trace_id=trace_id,
        )
        detail = {
            "chatId": probe_chat_id,
            "traceId": outcome.trace_id,
            "warnings": list(outcome.warnings),
            "status": outcome.status,
        }
        if outcome.error_code:
            detail["errorCode"] = outcome.error_code
        if outcome.status != "success":
            telemetry_emit(
                "channel.binding.internal_probe_failed",
                level="warning",
                request_id=trace_id,
                payload={"workflow_id": option.workflow_id, "detail": detail},
            )
            return "down", detail
        if "WORKFLOW_RESULT_TIMEOUT" in outcome.warnings:
            return "degraded", detail
        return "ok", detail

    async def _evaluate_error_counters(self, option) -> tuple[str, dict]:
        if self._health_store is None:
            return "unknown", {}
        snapshot = await self._health_store.snapshot(self._channel, option.workflow_id)
        counts = {
            "workflow_missing": int(snapshot.get("workflow_missing", 0) or 0),
            "enqueue_failed": int(snapshot.get("enqueue_failed", 0) or 0),
        }
        status = "ok"
        if counts["workflow_missing"] >= 3 or counts["enqueue_failed"] >= 5:
            status = "down"
        elif counts["workflow_missing"] > 0 or counts["enqueue_failed"] > 0:
            status = "degraded"
        detail = {
            "counts": counts,
            "updatedAt": snapshot.get("updatedAt"),
        }
        return status, detail

    @staticmethod
    def _reduce_status(statuses: tuple[str, str, str]) -> str:
        priority = {"down": 3, "degraded": 2, "ok": 1, "unknown": 0}
        highest = "unknown"
        highest_score = -1
        for status in statuses:
            score = priority.get(status, 0)
            if score > highest_score:
                highest = status
                highest_score = score
        return highest

    async def _activate_kill_switch(self, option, detail: Mapping[str, object]) -> None:
        try:
            await self._service.set_kill_switch_state(
                option.workflow_id,
                self._channel,
                active=True,
                actor="channel_binding_monitor",
            )
            self._logger.warning(
                "channel.binding.kill_switch",
                extra={"workflow_id": option.workflow_id, "channel": self._channel, "detail": detail},
            )
            if self._publisher is not None:
                await self._publisher.publish_binding(
                    ChannelBindingEvent(
                        channel=self._channel,
                        workflow_id=option.workflow_id,
                        operation="kill_switch",
                        binding_version=(self._registry.get_state(self._channel).version if self._registry.get_state(self._channel) else 0),
                        published_version=option.published_version or 0,
                        enabled=False,
                        secret_version=option.policy.secret_version if option.policy else None,
                        payload={"reason": "health_down", "detail": detail},
                    )
                )
            if self._health_store is not None:
                await self._health_store.reset(self._channel, option.workflow_id)
        finally:
            await self._registry.refresh(self._channel)
