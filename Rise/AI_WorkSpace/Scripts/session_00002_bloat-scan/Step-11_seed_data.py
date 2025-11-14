#!/usr/bin/env python3
from __future__ import annotations

"""
Seed minimal workflows + channel policies for Step-11 verification.

The Docker rebuild wiped Mongo, so this script recreates:
1. Two representative workflows (wf-demo + ops-matrix UUID) with channel metadata.
2. Matching Telegram channel policies using the secrets in .env.
"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from pymongo import MongoClient

# Ensure project modules resolve without mutating PYTHONPATH globally.
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from business_service.workflow.models import WorkflowDefinition  # type: ignore  # noqa: E402
from business_service.channel.models import (  # type: ignore  # noqa: E402
    DEFAULT_TIMEOUT_MESSAGE,
    DEFAULT_WORKFLOW_MISSING_MESSAGE,
)
from business_service.channel.policy import ChannelMode  # type: ignore  # noqa: E402
from project_utility.secrets import SecretBox, mask_secret  # type: ignore  # noqa: E402


def load_env_values(env_path: Path) -> Mapping[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'\"")
        values[key.strip()] = value
    return values


@dataclass(frozen=True)
class WorkflowSeed:
    workflow_id: str
    name: str
    description: str
    locale: str
    tags: tuple[str, ...]


WORKFLOW_SEEDS = (
    WorkflowSeed(
        workflow_id="wf-demo",
        name="Demo Immigration Concierge",
        description="Reference workflow for admin + Telegram binding regression.",
        locale="en-PH",
        tags=("demo", "immigration", "telegram"),
    ),
    WorkflowSeed(
        workflow_id="2427173f-8aca-4c31-90c5-eff157395b27",
        name="Ops Matrix – Accreditation Escalation",
        description="Workflow used by Step-11 ops matrix + runbooks.",
        locale="en-PH",
        tags=("ops-matrix", "accreditation"),
    ),
)


def build_workflow_doc(seed: WorkflowSeed, *, actor: str) -> Mapping[str, Any]:
    now = datetime.now(timezone.utc)
    metadata = {
        "channels": {
            "telegram": {
                "enabled": True,
                "killSwitch": False,
                "locale": seed.locale,
                "lastRefreshAt": now.isoformat(),
                "lastActor": actor,
            }
        },
        "tags": list(seed.tags),
    }
    definition = WorkflowDefinition(
        workflow_id=seed.workflow_id,
        name=seed.name,
        description=seed.description,
        stage_ids=tuple(),
        metadata=metadata,
        node_sequence=tuple(),
        prompt_bindings=tuple(),
        strategy={"retryLimit": 2, "timeoutSeconds": 60, "waitForResult": True},
        status="published",
        version=1,
        published_version=1,
        pending_changes=False,
        publish_history=tuple(),
        history_checksum="seed-00002",
        created_at=now,
        updated_at=now,
        updated_by=actor,
    )
    return definition.to_document()


def build_channel_policy_doc(
    workflow_id: str,
    *,
    encrypted_token: str,
    token_mask: str,
    webhook_url: str,
    actor: str,
) -> Mapping[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "workflow_id": workflow_id,
        "channel": "telegram",
        "encrypted_bot_token": encrypted_token,
        "bot_token_mask": token_mask,
        "webhook_url": webhook_url,
        "wait_for_result": True,
        "workflow_missing_message": DEFAULT_WORKFLOW_MISSING_MESSAGE,
        "timeout_message": DEFAULT_TIMEOUT_MESSAGE,
        "metadata": {
            "health": {
                "status": "ok",
                "lastCheckedAt": now.isoformat(),
                "detail": {"source": "seed-data"},
            }
        },
        "updated_by": actor,
        "updated_at": now,
        "secret_version": 1,
        "mode": ChannelMode.WEBHOOK.value,
    }


def main() -> int:
    env_values = load_env_values(REPO_ROOT / ".env")
    for key, value in env_values.items():
        os.environ.setdefault(key, value)

    mongo_uri = env_values.get(
        "MONGODB_URI",
        "mongodb://root:changeme@localhost:37017/?replicaSet=rs0&authSource=admin",
    )
    mongo_db = env_values.get("MONGODB_DATABASE", "rise")
    webhook_url = env_values.get("WEB_HOOK")
    bot_token = env_values.get("TELEGRAM_BOT_TOKEN")
    secret_key = env_values.get("TELEGRAM_TOKEN_SECRET")
    if not webhook_url or not bot_token or not secret_key:
        raise RuntimeError("WEB_HOOK, TELEGRAM_BOT_TOKEN, and TELEGRAM_TOKEN_SECRET are required for seeding.")

    actor = "seed-script"
    client = MongoClient(mongo_uri, tz_aware=True)
    db = client[mongo_db]

    # Seed workflows
    workflow_collection = db["workflows"]
    for seed in WORKFLOW_SEEDS:
        doc = build_workflow_doc(seed, actor=actor)
        workflow_collection.replace_one({"workflow_id": seed.workflow_id}, doc, upsert=True)
        print(f"[seed-data] workflow upserted -> {seed.workflow_id}")

    # Seed channel policies
    secret_box = SecretBox(secret_key)
    encrypted_token = secret_box.encrypt(bot_token)
    token_mask = mask_secret(bot_token)
    policy_collection = db["workflow_channels"]
    for seed in WORKFLOW_SEEDS:
        policy_doc = build_channel_policy_doc(
            seed.workflow_id,
            encrypted_token=encrypted_token,
            token_mask=token_mask,
            webhook_url=webhook_url,
            actor=actor,
        )
        policy_collection.replace_one(
            {"workflow_id": seed.workflow_id, "channel": "telegram"},
            policy_doc,
            upsert=True,
        )
        print(f"[seed-data] channel policy upserted -> {seed.workflow_id}")

    print("[seed-data] Completed workflow + channel policy seeding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
