from __future__ import annotations

"""Task runtime gateway coordinating sync/async dispatch."""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from redis.asyncio import Redis

from project_utility.db.redis import get_async_redis

from foundational_service.persist.task_envelope import TaskEnvelope
from foundational_service.persist.worker import TaskRuntime, TaskSubmitter

__all__ = [
    "AsyncResultHandle",
    "RuntimeDispatchOutcome",
    "RuntimeGateway",
    "set_task_queue_accessors",
    "AsyncAckReservation",
    "AsyncResultHandleFactory",
]

SubmitterFactory = Callable[[], Optional[TaskSubmitter]]
RuntimeFactory = Callable[[], Optional[TaskRuntime]]

_SUBMITTER_FACTORY: Optional[SubmitterFactory] = None
_RUNTIME_FACTORY: Optional[RuntimeFactory] = None


def set_task_queue_accessors(
    *,
    submitter_factory: SubmitterFactory,
    runtime_factory: RuntimeFactory,
) -> None:
    """Register factories used by the default runtime gateway."""

    global _SUBMITTER_FACTORY, _RUNTIME_FACTORY
    _SUBMITTER_FACTORY = submitter_factory
    _RUNTIME_FACTORY = runtime_factory


@dataclass(slots=True)
class AsyncResultHandle:
    runtime: TaskRuntime
    waiter: asyncio.Future[Any]
    task_id: str

    async def resolve(self) -> Mapping[str, Any]:
        try:
            return await self.waiter
        finally:
            await self.runtime.results.discard(self.task_id, self.waiter)

    async def discard(self) -> None:
        await self.runtime.results.discard(self.task_id, self.waiter)


@dataclass(slots=True)
class RuntimeDispatchOutcome:
    envelope: TaskEnvelope
    status: str
    handle: Optional[AsyncResultHandle] = None
    result_payload: Optional[Mapping[str, Any]] = None


class EnqueueFailedError(RuntimeError):
    def __init__(self, envelope: TaskEnvelope, error: Exception) -> None:
        super().__init__("task_enqueue_failed")
        self.envelope = envelope
        self.error = error


class RuntimeGateway:
    """Encapsulates TaskRuntime + TaskSubmitter orchestration."""

    def __init__(
        self,
        *,
        submitter_factory: Optional[SubmitterFactory] = None,
        runtime_factory: Optional[RuntimeFactory] = None,
    ) -> None:
        self._submitter_factory = submitter_factory
        self._runtime_factory = runtime_factory

    async def dispatch(
        self,
        *,
        envelope: TaskEnvelope,
        expects_result: bool,
        wait_for_result: bool,
        wait_timeout: Optional[float],
    ) -> RuntimeDispatchOutcome:
        submitter = self._get_submitter()
        runtime = self._get_runtime()
        handle: Optional[AsyncResultHandle] = None
        waiter: Optional[asyncio.Future[Any]] = None

        if expects_result:
            waiter = await runtime.results.register(envelope.task_id)
            handle = AsyncResultHandle(runtime=runtime, waiter=waiter, task_id=envelope.task_id)

        try:
            await submitter.submit(envelope)
        except Exception as exc:
            if waiter is not None:
                await runtime.results.discard(envelope.task_id, waiter)
            raise EnqueueFailedError(envelope, exc) from exc

        if expects_result and wait_for_result and handle is not None and waiter is not None:
            timeout = wait_timeout or 20.0
            try:
                payload = await asyncio.wait_for(waiter, timeout=timeout)
            except asyncio.TimeoutError:
                return RuntimeDispatchOutcome(envelope=envelope, status="timeout", handle=handle)
            except Exception:
                await runtime.results.discard(envelope.task_id, waiter)
                raise
            await runtime.results.discard(envelope.task_id, waiter)
            return RuntimeDispatchOutcome(
                envelope=envelope,
                status="completed",
                result_payload=payload,
            )

        if expects_result and handle is not None:
            return RuntimeDispatchOutcome(envelope=envelope, status="async_ack", handle=handle)

        return RuntimeDispatchOutcome(envelope=envelope, status="pending")

    def _get_submitter(self) -> TaskSubmitter:
        factory = self._submitter_factory or _SUBMITTER_FACTORY
        if factory is None:
            raise RuntimeError("task_submitter_unavailable")
        submitter = factory()
        if submitter is None:
            raise RuntimeError("task_submitter_unavailable")
        return submitter

    def _get_runtime(self) -> TaskRuntime:
        factory = self._runtime_factory or _RUNTIME_FACTORY
        if factory is None:
            raise RuntimeError("task_runtime_unavailable")
        runtime = factory()
        if runtime is None:
            raise RuntimeError("task_runtime_unavailable")
        return runtime


@dataclass(slots=True)
class AsyncAckReservation:
    """Represents the reservation outcome for an async task."""

    is_new: bool
    task_id: str
    idempotency_key: Optional[str] = None
    duplicate: bool = False


class AsyncResultHandleFactory:
    """Manage async ack dedupe + pending tracking via Redis."""

    def __init__(
        self,
        *,
        redis_client: Optional[Redis] = None,
        ttl_seconds: Optional[int] = None,
        idempotency_prefix: str = "rise:telegram:idempotency",
        pending_prefix: str = "rise:telegram:pending",
    ) -> None:
        self._redis_client = redis_client
        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else 86400
        self._idempotency_prefix = idempotency_prefix
        self._pending_prefix = pending_prefix

    def _client(self) -> Optional[Redis]:
        if self._redis_client is not None:
            return self._redis_client
        try:
            self._redis_client = get_async_redis()
        except Exception:  # pragma: no cover - defensive fallback
            self._redis_client = None
        return self._redis_client

    async def reserve(self, *, idempotency_key: Optional[str], task_id: str) -> AsyncAckReservation:
        """Register an async task idempotency key."""

        client = self._client()
        if client is None or not idempotency_key or self._ttl_seconds <= 0:
            return AsyncAckReservation(is_new=True, task_id=task_id, idempotency_key=idempotency_key)
        key = f"{self._idempotency_prefix}:{idempotency_key}"
        try:
            created = await client.set(key, task_id, nx=True, ex=self._ttl_seconds)
            if created:
                return AsyncAckReservation(is_new=True, task_id=task_id, idempotency_key=idempotency_key)
            existing = await client.get(key)
            if existing:
                return AsyncAckReservation(
                    is_new=False,
                    task_id=str(existing),
                    idempotency_key=idempotency_key,
                    duplicate=True,
                )
        except Exception:  # pragma: no cover - defensive fallback
            return AsyncAckReservation(is_new=True, task_id=task_id, idempotency_key=idempotency_key)
        return AsyncAckReservation(
            is_new=False,
            task_id=task_id,
            idempotency_key=idempotency_key,
            duplicate=True,
        )

    async def track_pending(self, *, chat_id: Optional[str], task_id: str) -> None:
        """Increment pending counter for a chat/thread."""

        client = self._client()
        if client is None or not chat_id or self._ttl_seconds <= 0:
            return
        key = f"{self._pending_prefix}:{chat_id}"
        try:
            await client.hincrby(key, task_id, 1)
            await client.expire(key, self._ttl_seconds)
        except Exception:  # pragma: no cover - defensive fallback
            return
