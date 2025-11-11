from __future__ import annotations

"""Operations CLI for Telegram channel binding controls."""

import argparse
import asyncio
import json
from typing import Any, Dict

from business_service.channel.command_service import ChannelBindingCommandService
from business_service.channel.registry import ChannelBindingRegistry
from business_service.channel.repository import AsyncWorkflowChannelRepository
from business_service.channel.service import WorkflowChannelService
from business_service.workflow import AsyncWorkflowRepository
from foundational_service.messaging.channel_binding_event_publisher import (
    DEADLETTER_COLLECTION,
    EVENT_QUEUE_KEY,
    ChannelBindingEventPublisher,
    get_channel_binding_event_publisher,
)
from interface_entry.runtime.channel_binding_event_replayer import ChannelBindingEventReplayer
from interface_entry.http.dependencies import get_mongo_client, get_settings
from project_utility.context import ContextBridge
from project_utility.db.mongo import get_mongo_database
from project_utility.db.redis import get_async_redis


async def _build_command_service() -> ChannelBindingCommandService:
    settings = get_settings()
    client = get_mongo_client()
    database = client[settings.mongodb_database]
    channel_repo = AsyncWorkflowChannelRepository(database["workflow_channels"])
    workflow_repo = AsyncWorkflowRepository(database["workflows"])
    service = WorkflowChannelService(repository=channel_repo, workflow_repository=workflow_repo)
    registry = ChannelBindingRegistry(service=service)
    await registry.refresh()
    publisher = get_channel_binding_event_publisher()
    return ChannelBindingCommandService(service=service, registry=registry, publisher=publisher)


async def _handle_kill_switch(args: argparse.Namespace) -> None:
    command_service = await _build_command_service()
    active = args.state == "on"
    outcome = await command_service.set_kill_switch_state(
        args.workflow_id,
        channel=args.channel,
        active=active,
        actor=args.actor,
        reason=args.reason,
    )
    payload: Dict[str, Any] = {
        "workflowId": outcome.option.workflow_id,
        "channel": outcome.option.channel,
        "status": outcome.option.status,
        "killSwitch": active,
        "warnings": list(outcome.warnings),
    }
    if outcome.option.policy:
        payload["secretVersion"] = outcome.option.policy.secret_version
    print(json.dumps(payload, ensure_ascii=False, indent=2))


async def _handle_queue_status(_: argparse.Namespace) -> None:
    redis = get_async_redis()
    queue_length = await redis.llen(EVENT_QUEUE_KEY)

    def _count_deadletters() -> int:
        db = get_mongo_database()
        return db[DEADLETTER_COLLECTION].count_documents({})

    deadletter_count = await asyncio.to_thread(_count_deadletters)
    payload = {
        "eventQueueLength": queue_length,
        "deadletterCount": deadletter_count,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


async def _handle_replay(args: argparse.Namespace) -> None:
    publisher: ChannelBindingEventPublisher = get_channel_binding_event_publisher()
    replayer = ChannelBindingEventReplayer(publisher)
    iterations = max(1, args.iterations)
    for idx in range(iterations):
        await replayer.replay_pending()
        if idx < iterations - 1 and args.interval > 0:
            await asyncio.sleep(args.interval)
    print(json.dumps({"replayIterations": iterations}, ensure_ascii=False, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Channel binding admin utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    kill_switch = subparsers.add_parser("kill-switch", help="Toggle kill switch state for a workflow")
    kill_switch.add_argument("workflow_id", help="Workflow identifier")
    kill_switch.add_argument(
        "--channel",
        default="telegram",
        help="Channel identifier (default: telegram)",
    )
    kill_switch.add_argument(
        "--state",
        choices=("on", "off"),
        required=True,
        help="Target kill switch state",
    )
    kill_switch.add_argument(
        "--actor",
        default="channel_binding_cli",
        help="Actor id recorded in audit trail",
    )
    kill_switch.add_argument(
        "--reason",
        default=None,
        help="Optional reason to include in the published event",
    )

    queue_status = subparsers.add_parser("queue-status", help="Inspect binding event queue/deadletters")

    replay = subparsers.add_parser("replay-queue", help="Manually trigger event queue replay")
    replay.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="How many replay cycles to run (default: 1)",
    )
    replay.add_argument(
        "--interval",
        type=float,
        default=0.0,
        help="Sleep seconds between iterations (default: 0)",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    ContextBridge.set_request_id()
    if args.command == "kill-switch":
        asyncio.run(_handle_kill_switch(args))
        return
    if args.command == "queue-status":
        asyncio.run(_handle_queue_status(args))
        return
    if args.command == "replay-queue":
        asyncio.run(_handle_replay(args))
        return
    parser.error(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()

