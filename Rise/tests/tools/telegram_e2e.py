#!/usr/bin/env python
"""
Minimal Telegram E2E helper used to exercise Rise workflow endpoints in mock mode.

The historical script referenced in requirements is absent from the repository,
so this implementation focuses on the essentials required by Step-09:
1. Verify that the Rise API is reachable (`/healthz`).
2. Attempt to trigger the workflow test runner endpoint in mock mode.
3. Emit a structured JSON summary that downstream logs can archive.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def fetch_json(url: str, *, data: bytes | None = None, method: str = "GET") -> dict:
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # nosec B310
        body = response.read().decode("utf-8")
        if not body:
            return {"status": response.status, "body": ""}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"status": response.status, "body": body}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mock", "real"], default="mock")
    parser.add_argument("--workflow", required=True)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("RISE_API_BASE_URL", "http://localhost:8000"),
    )
    args = parser.parse_args()

    summary = {
        "mode": args.mode,
        "workflow": args.workflow,
        "base_url": args.base_url,
    }

    try:
        summary["healthz"] = fetch_json(f"{args.base_url}/healthz")
    except Exception as exc:  # pragma: no cover - diagnostics only
        summary["healthz_error"] = str(exc)

    trigger_payload = json.dumps(
        {
            "mode": args.mode,
            "source": "telegram_e2e_cli",
        }
    ).encode("utf-8")

    try:
        summary["test_run"] = fetch_json(
            f"{args.base_url}/api/workflows/{args.workflow}/tests/run",
            data=trigger_payload,
            method="POST",
        )
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        summary["test_run_error"] = {
            "status": exc.code,
            "body": error_body,
        }
    except Exception as exc:  # pragma: no cover - diagnostics only
        summary["test_run_error"] = str(exc)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
