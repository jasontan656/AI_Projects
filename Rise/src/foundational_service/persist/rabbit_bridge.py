from __future__ import annotations

"""RabbitMQ bridge utilities for mirroring and rehydrating task envelopes."""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Mapping, Optional

import aio_pika

from .task_envelope import TaskEnvelope

log = logging.getLogger("persist.rabbit_bridge")


@dataclass(slots=True)
class RabbitConfig:
    url: str
    exchange: str = os.getenv("RABBITMQ_EXCHANGE", "rise.tasks.durable")
    exchange_type: str = os.getenv("RABBITMQ_EXCHANGE_TYPE", "topic")
    queue: str = os.getenv("RABBITMQ_QUEUE", "rise.tasks.quorum")
    routing_key: str = os.getenv("RABBITMQ_ROUTING_KEY", "rise.tasks")
    dlx: Optional[str] = os.getenv("RABBITMQ_DLX", "rise.tasks.dlx")
    prefetch: int = int(os.getenv("RABBITMQ_PREFETCH", "64"))
    publish_timeout: float = float(os.getenv("RABBITMQ_PUBLISH_TIMEOUT", "5"))

    @classmethod
    def from_env(cls) -> "RabbitConfig":
        url = os.getenv("RABBITMQ_URL")
        if not url:
            raise RuntimeError("missing required environment variable: RABBITMQ_URL")
        return cls(url=url)

    def queue_arguments(self) -> Mapping[str, Any]:
        arguments: dict[str, Any] = {
            "x-queue-type": "quorum",
            "x-delivery-limit": int(os.getenv("RABBITMQ_DELIVERY_LIMIT", "5")),
        }
        max_length = os.getenv("RABBITMQ_QUEUE_MAX_LENGTH")
        if max_length:
            arguments["max-length"] = int(max_length)
        overflow = os.getenv("RABBITMQ_QUEUE_OVERFLOW")
        if overflow:
            arguments["overflow"] = overflow
        if self.dlx:
            arguments["x-dead-letter-exchange"] = self.dlx
        return arguments


class RabbitPublisher:
    """Durable publisher with confirm support."""

    def __init__(self, config: RabbitConfig) -> None:
        self.config = config
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._exchange: Optional[aio_pika.Exchange] = None

    async def start(self) -> None:
        if self._connection is not None:
            return
        self._connection = await aio_pika.connect_robust(self.config.url)
        self._channel = await self._connection.channel(publisher_confirms=True)
        await self._channel.set_qos(prefetch_count=self.config.prefetch)
        self._exchange = await self._channel.declare_exchange(
            self.config.exchange,
            aio_pika.ExchangeType(self.config.exchange_type),
            durable=True,
        )
        queue = await self._channel.declare_queue(
            self.config.queue,
            durable=True,
            arguments=self.config.queue_arguments(),
        )
        await queue.bind(self._exchange, routing_key=self.config.routing_key)
        log.info(
            "rabbit.publisher.ready",
            extra={
                "exchange": self.config.exchange,
                "queue": self.config.queue,
                "routing_key": self.config.routing_key,
            },
        )

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def publish_task(self, envelope: TaskEnvelope) -> None:
        if self._exchange is None:
            await self.start()
        assert self._exchange is not None
        payload = envelope.to_dict()
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        message = aio_pika.Message(
            body=body,
            message_id=envelope.task_id,
            timestamp=envelope.updated_at,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={
                "workflowId": payload["payload"].get("workflowId"),
                "channel": payload["payload"].get("telemetry", {}).get("channel"),
            },
        )
        publish_coro = self._exchange.publish(
            message,
            routing_key=self.config.routing_key,
            mandatory=False,
        )
        try:
            await asyncio.wait_for(publish_coro, timeout=self.config.publish_timeout)
        except asyncio.TimeoutError as exc:
            log.error(
                "rabbit.publisher.timeout",
                extra={"task_id": envelope.task_id, "timeout": self.config.publish_timeout},
            )
            raise


class RabbitConsumer:
    """Simple consumer wrapper used by the rehydrator."""

    def __init__(self, config: RabbitConfig) -> None:
        self.config = config
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._queue: Optional[aio_pika.Queue] = None

    async def start(self) -> None:
        if self._connection is not None:
            return
        self._connection = await aio_pika.connect_robust(self.config.url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self.config.prefetch)
        exchange = await self._channel.declare_exchange(
            self.config.exchange,
            aio_pika.ExchangeType(self.config.exchange_type),
            durable=True,
        )
        self._queue = await self._channel.declare_queue(
            self.config.queue,
            durable=True,
            arguments=self.config.queue_arguments(),
        )
        await self._queue.bind(exchange, routing_key=self.config.routing_key)

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def iterate(self):
        if self._queue is None:
            await self.start()
        assert self._queue is not None
        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                yield message


def envelope_from_message(message: aio_pika.IncomingMessage) -> TaskEnvelope:
    payload = json.loads(message.body.decode("utf-8"))
    return TaskEnvelope.from_dict(payload)


__all__ = [
    "RabbitConfig",
    "RabbitPublisher",
    "RabbitConsumer",
    "envelope_from_message",
]
