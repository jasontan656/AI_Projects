from __future__ import annotations

from typing import List

import redis
from pymongo import MongoClient

from test_config import TestConfig


class DBClient:
    """数据库客户端（Mongo + Redis）用于简单验证结果"""

    def __init__(self, config: TestConfig) -> None:
        self.config = config
        # 懒连接，避免服务未启动时报错
        self._mongo: MongoClient | None = None
        self._redis = None

    @property
    def mongo(self) -> MongoClient:
        if self._mongo is None:
            self._mongo = MongoClient(self.config.MONGODB_URL, serverSelectionTimeoutMS=3000)
        return self._mongo

    @property
    def db(self):  # type: ignore[no-untyped-def]
        db_name = self.config.MONGODB_URL.rsplit("/", 1)[-1]
        return self.mongo[db_name]

    @property
    def redis(self):  # type: ignore[no-untyped-def]
        if self._redis is None:
            self._redis = redis.from_url(self.config.REDIS_URL, socket_connect_timeout=3)
        return self._redis

    def count_messages(self, collection: str = "chat_messages") -> int:
        try:
            return int(self.db[collection].count_documents({}))
        except Exception:
            return 0

    def clear_messages(self, collection: str = "chat_messages") -> None:
        try:
            self.db[collection].delete_many({})
        except Exception:
            pass

    def get_redis_keys(self, pattern: str = "*") -> List[str]:
        try:
            return [k.decode() for k in self.redis.keys(pattern)]
        except Exception:
            return []

    def clear_redis(self) -> None:
        try:
            self.redis.flushdb()
        except Exception:
            pass

