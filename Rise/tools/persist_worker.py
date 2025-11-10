import asyncio
import signal
from contextlib import suppress

from interface_entry.http.dependencies import get_task_runtime
from project_utility.telemetry import emit as telemetry_emit, setup_telemetry


async def _run_worker() -> None:
    runtime = get_task_runtime()
    await runtime.start()
    telemetry_emit("tools.persist_worker.started")

    stop_event = asyncio.Event()

    def _signal_handler(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        await stop_event.wait()
    finally:
        await runtime.stop()
        telemetry_emit("tools.persist_worker.stopped")


if __name__ == "__main__":
    setup_telemetry()
    try:
        asyncio.run(_run_worker())
    except KeyboardInterrupt:
        pass
