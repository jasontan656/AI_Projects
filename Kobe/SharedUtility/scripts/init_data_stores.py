"""
Utility to initialise MongoDB collections and verify Redis connectivity for Kobe runtime.

This script is idempotent: running it multiple times will keep the expected schema intact.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Optional

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import CollectionInvalid, PyMongoError

try:  # pragma: no cover - redis 为可选依赖
    import redis  # type: ignore[import]

    _RedisType = redis.Redis  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    redis = None  # type: ignore[assignment]
    _RedisType = None  # type: ignore[assignment]


CHAT_SUMMARY_COLLECTION_DEFAULT = "chat_summaries"
CHAT_SUMMARY_UNIQUE_INDEX = "idx_chat_id_unique"
CHAT_SUMMARY_UPDATED_AT_INDEX = "idx_updated_at"


@dataclass(slots=True)
class InitConfig:
    mongo_uri: str
    mongo_database: str
    mongo_collection: str
    redis_url: Optional[str]


def build_config() -> InitConfig:
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongo_database = os.getenv("MONGODB_DATABASE", "kobe")
    mongo_collection = os.getenv(
        "CHAT_SUMMARY_COLLECTION", CHAT_SUMMARY_COLLECTION_DEFAULT
    )
    redis_url = os.getenv("REDIS_URL")
    return InitConfig(
        mongo_uri=mongo_uri,
        mongo_database=mongo_database,
        mongo_collection=mongo_collection,
        redis_url=redis_url,
    )


def ensure_chat_summary_collection(
    client: MongoClient, database_name: str, collection_name: str
) -> Collection:
    db = client[database_name]

    if collection_name in db.list_collection_names():
        collection = db[collection_name]
    else:
        collection = db.create_collection(collection_name)

    # unique chat identifier (chat_id could be user id or composite key)
    collection.create_index(
        [("chat_id", ASCENDING)], name=CHAT_SUMMARY_UNIQUE_INDEX, unique=True
    )
    # sort helper for pruning / querying latest records
    collection.create_index(
        [("updated_at", ASCENDING)], name=CHAT_SUMMARY_UPDATED_AT_INDEX
    )
    return collection


def ping_redis(url: str) -> None:
    if redis is None:
        print("redis package not installed; skipping Redis connectivity check.")
        return
    client: _RedisType = redis.Redis.from_url(url, decode_responses=True)  # type: ignore[assignment]
    client.ping()
    print(f"Redis ping succeeded for {url!s}")


def main() -> int:
    config = build_config()
    print("=== Initialising data stores ===")
    print(f"- Mongo URI: {config.mongo_uri}")
    print(f"- Mongo DB : {config.mongo_database}")
    print(f"- Collection: {config.mongo_collection}")

    try:
        mongo_client = MongoClient(config.mongo_uri, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command("ping")
    except PyMongoError as exc:  # pragma: no cover - connection issue
        print(f"[ERROR] Unable to connect to MongoDB: {exc}", file=sys.stderr)
        return 1

    try:
        collection = ensure_chat_summary_collection(
            mongo_client, config.mongo_database, config.mongo_collection
        )
        print(
            f"Mongo collection ready: {collection.full_name} "
            f"(indexes: {collection.index_information().keys()})"
        )
    except CollectionInvalid as exc:  # pragma: no cover - schema issue
        print(f"[ERROR] Failed to create collection: {exc}", file=sys.stderr)
        return 1

    if config.redis_url:
        try:
            ping_redis(config.redis_url)
        except Exception as exc:  # pragma: no cover - connection issue
            print(f"[WARNING] Redis ping failed: {exc}", file=sys.stderr)
    else:
        print("REDIS_URL not provided; skipping Redis ping.")

    print("Data store initialisation completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
