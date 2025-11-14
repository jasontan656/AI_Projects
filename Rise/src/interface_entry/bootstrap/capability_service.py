from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import FastAPI

from foundational_service.bootstrap.webhook import behavior_webhook_startup
from foundational_service.integrations.telegram_client import TelegramClientError
from foundational_service.messaging.channel_binding_event_publisher import get_channel_binding_event_publisher
from foundational_service.observability.public_endpoint_probe import PublicEndpointSecurityProbe
from interface_entry.bootstrap.startup_housekeeping import format_endpoint_detail
from interface_entry.runtime.capabilities import CapabilityProbe, CapabilityRegistry, CapabilityState
from interface_entry.runtime.public_endpoint import PublicEndpointProbe
from project_utility.context import ContextBridge
from project_utility.db.redis import get_async_redis


@dataclass(slots=True)
class CapabilityServiceConfig:
    public_url: str
    webhook_path: str
    webhook_secret: str
    telegram_token: str
    telegram_probe_mode: str
    redis_url: Optional[str]


class CapabilityService:
    def __init__(self, app: FastAPI, log: logging.Logger, config: CapabilityServiceConfig) -> None:
        self.app = app
        self.log = log
        self.config = config
        from interface_entry.http.dependencies import set_capability_registry

        self.registry = CapabilityRegistry(logger=log)
        self.app.state.capabilities = self.registry
        self.app.state.webhook_security = None
        set_capability_registry(self.registry)
        self._webhook_security_probe: Optional[PublicEndpointSecurityProbe] = None
        self._public_endpoint_probe: Optional[PublicEndpointProbe] = None

    def register_core_probes(self) -> None:
        self._register_mongo_probe()
        self._register_redis_probe()
        self._register_rabbitmq_probe()
        self._register_telegram_probe()
        self._register_public_endpoint_probe()

    def register_webhook_probe(self, bootstrap_state: Any) -> None:
        async def _probe_telegram_webhook() -> CapabilityState:
            mode = self.config.telegram_probe_mode
            if mode == "skip":
                self.log.warning(
                    "startup.telegram_webhook.skipped",
                    extra={"mode": mode, "reason": "probe explicitly disabled"},
                )
                return CapabilityState(status="degraded", detail="probe skipped", ttl_seconds=300.0)
            public_state = self.registry.get_state("public_endpoint")
            if public_state and public_state.status != "available":
                detail = f"blocked_by_public_endpoint:{public_state.detail or public_state.status}"
                ttl = min(300.0, public_state.ttl_seconds)
                return CapabilityState(status="degraded", detail=detail, ttl_seconds=ttl)
            try:
                self.log.info(
                    "startup.step",
                    extra={
                        "step": "behavior_webhook_startup.invoke",
                        "description": "Registering webhook with Telegram",
                    },
                )
                startup_meta = await behavior_webhook_startup(
                    bootstrap_state.bot,
                    f"{self.config.public_url.rstrip('/')}{self.config.webhook_path}",
                    self.config.webhook_secret,
                    drop_pending_updates=False,
                )
                for prompt in startup_meta.get("prompt_events", []):
                    self.log.warning(
                        "webhook.prompt.retry",
                        extra={
                            "prompt_id": prompt.get("prompt_id"),
                            "prompt_text": prompt.get("prompt_text", ""),
                            "request_id": ContextBridge.request_id(),
                            "retry": prompt.get("prompt_variables", {}).get("retry"),
                        },
                    )
                self.log.info(
                    "startup.complete",
                    extra={
                        "description": "Application ready",
                        "router": bootstrap_state.router.name,
                        "stages": startup_meta.get("telemetry", {}).get("stages", []),
                        "bootstrapped_request_id": startup_meta.get("telemetry", {}).get("request_id"),
                    },
                )
                return CapabilityState(status="available", ttl_seconds=300.0)
            except Exception as exc:  # pragma: no cover - network/env dependent
                self.log.warning(
                    "startup.telegram_webhook.degraded",
                    extra={"mode": mode, "error": repr(exc)},
                )
                return CapabilityState(status="degraded", detail=str(exc), ttl_seconds=180.0)

        self.registry.register_probe(
            CapabilityProbe(
                "telegram_webhook",
                _probe_telegram_webhook,
                hard=False,
                retry_interval=300.0,
                base_interval=180.0,
                max_interval=600.0,
                multiplier=1.2,
            )
        )

    def _register_mongo_probe(self) -> None:
        async def _probe_mongo() -> CapabilityState:
            mongo_uri = os.getenv("MONGODB_URI")
            if not mongo_uri:
                return CapabilityState(status="unavailable", detail="MONGODB_URI not configured", ttl_seconds=30.0)
            from motor.motor_asyncio import AsyncIOMotorClient

            endpoint_detail = format_endpoint_detail(mongo_uri)
            client = AsyncIOMotorClient(mongo_uri, tz_aware=True, serverSelectionTimeoutMS=3000)
            try:
                await asyncio.wait_for(client.admin.command("ping"), timeout=5.0)
                return CapabilityState(status="available", ttl_seconds=60.0, detail=endpoint_detail)
            except Exception as exc:  # pragma: no cover - network/env specific
                return CapabilityState(status="unavailable", detail=f"{endpoint_detail}: {exc}", ttl_seconds=30.0)
            finally:
                client.close()

        self.registry.register_probe(
            CapabilityProbe(
                "mongo",
                _probe_mongo,
                hard=True,
                retry_interval=60.0,
                base_interval=45.0,
                max_interval=300.0,
                multiplier=1.5,
            )
        )

    def _register_redis_probe(self) -> None:
        async def _probe_redis() -> CapabilityState:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                return CapabilityState(status="unavailable", detail="REDIS_URL not configured", ttl_seconds=30.0)
            from redis.asyncio import Redis  # type: ignore[import]

            client = Redis.from_url(redis_url)
            try:
                await asyncio.wait_for(client.ping(), timeout=3.0)
                return CapabilityState(status="available", ttl_seconds=30.0, detail=format_endpoint_detail(redis_url))
            except Exception as exc:  # pragma: no cover - network/env specific
                return CapabilityState(
                    status="unavailable",
                    detail=f"{format_endpoint_detail(redis_url)}: {exc}",
                    ttl_seconds=15.0,
                )
            finally:
                with suppress(Exception):
                    await client.close()

        self.registry.register_probe(
            CapabilityProbe(
                "redis",
                _probe_redis,
                hard=True,
                retry_interval=30.0,
                base_interval=15.0,
                max_interval=180.0,
                multiplier=1.6,
            )
        )

    def _register_rabbitmq_probe(self) -> None:
        async def _probe_rabbitmq() -> CapabilityState:
            rabbit_url = os.getenv("RABBITMQ_URL")
            if not rabbit_url:
                return CapabilityState(status="unavailable", detail="RABBITMQ_URL not configured", ttl_seconds=30.0)
            import aio_pika  # type: ignore[import]

            endpoint_detail = format_endpoint_detail(rabbit_url)
            try:
                connection = await aio_pika.connect_robust(rabbit_url, timeout=5)
            except Exception as exc:  # pragma: no cover - network/env specific
                return CapabilityState(status="unavailable", detail=f"{endpoint_detail}: {exc}", ttl_seconds=20.0)
            else:
                await connection.close()
                return CapabilityState(status="available", ttl_seconds=45.0, detail=endpoint_detail)

        self.registry.register_probe(
            CapabilityProbe(
                "rabbitmq",
                _probe_rabbitmq,
                hard=True,
                retry_interval=45.0,
                base_interval=30.0,
                max_interval=240.0,
                multiplier=1.4,
            )
        )

    def _register_telegram_probe(self) -> None:
        async def _probe_telegram() -> CapabilityState:
            from interface_entry.http.dependencies import prime_telegram_client

            probe_mode = self.config.telegram_probe_mode
            if probe_mode == "skip":
                return CapabilityState(status="available", detail="probe_skipped", ttl_seconds=180.0)
            token = self.config.telegram_token
            if not token:
                return CapabilityState(status="unavailable", detail="TELEGRAM_BOT_TOKEN missing", ttl_seconds=60.0)
            try:
                client = prime_telegram_client()
            except Exception as exc:  # pragma: no cover - defensive logging
                return CapabilityState(status="unavailable", detail=f"client_init_failed:{exc}", ttl_seconds=45.0)
            trace_id = f"capability:telegram:{os.getpid()}"
            try:
                await client.get_bot_info(token, trace_id=trace_id)
                return CapabilityState(status="available", ttl_seconds=45.0, detail="bot_ready")
            except TelegramClientError as exc:
                status_value = "degraded" if exc.code in {"RATE_LIMIT", "NETWORK_FAILURE"} else "unavailable"
                ttl_seconds = 30.0 if status_value == "unavailable" else 45.0
                detail = f"{exc.code}:{exc.message}"
                return CapabilityState(status=status_value, detail=detail, ttl_seconds=ttl_seconds)
            except Exception as exc:  # pragma: no cover - network/env specific
                return CapabilityState(status="unavailable", detail=str(exc), ttl_seconds=30.0)

        self.registry.register_probe(
            CapabilityProbe(
                "telegram",
                _probe_telegram,
                hard=False,
                retry_interval=40.0,
                base_interval=25.0,
                max_interval=240.0,
                multiplier=1.5,
            )
        )

    def _register_public_endpoint_probe(self) -> None:
        webhook_security_probe: Optional[PublicEndpointSecurityProbe] = None
        try:
            webhook_security_probe = PublicEndpointSecurityProbe(
                redis=get_async_redis(),
                logger=self.log,
                publisher=get_channel_binding_event_publisher(),
            )
        except Exception as exc:  # pragma: no cover - defensive
            self.log.warning(
                "startup.webhook_security_probe_unavailable",
                extra={"error": str(exc)},
            )

        public_endpoint_probe = PublicEndpointProbe(url=self.config.public_url, timeout=3.0, logger=self.log)
        self._webhook_security_probe = webhook_security_probe
        self._public_endpoint_probe = public_endpoint_probe

        async def _public_endpoint_wrapper() -> CapabilityState:
            state = await public_endpoint_probe.check()
            if webhook_security_probe is None:
                return state
            try:
                snapshot = await webhook_security_probe.inspect(
                    workflow_id="service:telegram",
                    channel="telegram",
                    endpoint=self.config.public_url,
                    secret=self.config.webhook_secret,
                )
                self.app.state.webhook_security = snapshot.to_dict()
            except Exception as exc:
                self.log.warning(
                    "webhook_security.observe_failed",
                    extra={"error": str(exc)},
                )
            return state

        self.registry.register_probe(
            CapabilityProbe(
                "public_endpoint",
                _public_endpoint_wrapper,
                hard=False,
                retry_interval=60.0,
                base_interval=30.0,
                max_interval=300.0,
                multiplier=1.5,
            )
        )


def snapshot_capabilities(app: FastAPI) -> Dict[str, Dict[str, object]]:
    registry: Optional[CapabilityRegistry] = getattr(app.state, "capabilities", None)
    if registry is None:
        return {}
    return registry.snapshot()


def derive_health_status(snapshot: Dict[str, Dict[str, object]]) -> str:
    if any(state.get("status") == "unavailable" for state in snapshot.values()):
        return "unavailable"
    if any(state.get("status") == "degraded" for state in snapshot.values()):
        return "degraded"
    return "ok" if snapshot else "unknown"
