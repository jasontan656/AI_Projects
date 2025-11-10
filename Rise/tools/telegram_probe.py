#!/usr/bin/env python
"""
Active Telegram webhook probe utility.

Usage:
    python tools/telegram_probe.py --token <BOT_TOKEN> --webhook https://example/ngrok --proxy http://proxy:8080
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

import aiohttp


async def _request_webhook_info(
    token: str,
    *,
    proxy: Optional[str],
    proxy_user: Optional[str],
    proxy_pass: Optional[str],
    timeout: float,
) -> Dict[str, Any]:
    api_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    proxy_auth = None
    if proxy and (proxy_user or proxy_pass):
        proxy_auth = aiohttp.BasicAuth(proxy_user or "", proxy_pass or "")
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.get(api_url, proxy=proxy, proxy_auth=proxy_auth) as response:
            payload = await response.text()
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as exc:  # pragma: no cover - network specific
                raise RuntimeError(f"Unexpected response: {payload}") from exc
            if not data.get("ok"):
                raise RuntimeError(f"Telegram API returned error: {data.get('description')}")
            return data


async def _probe(args: argparse.Namespace) -> int:
    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Missing bot token (use --token or TELEGRAM_BOT_TOKEN env).", file=sys.stderr)
        return 2
    expected_webhook = args.webhook or os.getenv("WEB_HOOK")
    proxy = args.proxy or os.getenv("TELEGRAM_PROXY_URL")
    proxy_user = args.proxy_user or os.getenv("TELEGRAM_PROXY_USER")
    proxy_pass = args.proxy_pass or os.getenv("TELEGRAM_PROXY_PASS")
    try:
        info = await _request_webhook_info(
            token,
            proxy=proxy,
            proxy_user=proxy_user,
            proxy_pass=proxy_pass,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"[FAIL] Unable to query getWebhookInfo: {exc}", file=sys.stderr)
        return 1

    result = info.get("result", {})
    current_url = result.get("url") or ""
    pending = result.get("pending_update_count", 0)
    matches = True
    if expected_webhook:
        matches = current_url.rstrip("/") == expected_webhook.rstrip("/")

    summary = {
        "status": "ok",
        "current_webhook": current_url,
        "matches_expected": matches,
        "pending_updates": pending,
        "has_custom_certificate": bool(result.get("has_custom_certificate")),
        "last_error_message": result.get("last_error_message"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not matches:
        print(
            f"[WARN] webhook mismatch (expected {expected_webhook or '<unset>'}).",
            file=sys.stderr,
        )
        return 3
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe Telegram webhook connectivity.")
    parser.add_argument("--token", help="Bot token; defaults to TELEGRAM_BOT_TOKEN.")
    parser.add_argument("--webhook", help="Expected webhook URL; defaults to WEB_HOOK env.")
    parser.add_argument("--proxy", help="HTTP(S) proxy URL; defaults to TELEGRAM_PROXY_URL.")
    parser.add_argument("--proxy-user", help="Proxy username; defaults to TELEGRAM_PROXY_USER.")
    parser.add_argument("--proxy-pass", help="Proxy password; defaults to TELEGRAM_PROXY_PASS.")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout seconds (default: 10).")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    exit_code = asyncio.run(_probe(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
