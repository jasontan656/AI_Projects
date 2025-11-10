from __future__ import annotations

"""Capability registry used to gate optional/critical subsystems."""

import asyncio
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Awaitable, Callable, DefaultDict, Dict, Iterable, List, Literal, Optional

from fastapi import HTTPException, status
from project_utility.telemetry import emit as telemetry_emit

CapabilityStatus = Literal["available", "degraded", "unavailable"]
CapabilityListener = Callable[[str, "CapabilityState", Optional["CapabilityState"]], Awaitable[None] | None]


@dataclass
class CapabilityState:
    """Snapshot describing the last known status of a capability."""

    status: CapabilityStatus
    detail: Optional[str] = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: float = 60.0

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["checked_at"] = self.checked_at.isoformat()
        return payload


@dataclass
class CapabilityProbe:
    """Descriptor for a capability checker coroutine."""

    name: str
    checker: Callable[[], Awaitable[CapabilityState]]
    hard: bool = True
    retry_interval: float = 60.0
    base_interval: Optional[float] = None
    max_interval: float = 300.0
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.base_interval is None:
            self.base_interval = max(self.retry_interval, 5.0)
        if self.max_interval < self.base_interval:
            self.max_interval = self.base_interval


def service_unavailable_error(
    capability: str,
    *,
    detail: Optional[str] = None,
    status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
    retry_after: int = 30,
) -> HTTPException:
    payload = {
        "capability": capability,
        "status": "unavailable",
    }
    if detail:
        payload["detail"] = detail
    return HTTPException(
        status_code=status_code,
        detail=payload,
        headers={"Retry-After": str(retry_after)},
    )


class CapabilityRegistry:
    """Thread-safe storage for capability states and probes."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._states: Dict[str, CapabilityState] = {}
        self._probes: Dict[str, CapabilityProbe] = {}
        self._listeners: DefaultDict[str, List[CapabilityListener]] = defaultdict(list)
        self._lock = Lock()
        self._logger = logger or logging.getLogger("interface_entry.capabilities")

    def register_probe(self, probe: CapabilityProbe) -> None:
        with self._lock:
            self._probes[probe.name] = probe

    def iter_probes(self) -> Iterable[CapabilityProbe]:
        with self._lock:
            return tuple(self._probes.values())

    def get_probe(self, name: str) -> Optional[CapabilityProbe]:
        with self._lock:
            return self._probes.get(name)

    def register_listener(self, name: str, callback: CapabilityListener) -> None:
        with self._lock:
            self._listeners[name].append(callback)

    def unregister_listener(self, name: str, callback: CapabilityListener) -> None:
        with self._lock:
            listeners = self._listeners.get(name)
            if not listeners:
                return
            if callback in listeners:
                listeners.remove(callback)
            if not listeners:
                self._listeners.pop(name, None)

    def set_state(self, name: str, state: CapabilityState) -> CapabilityState:
        with self._lock:
            previous = self._states.get(name)
            self._states[name] = state
        if previous is None or previous.status != state.status:
            telemetry_emit(
                "capability.state_changed",
                payload={
                    "capability": name,
                    "status": state.status,
                    "detail": state.detail,
                },
            )
            self._dispatch_listeners(name, state, previous)
        return state

    def get_state(self, name: str) -> Optional[CapabilityState]:
        with self._lock:
            return self._states.get(name)

    def is_available(self, name: str) -> bool:
        state = self.get_state(name)
        return bool(state and state.status == "available")

    def require(self, name: str, *, hard: bool = True) -> CapabilityState:
        state = self.get_state(name)
        if state and state.status == "available":
            return state
        detail = state.detail if state else None
        raise service_unavailable_error(name, detail=detail)

    def snapshot(self) -> Dict[str, Dict[str, object]]:
        with self._lock:
            return {name: state.to_dict() for name, state in self._states.items()}

    def _dispatch_listeners(
        self,
        name: str,
        state: CapabilityState,
        previous: Optional[CapabilityState],
    ) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            telemetry_emit(
                "capability.listener_skipped",
                level="debug",
                payload={"capability": name, "reason": "no_running_loop"},
            )
            return

        listeners: List[CapabilityListener] = []
        with self._lock:
            listeners.extend(self._listeners.get(name, ()))
            listeners.extend(self._listeners.get("*", ()))
        if not listeners:
            return

        def _invoke(callback: CapabilityListener) -> None:
            try:
                result = callback(name, state, previous)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:  # pragma: no cover - listener isolation
                telemetry_emit(
                    "capability.listener_error",
                    level="error",
                    payload={"capability": name},
                )

        for callback in listeners:
            loop.call_soon_threadsafe(_invoke, callback)

    async def run_probe(self, name: str) -> CapabilityState:
        probe = self.get_probe(name)
        if probe is None:
            raise KeyError(f"probe_not_registered:{name}")
        try:
            state = await probe.checker()
        except Exception as exc:  # pragma: no cover - safeguard failed probes
            telemetry_emit(
                "capability.probe_failed",
                level="warning",
                payload={"capability": name, "error": repr(exc)},
            )
            state = CapabilityState(
                status="unavailable",
                detail=str(exc),
                ttl_seconds=probe.retry_interval or 60.0,
            )
        previous = self.get_state(name)
        if previous is None:
            telemetry_emit(
                "startup.capability",
                payload={"capability": name, "status": state.status, "detail": state.detail},
            )
        return self.set_state(name, state)

    async def run_all_probes(self) -> Dict[str, CapabilityState]:
        probes = tuple(self.iter_probes())
        tasks = [self.run_probe(probe.name) for probe in probes]
        results = await asyncio.gather(*tasks)
        return {probe.name: result for probe, result in zip(probes, results)}


__all__ = [
    "CapabilityRegistry",
    "CapabilityProbe",
    "CapabilityState",
    "CapabilityStatus",
    "CapabilityListener",
    "service_unavailable_error",
]
