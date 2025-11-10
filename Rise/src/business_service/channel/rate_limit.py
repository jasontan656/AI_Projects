from __future__ import annotations

"""Rate limiting helpers for channel test endpoints."""

from dataclasses import dataclass
from typing import Optional

from redis.asyncio import Redis

__all__ = ["ChannelRateLimiter", "RateLimitExceeded"]


@dataclass(slots=True)
class RateLimitExceeded(RuntimeError):
    retry_after: int


class ChannelRateLimiter:
    def __init__(
        self,
        redis_client: Redis,
        *,
        max_attempts: int = 3,
        ttl_seconds: int = 60,
    ) -> None:
        self._redis = redis_client
        self._max_attempts = max_attempts
        self._ttl_seconds = ttl_seconds

    async def check(self, workflow_id: str) -> None:
        key = f"channel:test:{workflow_id}"
        attempts = await self._redis.incr(key)
        if attempts == 1:
            await self._redis.expire(key, self._ttl_seconds)
        if attempts > self._max_attempts:
            ttl = await self._redis.ttl(key)
            retry_after = ttl if ttl and ttl > 0 else self._ttl_seconds
            raise RateLimitExceeded(retry_after=int(retry_after))
