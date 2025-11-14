from __future__ import annotations

import argparse
import asyncio
from typing import Sequence

from motor.motor_asyncio import AsyncIOMotorClient

from business_service.channel.coverage_status import CoverageStatusService
from project_utility.db.redis import get_async_redis


async def _seed(args: argparse.Namespace) -> None:
    redis = get_async_redis()
    mongo = AsyncIOMotorClient(args.mongo_uri, tz_aware=True)
    history_collection = mongo[args.mongo_database]["workflow_run_coverage"]
    service = CoverageStatusService(
        redis_client=redis,
        history_collection=history_collection,
        ttl_seconds=args.ttl,
    )
    status = await service.mark_status(
        args.workflow_id,
        status=args.status,
        scenarios=args.scenarios or ["passport_text", "passport_attachment"],
        mode=args.mode,
        actor_id=args.actor_id,
        metadata={"trigger": "seed_script"},
    )
    print(status.to_dict())


def _parse_scenarios(value: str) -> Sequence[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed workflow coverage status for local testing.")
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--status", default="pending")
    parser.add_argument("--mode", default="webhook")
    parser.add_argument("--scenarios", type=_parse_scenarios, default="passport_text")
    parser.add_argument("--actor-id", default="seed-script")
    parser.add_argument("--ttl", type=int, default=86400)
    parser.add_argument("--mongo-uri", required=True)
    parser.add_argument("--mongo-database", required=True)
    args = parser.parse_args()
    asyncio.run(_seed(args))


if __name__ == "__main__":
    main()
