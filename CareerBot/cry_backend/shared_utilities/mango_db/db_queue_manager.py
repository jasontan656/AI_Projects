import asyncio
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
import json
import os
from ..time import Time
from hub.logger import info


class _DBQueueManager:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self._stop = asyncio.Event()
        self._client: Optional[AsyncIOMotorClient] = None
        self._db = None
        self._start_lock = asyncio.Lock()
        self._max_workers = 32
        self._debug = os.getenv("DBQ_DEBUG") == "1"

    def _load_config(self) -> dict:
        cfg_path = os.path.join(os.path.dirname(__file__), "mongo_config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        active = data.get("active_profile")
        profs = data.get("profiles", {})
        prof = profs.get(active, {})
        if not prof or not prof.get("enabled", True):
            # 退回到第一个 enabled 的 profile
            for v in profs.values():
                if v.get("enabled", False):
                    prof = v
                    break
        return prof

    async def _ensure_client(self) -> None:
        if self._client is not None and self._db is not None:
            return
        prof = self._load_config()
        conn = prof.get("connection", {})
        pool = prof.get("pool", {})
        qcfg = prof.get("queue", {})
        uri = conn.get("uri", "mongodb://localhost:27017/")
        dbname = conn.get("database", "careerbot_mongodb")
        max_pool = int(pool.get("maxPoolSize", 256))
        self._max_workers = min(32, int(qcfg.get("workers", 32)))
        self._client = AsyncIOMotorClient(uri, maxPoolSize=max_pool)
        self._db = self._client[dbname]
        if self._debug:
            info("db_queue.client_initialized", database=dbname, max_workers=self._max_workers)

    async def start(self, concurrency: int = None) -> None:
        if self.workers:
            return
        self._stop.clear()
        await self._ensure_client()
        worker_n = int(concurrency or self._max_workers)
        for _ in range(max(1, worker_n)):
            self.workers.append(asyncio.create_task(self._worker()))
        if self._debug:
            info("db_queue.prewarmed_workers", worker_count=len(self.workers))

    async def _ensure_workers(self) -> None:
        if self.workers:
            return
        async with self._start_lock:
            if self.workers:
                return
            await self._ensure_client()
            # Lazily start with a single worker; we'll scale based on queue
            self.workers.append(asyncio.create_task(self._worker()))
            if self._debug:
                info("db_queue.lazy_worker_started", worker_count=len(self.workers))

    def _maybe_scale(self) -> None:
        # Scale up to the current queue size, capped by configured max workers
        target = min(self._max_workers, max(1, self.queue.qsize()))
        while len(self.workers) < target:
            self.workers.append(asyncio.create_task(self._worker()))
        if self._debug and len(self.workers) > 0:
            info("db_queue.scaled", worker_count=len(self.workers), target=target, queue_size=self.queue.qsize())

    async def stop(self) -> None:
        self._stop.set()
        for _ in self.workers:
            await self.queue.put({"kind": "__stop__"})
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    async def _worker(self) -> None:
        assert self._db is not None
        if self._debug:
            info("db_queue.worker_booted")
        while not self._stop.is_set():
            task = await self.queue.get()
            try:
                kind = task.get("kind")
                if kind == "__stop__":
                    return
                if kind == "find":
                    cur = self._db[task["collection"]].find(task["filter"], task.get("projection"))
                    res = await cur.to_list(length=None)
                    task["future"].set_result(res)
                elif kind == "aggregate":
                    cur = self._db[task["collection"]].aggregate(task["pipeline"], allowDiskUse=True)
                    res = await cur.to_list(length=None)
                    task["future"].set_result(res)
                elif kind == "insert":
                    await self._db[task["collection"]].insert_one(task["document"])
                    task["future"].set_result(True)
                elif kind == "update":
                    # 归档：仅对 user_status/user_profiles 启用，且仅针对 $set 字段
                    collection = task["collection"]
                    filter_doc = task["filter"]
                    update_doc = task["update_doc"]
                    archive_enabled = collection in ("user_status", "user_profiles")
                    if archive_enabled and "$set" in update_doc:
                        old = await self._db[collection].find_one(filter_doc)
                        if old is not None:
                            logs: Dict[str, Any] = {}
                            for k, v in update_doc["$set"].items():
                                if k in old and old[k] != v:
                                    logs[f"{k}_{Time.timestamp()}"] = old[k]
                            if logs:
                                user_id = filter_doc.get("user_id")
                                if user_id is not None:
                                    await self._db["user_archive"].update_one({"_id": user_id}, {"$set": {**logs, "user_id": user_id}}, upsert=True)
                    await self._db[collection].update_one(filter_doc, update_doc, upsert=True)
                    task["future"].set_result(True)
                else:
                    task["future"].set_exception(RuntimeError(f"unknown task kind: {kind}"))
            except Exception as e:
                if not task["future"].done():
                    task["future"].set_exception(e)
            finally:
                self.queue.task_done()

    async def a_find(self, collection: str, filter: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        await self._ensure_workers()
        await self.queue.put({"kind": "find", "collection": collection, "filter": filter, "projection": projection, "future": fut})
        self._maybe_scale()
        return await fut

    async def a_aggregate(self, collection: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        await self._ensure_workers()
        await self.queue.put({"kind": "aggregate", "collection": collection, "pipeline": pipeline, "future": fut})
        self._maybe_scale()
        return await fut

    async def a_insert(self, collection: str, document: Dict[str, Any]) -> bool:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        await self._ensure_workers()
        await self.queue.put({"kind": "insert", "collection": collection, "document": document, "future": fut})
        self._maybe_scale()
        return await fut

    async def a_update(self, collection: str, filter: Dict[str, Any], update_doc: Dict[str, Any]) -> bool:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        await self._ensure_workers()
        await self.queue.put({"kind": "update", "collection": collection, "filter": filter, "update_doc": update_doc, "future": fut})
        self._maybe_scale()
        return await fut


_mgr = _DBQueueManager()


async def start_workers(concurrency: int = 32) -> None:
    await _mgr.start(concurrency=concurrency)


async def stop_workers() -> None:
    await _mgr.stop()


async def a_find(collection: str, filter: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    return await _mgr.a_find(collection, filter, projection)


async def a_aggregate(collection: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return await _mgr.a_aggregate(collection, pipeline)


async def a_insert(collection: str, document: Dict[str, Any]) -> bool:
    return await _mgr.a_insert(collection, document)


async def a_update(collection: str, filter: Dict[str, Any], update_doc: Dict[str, Any]) -> bool:
    return await _mgr.a_update(collection, filter, update_doc)


