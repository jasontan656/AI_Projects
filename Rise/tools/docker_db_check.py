#!/usr/bin/env python
"""Docker compose health checks with structured JSON output."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from dotenv import load_dotenv


def _run_command(command: Sequence[str], label: str) -> Tuple[bool, str, str]:
    print(f"[CHECK] {label}: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if result.returncode == 0:
        print(f"[PASS] {label}: {stdout or 'ok'}")
        return True, stdout, stderr
    print(f"[FAIL] {label} (exit {result.returncode})", file=sys.stderr)
    if stdout:
        print(stdout, file=sys.stderr)
    if stderr:
        print(stderr, file=sys.stderr)
    return False, stdout, stderr


def _compose_command(base: List[str], service: str, inner: Sequence[str]) -> List[str]:
    return base + ["exec", "-T", service, *inner]


def _mongo_status_command(
    compose_parts: List[str],
    service: str,
    username: str,
    password: str,
    auth_db: str,
    port: str,
) -> List[str]:
    script = _mongo_check_script()
    return _compose_command(
        compose_parts,
        service,
        [
            "mongosh",
            "--quiet",
            "--port",
            port,
            "-u",
            username,
            "-p",
            password,
            "--authenticationDatabase",
            auth_db,
            "--eval",
            script,
        ],
    )


def _initiate_repl_set(
    compose_parts: List[str],
    service: str,
    username: str,
    password: str,
    auth_db: str,
    host: Optional[str] = None,
    port: str = "27017",
) -> Tuple[bool, str, str]:
    replica_host = host or os.getenv("MONGODB_REPLICA_SET_HOST") or "mongo:27017"
    init_script = (
        "const config = {_id: 'rs0', members: [{ _id: 0, host: '%s' }]};"
        "try { printjson(rs.initiate(config)); } catch (err) { print(err); quit(1); }"
    ) % replica_host
    command = _compose_command(
        compose_parts,
        service,
        [
            "mongosh",
            "--quiet",
            "--port",
            port,
            "-u",
            username,
            "-p",
            password,
            "--authenticationDatabase",
            auth_db,
            "--eval",
            init_script,
        ],
    )
    return _run_command(command, "mongo_repl_init")


def _mongo_check_script() -> str:
    return (
        "const status = rs.status();"
        "if (status.ok !== 1) { throw new Error(JSON.stringify(status)); }"
        "const primary = (status.members.find(m => m.stateStr === 'PRIMARY') || {}).name || null;"
        "print(JSON.stringify({ set: status.set, members: status.members.length, primary }));"
    )


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Validate dockerized MongoDB/Redis/RabbitMQ health.")
    parser.add_argument("--compose-cmd", default="docker compose", help="Docker compose command prefix.")
    parser.add_argument("--mongo-service", default="mongo", help="Mongo service name.")
    parser.add_argument("--redis-service", default="redis", help="Redis service name.")
    parser.add_argument("--rabbit-service", default="rabbitmq", help="RabbitMQ service name.")
    parser.add_argument("--mongo-username", default="root", help="MongoDB admin username.")
    parser.add_argument("--mongo-password", default="changeme", help="MongoDB admin password.")
    parser.add_argument(
        "--mongo-auth-db",
        default="admin",
        help="MongoDB authentication database for the provided credentials.",
    )
    parser.add_argument("--rabbit-port", default="5672", help="RabbitMQ port to validate.")
    args = parser.parse_args()

    compose_parts = shlex.split(args.compose_cmd)
    mongo_port = os.getenv("MONGODB_PORT", "27017")
    mongo_command = _mongo_status_command(
        compose_parts,
        args.mongo_service,
        args.mongo_username,
        args.mongo_password,
        args.mongo_auth_db,
        mongo_port,
    )
    check_matrix: Mapping[str, List[str]] = {
        "mongo": mongo_command,
        "redis": _compose_command(compose_parts, args.redis_service, ["redis-cli", "PING"]),
        "rabbitmq": _compose_command(
            compose_parts,
            args.rabbit_service,
            ["rabbitmq-diagnostics", "check_port_listener", args.rabbit_port],
        ),
    }

    reports: Dict[str, Dict[str, str]] = {}
    success = True
    for label, command in check_matrix.items():
        ok, stdout, stderr = _run_command(command, label)
        if label == "mongo" and not ok and any(
            token in (stdout + stderr)
            for token in ("NotYetInitialized", "no replset config has been received")
        ):
            init_ok, init_stdout, init_stderr = _initiate_repl_set(
                compose_parts,
                args.mongo_service,
                args.mongo_username,
                args.mongo_password,
                args.mongo_auth_db,
                port=mongo_port,
            )
            reports["mongo_repl_init"] = {
                "status": "ok" if init_ok else "failed",
                "stdout": init_stdout,
                "stderr": init_stderr,
            }
            if init_ok:
                mongo_command = _mongo_status_command(
                    compose_parts,
                    args.mongo_service,
                    args.mongo_username,
                    args.mongo_password,
                    args.mongo_auth_db,
                )
                ok, stdout, stderr = _run_command(mongo_command, label)
        success &= ok
        reports[label] = {
            "status": "ok" if ok else "failed",
            "stdout": stdout,
            "stderr": stderr,
        }

    summary = {
        "status": "ok" if success else "failed",
        "timestamp": int(time.time()),
        "checks": reports,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
