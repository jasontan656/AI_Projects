from __future__ import annotations

import asyncio
import logging
from typing import Optional

from business_service.channel.events import (
    CHANNEL_BINDING_HEALTH_TOPIC,
    CHANNEL_BINDING_TOPIC,
    ChannelBindingEvent,
    ChannelBindingHealthEvent,
)
from foundational_service.messaging.channel_binding_event_publisher import (
    ChannelBindingEventPublisher,
    DEADLETTER_MAX_RETRIES,
    EVENT_QUEUE_KEY,
)
from project_utility.db.redis import get_async_redis
from project_utility.telemetry import emit as telemetry_emit


class ChannelBindingEventReplayer:
    """Background helper that replays queued channel binding events."""

    def __init__(
        self,
        publisher: ChannelBindingEventPublisher,
        *,
        batch_size: int = 100,
    ) -> None:
        self._publisher = publisher
        self._batch_size = batch_size
        self._logger = logging.getLogger("channel_binding.replayer")

    async def replay_pending(self) -> None:
        redis = get_async_redis()
        for _ in range(self._batch_size):
            payload = await redis.lpop(EVENT_QUEUE_KEY)
            if payload is None:
                break
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            topic = CHANNEL_BINDING_TOPIC
            raw_payload = payload
            retry_count = 0
            workflow_id = "unknown"
            try:
                topic, raw_payload, retry_count = ChannelBindingEventPublisher.decode_queue_payload(payload)
                if topic == CHANNEL_BINDING_HEALTH_TOPIC:
                    event = ChannelBindingHealthEvent.loads(raw_payload)
                    workflow_id = event.workflow_id
                    result = await self._publisher.publish_health(
                        event, replay=True, retry_count=retry_count
                    )
                else:
                    event = ChannelBindingEvent.loads(raw_payload)
                    workflow_id = event.workflow_id
                    result = await self._publisher.publish_binding(
                        event, replay=True, retry_count=retry_count
                    )
            except Exception as exc:  # pragma: no cover - defensive
                self._logger.warning("channel.binding.event_corrupt", exc_info=exc)
                await self._publisher.record_deadletter(
                    topic,
                    raw_payload,
                    reason="deserialize_failed",
                    error=str(exc),
                    retry_count=retry_count,
                )
                continue
            if result.status != "sent":
                updated_retry = retry_count + 1
                if updated_retry >= DEADLETTER_MAX_RETRIES:
                    await self._publisher.record_deadletter(
                        topic,
                        raw_payload,
                        reason="retry_exhausted",
                        error=result.error,
                        retry_count=updated_retry,
                    )
                    telemetry_emit(
                        "channel.binding.event_deadletter",
                        level="error",
                        payload={
                            "workflow_id": workflow_id,
                            "status": result.status,
                            "topic": topic,
                        },
                    )
                else:
                    # Push back so it can be retried later and avoid busy loops.
                    await redis.lpush(
                        EVENT_QUEUE_KEY,
                        ChannelBindingEventPublisher.encode_queue_payload(
                            topic,
                            raw_payload,
                            updated_retry,
                        ),
                    )
                    telemetry_emit(
                        "channel.binding.event_retry_suspended",
                        level="warning",
                        payload={
                            "workflow_id": workflow_id,
                            "status": result.status,
                            "topic": topic,
                            "retryCount": updated_retry,
                        },
                    )
                    break
        else:
            # Batch completed without exhausting queue; schedule another run soon.
            await asyncio.sleep(0)


__all__ = ["ChannelBindingEventReplayer"]
