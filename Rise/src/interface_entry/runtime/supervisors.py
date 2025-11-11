from __future__ import annotations

"""Runtime supervisors responsible for dependency self-healing."""

import asyncio
import contextlib
import logging
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

from foundational_service.persist.worker import TaskRuntime
from interface_entry.http.dependencies import (
    DisabledTaskRuntime,
    get_task_runtime,
    get_task_runtime_if_enabled,
    shutdown_task_runtime,
)
from interface_entry.runtime.capabilities import CapabilityRegistry, CapabilityState
from interface_entry.runtime.channel_binding_event_replayer import ChannelBindingEventReplayer
from project_utility.telemetry import emit as telemetry_emit


RedisBackfillHook = Callable[[str], Awaitable[None]]


class RuntimeSupervisor:
    """Coordinate task runtime lifecycle and dependency recovery."""

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        critical_capabilities: Sequence[str] = ("redis", "rabbitmq"),
        redis_backfill: Optional[RedisBackfillHook] = None,
        logger: Optional[logging.Logger] = None,
        binding_replayer: ChannelBindingEventReplayer | None = None,
        binding_replayer_interval: float = 5.0,
    ) -> None:
        self._registry = registry
        self._critical = tuple(critical_capabilities)
        self._redis_backfill = redis_backfill
        self._logger = logger or logging.getLogger("interface_entry.runtime.supervisor")
        self._lock = asyncio.Lock()
        self._waiters: Dict[str, List[Tuple[str, asyncio.Future[CapabilityState]]]] = defaultdict(list)
        self._closed = False
        self._active_runtime: Optional[TaskRuntime] = None
        self._listener_names: List[str] = []
        self._binding_replayer = binding_replayer
        self._binding_replayer_interval = binding_replayer_interval
        self._binding_replayer_task: Optional[asyncio.Task[None]] = None
        self._binding_replayer_stop: Optional[asyncio.Event] = None

        for name in set(self._critical) | {"redis"}:
            registry.register_listener(name, self._handle_capability_event)
            self._listener_names.append(name)

    async def prime(self) -> None:
        """Align runtime state with the current capability snapshot."""
        await self._sync_task_runtime()

    async def shutdown(self) -> None:
        """Stop managed runtimes and detach listeners."""
        self._closed = True
        for name in self._listener_names:
            self._registry.unregister_listener(name, self._handle_capability_event)
        async with self._lock:
            await shutdown_task_runtime()
            self._active_runtime = None
            await self._stop_binding_replayer()
        for waiters in self._waiters.values():
            for _, future in waiters:
                if not future.done():
                    future.set_exception(asyncio.CancelledError())
        self._waiters.clear()

    async def wait_until(
        self,
        capability: str,
        *,
        status: str = "available",
        timeout: Optional[float] = 60.0,
    ) -> CapabilityState:
        """Block until a capability reaches the desired status."""
        state = self._registry.get_state(capability)
        if state and state.status == status:
            return state
        loop = asyncio.get_running_loop()
        future: asyncio.Future[CapabilityState] = loop.create_future()
        self._waiters[capability].append((status, future))
        return await asyncio.wait_for(future, timeout=timeout)

    async def _handle_capability_event(
        self,
        name: str,
        state: CapabilityState,
        previous: Optional[CapabilityState],
    ) -> None:
        if self._closed:
            return
        self._resolve_waiters(name, state)
        if name in self._critical:
            await self._sync_task_runtime()
        if (
            name == "redis"
            and self._redis_backfill is not None
            and state.status == "available"
            and (previous is None or previous.status != "available")
        ):
            await self._trigger_redis_backfill("backfill_after_recovery")

    def _resolve_waiters(self, name: str, state: CapabilityState) -> None:
        waiters = self._waiters.get(name)
        if not waiters:
            return
        remaining: List[Tuple[str, asyncio.Future[CapabilityState]]] = []
        for desired_status, future in waiters:
            if future.cancelled():
                continue
            if state.status == desired_status and not future.done():
                future.set_result(state)
            else:
                remaining.append((desired_status, future))
        if remaining:
            self._waiters[name] = remaining
        else:
            self._waiters.pop(name, None)

    async def _sync_task_runtime(self) -> None:
        blocked = self._blocked_capability()
        async with self._lock:
            if self._closed:
                return
            if blocked:
                await shutdown_task_runtime()
                if self._active_runtime is not None:
                    telemetry_emit(
                        "task_runtime.disabled",
                        level="warning",
                        payload={"reason": blocked},
                    )
                self._active_runtime = None
                await self._stop_binding_replayer()
                return

            runtime = get_task_runtime_if_enabled()
            if runtime is None:
                candidate = get_task_runtime()
                if isinstance(candidate, DisabledTaskRuntime):
                    return
                runtime = candidate
            if isinstance(runtime, DisabledTaskRuntime):
                return
            await runtime.start()
            if self._active_runtime is None:
                telemetry_emit("task_runtime.enabled", payload={"consumer": runtime.worker._consumer_id})
            self._active_runtime = runtime
            await self._start_binding_replayer()

    def _blocked_capability(self) -> Optional[str]:
        for name in self._critical:
            state = self._registry.get_state(name)
            if not state or state.status != "available":
                return name
        return None

    async def _trigger_redis_backfill(self, reason: str) -> None:
        if self._redis_backfill is None:
            return
        try:
            await self._redis_backfill(reason)
            telemetry_emit("knowledge.redis_backfill_completed", payload={"reason": reason})
        except Exception:
            telemetry_emit(
                "knowledge.redis_backfill_failed",
                level="error",
                payload={"reason": reason},
            )

    async def _start_binding_replayer(self) -> None:
        if self._binding_replayer is None or self._binding_replayer_task is not None:
            return
        stop_event = asyncio.Event()
        self._binding_replayer_stop = stop_event

        async def _runner() -> None:
            try:
                while not stop_event.is_set():
                    try:
                        await self._binding_replayer.replay_pending()  # type: ignore[union-attr]
                    except Exception as exc:  # pragma: no cover - defensive
                        self._logger.warning(
                            "channel.binding.replay_failed",
                            extra={"error": str(exc)},
                        )
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=self._binding_replayer_interval)
                    except asyncio.TimeoutError:
                        continue
            except asyncio.CancelledError:
                raise

        self._binding_replayer_task = asyncio.create_task(_runner(), name="channel-binding-replayer")

    async def _stop_binding_replayer(self) -> None:
        if self._binding_replayer_task is None:
            return
        if self._binding_replayer_stop:
            self._binding_replayer_stop.set()
        self._binding_replayer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._binding_replayer_task
        self._binding_replayer_task = None
        self._binding_replayer_stop = None


__all__ = ["RuntimeSupervisor"]
