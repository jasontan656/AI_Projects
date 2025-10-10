#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MongoDB access helpers for TaskQueue.

Provides collection handles and an index bootstrap routine.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/kobe")  # 使用标准库函数 os.getenv 读取 Mongo 连接串（libraries）
    return MongoClient(uri)  # 使用第三方库类 MongoClient 创建客户端；结果由 lru_cache(1) 复用（libraries）


def get_db() -> Database:
    name = os.getenv("MONGODB_DATABASE", "kobe")  # 使用环境变量 MONGODB_DATABASE 指定数据库名（libraries）
    return get_client()[name]  # 在对象 client 上使用下标访问选取数据库（method/dict 访问）


def coll_task_dedup() -> Collection:
    return get_db()["TaskDedup"]  # 选取集合 TaskDedup；用于指纹去重（modules）


def coll_task_checkpoint() -> Collection:
    return get_db()["TaskCheckpoint"]  # 选取集合 TaskCheckpoint；记录分片进度（modules）


def coll_pending_tasks() -> Collection:
    return get_db()["PendingTasks"]  # 选取集合 PendingTasks；含 lease_until TTL（modules）


def coll_task_error_log() -> Collection:
    return get_db()["TaskErrorLog"]  # 选取集合 TaskErrorLog；存储失败原因（modules）


def coll_raw_payload() -> Collection:
    return get_db()["RawPayload"]  # 选取集合 RawPayload；原始载荷归档（modules）


def ensure_indexes() -> None:
    """Create minimal indexes to support basic semantics.

    - TaskDedup.task_fingerprint: unique
    - TaskCheckpoint: (shard_key, sub_key) compound index
    - PendingTasks.task_key: unique, TTL on lease_until (requires TTL monitor)
    """
    coll_task_dedup().create_index("task_fingerprint", unique=True)  # 在集合上调用方法 create_index 建立唯一索引（method call）
    coll_task_checkpoint().create_index([("shard_key", 1), ("sub_key", 1)], unique=False)  # 复合索引（method call）
    coll_pending_tasks().create_index("task_key", unique=True)  # 待处理任务唯一键（method call）
    # TTL index example; requires `expireAfterSeconds` and a datetime field
    coll_pending_tasks().create_index("lease_until", expireAfterSeconds=0)  # TTL 索引；由 Mongo TTL 监视器生效（method call）
