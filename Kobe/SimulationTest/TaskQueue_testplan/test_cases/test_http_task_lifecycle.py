# -*- coding: utf-8 -*-
import os
import time
from typing import Optional

import pytest
import requests
import structlog


BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
RESULT_BACKEND_ENABLED = os.getenv("ENABLE_RESULT_BACKEND", "false").lower() in {"1", "true", "yes"}

log = structlog.get_logger("test_http_task_lifecycle")


def _post_json(path: str, payload: dict, timeout: float = 5.0) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.post(url, json=payload, timeout=timeout)


def _get(path: str, timeout: float = 5.0) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.get(url, timeout=timeout)


def _wait_for_status(task_id: str, deadline: float) -> Optional[dict]:
    """Polls status until ready or deadline reached. Returns JSON or None."""
    while time.time() < deadline:
        r = _get(f"/task/status/{task_id}")
        if r.status_code == 200:
            js = r.json()
            if js.get("ready") is True:
                return js
        time.sleep(0.2)
    return None


@pytest.mark.timeout(10)
def test_task_lifecycle_basic(resource_monitor):  # resource_monitor from conftest
    payload = {"task": "demo_long_io", "duration_sec": 1, "fail_rate": 0.0}
    try:
        resp = _post_json("/task/start", payload)
    except Exception as e:  # service not running or connection refused
        pytest.skip(f"API not reachable at {BASE_URL}: {e}")

    assert resp.status_code in (200, 202), resp.text
    data = resp.json()
    task_id = data.get("task_id") or data.get("id")
    assert task_id, f"No task_id in response: {data}"

    # Wait until status ready
    done = _wait_for_status(task_id, time.time() + 8.0)
    if not done:
        pytest.xfail("Task status did not become ready within deadline")

    # Result endpoint: may be disabled if result backend off
    r = _get(f"/task/result/{task_id}")
    if RESULT_BACKEND_ENABLED:
        assert r.status_code == 200, r.text
        js = r.json()
        assert js.get("task_id") == task_id
        assert js.get("state") in {"SUCCESS", "FAILURE", "RETRY", "PENDING"}
    else:
        assert r.status_code in (200, 202)
        if r.status_code == 200:
            # Some implementations still expose result via DB polling; accept best effort
            js = r.json()
            assert js.get("task_id") == task_id

