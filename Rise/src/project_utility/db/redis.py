from __future__ import annotations

"""Redis client helpers."""

import json
import os
from functools import lru_cache
from typing import Any, Mapping, MutableMapping, Optional

from redis.asyncio import Redis

__all__ = [
    "get_async_redis",
    "append_chat_summary",
]


@lru_cache(maxsize=1)
def get_async_redis() -> Redis:
    """Return a cached asyncio Redis client."""

    url = os.getenv("REDIS_URL")
    if not url:
        raise RuntimeError("REDIS_URL not configured")
    return Redis.from_url(url, decode_responses=True)


async def append_chat_summary(
    chat_id: str | int,
    entry: Mapping[str, Any],
    *,
    max_entries: int = 20,
    ttl_seconds: Optional[int] = None,
) -> None:
    """Append a chat summary entry while trimming to the configured max length."""

    key = f"chat:{chat_id}:summary"
    payload: MutableMapping[str, Any] = dict(entry)
    payload.setdefault("chat_id", chat_id)
    client = get_async_redis()
    await client.lpush(key, json.dumps(payload, ensure_ascii=False))
    await client.ltrim(key, 0, max_entries - 1)
    if ttl_seconds is not None and ttl_seconds > 0:
        await client.expire(key, ttl_seconds)
