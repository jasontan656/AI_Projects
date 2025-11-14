from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from project_utility.telemetry import emit as telemetry_emit

from business_service.channel.health_store import ChannelBindingHealthStore
from foundational_service.persist.task_envelope import TaskEnvelope

from .runtime_gateway import (
    AsyncResultHandleFactory,
    EnqueueFailedError,
    RuntimeDispatchOutcome,
    RuntimeGateway,
)


@dataclass(slots=True)
class DispatchConfig:
    expects_result: bool = False
    wait_for_result: bool = False
    wait_timeout: Optional[float] = None
    idempotency_key: Optional[str] = None


class RuntimeDispatchController:
    """Coordinates RuntimeGateway invocations with channel health bookkeeping."""

    def __init__(
        self,
        *,
        gateway: RuntimeGateway,
        health_store: ChannelBindingHealthStore,
        async_handle_factory: Optional[AsyncResultHandleFactory] = None,
    ) -> None:
        self._gateway = gateway
        self._health_store = health_store
        self._async_handle_factory = async_handle_factory

    async def dispatch(
        self,
        *,
        envelope: TaskEnvelope,
        workflow_id: str,
        channel: str,
        config: Optional[DispatchConfig] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> RuntimeDispatchOutcome:
        config = config or DispatchConfig()
        heartbeat_metadata: dict[str, Any] = {"taskId": envelope.task_id}
        if metadata:
            heartbeat_metadata.update(metadata)
        if config.idempotency_key and self._async_handle_factory is not None:
            reservation = await self._async_handle_factory.reserve(
                idempotency_key=config.idempotency_key,
                task_id=envelope.task_id,
            )
            heartbeat_metadata["idempotencyKey"] = config.idempotency_key
            if not reservation.is_new:
                await self._health_store.record_test_heartbeat(
                    channel,
                    workflow_id,
                    status="duplicate",
                    metadata=heartbeat_metadata,
                )
                return RuntimeDispatchOutcome(envelope=envelope, status="duplicate")

        try:
            outcome = await self._gateway.dispatch(
                envelope=envelope,
                expects_result=config.expects_result,
                wait_for_result=config.wait_for_result,
                wait_timeout=config.wait_timeout,
            )
        except EnqueueFailedError as exc:
            await self._health_store.increment_error(channel, workflow_id, "enqueue_failed")
            telemetry_emit(
                "runtime.dispatch.enqueue_failed",
                level="error",
                workflow_id=workflow_id,
                channel=channel,
                payload={"taskId": envelope.task_id, "error": str(exc.error)},
            )
            raise

        await self._health_store.record_test_heartbeat(
            channel,
            workflow_id,
            status=outcome.status,
            metadata=heartbeat_metadata,
        )
        return outcome


__all__ = ["DispatchConfig", "RuntimeDispatchController"]
