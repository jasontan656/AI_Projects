from __future__ import annotations

"""
Interactive chat terminal for Career Bot hub.

Constitution-aligned client:
- Uses LangServe `/chat/stream_events` for streaming events
- Builds ChatRequest per hub.hub.ChatRequest; envelope is assembled server-side
- Generates compliant user_id/request_id via shared_utilities.time.Time
- Normalizes auth_username via shared_utilities.validator

Run from repo root `cry_backend` with local .venv:
  python -m scripts.chat_terminal.start

Note: Fail-fast by default; no silent catch-all.
"""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

import anyio
import httpx

from shared_utilities.time import Time
from shared_utilities.validator import normalize_auth_username


DEFAULT_HOST = os.getenv("CHAT_HOST", "http://localhost:8000")
CHAT_INVOKE = "/chat/invoke"
CHAT_STREAM_EVENTS = "/chat/stream_events"


@dataclass
class Session:
    user_id: str
    auth_username: str = ""
    authorization: Optional[str] = None
    session_id: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    def new_request_id(self) -> str:
        return Time.timestamp()


def _build_chat_request(
    *,
    message: str,
    sess: Session,
    request_id: Optional[str] = None,
    prefer_stream: bool = True,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rid = request_id or sess.new_request_id()
    ctx = dict(extra_context or {})
    payload: Dict[str, Any] = {
        "message": message,
        "user_id": sess.user_id,
        "auth_username": sess.auth_username,
        "session_id": sess.session_id,
        "request_id": rid,
        "authorization": sess.authorization,
        "stream": prefer_stream,
        "context": ctx,
    }
    return payload


async def _stream_events(
    client: httpx.AsyncClient,
    url: str,
    payload: Dict[str, Any],
) -> AsyncIterator[Dict[str, Any]]:
    # LangServe stream_events returns SSE-like frames. We parse lines conservatively.
    # Expect lines like: "event: <type>" and "data: {json}"
    async with client.stream("POST", url, json=payload, timeout=None) as resp:
        resp.raise_for_status()
        event_type: Optional[str] = None
        async for line in resp.aiter_lines():
            if not line:
                continue
            if line.startswith(":"):
                # comment/heartbeat
                continue
            if line.startswith("event:"):
                # e.g., 'event: data'
                event_type = line.split(":", 1)[1].strip()
                continue
            if line.startswith("data:"):
                raw = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    # Fail fast: surface the malformed frame
                    raise ValueError(f"Malformed event data frame: {raw!r}")
                # LangServe often sets {"event": "...", "data": {...}} too; normalize
                if isinstance(data, dict) and "data" in data and "event" in data:
                    inner = data.get("data")
                    et = str(data.get("event"))
                    if isinstance(inner, dict):
                        inner.setdefault("type", et)
                        yield inner
                        event_type = None
                        continue
                # Otherwise rely on previously parsed event_type or payload type
                if isinstance(data, dict):
                    if event_type and "type" not in data:
                        data["type"] = event_type
                    yield data
                event_type = None


def _print_event(evt: Dict[str, Any]) -> None:
    et = str(evt.get("type") or "").lower()
    if et == "token":
        token = evt.get("token")
        if isinstance(token, str):
            # Print without newline to emulate streaming
            sys.stdout.write(token)
            sys.stdout.flush()
        return
    if et == "ui":
        print("\n[ui]", json.dumps(evt.get("ui") or evt, ensure_ascii=False, indent=2))
        return
    if et == "artifact":
        print("\n[artifact]", json.dumps(evt.get("artifact") or evt, ensure_ascii=False))
        return
    if et == "metrics":
        print("\n[metrics]", json.dumps(evt, ensure_ascii=False))
        return
    if et == "final":
        # ensure newline after possible token stream
        print()
        print("[final]", json.dumps(evt, ensure_ascii=False, indent=2))
        return
    if et == "error":
        print()
        print("[error]", json.dumps(evt, ensure_ascii=False, indent=2))
        return
    # Fallback for untagged payloads
    print("\n[event]", json.dumps(evt, ensure_ascii=False))


async def one_shot(host: str, sess: Session, message: str) -> None:
    url = host.rstrip("/") + CHAT_STREAM_EVENTS
    async with httpx.AsyncClient() as client:
        payload = _build_chat_request(message=message, sess=sess, prefer_stream=True)
        async for evt in _stream_events(client, url, payload):
            _print_event(evt)


async def interactive(host: str, sess: Session) -> None:
    print(f"Chat Terminal connected to {host}")
    print("Type a message and press Enter. Commands: /history, /clear, /exit")
    while True:
        line = input("> ").rstrip("\n")
        if not line:
            continue
        if line == "/exit":
            print("Bye.")
            return
        if line == "/history":
            for i, item in enumerate(sess.history[-20:], start=1):
                print(f"{i:02d}. {item.get('message','')} (request_id={item.get('request_id','')})")
            continue
        if line == "/clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue
        if line == ">>>":
            print("... multiline mode; finish with /end")
            buf: List[str] = []
            while True:
                l2 = input("... ")
                if l2.strip() == "/end":
                    break
                buf.append(l2)
            line = "\n".join(buf)

        request_id = sess.new_request_id()
        record = {"message": line, "request_id": request_id}
        sess.history.append(record)

        url = host.rstrip("/") + CHAT_STREAM_EVENTS
        async with httpx.AsyncClient() as client:
            payload = _build_chat_request(message=line, sess=sess, request_id=request_id, prefer_stream=True)
            try:
                async for evt in _stream_events(client, url, payload):
                    _print_event(evt)
            finally:
                # ensure newline after token stream
                print()


def _parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Career Bot Chat Terminal (workbench)")
    p.add_argument("--host", default=DEFAULT_HOST, help="API host base (default: http://localhost:8000)")
    p.add_argument("--message", default=None, help="Send one message and exit")
    p.add_argument("--auth-username", default="", help="Initial auth username (normalized)")
    p.add_argument("--authorization", default=None, help="Bearer token if available")
    p.add_argument("--session-id", default=None, help="Reuse a session id if available")
    return p.parse_args(argv)


def _init_session(auth_username: str, authorization: Optional[str], session_id: Optional[str]) -> Session:
    try:
        norm_user = normalize_auth_username(auth_username)
    except ValueError as exc:
        # Fail fast with clear message
        raise SystemExit(str(exc))
    user_id = Time.timestamp()
    return Session(user_id=user_id, auth_username=norm_user, authorization=authorization, session_id=session_id)


def main(argv: Optional[List[str]] = None) -> None:
    ns = _parse_args(list(argv or sys.argv[1:]))
    sess = _init_session(ns.auth_username, ns.authorization, ns.session_id)
    try:
        if ns.message:
            anyio.run(one_shot, ns.host, sess, ns.message)
        else:
            anyio.run(interactive, ns.host, sess)
    except httpx.HTTPError as e:
        raise SystemExit(f"HTTP error: {e}")
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()

