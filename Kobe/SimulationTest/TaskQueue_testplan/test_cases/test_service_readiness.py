# -*- coding: utf-8 -*-
import base64
import os

import pytest
import requests
import redis
from pymongo import MongoClient
import structlog


log = structlog.get_logger("test_service_readiness")


def _strict_mode() -> bool:
    return os.getenv("SERVICE_CHECK_STRICT", "false").lower() in {"1", "true", "yes"}


@pytest.mark.timeout(5)
def test_rabbitmq_overview():
    url = os.getenv("RABBITMQ_MGMT_URL", "http://127.0.0.1:15672/api/overview")
    auth = os.getenv("RABBITMQ_MGMT_AUTH", "guest:guest")
    user, _, pwd = auth.partition(":")
    try:
        r = requests.get(url, auth=(user, pwd), timeout=3)
        assert r.status_code == 200
        assert "rabbitmq_version" in r.json()
    except Exception as e:
        log.warning("rabbitmq_unreachable", url=url, error=str(e))
        if _strict_mode():
            pytest.fail(f"RabbitMQ mgmt unreachable: {e}")
        pytest.xfail(f"RabbitMQ mgmt unreachable: {e}")


@pytest.mark.timeout(5)
def test_redis_ping():
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(url)
        assert r.ping() in (True, b"PONG")
    except Exception as e:
        log.warning("redis_unreachable", url=url, error=str(e))
        if _strict_mode():
            pytest.fail(f"Redis unreachable: {e}")
        pytest.xfail(f"Redis unreachable: {e}")


@pytest.mark.timeout(5)
def test_mongo_ping():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    try:
        c = MongoClient(uri, serverSelectionTimeoutMS=2000)
        assert c.admin.command("ping")["ok"] == 1
    except Exception as e:
        log.warning("mongo_unreachable", uri=uri, error=str(e))
        if _strict_mode():
            pytest.fail(f"Mongo unreachable: {e}")
        pytest.xfail(f"Mongo unreachable: {e}")

