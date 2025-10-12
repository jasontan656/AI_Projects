from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Dict

import psutil


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self) -> None:
        self.process = psutil.Process()
        self.metrics: Dict[str, Dict] = {}

    @contextmanager
    def monitor(self, scenario_id: str):
        start_time = time.perf_counter()
        start_cpu = self.process.cpu_percent(interval=None)
        start_memory = self.process.memory_info().rss

        peak_memory = start_memory
        peak_cpu = start_cpu

        stop_event = threading.Event()

        def loop() -> None:
            nonlocal peak_memory, peak_cpu
            while not stop_event.is_set():
                current_memory = self.process.memory_info().rss
                current_cpu = self.process.cpu_percent(interval=None)
                peak_memory = max(peak_memory, current_memory)
                peak_cpu = max(peak_cpu, current_cpu)
                time.sleep(0.1)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        try:
            yield
        finally:
            stop_event.set()
            t.join(timeout=1)
            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss
            self.metrics[scenario_id] = {
                "duration": end_time - start_time,
                "memory": {
                    "start": start_memory / 1024 / 1024,
                    "end": end_memory / 1024 / 1024,
                    "peak": peak_memory / 1024 / 1024,
                    "delta": (end_memory - start_memory) / 1024 / 1024,
                },
                "cpu": {"start": start_cpu, "peak": peak_cpu},
            }

    def get_metrics(self, scenario_id: str) -> Dict:
        return self.metrics.get(scenario_id, {})

    def get_all_metrics(self) -> Dict[str, Dict]:
        return self.metrics

