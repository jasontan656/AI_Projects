from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from business_service.conversation.runtime_dispatch import DispatchConfig, RuntimeDispatchController
from business_service.conversation.runtime_gateway import RuntimeDispatchOutcome
from business_service.channel.health_store import ChannelBindingHealthStore
from foundational_service.persist.task_envelope import TaskEnvelope


class _FakeGateway:
    def __init__(self, outcome: RuntimeDispatchOutcome) -> None:
        self._outcome = outcome

    async def dispatch(self, **kwargs: Any) -> RuntimeDispatchOutcome:
        return self._outcome


class _InMemoryHealthStore(ChannelBindingHealthStore):
    def __init__(self) -> None:
        super().__init__(redis_client=_AsyncNullRedis())  # type: ignore[arg-type]
        self.events: list[Dict[str, Any]] = []

    async def record_test_heartbeat(self, channel: str, workflow_id: str, *, status: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({"channel": channel, "workflow_id": workflow_id, "status": status, "metadata": metadata or {}})

    async def increment_error(self, channel: str, workflow_id: Optional[str], error_type: str) -> None:
        self.events.append({"channel": channel, "workflow_id": workflow_id, "status": error_type})


class _AsyncNullRedis:
    async def hset(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def expire(self, *args: Any, **kwargs: Any) -> None:
        return None


async def main() -> None:
    envelope = TaskEnvelope.new(task_type="telegram.workflow", payload={"message": "ping"})
    outcome = RuntimeDispatchOutcome(envelope=envelope, status="completed", result_payload={"reply": "pong"})
    controller = RuntimeDispatchController(
        gateway=_FakeGateway(outcome),
        health_store=_InMemoryHealthStore(),
    )
    result = await controller.dispatch(
        envelope=envelope,
        workflow_id="wf-passport",
        channel="telegram",
        config=DispatchConfig(expects_result=True),
    )
    print("Dispatch result:", result.status)


if __name__ == "__main__":
    asyncio.run(main())
