from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import shutil
from contextlib import suppress
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI, HTTPException, Response, status
from starlette.middleware.cors import CORSMiddleware

from business_logic import KnowledgeSnapshotOrchestrator
from business_service import KnowledgeSnapshotService
from business_service.channel.health_store import ChannelBindingHealthStore
from business_service.channel.repository import AsyncWorkflowChannelRepository
from business_service.channel.service import WorkflowChannelService
from business_service.conversation import service as conversation_service_module
from business_service.workflow import AsyncWorkflowRepository
from foundational_service.bootstrap.webhook import behavior_webhook_startup
from foundational_service.contracts.registry import BehaviorContract, behavior_top_entry
from project_utility.context import ContextBridge
from project_utility.config.paths import get_log_root, get_repo_root
from project_utility.logging import (
    configure_logging,
    finalize_log_workspace,
    initialize_log_workspace,
)
from interface_entry.config.manifest_loader import load_doc_context, load_top_entry_manifest
from interface_entry.http.dependencies import (
    application_lifespan,
    get_mongo_client,
    get_settings,
    get_task_runtime,
    get_task_runtime_if_enabled,
    get_telegram_client,
    set_capability_registry,
    set_channel_binding_registry,
    shutdown_task_runtime,
)
from interface_entry.http.errors import http_exception_handler, unhandled_exception_handler
from interface_entry.http.middleware import FastAPIRequestIDMiddleware, LoggingMiddleware
from interface_entry.http.channels import get_router as get_channel_router
from interface_entry.http.pipeline_nodes import get_router as get_pipeline_node_router
from interface_entry.http.prompts import get_router as get_prompt_router
from interface_entry.http.stages import get_router as get_stage_router
from interface_entry.http.tools import get_router as get_tool_router
from interface_entry.http.workflows import get_router as get_workflow_router
from interface_entry.middleware.signature import SignatureVerifyMiddleware
from interface_entry.telegram.channel_binding_provider import (
    CompositeChannelBindingProvider,
    DispatcherChannelBindingProvider,
)
from interface_entry.telegram.runtime import bootstrap_aiogram_service, get_bootstrap_metadata
from interface_entry.telegram.routes import register_routes
from foundational_service.persist.controllers import build_task_admin_router
from foundational_service.persist.worker import TaskRuntime
from foundational_service.telemetry.bus import TelemetryConsoleSubscriber, build_console_subscriber
from foundational_service.messaging.channel_binding_event_publisher import get_channel_binding_event_publisher
from foundational_service.telemetry.config import load_telemetry_config
from interface_entry.runtime.capabilities import CapabilityProbe, CapabilityRegistry, CapabilityState
from interface_entry.runtime.channel_binding_event_replayer import ChannelBindingEventReplayer
from interface_entry.runtime.public_endpoint import PublicEndpointProbe
from interface_entry.runtime.supervisors import RuntimeSupervisor

from dotenv import load_dotenv  # type: ignore[import]


REPO_ROOT = get_repo_root()

load_dotenv(dotenv_path=str(REPO_ROOT / ".env"))


log = logging.getLogger("interface_entry.app")

REPO_ROOT = get_repo_root()
load_dotenv(dotenv_path=str(REPO_ROOT / ".env"))

WEBHOOK_PATH = "/telegram/webhook"
TOP_ENTRY_MANIFEST = load_top_entry_manifest()
DOC_CONTEXT = load_doc_context()
DOC_ID = DOC_CONTEXT["doc_id"]
DOC_COMMIT = DOC_CONTEXT["doc_commit"]

_telemetry_console_subscriber: Optional[TelemetryConsoleSubscriber] = None


class TelegramWebhookUnavailableError(RuntimeError):
    """Raised when Telegram webhook cannot be reached during startup."""


def _sanitize_endpoint(raw: str) -> str:
    if "@" in raw:
        return raw.split("@", 1)[1]
    return raw


def _format_endpoint_detail(uri: Optional[str]) -> str:
    return f"endpoint={_sanitize_endpoint(uri or 'unknown')}"


def _override_uri_host(uri: str, host: str) -> str:
    parsed = urlparse(uri)
    hostname = parsed.hostname
    if not hostname:
        return uri
    # Avoid touching multi-host connection strings.
    if "," in parsed.netloc:
        return uri
    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth += f":{parsed.password}"
        auth += "@"
    port_segment = f":{parsed.port}" if parsed.port else ""
    host_literal = host
    if ":" in host_literal and not host_literal.startswith("["):
        host_literal = f"[{host_literal}]"
    new_netloc = f"{auth}{host_literal}{port_segment}"
    return urlunparse(parsed._replace(netloc=new_netloc))


def _apply_host_override_env(env_key: str, override_host: Optional[str], *, service: str) -> None:
    if not override_host:
        return
    uri = os.getenv(env_key)
    if not uri:
        return
    try:
        updated = _override_uri_host(uri, override_host)
    except Exception as exc:  # pragma: no cover - defensive guard
        logging.getLogger("interface_entry.app").warning(
            "startup.service_host_override_failed",
            extra={"service": service, "error": str(exc)},
        )
        return
    if updated != uri:
        os.environ[env_key] = updated
        logging.getLogger("interface_entry.app").info(
            "startup.service_host_override",
            extra={"service": service, "host": override_host},
        )


from interface_entry.bootstrap.channel_binding_bootstrap import (
    channel_binding_lifespan,
    prime_channel_binding_registry,
)
from interface_entry.bootstrap.runtime_lifespan import configure_runtime_lifespan

def release_logging_handlers() -> None:
    logging.shutdown()
    logger_names = [None, *list(logging.root.manager.loggerDict.keys())]
    for name in logger_names:
        logger = logging.getLogger(name) if name else logging.getLogger()
        for handler in list(logger.handlers):
            with suppress(Exception):
                handler.flush()
            with suppress(Exception):
                handler.close()
            logger.removeHandler(handler)


def perform_clean_startup() -> None:
    release_logging_handlers()
    log_root = initialize_log_workspace()
    configure_logging()
    log.info("startup.clean.begin")
    issues: List[str] = []

    log.info(
        "startup.clean.segment.begin",
        extra={"segment": "logs", "path": str(log_root)},
    )
    log.info(
        "startup.clean.segment.ready",
        extra={"segment": "logs", "path": str(log_root), "mode": "workspace"},
    )

    directories = {
        "runtime_state": REPO_ROOT / "openai_agents" / "agent_contract" / "runtime_state",
    }
    for label, target in directories.items():
        try:
            log.info(
                "startup.clean.segment.begin",
                extra={"segment": label, "path": str(target)},
            )
            if target.exists():
                log.info(
                    "startup.clean.segment.removing",
                    extra={"segment": label, "path": str(target)},
                )
                shutil.rmtree(target)
                log.info(
                    "startup.clean.segment.removed",
                    extra={"segment": label, "path": str(target)},
                )
            target.mkdir(parents=True, exist_ok=True)
            log.info(
                "startup.clean.segment.ready",
                extra={"segment": label, "path": str(target)},
            )
        except Exception as exc:  # pragma: no cover - surface filesystem failures immediately
            issues.append(f"{label}: {exc}")
            log.error(
                "startup.clean.segment_failed",
                extra={"segment": label, "error": repr(exc)},
            )

    def _execute(label: str, func: Callable[[], None]) -> None:
        try:
            log.info("startup.clean.segment.begin", extra={"segment": label})
            func()
            log.info("startup.clean.segment.ready", extra={"segment": label})
        except Exception as exc:  # pragma: no cover - propagate external service errors
            issues.append(f"{label}: {exc}")
            log.error(
                "startup.clean.segment_failed",
                extra={"segment": label, "error": repr(exc)},
            )

    _execute("redis", _purge_redis_store)
    _execute("mongodb", _purge_mongo_store)

    final_status = "ok" if not issues else "failed"
    log.info("startup.clean.status", extra={"status": final_status, "issues": issues})

    if issues:
        raise RuntimeError("startup_clean_failed: " + "; ".join(issues))

    log.info("startup.clean.complete")


def _purge_redis_store() -> None:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL not configured")

    from redis import Redis  # type: ignore[import]

    redis_client = Redis.from_url(redis_url)
    redis_client.flushall()
    log.info("startup.clean.redis", extra={"endpoint": _sanitize_endpoint(redis_url)})


def _purge_mongo_store() -> None:
    mongo_uri = os.getenv("MONGODB_URI")
    mongo_db = os.getenv("MONGODB_DATABASE")
    if not mongo_uri or not mongo_db:
        missing = "MONGODB_URI" if not mongo_uri else "MONGODB_DATABASE"
        raise RuntimeError(f"{missing} not configured")

    from pymongo import MongoClient  # type: ignore[import]

    client = MongoClient(mongo_uri)
    try:
        db = client[mongo_db]
        collections: List[str] = db.list_collection_names()
        for collection_name in collections:
            db[collection_name].delete_many({})
        log.info(
            "startup.clean.mongodb",
            extra={
                "endpoint": _sanitize_endpoint(mongo_uri),
                "database": mongo_db,
                "collections": collections,
            },
        )
    finally:
        with suppress(Exception):
            client.close()


def _env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        if name == "TELEGRAM_BOT_TOKEN":
            raise RuntimeError("bootstrap_refused_missing_token")
        raise RuntimeError(f"missing required environment variable: {name}")
    return value or ""


def configure_application(app: FastAPI) -> FastAPI:
    initialize_log_workspace()
    configure_logging()
    telemetry_config = load_telemetry_config()
    subscriber = build_console_subscriber(telemetry_config)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_middleware(FastAPIRequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SignatureVerifyMiddleware, webhook_path=WEBHOOK_PATH)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    capability_registry = CapabilityRegistry(logger=log)
    app.state.capabilities = capability_registry
    set_capability_registry(capability_registry)
    app.state.telemetry_console_subscriber = subscriber
    global _telemetry_console_subscriber
    _telemetry_console_subscriber = subscriber

    docker_bridge_host = os.getenv("DOCKER_HOST_BRIDGE")
    _apply_host_override_env("MONGODB_URI", os.getenv("MONGODB_HOST_OVERRIDE") or docker_bridge_host, service="mongo")
    _apply_host_override_env("REDIS_URL", os.getenv("REDIS_HOST_OVERRIDE") or docker_bridge_host, service="redis")
    _apply_host_override_env("RABBITMQ_URL", os.getenv("RABBITMQ_HOST_OVERRIDE") or docker_bridge_host, service="rabbitmq")

    token = _env("TELEGRAM_BOT_TOKEN")
    webhook_secret = _env("TELEGRAM_BOT_SECRETS")
    public_url = _env("WEB_HOOK")
    redis_url = os.getenv("REDIS_URL")
    telegram_probe_mode = (os.getenv("TELEGRAM_PROBE_MODE") or "webhook").strip().lower()
    allowed_probe_modes = {"webhook", "skip"}
    if telegram_probe_mode not in allowed_probe_modes:
        log.error(
            "startup.telegram_probe_mode.invalid",
            extra={"provided": telegram_probe_mode, "allowed": sorted(allowed_probe_modes)},
        )
        raise RuntimeError("unsupported TELEGRAM_PROBE_MODE")
    telegram_proxy_url = os.getenv("TELEGRAM_PROXY_URL")
    telegram_proxy_user = os.getenv("TELEGRAM_PROXY_USER")
    telegram_proxy_pass = os.getenv("TELEGRAM_PROXY_PASS")
    if telegram_proxy_url:
        proxy_uri = telegram_proxy_url
        if telegram_proxy_user or telegram_proxy_pass:
            parsed = urlparse(telegram_proxy_url)
            username = telegram_proxy_user or parsed.username or ""
            password = telegram_proxy_pass or parsed.password or ""
            hostname = parsed.hostname or ""
            port_segment = f":{parsed.port}" if parsed.port else ""
            auth_segment = ""
            if username or password:
                auth_segment = f"{username}:{password}@"
            proxy_uri = urlunparse(
                (
                    parsed.scheme or "http",
                    f"{auth_segment}{hostname}{port_segment}",
                    parsed.path or "",
                    parsed.params or "",
                    parsed.query or "",
                    parsed.fragment or "",
                )
            )
        os.environ.setdefault("HTTPS_PROXY", proxy_uri)
        os.environ.setdefault("HTTP_PROXY", proxy_uri)
    if not public_url.lower().startswith("https://"):
        log.error("startup.insecure_webhook", extra={"public_url": public_url})
        raise RuntimeError("bootstrap_refused_insecure_webhook")

    def _log_startup_step(step: str, description: str, **metadata: Any) -> None:
        log.info("startup.step", extra={"step": step, "description": description, **metadata})

    async def _probe_mongo() -> CapabilityState:
        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            return CapabilityState(status="unavailable", detail="MONGODB_URI not configured", ttl_seconds=30.0)
        from motor.motor_asyncio import AsyncIOMotorClient

        endpoint_detail = _format_endpoint_detail(mongo_uri)
        client = AsyncIOMotorClient(mongo_uri, tz_aware=True, serverSelectionTimeoutMS=3000)
        try:
            await asyncio.wait_for(client.admin.command("ping"), timeout=5.0)
            return CapabilityState(status="available", ttl_seconds=60.0, detail=endpoint_detail)
        except Exception as exc:  # pragma: no cover - network/env specific
            return CapabilityState(status="unavailable", detail=f"{endpoint_detail}: {exc}", ttl_seconds=30.0)
        finally:
            client.close()

    async def _probe_redis() -> CapabilityState:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return CapabilityState(status="unavailable", detail="REDIS_URL not configured", ttl_seconds=30.0)
        from redis.asyncio import Redis  # type: ignore[import]

        client = Redis.from_url(redis_url)
        try:
            await asyncio.wait_for(client.ping(), timeout=3.0)
            return CapabilityState(status="available", ttl_seconds=30.0, detail=_format_endpoint_detail(redis_url))
        except Exception as exc:  # pragma: no cover - network/env specific
            return CapabilityState(
                status="unavailable",
                detail=f"{_format_endpoint_detail(redis_url)}: {exc}",
                ttl_seconds=15.0,
            )
        finally:
            with suppress(Exception):
                await client.close()

    async def _probe_rabbitmq() -> CapabilityState:
        rabbit_url = os.getenv("RABBITMQ_URL")
        if not rabbit_url:
            return CapabilityState(status="unavailable", detail="RABBITMQ_URL not configured", ttl_seconds=30.0)
        import aio_pika  # type: ignore[import]

        endpoint_detail = _format_endpoint_detail(rabbit_url)
        try:
            connection = await aio_pika.connect_robust(rabbit_url, timeout=5)
        except Exception as exc:  # pragma: no cover - network/env specific
            return CapabilityState(status="unavailable", detail=f"{endpoint_detail}: {exc}", ttl_seconds=20.0)
        else:
            await connection.close()
            return CapabilityState(status="available", ttl_seconds=45.0, detail=endpoint_detail)

    capability_registry.register_probe(
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
    capability_registry.register_probe(
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
    capability_registry.register_probe(
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

    public_endpoint_probe = PublicEndpointProbe(url=public_url, timeout=3.0, logger=log)
    capability_registry.register_probe(
        CapabilityProbe(
            "public_endpoint",
            public_endpoint_probe.check,
            hard=False,
            retry_interval=60.0,
            base_interval=30.0,
            max_interval=300.0,
            multiplier=1.5,
        )
    )

    _log_startup_step(
        "bootstrap_aiogram.start",
        "Initialising aiogram bootstrap sequence",
    )

    bootstrap_state = bootstrap_aiogram_service(
        api_token=token,
        webhook_url=WEBHOOK_PATH,
        redis_url=redis_url,
        fastapi_app=None,
    )
    _log_startup_step(
        "bootstrap_aiogram.complete",
        "Aiogram bootstrap finished",
        router=bootstrap_state.router.name,
    )
    metadata = get_bootstrap_metadata()
    policy: Dict[str, Any] = metadata["policy"]
    metrics_state: Dict[str, Any] = metadata["metrics"]
    telemetry = metadata["telemetry"]
    bootstrap_redis_runtime: Dict[str, Any] = metadata.get("redis", {}) or {}
    redis_runtime: Dict[str, Any] = dict(bootstrap_redis_runtime)
    redis_active = bool(redis_runtime.get("available"))

    contract = BehaviorContract()
    top_entry_validation = behavior_top_entry(TOP_ENTRY_MANIFEST, app=app)
    app.state.top_entry_manifest = top_entry_validation

    def configure_policy(policy_obj: dict[str, object]) -> None:
        app.state.runtime_policy = policy_obj

    setattr(app, "configure_policy", configure_policy)
    _log_startup_step("behavior_contract.apply", "Applying behavior contract")
    contract.apply_contract(app)
    app.state.doc_context = {"doc_id": DOC_ID, "doc_commit": DOC_COMMIT}
    app.state.runtime_policy = policy
    app.state.bootstrap_metrics = metrics_state
    app.state.webhook_secret = webhook_secret
    app.state.public_url = public_url
    app.state.telegram = bootstrap_state
    app.state.telegram_metrics = metrics_state
    app.state.asset_guard = metadata.get("asset_guard")
    app.state.redis_runtime = redis_runtime

    conversation_service_module.set_task_queue_accessors(
        submitter_factory=lambda: get_task_runtime().submitter,
        runtime_factory=get_task_runtime,
    )
    channel_binding_registry = prime_channel_binding_registry()
    app.state.channel_binding_registry = channel_binding_registry
    set_channel_binding_registry(channel_binding_registry)
    dispatcher_provider = DispatcherChannelBindingProvider(bootstrap_state.dispatcher)
    binding_provider = CompositeChannelBindingProvider(dispatcher_provider, channel_binding_registry)
    conversation_service_module.set_channel_binding_provider(binding_provider)
    channel_binding_registry.attach_dispatcher(bootstrap_state.dispatcher)
    channel_binding_health_store = ChannelBindingHealthStore()
    app.state.channel_binding_health_store = channel_binding_health_store
    conversation_service_module.set_channel_binding_health_store(channel_binding_health_store)

    channel_binding_event_publisher = get_channel_binding_event_publisher()
    app.state.channel_binding_event_publisher = channel_binding_event_publisher
    channel_binding_event_replayer = ChannelBindingEventReplayer(channel_binding_event_publisher)
    app.state.channel_binding_event_replayer = channel_binding_event_replayer

    redis_primary_hint = bool(redis_url)
    _log_startup_step("memory_loader.start", "Loading KnowledgeBase snapshot")
    knowledge_service = KnowledgeSnapshotService(
        base_path=REPO_ROOT / "KnowledgeBase",
        org_index_path=REPO_ROOT / "KnowledgeBase" / "KnowledgeBase_index.yaml",
        redis_url=redis_url,
        redis_prefix="rise:kb",
        redis_primary=redis_primary_hint,
        redis_metadata=redis_runtime,
        capability_lookup=capability_registry.get_state,
    )
    knowledge_orchestrator = KnowledgeSnapshotOrchestrator(knowledge_service)
    snapshot_state = knowledge_orchestrator.load()
    app.state.knowledge_snapshot_orchestrator = knowledge_orchestrator

    async def _redis_backfill(reason: str) -> None:
        await asyncio.to_thread(knowledge_service.backfill_to_redis, reason=reason)
        replayer = getattr(app.state, "channel_binding_event_replayer", None)
        if replayer is not None:
            await replayer.replay_pending()

    runtime_supervisor = RuntimeSupervisor(
        registry=capability_registry,
        redis_backfill=_redis_backfill,
        logger=log,
        binding_replayer=channel_binding_event_replayer,
        binding_replayer_interval=5.0,
    )
    app.state.runtime_supervisor = runtime_supervisor

    configure_runtime_lifespan(
        app,
        capability_registry=capability_registry,
        runtime_supervisor=runtime_supervisor,
        application_lifespan=application_lifespan,
        log=log,
        extra_contexts=(channel_binding_lifespan,),
    )

    def _legacy_refresh(reason: str = "manual") -> Dict[str, Any]:
        refreshed_state = knowledge_orchestrator.refresh(reason)
        return refreshed_state.to_legacy_dict()

    app.state.memory_loader = {"refresh": _legacy_refresh}
    app.state.memory_snapshot_obj = snapshot_state.snapshot
    app.state.memory_snapshot = snapshot_state.snapshot_dict
    app.state.memory_snapshot_status = snapshot_state.status
    app.state.memory_snapshot_telemetry = snapshot_state.telemetry
    app.state.memory_snapshot_health = snapshot_state.health
    app.state.memory_snapshot_missing_agencies = list(snapshot_state.missing_agencies)
    loader_metadata = dict(snapshot_state.metadata)
    app.state.memory_loader_metadata = loader_metadata
    latest_redis_runtime = loader_metadata.get("redis", {})
    if isinstance(latest_redis_runtime, dict):
        redis_runtime = latest_redis_runtime
        redis_active = bool(redis_runtime.get("available"))
        app.state.redis_runtime = redis_runtime
    else:
        redis_active = bool(redis_runtime.get("available"))
    app.state.memory_backend = redis_runtime
    _log_startup_step(
        "memory_loader.complete",
        "KnowledgeBase snapshot ready",
        status=snapshot_state.status,
        redis_primary=redis_active,
    )

    def refresh_memory_snapshot(refresh_reason: str = "manual") -> Dict[str, Any]:
        refreshed_state = knowledge_orchestrator.refresh(refresh_reason)
        app.state.memory_snapshot_obj = refreshed_state.snapshot
        app.state.memory_snapshot = refreshed_state.snapshot_dict
        app.state.memory_snapshot_status = refreshed_state.status
        app.state.memory_snapshot_telemetry = refreshed_state.telemetry
        app.state.memory_snapshot_health = refreshed_state.health
        app.state.memory_snapshot_missing_agencies = list(refreshed_state.missing_agencies)
        app.state.memory_loader_metadata = dict(refreshed_state.metadata)
        app.state.memory_backend = refreshed_state.metadata.get("redis", {})
        return refreshed_state.to_legacy_dict()

    app.state.memory_snapshot_refresh = refresh_memory_snapshot

    _log_startup_step("register_routes", "Registering Telegram routes")
    register_routes(app, bootstrap_state.dispatcher, WEBHOOK_PATH, policy, webhook_secret)
    app.include_router(get_pipeline_node_router())
    app.include_router(get_prompt_router())
    app.include_router(get_tool_router())
    app.include_router(get_stage_router())
    app.include_router(get_workflow_router())
    app.include_router(get_channel_router())

    def _task_runtime_provider() -> Optional[TaskRuntime]:
        return get_task_runtime_if_enabled()

    app.include_router(build_task_admin_router(_task_runtime_provider))

    _log_startup_step(
        "bootstrap.complete",
        "bootstrap_aiogram_service completed",
        redis_enabled=redis_active,
        router=bootstrap_state.router.name,
    )

    async def _probe_telegram_webhook() -> CapabilityState:
        mode = telegram_probe_mode
        if mode == "skip":
            log.warning(
                "startup.telegram_webhook.skipped",
                extra={"mode": mode, "reason": "probe explicitly disabled"},
            )
            return CapabilityState(status="degraded", detail="probe skipped", ttl_seconds=300.0)
        public_state = capability_registry.get_state("public_endpoint")
        if public_state and public_state.status != "available":
            detail = f"blocked_by_public_endpoint:{public_state.detail or public_state.status}"
            return CapabilityState(status="degraded", detail=detail, ttl_seconds=min(300.0, public_state.ttl_seconds))
        try:
            _log_startup_step(
                "behavior_webhook_startup.invoke",
                "Registering webhook with Telegram",
            )
            startup_meta = await behavior_webhook_startup(
                bootstrap_state.bot,
                f"{public_url.rstrip('/')}{WEBHOOK_PATH}",
                webhook_secret,
                drop_pending_updates=False,
            )
            for prompt in startup_meta.get("prompt_events", []):
                log.warning(
                    "webhook.prompt.retry",
                    extra={
                        "prompt_id": prompt.get("prompt_id"),
                        "prompt_text": prompt.get("prompt_text", ""),
                        "request_id": ContextBridge.request_id(),
                        "retry": prompt.get("prompt_variables", {}).get("retry"),
                    },
                )
            _log_startup_step(
                "startup.complete",
                "Application ready",
                router=bootstrap_state.router.name,
                stages=startup_meta.get("telemetry", {}).get("stages", []),
                bootstrapped_request_id=telemetry.get("request_id"),
            )
            return CapabilityState(status="available", ttl_seconds=300.0)
        except Exception as exc:  # pragma: no cover - network/env dependent
            log.warning(
                "startup.telegram_webhook.degraded",
                extra={"mode": mode, "error": repr(exc)},
            )
            return CapabilityState(status="degraded", detail=str(exc), ttl_seconds=180.0)

    capability_registry.register_probe(
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




    def _capability_snapshot() -> Dict[str, Dict[str, object]]:
        registry: Optional[CapabilityRegistry] = getattr(app.state, "capabilities", None)
        if registry is None:
            return {}
        return registry.snapshot()

    def _derive_health(snapshot: Dict[str, Dict[str, object]]) -> str:
        if any(state.get("status") == "unavailable" for state in snapshot.values()):
            return "unavailable"
        if any(state.get("status") == "degraded" for state in snapshot.values()):
            return "degraded"
        return "ok" if snapshot else "unknown"

    @app.get("/")
    async def root_probe() -> Dict[str, object]:
        snapshot = _capability_snapshot()
        return {
            "status": _derive_health(snapshot),
            "public_url": public_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.head("/")
    async def root_probe_head() -> Response:
        return Response(status_code=status.HTTP_200_OK)

    @app.get("/healthz")
    async def healthz() -> Dict[str, object]:
        snapshot = _capability_snapshot()
        state = getattr(app.state, "telegram", None)
        return {
            "status": _derive_health(snapshot),
            "router": getattr(state.router, "name", "pending") if state else "pending",
            "capabilities": snapshot,
        }

    @app.get("/healthz/startup")
    async def startup_health() -> Dict[str, object]:
        snapshot = _capability_snapshot()
        return {
            "status": _derive_health(snapshot),
            "capabilities": snapshot,
        }

    @app.get("/healthz/readiness")
    async def readiness_health() -> Dict[str, object]:
        refresher = getattr(app.state, "capability_refresh", None)
        if callable(refresher):
            await refresher()
        snapshot = _capability_snapshot()
        return {
            "status": _derive_health(snapshot),
            "capabilities": snapshot,
        }

    @app.get("/internal/memory_health")
    async def memory_health() -> Dict[str, Any]:
        snapshot = getattr(app.state, "memory_snapshot", {})
        status = getattr(app.state, "memory_snapshot_status", "unknown")
        telemetry_state = getattr(app.state, "memory_snapshot_telemetry", {})
        health = getattr(app.state, "memory_snapshot_health", {})
        missing = getattr(app.state, "memory_snapshot_missing_agencies", [])
        metadata = getattr(app.state, "memory_loader_metadata", {})
        checksum_status = (
            telemetry_state.get("checksum_status")
            or health.get("checksum_status")
            or snapshot.get("stats", {}).get("checksum_status")
        )
        return {
            "status": status,
            "snapshot_version": snapshot.get("snapshot_version"),
            "snapshot_checksum": snapshot.get("checksum"),
            "checksum_status": checksum_status,
            "stats": snapshot.get("stats", {}),
            "health": health,
            "missing_agencies": missing,
            "telemetry": telemetry_state,
            "metadata": metadata,
        }

    return app


