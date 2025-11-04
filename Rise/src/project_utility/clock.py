"""
Timezone helpers for Rise services.

All runtime timestamps route through this module to ensure they are rendered in the Asia/Manila
timezone. The implementation intentionally mirrors the legacy `shared_utility.timezone` module but
is colocated in the project utility layer.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from typing import Optional

try:  # pragma: no cover - Windows environments may lack tzdata
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except Exception:  # pragma: no cover - fall back to a fixed offset if zoneinfo fails
    ZoneInfo = None  # type: ignore[assignment]

    class ZoneInfoNotFoundError(Exception):
        """Stub fallback when zoneinfo database is unavailable."""


def _resolve_ph_timezone() -> tzinfo:
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Manila")  # type: ignore[call-arg]
        except ZoneInfoNotFoundError:
            pass
    return timezone(timedelta(hours=8))


_PH_TIME_ZONE = _resolve_ph_timezone()


def philippine_time_zone() -> tzinfo:
    """Return the canonical Asia/Manila time zone instance."""

    return _PH_TIME_ZONE


def philippine_now() -> datetime:
    """Current aware datetime in Asia/Manila."""

    return datetime.now(_PH_TIME_ZONE)


def ensure_philippine(dt: datetime) -> datetime:
    """Convert any datetime into Asia/Manila, defaulting naive values."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=_PH_TIME_ZONE)
    return dt.astimezone(_PH_TIME_ZONE)


def philippine_iso(dt: Optional[datetime] = None) -> str:
    """Render ISO-8601 string in Asia/Manila with explicit offset."""

    target = ensure_philippine(dt or philippine_now())
    return target.isoformat()


def philippine_from_timestamp(timestamp: float) -> datetime:
    """Build Asia/Manila datetime from POSIX timestamp seconds."""

    return datetime.fromtimestamp(timestamp, tz=_PH_TIME_ZONE)


__all__ = [
    "ZoneInfoNotFoundError",
    "ensure_philippine",
    "philippine_from_timestamp",
    "philippine_iso",
    "philippine_now",
    "philippine_time_zone",
]
