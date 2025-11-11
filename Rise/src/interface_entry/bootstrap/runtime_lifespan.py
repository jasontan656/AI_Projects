from __future__ import annotations

import asyncio
import random
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from fastapi import FastAPI

from interface_entry.runtime.capabilities import CapabilityProbe, CapabilityRegistry, CapabilityState
from interface_entry.runtime.supervisors import RuntimeSupervisor
from project_utility.logging import finalize_log_workspace


AsyncLifespanFactory = Callable[[], Awaitable[None]]
AsyncLifespanContextFactory = Callable[[FastAPI], Any]


def configure_runtime_lifespan(
    app: FastAPI,
    *,
    capability_registry: CapabilityRegistry,
    runtime_supervisor: RuntimeSupervisor,
    application_lifespan: Callable[[], Any],
    log,
    extra_contexts: Optional[Sequence[AsyncLifespanContextFactory]] = None,
) -> None:
    """Attach the unified async lifespan that drives capability probes and runtime shutdown."""

    async def _run_initial_capability_checks() -> None:
        await capability_registry.run_all_probes()
        await runtime_supervisor.prime()

    async def _start_capability_monitors(stop_event: asyncio.Event) -> List[asyncio.Task]:
        tasks: List[asyncio.Task] = []
        rng = random.Random()

        async def _loop(probe: CapabilityProbe) -> None:
            base_interval = max(5.0, probe.base_interval or probe.retry_interval or 30.0)
            current_interval = base_interval
            max_interval = max(base_interval, probe.max_interval or base_interval)
            multiplier = probe.multiplier or 2.0
            try:
                while not stop_event.is_set():
                    jitter = rng.uniform(0.5, 1.5)
                    await asyncio.sleep(max(5.0, current_interval * jitter))
                    state = await capability_registry.run_probe(probe.name)
                    if state.status == "available":
                        current_interval = base_interval
                    else:
                        current_interval = min(current_interval * multiplier, max_interval)
            except asyncio.CancelledError:
                log.info(
                    "capability_monitor.cancelled",
                    extra={"probe": probe.name, "interval": current_interval},
                )
                return

        for probe in capability_registry.iter_probes():
            tasks.append(asyncio.create_task(_loop(probe), name=f"capability-probe-{probe.name}"))
        return tasks

    async def _refresh_capabilities() -> Dict[str, CapabilityState]:
        return await capability_registry.run_all_probes()

    app.state.capability_refresh = _refresh_capabilities

    @asynccontextmanager
    async def lifespan(app_context: FastAPI):
        monitor_stop = asyncio.Event()
        await _run_initial_capability_checks()
        monitor_tasks = await _start_capability_monitors(monitor_stop)
        exit_stack = AsyncExitStack()
        try:
            if extra_contexts:
                for factory in extra_contexts:
                    context_manager = factory(app_context)
                    await exit_stack.enter_async_context(context_manager)
            async with application_lifespan():
                try:
                    yield
                except asyncio.CancelledError:
                    log.info("shutdown.cancelled", extra={"origin": "lifespan"})
        finally:
            await exit_stack.aclose()
            monitor_stop.set()
            for task in monitor_tasks:
                task.cancel()
                with suppress(Exception):
                    await task
            await runtime_supervisor.shutdown()
            state = getattr(app_context.state, "telegram", None)
            if state:
                await state.bot.session.close()
            telemetry_subscriber = getattr(app_context.state, "telemetry_console_subscriber", None)
            if telemetry_subscriber:
                telemetry_subscriber.stop()
            log.info("shutdown.complete")
            finalize_log_workspace(reason="lifespan")

    app.router.lifespan_context = lifespan


__all__ = ["configure_runtime_lifespan"]
