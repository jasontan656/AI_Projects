from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from business_logic import KnowledgeSnapshotOrchestrator
from business_service import KnowledgeSnapshotService
from business_service.channel.health_store import ChannelBindingHealthStore
from business_service.channel.repository import AsyncWorkflowChannelRepository
from business_service.channel.service import WorkflowChannelService
from business_service.conversation import service as conversation_service_module
from business_service.conversation.health import ChannelHealthReporter, set_channel_health_reporter
from business_service.pipeline.repository import AsyncMongoPipelineNodeRepository
from business_service.pipeline.service import AsyncPipelineNodeService
from business_service.workflow import AsyncWorkflowRepository
from foundational_service.contracts.registry import BehaviorContract, behavior_top_entry
from foundational_service.integrations.memory_loader import configure_knowledge_snapshot
from project_utility.context import ContextBridge
from project_utility.config.paths import get_repo_root
from project_utility.db.redis import get_async_redis
from interface_entry.config.manifest_loader import load_doc_context, load_top_entry_manifest
from interface_entry.bootstrap.capability_service import CapabilityService, CapabilityServiceConfig
from interface_entry.bootstrap.channel_binding_bootstrap import (
    channel_binding_lifespan,
    prime_channel_binding_registry,
)
from interface_entry.bootstrap.health_routes import register_health_routes
from interface_entry.bootstrap.runtime_lifespan import configure_runtime_lifespan
from interface_entry.bootstrap.startup_housekeeping import (
    apply_host_override_env,
    prepare_logging_environment,
    require_env,
)
from interface_entry.http.dependencies import (
    application_lifespan,
    get_mongo_client,
    get_settings,
    get_task_runtime,
    get_task_runtime_if_enabled,
    get_telegram_client,
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
from foundational_service.telemetry.console_view import TelemetryConsoleSubscriber, build_console_subscriber
from foundational_service.messaging.channel_binding_event_publisher import get_channel_binding_event_publisher
from foundational_service.telemetry.config import load_telemetry_config
from interface_entry.runtime.channel_binding_event_replayer import ChannelBindingEventReplayer
from interface_entry.runtime.supervisors import RuntimeSupervisor

from dotenv import load_dotenv  # type: ignore[import]


REPO_ROOT = get_repo_root()

load_dotenv(dotenv_path=str(REPO_ROOT / ".env"))


log = logging.getLogger("interface_entry.app")

configure_knowledge_snapshot(KnowledgeSnapshotService)

WEBHOOK_PATH = "/telegram/webhook"
TOP_ENTRY_MANIFEST = load_top_entry_manifest()
DOC_CONTEXT = load_doc_context()
DOC_ID = DOC_CONTEXT["doc_id"]
DOC_COMMIT = DOC_CONTEXT["doc_commit"]

_telemetry_console_subscriber: Optional[TelemetryConsoleSubscriber] = None


class TelegramWebhookUnavailableError(RuntimeError):
    """Raised when Telegram webhook cannot be reached during startup."""


def configure_application(app: FastAPI) -> FastAPI:
    prepare_logging_environment()
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
    app.state.telemetry_console_subscriber = subscriber
    global _telemetry_console_subscriber
    _telemetry_console_subscriber = subscriber

    docker_bridge_host = os.getenv("DOCKER_HOST_BRIDGE")
    apply_host_override_env("MONGODB_URI", os.getenv("MONGODB_HOST_OVERRIDE") or docker_bridge_host, service="mongo")
    apply_host_override_env("REDIS_URL", os.getenv("REDIS_HOST_OVERRIDE") or docker_bridge_host, service="redis")
    apply_host_override_env("RABBITMQ_URL", os.getenv("RABBITMQ_HOST_OVERRIDE") or docker_bridge_host, service="rabbitmq")

    token = require_env("TELEGRAM_BOT_TOKEN")
    webhook_secret = require_env("TELEGRAM_BOT_SECRETS")
    public_url = require_env("WEB_HOOK")
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

    capability_service = CapabilityService(
        app=app,
        log=log,
        config=CapabilityServiceConfig(
            public_url=public_url,
            webhook_path=WEBHOOK_PATH,
            webhook_secret=webhook_secret,
            telegram_token=token,
            telegram_probe_mode=telegram_probe_mode,
            redis_url=redis_url,
        ),
    )
    capability_service.register_core_probes()
    capability_registry = capability_service.registry

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
    channel_health_reporter = ChannelHealthReporter(
        store=channel_binding_health_store,
        redis_client=get_async_redis(),
    )
    app.state.channel_health_reporter = channel_health_reporter
    set_channel_health_reporter(channel_health_reporter)

    settings = get_settings()
    mongo_client = get_mongo_client()
    pipeline_collection = mongo_client[settings.mongodb_database]["pipeline_nodes"]
    pipeline_repository = AsyncMongoPipelineNodeRepository(pipeline_collection)
    pipeline_service = AsyncPipelineNodeService(repository=pipeline_repository)
    app.state.pipeline_node_service = pipeline_service
    conversation_service_module.set_pipeline_service_factory(
        lambda: conversation_service_module.PipelineNodeGuardService(pipeline_service=pipeline_service)
    )

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

    capability_service.register_webhook_probe(bootstrap_state)




    register_health_routes(app, public_url=public_url)
    return app


