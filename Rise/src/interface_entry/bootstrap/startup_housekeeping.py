from __future__ import annotations

import logging
import os
import shutil
from contextlib import suppress
from typing import Callable, List, Optional
from urllib.parse import urlparse, urlunparse

from project_utility.config.paths import get_repo_root
from project_utility.logging import configure_logging, initialize_log_workspace

log = logging.getLogger("interface_entry.app")
REPO_ROOT = get_repo_root()

__all__ = [
    "apply_host_override_env",
    "format_endpoint_detail",
    "perform_clean_startup",
    "prepare_logging_environment",
    "release_logging_handlers",
    "require_env",
    "sanitize_endpoint",
]


def sanitize_endpoint(raw: str) -> str:
    if "@" in raw:
        return raw.split("@", 1)[1]
    return raw


def format_endpoint_detail(uri: Optional[str]) -> str:
    return f"endpoint={sanitize_endpoint(uri or 'unknown')}"


def _override_uri_host(uri: str, host: str) -> str:
    parsed = urlparse(uri)
    hostname = parsed.hostname
    if not hostname:
        return uri
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


def apply_host_override_env(env_key: str, override_host: Optional[str], *, service: str) -> None:
    if not override_host:
        return
    uri = os.getenv(env_key)
    if not uri:
        return
    try:
        updated = _override_uri_host(uri, override_host)
    except Exception as exc:  # pragma: no cover - defensive guard
        log.warning(
            "startup.service_host_override_failed",
            extra={"service": service, "error": str(exc)},
        )
        return
    if updated != uri:
        os.environ[env_key] = updated
        log.info(
            "startup.service_host_override",
            extra={"service": service, "host": override_host},
        )


def require_env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        if name == "TELEGRAM_BOT_TOKEN":
            raise RuntimeError("bootstrap_refused_missing_token")
        raise RuntimeError(f"missing required environment variable: {name}")
    return value or ""


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


def prepare_logging_environment() -> None:
    initialize_log_workspace()
    configure_logging()


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
    log.info("startup.clean.redis", extra={"endpoint": sanitize_endpoint(redis_url)})


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
                "endpoint": sanitize_endpoint(mongo_uri),
                "database": mongo_db,
                "collections": collections,
            },
        )
    finally:
        with suppress(Exception):
            client.close()
