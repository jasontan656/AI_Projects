#!/usr/bin/env python3
from __future__ import annotations

"""
CLI helper to refresh a workflow's channel binding via the Rise HTTP API.

The command mirrors the runbook described in session_00002_bloat-scan and can be
chained from Step-11 automation to validate Redis/Mongo snapshots before the
Up Channel Form is resynced.
"""

import argparse
import asyncio
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


@dataclass(slots=True)
class BindingSnapshot:
    workflow_id: str
    channel: str
    binding_version: str | None
    refreshed_at: str | None
    locale: str | None


def _build_headers(actor_id: str, actor_roles: str) -> dict[str, str]:
    headers = {
        "X-Actor-Id": actor_id,
        "X-Actor-Roles": actor_roles,
        "Accept": "application/json",
    }
    return headers


def _extract_snapshot(data: dict[str, Any], channel: str) -> BindingSnapshot:
    envelope = data or {}
    detail = envelope.get("data") or {}
    meta = envelope.get("meta") or {}
    if isinstance(detail, Mapping) and detail.get("workflowId"):
        payload = detail
    else:
        payload = detail.get("channel", {})
    snapshot = BindingSnapshot(
        workflow_id=str(payload.get("workflowId") or ""),
        channel=channel,
        binding_version=payload.get("bindingVersion"),
        refreshed_at=meta.get("refreshedAt") or payload.get("bindingUpdatedAt") or payload.get("updatedAt"),
        locale=payload.get("locale") or payload.get("preferredLocale"),
    )
    return snapshot


def _print_snapshot(prefix: str, snap: BindingSnapshot) -> None:
    print(
        f"[{prefix}] workflow={snap.workflow_id or 'n/a'} "
        f"channel={snap.channel} "
        f"version={snap.binding_version or 'unknown'} "
        f"refreshed_at={snap.refreshed_at or 'n/a'} "
        f"locale={snap.locale or 'n/a'}"
    )


async def refresh_binding(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    refresh_url = f"{base_url}/api/channel-bindings/{args.workflow}/refresh"
    detail_url = f"{base_url}/api/channel-bindings/{args.workflow}"
    headers = _build_headers(args.actor_id, args.actor_roles)
    params = {"channel": args.channel}
    timeout = httpx.Timeout(args.timeout, read=args.timeout)

    async with httpx.AsyncClient(timeout=timeout) as client:
        print(f"[refresh] POST {refresh_url}?channel={args.channel}")
        response = await client.post(refresh_url, params=params, headers=headers)
        response.raise_for_status()
        refreshed = response.json()
        snapshot = _extract_snapshot(refreshed, args.channel)
        _print_snapshot("refresh", snapshot)

        if args.skip_detail:
            return 0

        print(f"[refresh] GET {detail_url}?channel={args.channel}")
        detail_resp = await client.get(detail_url, params=params, headers=headers)
        detail_resp.raise_for_status()
        detail_snapshot = _extract_snapshot(detail_resp.json(), args.channel)
        _print_snapshot("detail", detail_snapshot)

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh Rise channel binding snapshots via HTTP API."
    )
    parser.add_argument("--workflow", required=True, help="Workflow ID to refresh.")
    parser.add_argument("--channel", default="telegram", help="Channel identifier.")
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Rise backend base URL."
    )
    parser.add_argument(
        "--actor-id",
        default="ops-cli",
        help="Actor ID used for authenticated requests (X-Actor-Id).",
    )
    parser.add_argument(
        "--actor-roles",
        default="admin",
        help="Comma-separated roles for X-Actor-Roles header.",
    )
    parser.add_argument(
        "--timeout", type=float, default=20.0, help="HTTP timeout in seconds."
    )
    parser.add_argument(
        "--skip-detail",
        action="store_true",
        help="Skip the follow-up GET call that prints post-refresh binding details.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(refresh_binding(args))
    except httpx.HTTPStatusError as exc:
        response = exc.response
        print(
            f"[ERROR] HTTP {response.status_code} -> {response.text.strip() or response.reason_phrase}"
        )
        return 1
    except httpx.HTTPError as exc:
        print(f"[ERROR] transport failure: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
