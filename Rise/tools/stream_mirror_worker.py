from __future__ import annotations

import asyncio
import os
import socket
from contextlib import suppress

from foundational_service.persist.rabbit_bridge import RabbitConfig, RabbitPublisher
from foundational_service.persist.redis_queue import RedisTaskQueue
from project_utility.db.redis import get_async_redis
from project_utility.telemetry import emit as telemetry_emit, setup_telemetry

MIRROR_GROUP = os.getenv("TASK_QUEUE_MIRROR_GROUP", "mirror-workers")


async def mirror_loop() -> None:
    rabbit_config = RabbitConfig.from_env()
    publisher = RabbitPublisher(rabbit_config)
    await publisher.start()

    redis_client = get_async_redis()
    queue = RedisTaskQueue(redis_client, group_name=MIRROR_GROUP)
    await queue.ensure_group()

    consumer_id = f"{socket.gethostname()}-mirror"
    telemetry_emit(
        "tools.stream_mirror.start",
        payload={"rabbit_exchange": rabbit_config.exchange, "consumer": consumer_id},
    )

    try:
        while True:
            batch = await queue.read_group(
                consumer_id,
                count=10,
                block_ms=5000,
            )
            if not batch:
                continue
            for stream_task in batch:
                envelope = stream_task.envelope
                try:
                    await publisher.publish_task(envelope)
                    await queue.ack(stream_task.stream_id, delete=False)
                    telemetry_emit(
                        "tools.stream_mirror.publish",
                        level="debug",
                        payload={"task_id": envelope.task_id},
                    )
                except Exception as exc:
                    telemetry_emit(
                        "tools.stream_mirror.publish_failed",
                        level="error",
                        payload={"task_id": envelope.task_id, "error": str(exc)},
                    )
                    await asyncio.sleep(1)
    finally:
        await publisher.close()


def main() -> None:
    setup_telemetry()
    with suppress(KeyboardInterrupt):
        asyncio.run(mirror_loop())


if __name__ == "__main__":
    main()
