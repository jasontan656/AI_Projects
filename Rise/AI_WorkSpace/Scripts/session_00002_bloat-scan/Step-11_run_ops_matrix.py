#!/usr/bin/env python3
from __future__ import annotations

"""
Helper runner that enforces a 30-second timeout when invoking Step-11_ops_matrix.ps1.
"""

import argparse
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Step-11 ops matrix script with a timeout.")
    parser.add_argument("--env", default="staging", choices=["local", "staging"], help="Target environment label.")
    parser.add_argument("--workflow", required=True, help="Workflow ID to operate on.")
    parser.add_argument("--channel", default="telegram", help="Channel identifier.")
    parser.add_argument("--slack-webhook", default="", help="Slack Incoming Webhook URL (optional).")
    parser.add_argument("--pagerduty-key", default="", help="PagerDuty Events API routing key (optional).")
    parser.add_argument(
        "--pagerduty-url",
        default="https://events.pagerduty.com/v2/enqueue",
        help="PagerDuty Events API endpoint.",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds.")
    parser.add_argument("--actor-id", default="ops-cli", help="Actor ID header for API calls.")
    parser.add_argument("--actor-roles", default="admin", help="Actor roles header for API calls.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).with_name("Step-11_ops_matrix.ps1")
    repo_root = Path(__file__).resolve().parents[2]
    log_path = Path(__file__).with_name("Step-11_ops_matrix.log")

    if log_path.exists():
        log_path.unlink()

    cmd = [
        "pwsh",
        str(script_path),
        "--env",
        args.env,
        "--workflow",
        args.workflow,
        "--channel",
        args.channel,
        "--SlackWebhook",
        args.slack_webhook,
        "--PagerDutyRoutingKey",
        args.pagerduty_key,
        "--PagerDutyEventsUrl",
        args.pagerduty_url,
        "--actor-id",
        args.actor_id,
        "--actor-roles",
        args.actor_roles,
    ]

    with log_path.open("w", encoding="utf-8") as log_handle:
        subprocess.run(
            cmd,
            cwd=repo_root,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            timeout=args.timeout,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
