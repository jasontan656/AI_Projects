from __future__ import annotations

"""Task envelope primitives backing the Redis queue runtime."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Mapping, MutableMapping, Optional
from uuid import uuid4

__all__ = [
    "RetryState",
    "TaskEnvelope",
    "TaskStatus",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RETRY = "retry"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    FAILED = "failed"


@dataclass(slots=True)
class RetryState:
    count: int = 0
    max: int = 3
    next_attempt_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "max": self.max,
            "nextAttemptAt": self.next_attempt_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RetryState":
        return cls(
            count=int(data.get("count", 0)),
            max=int(data.get("max", 3)),
            next_attempt_at=float(data.get("nextAttemptAt", 0.0)),
        )

    def schedule_next(self, delay_seconds: float) -> None:
        self.count += 1
        self.next_attempt_at = max(0.0, _utcnow().timestamp() + max(0.0, delay_seconds))

    def exhausted(self) -> bool:
        return self.count >= self.max


@dataclass(slots=True)
class TaskEnvelope:
    task_id: str
    type: str
    payload: MutableMapping[str, Any]
    context: MutableMapping[str, Any]
    retry: RetryState = field(default_factory=RetryState)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    result: Optional[Mapping[str, Any]] = None
    error: Optional[str] = None

    def mark_status(self, status: TaskStatus) -> None:
        self.status = status
        self.touch()

    def touch(self) -> None:
        self.updated_at = _utcnow()

    def set_result(self, result: Mapping[str, Any]) -> None:
        self.result = dict(result)
        self.error = None
        self.touch()

    def set_error(self, error: Optional[str]) -> None:
        self.error = error
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "type": self.type,
            "payload": dict(self.payload),
            "context": dict(self.context),
            "retry": self.retry.to_dict(),
            "status": self.status.value,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "result": self.result,
            "error": self.error,
        }

    def to_public_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data.setdefault("retry", self.retry.to_dict())
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TaskEnvelope":
        retry = RetryState.from_dict(data.get("retry", {}))
        status = TaskStatus(data.get("status", TaskStatus.PENDING.value))
        created_at_raw = data.get("createdAt")
        updated_at_raw = data.get("updatedAt")
        created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else _utcnow()
        updated_at = datetime.fromisoformat(updated_at_raw) if updated_at_raw else created_at
        return cls(
            task_id=str(data.get("taskId")),
            type=str(data.get("type")),
            payload=dict(data.get("payload") or {}),
            context=dict(data.get("context") or {}),
            retry=retry,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            result=data.get("result"),
            error=data.get("error"),
        )

    @classmethod
    def from_json(cls, raw: str) -> "TaskEnvelope":
        payload = json.loads(raw)
        return cls.from_dict(payload)

    @classmethod
    def new(
        cls,
        *,
        task_type: str,
        payload: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
        retry: Optional[RetryState] = None,
    ) -> "TaskEnvelope":
        return cls(
            task_id=uuid4().hex,
            type=task_type,
            payload=dict(payload),
            context=dict(context or {}),
            retry=retry or RetryState(),
        )

    def clone(self) -> "TaskEnvelope":
        return TaskEnvelope.from_dict(self.to_dict())
