"""维度3：并发与性能"""

from __future__ import annotations

import queue
import threading
from statistics import mean
from typing import Any, Dict, List

import pytest


class ConcurrentTester:
    """并发测试器（I/O 密集）"""

    def __init__(self, num_workers: int) -> None:
        self.num_workers = num_workers
        self.results: "queue.Queue[Dict[str, Any]]" = queue.Queue()

    def run_concurrent(self, func, args_list=None, kwargs_list=None):  # type: ignore[no-untyped-def]
        if args_list is None:
            args_list = [tuple()] * self.num_workers
        if kwargs_list is None:
            kwargs_list = [{}] * self.num_workers

        def worker(i: int, a, k):  # type: ignore[no-untyped-def]
            import time

            t0 = time.perf_counter()
            try:
                res = func(*a, **k)
                dt = time.perf_counter() - t0
                self.results.put({"success": True, "result": res, "duration": dt, "worker_id": i})
            except Exception as e:  # noqa: BLE001
                dt = time.perf_counter() - t0
                self.results.put({"success": False, "error": str(e), "duration": dt, "worker_id": i})

        threads: List[threading.Thread] = []
        for i in range(self.num_workers):
            a = args_list[i] if i < len(args_list) else tuple()
            k = kwargs_list[i] if i < len(kwargs_list) else {}
            t = threading.Thread(target=worker, args=(i, a, k), daemon=True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        out: List[Dict[str, Any]] = []
        while not self.results.empty():
            out.append(self.results.get())
        return out

    @staticmethod
    def _pct(values: List[float], q: float) -> float:
        if not values:
            return 0.0
        xs = sorted(values)
        idx = max(0, min(len(xs) - 1, int(round((len(xs) - 1) * q))))
        return xs[idx]

    def analyze(self, results: List[Dict[str, Any]]) -> Dict[str, float | int]:
        tot = len(results)
        ok = sum(1 for r in results if r.get("success"))
        durs = [r["duration"] for r in results]
        return {
            "total": tot,
            "success_count": ok,
            "failure_count": tot - ok,
            "success_rate": (ok / tot) if tot else 0.0,
            "avg_duration": mean(durs) if durs else 0.0,
            "p95_duration": self._pct(durs, 0.95),
        }


@pytest.mark.p1
@pytest.mark.timeout(120)
def test_scenario_3_1__ten_concurrent_health(api_client):
    tester = ConcurrentTester(num_workers=10)
    results = tester.run_concurrent(func=lambda: api_client.health())
    stats = tester.analyze(results)
    assert stats["success_rate"] >= 0.95

