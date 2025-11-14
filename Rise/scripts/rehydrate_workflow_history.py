from __future__ import annotations

"""Rebuild workflow publish history from the audit collection."""

import argparse
import os
import sys
from typing import Sequence

from pymongo import MongoClient

from business_service.workflow.models import WorkflowPublishRecord
from business_service.workflow.workflow_history_repository import (
    WorkflowHistoryRepository,
    calculate_history_checksum,
)
from business_service.workflow.workflow_repository import PUBLISH_HISTORY_LIMIT


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rehydrate workflow publish history from audit records.")
    parser.add_argument("--workflow", required=True, help="Target workflow_id to rehydrate")
    parser.add_argument("--mongo-uri", default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017/"))
    parser.add_argument("--database", default=os.environ.get("MONGODB_DATABASE", "rise"))
    parser.add_argument(
        "--history-collection",
        default="workflow_history",
        help="Collection storing audit entries (default: workflow_history)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=PUBLISH_HISTORY_LIMIT,
        help=f"Number of records to materialize back into workflows.publish_history (default: {PUBLISH_HISTORY_LIMIT})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the rebuilt history & checksum back to the workflow document",
    )
    return parser.parse_args()


def _rehydrate(
    workflow_id: str,
    repo: WorkflowHistoryRepository,
    db,
    *,
    limit: int,
    apply_patch: bool,
) -> int:
    history: Sequence[WorkflowPublishRecord] = repo.list_history(workflow_id, limit=limit)
    checksum = calculate_history_checksum(history)
    workflows = db["workflows"]
    workflow_doc = workflows.find_one({"workflow_id": workflow_id})
    if workflow_doc is None:
        print(f"[rehydrate] workflow '{workflow_id}' not found in 'workflows' collection", file=sys.stderr)
        return 1
    print(f"[rehydrate] workflow_id={workflow_id} history_records={len(history)} checksum={checksum}")
    if not history:
        print("[rehydrate] no history records available; nothing to write")
        return 0
    if apply_patch:
        workflows.update_one(
            {"workflow_id": workflow_id},
            {
                "$set": {
                    "publish_history": [record.to_document() for record in history],
                    "history_checksum": checksum,
                }
            },
        )
        print(f"[rehydrate] workflow '{workflow_id}' publish_history updated ({len(history)} records)")
    return 0


def main() -> int:
    args = _parse_args()
    client = MongoClient(args.mongo_uri)
    database = client[args.database]
    history_collection = database[args.history_collection]
    repo = WorkflowHistoryRepository(history_collection)
    return _rehydrate(
        args.workflow,
        repo,
        database,
        limit=args.limit,
        apply_patch=args.apply,
    )


if __name__ == "__main__":
    raise SystemExit(main())
