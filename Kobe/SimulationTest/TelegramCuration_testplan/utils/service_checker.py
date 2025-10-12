from __future__ import annotations

import requests
import pika
import pymongo
import redis

from test_config import TestConfig


class ServiceChecker:
    """依赖服务状态检查器"""

    def __init__(self, config: TestConfig) -> None:
        self.config = config

    def check_redis(self) -> bool:
        try:
            r = redis.from_url(self.config.REDIS_URL, socket_connect_timeout=3)
            return bool(r.ping())
        except Exception:
            return False

    def check_mongodb(self) -> bool:
        try:
            client = pymongo.MongoClient(self.config.MONGODB_URL, serverSelectionTimeoutMS=3000)
            client.server_info()
            return True
        except Exception:
            return False

    def check_rabbitmq(self) -> bool:
        try:
            conn = pika.BlockingConnection(pika.URLParameters(self.config.RABBITMQ_URL))
            conn.close()
            return True
        except Exception:
            return False

    def check_fastapi(self) -> bool:
        try:
            resp = requests.get(self.config.FASTAPI_URL.rstrip("/") + "/health", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def check_all(self) -> dict:
        return {
            "fastapi": self.check_fastapi(),
            "rabbitmq": self.check_rabbitmq(),
            "redis": self.check_redis(),
            "mongodb": self.check_mongodb(),
        }

