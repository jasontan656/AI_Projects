"""Time utilities providing timezone-aware timestamps."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid


class Time:
    """Centralized time helpers abiding by the project constitution."""

    _TIMESTAMP_PATTERN = "%Y%m%dT%H%M%S"

    @classmethod
    def now(cls) -> datetime:
        """Return the current datetime in UTC."""
        return datetime.now(timezone.utc)

    @classmethod
    def now_plus(cls, delta: timedelta) -> datetime:
        """Return the current UTC datetime plus the provided delta."""
        if not isinstance(delta, timedelta):
            raise TypeError("delta must be a datetime.timedelta instance")
        return cls.now() + delta

    @classmethod
    def timestamp(cls) -> str:
        """Return a constitution-compliant timestamp+uuid identifier."""
        current_time = cls.now()
        timestamp_part = current_time.strftime("%Y%m%dT%H%M%S")
        offset = current_time.strftime("%z")
        if offset.startswith("+") or offset.startswith("-"):
            offset = offset[1:]
        uuid_part = uuid.uuid4().hex
        return f"{timestamp_part}{offset}{uuid_part}"


__all__ = ["Time"]
