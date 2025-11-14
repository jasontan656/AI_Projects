#!/usr/bin/env python3
from __future__ import annotations

"""
Utility script to fix the MongoDB replica-set host after Docker rebuilds.

The local rs0 member occasionally keeps stale hostnames (e.g., rise-mongo-1)
inside its persisted config, which makes clients outside the Docker network
fail during the handshake. This script connects via a direct link, rewrites
the lone member host to localhost:<port>, and prints the before/after config.
"""

import os
import sys
from pprint import pprint

from pymongo import MongoClient
from pymongo.errors import PyMongoError


def _build_direct_uri() -> str:
    """Return a direct connection URI so we can talk to the primary even when rs config is broken."""

    base_uri = os.getenv("MONGODB_URI", "mongodb://root:changeme@localhost:37017/?authSource=admin")
    if "directConnection" in base_uri:
        return base_uri
    separator = "&" if "?" in base_uri else "?"
    return f"{base_uri}{separator}directConnection=true"


def main() -> int:
    uri = _build_direct_uri()
    target_host = os.getenv("MONGODB_REPLICA_SET_HOST", "localhost:37017")
    print(f"[mongo-reconfig] Connecting with URI: {uri}")
    try:
        client = MongoClient(uri, tz_aware=True)
        admin = client["admin"]
        raw_config = admin.command("replSetGetConfig")
    except PyMongoError as exc:  # pragma: no cover - diagnostic utility
        print(f"[mongo-reconfig] Failed to read replica config: {exc}", file=sys.stderr)
        return 1

    config = raw_config.get("config") or {}
    members = config.get("members") or []
    if not members:
        print("[mongo-reconfig] No members found in config; aborting.", file=sys.stderr)
        return 1

    current_host = members[0].get("host")
    print(f"[mongo-reconfig] Current member host: {current_host}")
    if current_host == target_host:
        print("[mongo-reconfig] Replica set already points to the expected host. No changes applied.")
        pprint(config)
        return 0

    members[0]["host"] = target_host
    config["version"] = int(config.get("version", 1)) + 1
    print(f"[mongo-reconfig] Updating host to: {target_host} (version -> {config['version']})")

    try:
        admin.command("replSetReconfig", config, force=True)
    except PyMongoError as exc:  # pragma: no cover - diagnostic utility
        print(f"[mongo-reconfig] replSetReconfig failed: {exc}", file=sys.stderr)
        return 1

    print("[mongo-reconfig] Replica set reconfigured successfully. New config:")
    try:
        new_config = admin.command("replSetGetConfig").get("config", {})
    except PyMongoError:
        new_config = config
    pprint(new_config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
