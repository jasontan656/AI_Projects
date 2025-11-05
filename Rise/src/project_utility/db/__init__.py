from __future__ import annotations

"""Database utilities."""

from project_utility.db.mongo import get_mongo_client, get_mongo_database

__all__ = [
    "get_mongo_client",
    "get_mongo_database",
]
