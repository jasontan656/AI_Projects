from __future__ import annotations

"""Channel health reporting utilities."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Optional

from redis.asyncio import Redis

from business_service.channel.health_store import ChannelBindingHealthStore
from project_utility.db.redis import get_async_redis
from project_utility.telemetry import emit as telemetry_emit

__all__ = [
    "ChannelHealthReporter",
    "set_channel_health_reporter",
    "get_channel_health_reporter",
    "build_default_health_reporter",
]

_HEALTH_REPORTER: Optional["ChannelHealthReporter"] = None


def set_channel_health_reporter(reporter: "ChannelHealthReporter") -> None:
    global _HEALTH_REPORTER
    _HEALTH_REPORTER = reporter


def get_channel_health_reporter() -> Optional["ChannelHealthReporter"]:
    return _HEALTH_REPORTER


@dataclass(slots=True)
class ChannelHealthReporter:
    store: ChannelBindingHealthStore
    redis_client: Redis
    ttl_seconds: int = 120

    def schedule_error(self, channel: str, workflow_id: Optional[str], error_type: str) -> None:
        if not workflow_id:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._record_error(channel, workflow_id, error_type))

    async def _record_error(self, channel: str, workflow_id: str, error_type: str) -> None:
        await self.store.increment_error(channel, workflow_id, error_type)
        telemetry_emit(
            "channel.health.error",
            payload={"channel": channel, "workflow_id": workflow_id, "type": error_type},
        )

    async def record_snapshot(
        self,
        *,
        channel: str,
        workflow_id: Optional[str],
        mode: str,
        pending: int,
        latency_ms: Optional[float] = None,
        manual_guard: bool = False,
    ) -> None:
        if not workflow_id:
            return
        now = datetime.now(timezone.utc).isoformat()
        key = f"rise:channel_health:{channel}"
        mapping = {
            "workflow_id": workflow_id,
            "mode": mode,
            "pending": pending,
            "manual_guard": "1" if manual_guard else "0",
            "last_seen": now,
        }
        if latency_ms is not None:
            mapping["latency_ms"] = f"{latency_ms:.3f}"
        await self.redis_client.hset(key, mapping=mapping)
        await self.redis_client.expire(key, self.ttl_seconds)
        telemetry_emit(
            "channel.health.snapshot",
            payload={
                "channel": channel,
                "workflow_id": workflow_id,
                "mode": mode,
                "pending": pending,
                "manual_guard": manual_guard,
                "timestamp": now,
                "latency_ms": latency_ms,
            },
        )


def build_default_health_reporter(ttl_seconds: int = 120) -> ChannelHealthReporter:
    return ChannelHealthReporter(
        store=ChannelBindingHealthStore(),
        redis_client=get_async_redis(),
        ttl_seconds=ttl_seconds,
    )
