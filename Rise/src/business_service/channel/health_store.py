from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from project_utility.db.redis import get_async_redis


class ChannelBindingHealthStore:
    """Redis-backed counters for channel binding health error events."""

    def __init__(self, *, ttl_seconds: int = 900, redis_client: Optional[Any] = None) -> None:
        self._redis = redis_client or get_async_redis()
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _key(channel: str, workflow_id: str) -> str:
        return f"rise:channel_binding:health:{channel}:{workflow_id}"

    async def increment_error(self, channel: str, workflow_id: Optional[str], error_type: str) -> None:
        if not workflow_id:
            return
        key = self._key(channel, workflow_id)
        await self._redis.hincrby(key, error_type, 1)
        await self._redis.hset(key, "updatedAt", datetime.now(timezone.utc).isoformat())
        await self._redis.expire(key, self._ttl_seconds)

    async def reset(self, channel: str, workflow_id: str) -> None:
        await self._redis.delete(self._key(channel, workflow_id))

    async def snapshot(self, channel: str, workflow_id: str) -> Mapping[str, object]:
        data = await self._redis.hgetall(self._key(channel, workflow_id))
        normalized: dict[str, object] = {}
        for key, value in data.items():
            if key in {"workflow_missing", "enqueue_failed"}:
                try:
                    normalized[key] = int(value)
                except (TypeError, ValueError):
                    normalized[key] = 0
            else:
                normalized[key] = value
        return normalized

    async def record_test_heartbeat(
        self,
        channel: str,
        workflow_id: str,
        *,
        status: str,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        key = self._key(channel, workflow_id)
        payload: dict[str, Any] = {
            "lastHeartbeatAt": datetime.now(timezone.utc).isoformat(),
            "lastHeartbeatStatus": status,
        }
        if metadata:
            payload.update({f"heartbeat_{k}": v for k, v in metadata.items()})
        await self._redis.hset(key, mapping=payload)
        await self._redis.expire(key, self._ttl_seconds)


__all__ = ["ChannelBindingHealthStore"]
