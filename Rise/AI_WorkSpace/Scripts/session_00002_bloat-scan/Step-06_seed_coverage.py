from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone
from typing import Sequence

import motor.motor_asyncio
import redis.asyncio as redis

from business_service.channel.coverage_status import CoverageStatusService


def _default_env(name: str, fallback: str) -> str:
    return os.environ.get(name, fallback)


async def seed_coverage(
    workflow_id: str,
    *,
    status: str,
    scenarios: Sequence[str],
    mode: str,
    actor_id: str,
) -> None:
    redis_url = _default_env("REDIS_URL", "redis://localhost:6380/0")
    mongo_uri = _default_env("MONGODB_URI", "mongodb://root:changeme@localhost:37017/?replicaSet=rs0&authSource=admin")
    mongo_db = _default_env("MONGODB_DATABASE", "rise")

    redis_client = redis.from_url(redis_url)
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    history_collection = mongo_client[mongo_db]["workflow_run_coverage"]

    service = CoverageStatusService(
        redis_client=redis_client,
        history_collection=history_collection,
    )

    await service.mark_status(
        workflow_id,
        status=status,
        scenarios=list(scenarios),
        mode=mode,
        actor_id=actor_id,
        last_run_id=f"seed-{datetime.now(timezone.utc).strftime('%H%M%S')}",
        metadata={"source": "Step-06_seed_coverage", "actorId": actor_id},
    )

    await redis_client.close()
    mongo_client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed workflow coverage status for telemetry verification.")
    parser.add_argument("--workflow", default="wf-demo", help="Workflow ID to update.")
    parser.add_argument("--status", default="passed", choices=["passed", "failed", "pending"], help="Coverage status value.")
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=["golden_path"],
        help="Scenario names to associate with the run.",
    )
    parser.add_argument("--mode", default="webhook", help="Execution mode label.")
    parser.add_argument("--actor-id", default="cli-probe", help="Actor identifier stored in telemetry metadata.")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(
        seed_coverage(
            arguments.workflow,
            status=arguments.status,
            scenarios=arguments.scenarios,
            mode=arguments.mode,
            actor_id=arguments.actor_id,
        )
    )
