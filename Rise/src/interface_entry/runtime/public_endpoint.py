from __future__ import annotations

"""Public endpoint probe utilities."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests
from requests import exceptions as req_exc

from interface_entry.runtime.capabilities import CapabilityState
from project_utility.telemetry import emit as telemetry_emit


@dataclass(slots=True)
class PublicEndpointProbe:
    """Perform lightweight HEAD checks to confirm webhook reachability."""

    url: str
    timeout: float = 3.0
    failure_threshold: int = 5
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("interface_entry.public_endpoint_probe"))
    _failure_count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._failure_count = 0

    async def check(self) -> CapabilityState:
        return await asyncio.to_thread(self._check_sync)

    def _check_sync(self) -> CapabilityState:
        if not self.url:
            return CapabilityState(status="unavailable", detail="public_url_missing", ttl_seconds=30.0)
        try:
            response = requests.head(self.url, allow_redirects=False, timeout=self.timeout)
        except req_exc.SSLError as exc:
            return self._record_failure("ssl_error", exc, degraded=True)
        except (req_exc.ConnectTimeout, req_exc.ReadTimeout, req_exc.ConnectionError) as exc:
            return self._record_failure("connection_error", exc, degraded=False)
        except Exception as exc:  # pragma: no cover - defensive guard
            return self._record_failure("unknown_error", exc, degraded=True)

        self._failure_count = 0
        status = "available" if 200 <= response.status_code < 400 else "degraded"
        detail = f"http_status={response.status_code}"
        return CapabilityState(status=status, detail=detail, ttl_seconds=120.0)

    def _record_failure(self, category: str, exc: Exception, *, degraded: bool) -> CapabilityState:
        self._failure_count += 1
        payload = {"category": category, "failures": self._failure_count, "url": self.url}
        if self._failure_count >= self.failure_threshold:
            telemetry_emit(
                "public_endpoint.unreachable",
                level="warning",
                payload={**payload, "error": repr(exc)},
            )
        else:
            telemetry_emit("public_endpoint.retry", payload=payload)
        status = "degraded" if degraded else "unavailable"
        detail = f"{category}:{exc}"
        ttl = 90.0 if degraded else 45.0
        return CapabilityState(status=status, detail=detail, ttl_seconds=ttl)


__all__ = ["PublicEndpointProbe"]
