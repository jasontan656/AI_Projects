from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from typing import AsyncIterator, Dict

from fastapi import FastAPI, HTTPException

from business_service.channel.events import (
    CHANNEL_BINDING_HEALTH_TOPIC,
    CHANNEL_BINDING_TOPIC,
    ChannelBindingEvent,
    ChannelBindingHealthEvent,
)
from business_service.channel.registry import ChannelBindingRegistry
from business_service.channel.repository import AsyncWorkflowChannelRepository
from business_service.channel.service import WorkflowChannelService
from business_service.workflow import AsyncWorkflowRepository
from interface_entry.http.dependencies import (
    get_mongo_client,
    get_settings,
    get_telegram_client,
)
from interface_entry.runtime.channel_binding_monitor import ChannelBindingMonitor
from foundational_service.persist.observability import WorkflowRunReadRepository
from project_utility.db.redis import get_async_redis

_log = logging.getLogger("channel_binding.bootstrap")


def _build_channel_binding_service() -> WorkflowChannelService:
    settings = get_settings()
    client = get_mongo_client()
    database = client[settings.mongodb_database]
    channel_repo = AsyncWorkflowChannelRepository(database["workflow_channels"])
    workflow_repo = AsyncWorkflowRepository(database["workflows"])
    return WorkflowChannelService(repository=channel_repo, workflow_repository=workflow_repo)


def _build_workflow_run_repository() -> WorkflowRunReadRepository:
    settings = get_settings()
    client = get_mongo_client()
    database = client[settings.mongodb_database]
    return WorkflowRunReadRepository(database["workflow_runs"])


def prime_channel_binding_registry() -> ChannelBindingRegistry:
    """Create a ChannelBindingRegistry; actual refresh occurs during lifespan."""

    service = _build_channel_binding_service()
    return ChannelBindingRegistry(service=service)


async def start_channel_binding_listener(app: FastAPI) -> None:
    registry: ChannelBindingRegistry | None = getattr(app.state, "channel_binding_registry", None)
    if registry is None:
        return
    redis = get_async_redis()
    pubsub = redis.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(CHANNEL_BINDING_TOPIC, CHANNEL_BINDING_HEALTH_TOPIC)

    async def _runner() -> None:
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                channel_name = message.get("channel")
                data = message.get("data")
                try:
                    channel_text = channel_name.decode("utf-8") if isinstance(channel_name, bytes) else str(channel_name)
                except Exception:
                    channel_text = ""
                if channel_text == CHANNEL_BINDING_TOPIC:
                    try:
                        event = ChannelBindingEvent.loads(data)
                    except Exception:
                        continue
                    await registry.handle_event(event)
                elif channel_text == CHANNEL_BINDING_HEALTH_TOPIC:
                    try:
                        event = ChannelBindingHealthEvent.loads(data)
                    except Exception:
                        continue
                    await registry.refresh(event.channel)
        finally:
            await pubsub.close()

    task = asyncio.create_task(_runner(), name="channel-binding-listener")
    app.state.channel_binding_listener = {"task": task, "pubsub": pubsub}


async def stop_channel_binding_listener(app: FastAPI) -> None:
    holder: Dict[str, object] | None = getattr(app.state, "channel_binding_listener", None)
    if not holder:
        return
    task = holder.get("task")
    if isinstance(task, asyncio.Task):
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    pubsub = holder.get("pubsub")
    if pubsub:
        await pubsub.close()
    app.state.channel_binding_listener = None


async def start_channel_binding_monitor(app: FastAPI) -> None:
    registry: ChannelBindingRegistry | None = getattr(app.state, "channel_binding_registry", None)
    if registry is None:
        return
    service = _build_channel_binding_service()
    try:
        telegram_client = get_telegram_client()
    except HTTPException as exc:
        _log.warning(
            "channel.binding.monitor_disabled",
            extra={"reason": exc.detail or "capability_unavailable"},
        )
        return
    publisher = getattr(app.state, "channel_binding_event_publisher", None)
    health_store = getattr(app.state, "channel_binding_health_store", None)
    run_repository = _build_workflow_run_repository()
    monitor = ChannelBindingMonitor(
        service=service,
        registry=registry,
        telegram_client=telegram_client,
        publisher=publisher,
        health_store=health_store,
        run_repository=run_repository,
    )
    app.state.channel_binding_monitor = monitor
    await monitor.start()


async def stop_channel_binding_monitor(app: FastAPI) -> None:
    monitor: ChannelBindingMonitor | None = getattr(app.state, "channel_binding_monitor", None)
    if monitor is None:
        return
    await monitor.stop()
    app.state.channel_binding_monitor = None


async def start_channel_binding_validator(app: FastAPI, *, interval_seconds: float = 600.0) -> None:
    registry: ChannelBindingRegistry | None = getattr(app.state, "channel_binding_registry", None)
    if registry is None:
        return
    stop_event = asyncio.Event()

    async def _runner() -> None:
        try:
            while not stop_event.is_set():
                try:
                    await registry.refresh()
                except Exception as exc:  # pragma: no cover - defensive logging
                    _log.warning("channel.binding.validator.failed", extra={"error": str(exc)})
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise

    task = asyncio.create_task(_runner(), name="channel-binding-validator")
    app.state.channel_binding_validator = {"task": task, "stop_event": stop_event}


async def stop_channel_binding_validator(app: FastAPI) -> None:
    holder: Dict[str, object] | None = getattr(app.state, "channel_binding_validator", None)
    if not holder:
        return
    stop_event = holder.get("stop_event")
    if isinstance(stop_event, asyncio.Event):
        stop_event.set()
    task = holder.get("task")
    if isinstance(task, asyncio.Task):
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    app.state.channel_binding_validator = None


@asynccontextmanager
async def channel_binding_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Async lifespan hook that manages registry listener, monitor, and validator."""

    registry: ChannelBindingRegistry | None = getattr(app.state, "channel_binding_registry", None)
    if registry is not None:
        try:
            await registry.refresh()
        except Exception as exc:  # pragma: no cover - defensive logging
            _log.warning("channel.binding.refresh_failed", extra={"error": str(exc)})

    await start_channel_binding_listener(app)
    await start_channel_binding_monitor(app)
    await start_channel_binding_validator(app)
    try:
        yield
    finally:
        await stop_channel_binding_validator(app)
        await stop_channel_binding_monitor(app)
        await stop_channel_binding_listener(app)


__all__ = [
    "prime_channel_binding_registry",
    "channel_binding_lifespan",
    "start_channel_binding_listener",
    "stop_channel_binding_listener",
    "start_channel_binding_monitor",
    "stop_channel_binding_monitor",
    "start_channel_binding_validator",
    "stop_channel_binding_validator",
]
