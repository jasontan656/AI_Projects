"""Stress/soak test for RichLogger.

Spawns N threads that repeatedly initialize console/logging and emit messages.
Writes a simple performance summary JSON to the SimulationTest results directory.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

from Kobe.SharedUtility.RichLogger import init_console, init_logging


def worker(idx: int, loops: int, log: logging.Logger) -> None:
    for i in range(loops):
        init_console({})
        init_logging(level="INFO")
        log.info("worker %s iteration %s", idx, i)


def main() -> int:
    threads = int(os.getenv("STRESS_THREADS", "10"))
    loops = int(os.getenv("STRESS_LOOPS", "50"))

    log = logging.getLogger("richlogger.stress")

    t0 = time.perf_counter()
    ts: list[threading.Thread] = []
    for i in range(threads):
        t = threading.Thread(target=worker, args=(i, loops, log), daemon=True)
        t.start()
        ts.append(t)
    for t in ts:
        t.join()
    elapsed = time.perf_counter() - t0

    # Determine output location from the plan’s convention
    base = Path("D:/AI_Projects/Kobe/SimulationTest/RichLogger_testplan")
    out = base / "results" / "performance_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "threads": threads,
                "loops": loops,
                "elapsed_seconds": elapsed,
                "messages": threads * loops,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
