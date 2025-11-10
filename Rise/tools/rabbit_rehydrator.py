from __future__ import annotations

import argparse
import asyncio
from contextlib import suppress

from business_service.workflow.repository import StageRepository, WorkflowRepository
from foundational_service.persist.rabbit_bridge import (
    RabbitConfig,
    RabbitConsumer,
    envelope_from_message,
)
from foundational_service.persist.redis_queue import RedisTaskQueue
from foundational_service.persist.storage import WorkflowRunStorage
from foundational_service.persist.worker import RetryTask, SuspendTask, WorkflowTaskProcessor
from project_utility.db import get_mongo_database
from project_utility.db.redis import get_async_redis
from project_utility.telemetry import emit as telemetry_emit, setup_telemetry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RabbitMQ → Redis rehydrator/runner")
    parser.add_argument(
        "--mode",
        choices=("rehydrate", "execute"),
        default="rehydrate",
        help="rehydrate: push back to Redis; execute: run workflow immediately",
    )
    return parser.parse_args()


def build_processor() -> WorkflowTaskProcessor:
    database = get_mongo_database()
    workflow_repo = WorkflowRepository(database["workflows"])
    stage_repo = StageRepository(database["workflow_stages"])
    return WorkflowTaskProcessor(workflow_repository=workflow_repo, stage_repository=stage_repo)


async def execute_envelope(processor: WorkflowTaskProcessor, storage: WorkflowRunStorage, envelope) -> None:
    result = await processor.process(envelope)
    envelope.set_result(result)
    storage.upsert_result(envelope=envelope, result=result)


async def rehydrator_loop(mode: str) -> None:
    rabbit_config = RabbitConfig.from_env()
    consumer = RabbitConsumer(rabbit_config)
    await consumer.start()

    redis_queue = RedisTaskQueue(get_async_redis())
    processor = build_processor() if mode == "execute" else None
    storage = WorkflowRunStorage(get_mongo_database()) if mode == "execute" else None

    async for message in consumer.iterate():
        async with message.process(requeue=False, ignore_processed=True):
            envelope = envelope_from_message(message)
            if mode == "rehydrate":
                await redis_queue.enqueue_existing(envelope)
                telemetry_emit(
                    "tools.rabbit_rehydrator.enqueued",
                    payload={"task_id": envelope.task_id},
                )
                continue

            assert processor is not None and storage is not None
            try:
                await execute_envelope(processor, storage, envelope)
                telemetry_emit(
                    "tools.rabbit_rehydrator.executed",
                    payload={"task_id": envelope.task_id},
                )
            except RetryTask as exc:
                telemetry_emit(
                    "tools.rabbit_rehydrator.retry_requested",
                    level="warning",
                    payload={"task_id": envelope.task_id, "reason": exc.reason},
                )
                await message.reject(requeue=True)
                await asyncio.sleep(1)
                continue
            except SuspendTask as exc:
                telemetry_emit(
                    "tools.rabbit_rehydrator.suspended",
                    level="error",
                    payload={"task_id": envelope.task_id, "reason": exc.reason},
                )
                continue


def main() -> None:
    setup_telemetry()
    args = parse_args()
    telemetry_emit("tools.rabbit_rehydrator.start", payload={"mode": args.mode})
    with suppress(KeyboardInterrupt):
        asyncio.run(rehydrator_loop(args.mode))


if __name__ == "__main__":
    main()
