from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from business_service.channel.events import (
    CHANNEL_BINDING_HEALTH_TOPIC,
    CHANNEL_BINDING_TOPIC,
    ChannelBindingEvent,
    ChannelBindingHealthEvent,
)
from project_utility.db.mongo import get_mongo_database
from project_utility.db.redis import get_async_redis
from project_utility.telemetry import emit as telemetry_emit

EVENT_QUEUE_KEY = "rise:channel_binding:event_queue"
DEADLETTER_COLLECTION = "channel_binding_deadletter"
DEADLETTER_MAX_RETRIES = 3


@dataclass(slots=True)
class PublishResult:
    status: str
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class ChannelBindingEventPublisher:
    """Publish channel binding events with queue + deadletter fallbacks."""

    def __init__(self) -> None:
        self._redis = get_async_redis()
        self._logger = logging.getLogger("channel_binding.publisher")
        self._max_retries = DEADLETTER_MAX_RETRIES

    async def publish_binding(
        self,
        event: ChannelBindingEvent,
        *,
        replay: bool = False,
        retry_count: int = 0,
    ) -> PublishResult:
        return await self._publish(
            CHANNEL_BINDING_TOPIC,
            event.dumps(),
            workflow_id=event.workflow_id,
            replay=replay,
            retry_count=retry_count,
        )

    async def publish_health(
        self,
        event: ChannelBindingHealthEvent,
        *,
        replay: bool = False,
        retry_count: int = 0,
    ) -> PublishResult:
        return await self._publish(
            CHANNEL_BINDING_HEALTH_TOPIC,
            event.dumps(),
            workflow_id=event.workflow_id,
            replay=replay,
            retry_count=retry_count,
        )

    async def publish(
        self,
        event: ChannelBindingEvent,
        *,
        replay: bool = False,
        retry_count: int = 0,
    ) -> PublishResult:
        """Backward compatible shim for existing callers."""

        return await self.publish_binding(event, replay=replay, retry_count=retry_count)

    async def _publish(
        self,
        topic: str,
        payload: str,
        *,
        workflow_id: str,
        replay: bool,
        retry_count: int,
    ) -> PublishResult:
        try:
            await self._redis.publish(topic, payload)
            telemetry_emit(
                "channel.binding.event_published",
                payload={"status": "sent", "workflow_id": workflow_id, "topic": topic},
            )
            return PublishResult(status="sent")
        except Exception as exc:  # pragma: no cover - network specific
            error_text = str(exc)
            self._logger.warning(
                "channel.binding.publish_failed",
                extra={"topic": topic, "workflow_id": workflow_id},
                exc_info=exc,
            )
            if replay and (retry_count + 1) >= self._max_retries:
                await self.record_deadletter(
                    topic,
                    payload,
                    reason="publish_failed",
                    error=error_text,
                    retry_count=retry_count + 1,
                )
                telemetry_emit(
                    "channel.binding.event_deadletter",
                    level="error",
                    payload={
                        "workflow_id": workflow_id,
                        "error": error_text,
                        "topic": topic,
                    },
                )
                return PublishResult(status="failed", warnings=["event_deadletter"], error=error_text)
            await self._enqueue(topic, payload, retry_count)
            telemetry_emit(
                "channel.binding.event_queued",
                level="warning",
                payload={"workflow_id": workflow_id, "error": error_text, "topic": topic},
            )
            return PublishResult(status="queued", warnings=["event_queued"], error=error_text)

    async def _enqueue(self, topic: str, payload: str, retry_count: int) -> None:
        envelope = self.encode_queue_payload(topic, payload, retry_count)
        await self._redis.rpush(EVENT_QUEUE_KEY, envelope)

    async def record_deadletter(
        self,
        topic: str,
        payload: str,
        *,
        reason: str,
        error: Optional[str] = None,
        retry_count: int = 0,
        last_failure_at: Optional[datetime] = None,
    ) -> None:
        doc = {
            "topic": topic,
            "payload": payload,
            "reason": reason,
            "error": error,
            "retryCount": retry_count,
            "lastFailureAt": last_failure_at or datetime.now(timezone.utc),
            "recorded_at": datetime.now(timezone.utc),
        }
        await asyncio.to_thread(self._insert_deadletter, doc)

    @staticmethod
    def decode_queue_payload(raw_payload: str) -> Tuple[str, str, int]:
        try:
            data = json.loads(raw_payload)
        except json.JSONDecodeError:
            return CHANNEL_BINDING_TOPIC, raw_payload, 0
        topic = data.get("topic", CHANNEL_BINDING_TOPIC)
        payload = data.get("payload", "")
        retry_count = int(data.get("retryCount", 0))
        return topic, payload, retry_count

    @staticmethod
    def encode_queue_payload(topic: str, payload: str, retry_count: int) -> str:
        return json.dumps(
            {"topic": topic, "payload": payload, "retryCount": retry_count}
        )

    @staticmethod
    def _insert_deadletter(doc) -> None:
        db = get_mongo_database()
        db[DEADLETTER_COLLECTION].insert_one(doc)


_publisher_singleton: Optional[ChannelBindingEventPublisher] = None


def get_channel_binding_event_publisher() -> ChannelBindingEventPublisher:
    global _publisher_singleton
    if _publisher_singleton is None:
        _publisher_singleton = ChannelBindingEventPublisher()
    return _publisher_singleton


__all__ = [
    "ChannelBindingEventPublisher",
    "PublishResult",
    "EVENT_QUEUE_KEY",
    "DEADLETTER_COLLECTION",
    "DEADLETTER_MAX_RETRIES",
    "get_channel_binding_event_publisher",
]
