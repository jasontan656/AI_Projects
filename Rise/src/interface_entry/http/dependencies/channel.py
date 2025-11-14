from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import Depends, Request
from redis.asyncio import Redis

from business_service.channel.command_service import ChannelBindingCommandService
from business_service.channel.rate_limit import ChannelRateLimiter
from business_service.channel.registry import ChannelBindingRegistry
from business_service.channel.service import WorkflowChannelService
from business_service.channel.test_runner import ChannelBindingTestRunner
from foundational_service.integrations.telegram_client import TelegramClient
from foundational_service.persist.observability import WorkflowRunReadRepository
from project_utility.db.redis import get_async_redis

from . import _require_capability
from .workflow import (
    get_workflow_channel_repository,
    get_workflow_channel_service,
    get_workflow_run_repository,
)


_channel_rate_limiter: Optional[ChannelRateLimiter] = None
_channel_binding_test_runner: Optional[ChannelBindingTestRunner] = None
_channel_binding_registry: Optional[ChannelBindingRegistry] = None
_telegram_client: Optional[TelegramClient] = None


def _resolve_telegram_client(*, require_capability: bool) -> TelegramClient:
    global _telegram_client
    if require_capability:
        _require_capability("telegram", hard=True)
    if _telegram_client is None:
        _telegram_client = TelegramClient()
    return _telegram_client


def get_telegram_client() -> TelegramClient:
    return _resolve_telegram_client(require_capability=True)


def prime_telegram_client() -> TelegramClient:
    """Instantiate a Telegram client without capability enforcement."""

    return _resolve_telegram_client(require_capability=False)


def get_channel_rate_limiter() -> ChannelRateLimiter:
    global _channel_rate_limiter
    if _channel_rate_limiter is None:
        redis_client: Redis = get_async_redis()
        _channel_rate_limiter = ChannelRateLimiter(redis_client)
    return _channel_rate_limiter


async def get_channel_binding_test_runner(
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
    telegram_client: TelegramClient = Depends(get_telegram_client),
    run_repository: WorkflowRunReadRepository = Depends(get_workflow_run_repository),
) -> ChannelBindingTestRunner:
    global _channel_binding_test_runner
    if _channel_binding_test_runner is None:
        _channel_binding_test_runner = ChannelBindingTestRunner(
            service=service,
            telegram_client=telegram_client,
            run_repository=run_repository,
        )
    return _channel_binding_test_runner


async def get_channel_binding_registry(
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
) -> ChannelBindingRegistry:
    global _channel_binding_registry
    if _channel_binding_registry is None:
        _channel_binding_registry = ChannelBindingRegistry(service=service)
        await _channel_binding_registry.refresh()
    return _channel_binding_registry


def set_channel_binding_registry(registry: ChannelBindingRegistry) -> None:
    global _channel_binding_registry
    _channel_binding_registry = registry


async def get_channel_binding_command_service(
    request: Request,
    registry: ChannelBindingRegistry = Depends(get_channel_binding_registry),
    service: WorkflowChannelService = Depends(get_workflow_channel_service),
) -> ChannelBindingCommandService:
    publisher = getattr(request.app.state, "channel_binding_event_publisher", None)
    return ChannelBindingCommandService(service=service, registry=registry, publisher=publisher)


def reset_channel_dependencies() -> None:
    """Reset cached channel dependencies and close clients."""

    global _channel_rate_limiter, _channel_binding_test_runner, _channel_binding_registry, _telegram_client
    _channel_rate_limiter = None
    _channel_binding_test_runner = None
    _channel_binding_registry = None
    if _telegram_client is not None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_telegram_client.aclose())
            else:  # pragma: no cover - CLI shutdown
                loop.run_until_complete(_telegram_client.aclose())
        except Exception:  # pragma: no cover - defensive cleanup
            pass
    _telegram_client = None
