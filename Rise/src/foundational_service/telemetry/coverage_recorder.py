from __future__ import annotations

"""Coverage test run recorder and SSE fan-out."""

import asyncio
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Mapping, MutableMapping, Optional, Sequence, Set

from project_utility.config.paths import get_log_root


class CoverageTestEventRecorder:
    """Write coverage test run events to disk and fan out via SSE-friendly queues."""

    def __init__(
        self,
        *,
        log_root: Optional[Path] = None,
        history_limit: int = 10,
        heartbeat_seconds: float = 15.0,
    ) -> None:
        self._log_root = (log_root or get_log_root()).resolve() / "test_runs"
        self._history_limit = max(1, history_limit)
        self._heartbeat_seconds = max(5.0, heartbeat_seconds)
        self._subscribers: MutableMapping[str, Set[asyncio.Queue[Mapping[str, Any]]]] = {}
        self._lock = threading.RLock()

    async def record_completion(
        self,
        workflow_id: str,
        *,
        status: str,
        scenarios: Sequence[str],
        mode: str,
        actor_id: Optional[str],
        last_run_id: Optional[str],
        last_error: Optional[str],
        metadata: Mapping[str, Any],
    ) -> None:
        event_time = datetime.now(timezone.utc)
        event = {
            "workflowId": workflow_id,
            "status": status,
            "mode": mode,
            "scenarios": list(scenarios),
            "actorId": actor_id,
            "lastRunId": last_run_id,
            "lastError": last_error,
            "metadata": dict(metadata),
            "timestamp": event_time.isoformat(),
        }
        await asyncio.to_thread(self._persist_event, workflow_id, event, event_time)
        self._publish(workflow_id, event)

    async def stream(self, workflow_id: str) -> AsyncIterator[str]:
        queue: asyncio.Queue[Mapping[str, Any]] = asyncio.Queue(maxsize=100)
        self._add_subscriber(workflow_id, queue)
        try:
            history = await asyncio.to_thread(self._load_history, workflow_id)
            for event in history:
                yield self._format_event(event)
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=self._heartbeat_seconds)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield self._format_event(event)
        finally:
            self._remove_subscriber(workflow_id, queue)

    def _persist_event(self, workflow_id: str, event: Mapping[str, Any], event_time: datetime) -> None:
        directory = self._log_root / workflow_id
        directory.mkdir(parents=True, exist_ok=True)
        filename = event_time.strftime("%Y%m%dT%H%M%S%fZ")
        path = directory / f"{filename}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _publish(self, workflow_id: str, event: Mapping[str, Any]) -> None:
        with self._lock:
            queues = list(self._subscribers.get(workflow_id, set()))
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # pragma: no cover - defensive path
                continue

    def _add_subscriber(self, workflow_id: str, queue: asyncio.Queue[Mapping[str, Any]]) -> None:
        with self._lock:
            subscribers = self._subscribers.setdefault(workflow_id, set())
            subscribers.add(queue)

    def _remove_subscriber(self, workflow_id: str, queue: asyncio.Queue[Mapping[str, Any]]) -> None:
        with self._lock:
            subscribers = self._subscribers.get(workflow_id)
            if not subscribers:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(workflow_id, None)

    def _load_history(self, workflow_id: str) -> Sequence[Mapping[str, Any]]:
        directory = self._log_root / workflow_id
        if not directory.exists():
            return ()
        files = sorted(directory.glob("*.jsonl"))
        if not files:
            return ()
        events: list[Mapping[str, Any]] = []
        for path in files[-self._history_limit :]:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        events.append(json.loads(line))
            except FileNotFoundError:  # pragma: no cover - deleted mid-read
                continue
        return events[-self._history_limit :]

    def _format_event(self, event: Mapping[str, Any]) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


_COVERAGE_EVENT_RECORDER: Optional[CoverageTestEventRecorder] = None
_COVERAGE_RECORDER_LOCK = threading.Lock()


def get_coverage_test_event_recorder() -> CoverageTestEventRecorder:
    global _COVERAGE_EVENT_RECORDER
    if _COVERAGE_EVENT_RECORDER is None:
        with _COVERAGE_RECORDER_LOCK:
            if _COVERAGE_EVENT_RECORDER is None:
                _COVERAGE_EVENT_RECORDER = CoverageTestEventRecorder()
    return _COVERAGE_EVENT_RECORDER


__all__ = ["CoverageTestEventRecorder", "get_coverage_test_event_recorder"]
