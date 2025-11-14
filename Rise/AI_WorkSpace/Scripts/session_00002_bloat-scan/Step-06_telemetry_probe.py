#!/usr/bin/env python3
from __future__ import annotations

"""
Utility script for Step-06 to sample telemetry coverage SSE streams and JSONL mirrors.
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Sequence

import httpx

from project_utility.config.paths import get_log_root


async def _stream_events(url: str, limit: int, timeout: float, headers: dict[str, str]) -> Sequence[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, read=None)) as client:
        async with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("data:"):
                    payload = json.loads(line[5:].strip())
                    results.append(payload)
                    print(f"[SSE] {payload.get('timestamp')} status={payload.get('status')} scenarios={payload.get('scenarios')}")
                    if len(results) >= limit:
                        break
                elif line.startswith(":"):
                    print(f"[SSE] {line.strip()}")
    return results


def _tail_jsonl(count: int) -> Sequence[dict[str, Any]]:
    log_path = get_log_root() / "telemetry.jsonl"
    if not log_path.exists():
        print(f"[JSONL] file not found at {log_path}")
        return ()
    with log_path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()[-count:]
    events: list[dict[str, Any]] = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    for event in events:
        print(f"[JSONL] {event.get('timestamp')} {event.get('event_type')} level={event.get('level')}")
    return events


async def main() -> int:
    parser = argparse.ArgumentParser(description="Sample telemetry SSE and JSONL outputs.")
    parser.add_argument("--workflow", default="wf-demo", help="Workflow ID to stream coverage events from.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Rise backend base URL.")
    parser.add_argument("--limit", type=int, default=1, help="Number of SSE events to capture.")
    parser.add_argument("--jsonl-count", type=int, default=5, help="Number of JSONL entries to print.")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout for SSE stream.")
    parser.add_argument("--actor-id", default="cli-probe", help="Actor ID header for authenticated requests.")
    parser.add_argument("--actor-roles", default="admin", help="Comma-separated roles for the actor header.")
    parser.add_argument("--skip-stream", action="store_true", help="Skip SSE streaming and only tail JSONL.")
    args = parser.parse_args()

    stream_url = f"{args.base_url.rstrip('/')}/api/workflows/{args.workflow}/tests/stream"
    print(f"[INFO] Streaming {args.limit} events from {stream_url}")
    headers = {
        "X-Actor-Id": args.actor_id,
        "X-Actor-Roles": args.actor_roles,
        "Accept": "text/event-stream",
    }
    if not args.skip_stream:
        try:
            await _stream_events(stream_url, args.limit, args.timeout, headers)
        except httpx.HTTPStatusError as exc:
            print(f"[ERROR] SSE stream failed: {exc}")
        except httpx.HTTPError as exc:
            print(f"[ERROR] SSE transport error: {exc}")
    else:
        print("[INFO] skip-stream enabled; SSE step bypassed.")

    print(f"[INFO] Tail last {args.jsonl_count} telemetry JSONL entries")
    _tail_jsonl(args.jsonl_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
