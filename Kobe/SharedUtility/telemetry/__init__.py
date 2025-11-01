"""Telemetry package for UnifiedCS reasoning pipeline."""

from __future__ import annotations

from functools import lru_cache

from .bus import TelemetryBus
from .config import load_telemetry_config


@lru_cache(maxsize=1)
def get_telemetry_bus() -> TelemetryBus:
    """Return a singleton TelemetryBus instance."""

    config = load_telemetry_config()
    return TelemetryBus(config=config)


__all__ = ["get_telemetry_bus", "TelemetryBus"]
