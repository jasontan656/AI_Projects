from __future__ import annotations

"""Periodic channel binding refresh & health monitor."""

import asyncio
import contextlib
from datetime import datetime, timezone
from typing import Optional

from business_service.channel.registry import ChannelBindingRegistry
from business_service.channel.service import WorkflowChannelService
from foundational_service.integrations.telegram_client import TelegramClient, TelegramClientError
from project_utility.context import ContextBridge
from project_utility.telemetry import emit as telemetry_emit


class ChannelBindingMonitor:
    def __init__(
        self,
        *,
        service: WorkflowChannelService,
        registry: ChannelBindingRegistry,
        telegram_client: TelegramClient,
        channel: str = "telegram",
        interval_seconds: float = 600.0,
    ) -> None:
        self._service = service
        self._registry = registry
        self._telegram_client = telegram_client
        self._channel = channel
        self._interval = interval_seconds
        self._task: Optional[asyncio.Task[None]] = None
        self._stopped = asyncio.Event()

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
            status, detail = await self._evaluate_health(option.policy)
            checked_at = datetime.now(timezone.utc)
            await self._service.record_health_snapshot(
                option.workflow_id,
                self._channel,
                status=status,
                detail=detail,
                checked_at=checked_at,
            )
            refresh_required = True
        if refresh_required:
            await self._registry.refresh(self._channel)

    async def _evaluate_health(self, policy) -> tuple[str, dict]:
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
