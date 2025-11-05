from __future__ import annotations

"""MongoDB client helpers."""

import os
from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("missing required environment variable: MONGODB_URI")
    return MongoClient(uri, tz_aware=True)


def get_mongo_database() -> Database:
    db_name = os.getenv("MONGODB_DATABASE")
    if not db_name:
        raise RuntimeError("missing required environment variable: MONGODB_DATABASE")
    client = get_mongo_client()
    return client[db_name]
