from __future__ import annotations

"""Redis helpers for the task queue runtime."""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from project_utility.telemetry import emit as telemetry_emit

from .task_envelope import TaskEnvelope, TaskStatus

__all__ = ["RedisTaskQueue", "StreamTask"]


@dataclass(slots=True)
class StreamTask:
    stream_id: str
    envelope: TaskEnvelope


class RedisTaskQueue:
    def __init__(
        self,
        client: Redis,
        *,
        stream_key: Optional[str] = None,
        retry_key: Optional[str] = None,
        suspended_key: Optional[str] = None,
        group_name: Optional[str] = None,
        task_ttl_seconds: Optional[int] = None,
        stream_maxlen: Optional[int] = None,
        status_history: int = 50,
    ) -> None:
        namespace = os.getenv("TASK_QUEUE_NAMESPACE", "queue")
        self._redis = client
        self.stream_key = stream_key or f"{namespace}:tasks"
        self.retry_key = retry_key or f"{namespace}:retry"
        self.suspended_key = suspended_key or f"{namespace}:suspended"
        self.group_name = group_name or os.getenv("TASK_QUEUE_GROUP", "persist-workers")
        self._task_data_prefix = f"{namespace}:task"
        self._status_counter_prefix = f"{namespace}:status:count"
        self._status_recent_prefix = f"{namespace}:status:recent"
        self._task_ttl = task_ttl_seconds or int(os.getenv("TASK_DATA_TTL_SECONDS", "86400"))
        self._stream_maxlen = stream_maxlen or int(os.getenv("TASK_STREAM_MAXLEN", "5000"))
        self._status_history = status_history
        self._queue_name = namespace

    def _emit_queue_event(
        self,
        event_type: str,
        *,
        level: str = "info",
        envelope: Optional[TaskEnvelope] = None,
        payload: Optional[Mapping[str, Any]] = None,
        **fields: Any,
    ) -> None:
        base_payload: Dict[str, Any] = {"stream": self.stream_key, **(payload or {})}
        workflow_id = None
        request_id = None
        if envelope is not None:
            base_payload.setdefault("task_id", envelope.task_id)
            base_payload.setdefault("task_type", envelope.type)
            base_payload.setdefault("status", envelope.status.value)
            workflow_id = envelope.payload.get("workflowId") or envelope.context.get("workflowId")
            request_id = envelope.context.get("requestId")
        telemetry_emit(
            event_type,
            level=level,
            workflow_id=workflow_id,
            request_id=request_id,
            payload=base_payload,
            **fields,
        )

    async def ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                name=self.stream_key,
                groupname=self.group_name,
                id="0-0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                return
            raise

    async def enqueue(self, envelope: TaskEnvelope) -> str:
        envelope.mark_status(TaskStatus.PENDING)
        await self._persist_envelope(envelope)
        entry_id = await self._redis.xadd(
            self.stream_key,
            {"task": envelope.to_json()},
            maxlen=self._stream_maxlen,
            approximate=True,
        )
        return entry_id

    async def enqueue_existing(self, envelope: TaskEnvelope) -> str:
        envelope.mark_status(TaskStatus.PENDING)
        await self._persist_envelope(envelope)
        entry_id = await self._redis.xadd(
            self.stream_key,
            {"task": envelope.to_json()},
            maxlen=self._stream_maxlen,
            approximate=True,
        )
        return entry_id

    async def read_group(
        self,
        consumer_id: str,
        *,
        count: int = 1,
        block_ms: int = 5000,
    ) -> List[StreamTask]:
        response = await self._redis.xreadgroup(
            groupname=self.group_name,
            consumername=consumer_id,
            streams={self.stream_key: ">"},
            count=count,
            block=block_ms,
        )
        return self._decode_stream_response(response)

    async def auto_claim(
        self,
        consumer_id: str,
        *,
        min_idle_ms: int,
        count: int = 10,
    ) -> List[StreamTask]:
        claimed: List[StreamTask] = []
        try:
            next_id = "0-0"
            while True:
                resp = await self._redis.xautoclaim(
                    name=self.stream_key,
                    groupname=self.group_name,
                    consumername=consumer_id,
                    min_idle_time=min_idle_ms,
                    start_id=next_id,
                    count=count,
                )
                entries = []
                deleted = 0
                errors_detail: Optional[Any] = None
                if isinstance(resp, (list, tuple)):
                    next_id = resp[0]
                    if len(resp) > 1:
                        entries = resp[1] or []
                    if len(resp) > 2:
                        deleted = resp[2] or 0
                    if len(resp) > 3:
                        errors_detail = resp[3]
                else:  # pragma: no cover - legacy redis-py
                    next_id, entries = resp
                if deleted:
                    self._emit_queue_event(
                        "queue.auto_claim_deleted",
                        level="debug",
                        payload={"count": deleted},
                    )
                if errors_detail:
                    self._emit_queue_event(
                        "queue.auto_claim_errors",
                        level="warning",
                        payload={"detail": errors_detail},
                    )
                if not entries and next_id == "0-0":
                    break
                claimed.extend(self._decode_entries(entries))
                if next_id == "0-0":
                    break
        except ResponseError as exc:
            if "NOGROUP" in str(exc):
                await self.ensure_group()
                return []
            raise
        return claimed

    async def healthcheck(self) -> None:
        try:
            await asyncio.wait_for(self._redis.ping(), timeout=3.0)
            await self._redis.xpending(self.stream_key, self.group_name)
        except ResponseError as exc:
            if "NOGROUP" in str(exc):
                await self.ensure_group()
                return
            raise

    async def ack(self, stream_id: str, *, delete: bool = True) -> None:
        await self._redis.xack(self.stream_key, self.group_name, stream_id)
        if delete:
            await self._redis.xdel(self.stream_key, stream_id)

    async def mark_processing(self, envelope: TaskEnvelope, *, stream_id: str) -> None:
        envelope.mark_status(TaskStatus.PROCESSING)
        await self._persist_envelope(envelope)

    async def mark_completed(self, envelope: TaskEnvelope, *, stream_id: str) -> None:
        envelope.mark_status(TaskStatus.COMPLETED)
        await self._persist_envelope(envelope)
        await self._cleanup_retry_state(envelope.task_id)
        await self.ack(stream_id)
        self._emit_queue_event("queue.task_completed", envelope=envelope)

    async def mark_retry(
        self,
        envelope: TaskEnvelope,
        *,
        stream_id: str,
        delay_seconds: float,
        error: Optional[str] = None,
    ) -> bool:
        envelope.set_error(error)
        envelope.retry.schedule_next(delay_seconds)
        if envelope.retry.exhausted():
            await self.mark_suspended(envelope, stream_id=stream_id, error=error)
            return False
        envelope.mark_status(TaskStatus.RETRY)
        await self._persist_envelope(envelope)
        await self._redis.zadd(self.retry_key, {envelope.task_id: envelope.retry.next_attempt_at})
        await self.ack(stream_id)
        return True

    async def mark_suspended(
        self,
        envelope: TaskEnvelope,
        *,
        stream_id: str,
        error: Optional[str] = None,
    ) -> None:
        envelope.set_error(error)
        envelope.mark_status(TaskStatus.SUSPENDED)
        await self._persist_envelope(envelope)
        await self._cleanup_retry_state(envelope.task_id)
        await self._redis.zadd(self.suspended_key, {envelope.task_id: time.time()})
        await self.ack(stream_id)

    async def fetch_due_retries(self, limit: int = 20) -> List[TaskEnvelope]:
        now = time.time()
        task_ids = await self._redis.zrangebyscore(self.retry_key, min=0, max=now, start=0, num=limit)
        envelopes: List[TaskEnvelope] = []
        for task_id in task_ids:
            envelope = await self.get_task(task_id)
            if envelope is None:
                await self._redis.zrem(self.retry_key, task_id)
                continue
            envelopes.append(envelope)
            await self._redis.zrem(self.retry_key, task_id)
            envelope.retry.next_attempt_at = 0.0
        return envelopes

    async def list_suspended(self, limit: int = 50) -> List[TaskEnvelope]:
        task_ids = await self._redis.zrevrange(self.suspended_key, 0, limit - 1)
        results: List[TaskEnvelope] = []
        for task_id in task_ids:
            envelope = await self.get_task(task_id)
            if envelope:
                results.append(envelope)
        return results

    async def resume_task(self, task_id: str) -> Optional[TaskEnvelope]:
        envelope = await self.get_task(task_id)
        if envelope is None:
            return None
        await self._redis.zrem(self.suspended_key, task_id)
        entry_id = await self.enqueue_existing(envelope)
        self._emit_queue_event(
            "queue.task_resume",
            envelope=envelope,
            payload={"task_id": task_id, "entry_id": entry_id},
        )
        return envelope

    async def drop_task(self, task_id: str) -> bool:
        envelope = await self.get_task(task_id)
        key = self._task_key(task_id)
        deleted = await self._redis.delete(key)
        await self._cleanup_retry_state(task_id)
        await self._redis.zrem(self.suspended_key, task_id)
        if envelope:
            await self._remove_status_record(task_id, envelope.status.value)
        if deleted:
            self._emit_queue_event("queue.task_drop", level="info", envelope=envelope, payload={"task_id": task_id})
        return bool(deleted)

    async def get_task(self, task_id: str) -> Optional[TaskEnvelope]:
        raw = await self._redis.get(self._task_key(task_id))
        if not raw:
            return None
        try:
            return TaskEnvelope.from_json(raw)
        except Exception:  # pragma: no cover - guard corrupted payloads
            self._emit_queue_event(
                "queue.decode_failed",
                level="error",
                payload={"task_id": task_id},
            )
            return None

    async def get_stats(self) -> Mapping[str, Any]:
        statuses = list(TaskStatus)
        pipe = self._redis.pipeline()
        for status in statuses:
            pipe.get(self._status_counter_key(status))
        pipe.xlen(self.stream_key)
        pipe.zcard(self.retry_key)
        pipe.zcard(self.suspended_key)
        results = await pipe.execute()
        counts = {status.value: int(value or 0) for status, value in zip(statuses, results[: len(statuses)])}
        queue_length = int(results[len(statuses)] or 0)
        retry_length = int(results[len(statuses) + 1] or 0)
        suspended_length = int(results[len(statuses) + 2] or 0)
        recent: MutableMapping[str, List[Mapping[str, Any]]] = {}
        for status in statuses:
            recent[status.value] = [
                envelope.to_public_dict()
                for envelope in await self.list_recent(status.value, limit=5)
            ]
        return {
            "counts": counts,
            "streamLength": queue_length,
            "retryLength": retry_length,
            "suspendedLength": suspended_length,
            "recent": recent,
        }

    async def list_recent(self, status: str, limit: int = 5) -> List[TaskEnvelope]:
        task_ids = await self._redis.lrange(self._status_recent_key(status), 0, limit - 1)
        results: List[TaskEnvelope] = []
        seen: set[str] = set()
        for task_id in task_ids:
            if task_id in seen:
                continue
            seen.add(task_id)
            envelope = await self.get_task(task_id)
            if envelope:
                results.append(envelope)
        return results

    async def persist_snapshot(self, envelope: TaskEnvelope) -> None:
        await self._persist_envelope(envelope)

    async def _persist_envelope(self, envelope: TaskEnvelope) -> None:
        key = self._task_key(envelope.task_id)
        previous_raw = await self._redis.get(key)
        previous_status: Optional[str] = None
        if previous_raw:
            try:
                previous_status = json.loads(previous_raw).get("status")
            except Exception:  # pragma: no cover - corrupted JSON
                previous_status = None
        tx = self._redis.pipeline()
        tx.set(key, envelope.to_json(), ex=self._task_ttl)
        if previous_status != envelope.status.value:
            if previous_status:
                tx.incrby(self._status_counter_key(previous_status), -1)
            tx.incrby(self._status_counter_key(envelope.status.value), 1)
            tx.lpush(self._status_recent_key(envelope.status.value), envelope.task_id)
            tx.ltrim(self._status_recent_key(envelope.status.value), 0, self._status_history - 1)
        await tx.execute()

    async def _cleanup_retry_state(self, task_id: str) -> None:
        await self._redis.zrem(self.retry_key, task_id)

    async def _remove_status_record(self, task_id: str, status: str) -> None:
        key = self._status_counter_key(status)
        pipe = self._redis.pipeline()
        pipe.incrby(key, -1)
        pipe.lrem(self._status_recent_key(status), 0, task_id)
        pipe.get(key)
        _, _, current = await pipe.execute()
        try:
            value = int(current or 0)
        except (TypeError, ValueError):  # pragma: no cover - guard against corrupted counters
            value = 0
        if value < 0:
            await self._redis.set(key, 0)

    def _task_key(self, task_id: str) -> str:
        return f"{self._task_data_prefix}:{task_id}"

    def _status_counter_key(self, status: TaskStatus | str) -> str:
        label = status.value if isinstance(status, TaskStatus) else status
        return f"{self._status_counter_prefix}:{label}"

    def _status_recent_key(self, status: str) -> str:
        return f"{self._status_recent_prefix}:{status}"

    def _decode_stream_response(self, response: Sequence[tuple[str, List[tuple[str, Mapping[str, str]]]]]) -> List[StreamTask]:
        if not response:
            return []
        stream_entries = response[0][1]
        return self._decode_entries(stream_entries)

    def _decode_entries(self, entries: Iterable[tuple[str, Mapping[str, str]]]) -> List[StreamTask]:
        decoded: List[StreamTask] = []
        for entry_id, fields in entries:
            raw = fields.get("task")
            if not raw:
                continue
            try:
                envelope = TaskEnvelope.from_json(raw)
            except Exception:  # pragma: no cover - decode errors should surface but not crash loop
                self._emit_queue_event(
                    "queue.decode_failed",
                    level="error",
                    payload={"stream_id": entry_id},
                )
                continue
            decoded.append(StreamTask(stream_id=entry_id, envelope=envelope))
        return decoded

