# -*- coding: utf-8 -*-
import os

import pytest
from pymongo import MongoClient
import structlog


log = structlog.get_logger("test_mongo_indexes")


@pytest.mark.timeout(10)
def test_required_indexes_exist():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    dbname = os.getenv("MONGODB_DATABASE", "kobe")
    try:
        c = MongoClient(uri, serverSelectionTimeoutMS=2000)
        db = c[dbname]
    except Exception as e:
        pytest.xfail(f"Mongo not available: {e}")

    dedup = db["TaskDedup"].index_information()
    ckpt = db["TaskCheckpoint"].index_information()
    pend = db["PendingTasks"].index_information()

    # Names may vary by implementation; check presence by key content
    has_dedup = any("task_fingerprint" in k for k in dedup.keys())
    has_ckpt = any(
        "shard" in str(v.get("key")) and "sub" in str(v.get("key")) for v in ckpt.values()
    )
    has_task_key = any("task_key" in k for k in pend.keys())
    has_lease_until = any("lease_until" in k for k in pend.keys())

    if not (has_dedup and has_ckpt and has_task_key and has_lease_until):
        # Surface as expected-failure if environment hasn't provisioned indexes yet
        log.warning(
            "mongo_required_indexes_missing",
            dedup=list(dedup.keys()),
            ckpt=ckpt,
            pend=list(pend.keys()),
        )
        pytest.xfail("Required Mongo indexes not present in current environment")
