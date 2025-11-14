from __future__ import annotations

"""Telemetry event bus that fans out emitter events to local subscribers."""

import logging
import threading
from typing import Any, Callable, Mapping, MutableMapping, Optional, Sequence, Set

from project_utility.telemetry import emit as telemetry_emit
from project_utility.telemetry import register_listener, unregister_listener

EventListener = Callable[[Mapping[str, Any]], None]

log = logging.getLogger("foundational_service.telemetry.event_bus")


class TelemetryEventBus:
    """Central fan-out bus for telemetry events."""

    def __init__(
        self,
        *,
        register_fn: Callable[[EventListener], None] = register_listener,
        unregister_fn: Callable[[EventListener], None] = unregister_listener,
    ) -> None:
        self._register_fn = register_fn
        self._unregister_fn = unregister_fn
        self._listeners: Set[EventListener] = set()
        self._lock = threading.RLock()
        self._dispatcher_registered = False

    # ------------------------------------------------------------------ subscription API
    def subscribe(self, listener: EventListener) -> None:
        with self._lock:
            self._listeners.add(listener)
            self._ensure_dispatcher()

    def unsubscribe(self, listener: EventListener) -> None:
        with self._lock:
            self._listeners.discard(listener)
            if not self._listeners:
                self._teardown_dispatcher()

    # ------------------------------------------------------------------ emitter bridge
    def _ensure_dispatcher(self) -> None:
        if self._dispatcher_registered:
            return
        self._register_fn(self._dispatch)
        self._dispatcher_registered = True

    def _teardown_dispatcher(self) -> None:
        if not self._dispatcher_registered:
            return
        self._unregister_fn(self._dispatch)
        self._dispatcher_registered = False

    def _dispatch(self, event: Mapping[str, Any]) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:  # pragma: no cover - defensive logging
                log.exception("telemetry listener failed", extra={"event_type": event.get("event_type")})


_EVENT_BUS: Optional[TelemetryEventBus] = None
_EVENT_BUS_LOCK = threading.Lock()


def get_event_bus() -> TelemetryEventBus:
    global _EVENT_BUS
    if _EVENT_BUS is None:
        with _EVENT_BUS_LOCK:
            if _EVENT_BUS is None:
                _EVENT_BUS = TelemetryEventBus()
    return _EVENT_BUS


def publish_event(
    event_type: str,
    *,
    level: str = "info",
    payload: Optional[Mapping[str, Any]] = None,
    sensitive: Optional[Sequence[str]] = None,
    **fields: Any,
) -> None:
    """
    Convenience wrapper that emits structured telemetry events via the global emitter.
    """

    telemetry_emit(
        event_type,
        level=level,
        payload=payload,
        sensitive=sensitive,
        **fields,
    )


__all__ = ["TelemetryEventBus", "get_event_bus", "publish_event"]
