from ..time import Time
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import Dict, Any, Tuple, List
from .validator import (
    validate_insert,
    validate_update_set,
    validate_push,
    validate_set_on_insert,
)
from hub.logger import error, warning

COLLECTIONS = [
    "user_archive",
    "user_chathistory",
    "user_profiles",
    "user_status",
    "auth_login_index",
]


class DatabaseOperations:
    # 复用全局连接池，避免每次实例化都新建连接
    _CLIENTS: Dict[Tuple[str, str], MongoClient] = {}

    def __init__(self, connection_string: str = "mongodb://localhost:27017/", database_name: str = "careerbot_mongodb"):
        key = (connection_string, database_name)
        client = self._CLIENTS.get(key)
        if client is None:
            client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                maxPoolSize=256,
                retryWrites=True,
            )
            self._CLIENTS[key] = client
        self.client = client
        self.db = self.client[database_name]

    def insert(self, collection: str, document: dict):
        try:
            validate_insert(collection, document)
            return self.db[collection].insert_one(document)
        except PyMongoError as e:
            error("mongodb_connector.insert_failed", collection=collection, error=str(e))
            raise

    async def a_insert(self, collection: str, document: dict) -> bool:
        validate_insert(collection, document)
        return await q.a_insert(collection, document)

    def find(self, collection: str, filter: dict, projection: dict = None):
        try:
            cur = self.db[collection].find(filter, projection)
            return list(cur)
        except PyMongoError as e:
            error("mongodb_connector.find_failed", collection=collection, error=str(e))
            raise

    async def a_find(self, collection: str, filter: dict, projection: dict | None = None) -> List[Dict[str, Any]]:
        return await q.a_find(collection, filter, projection)

    def aggregate(self, collection: str, pipeline: list[dict]):
        try:
            cur = self.db[collection].aggregate(pipeline, allowDiskUse=True)
            return list(cur)
        except PyMongoError as e:
            error("mongodb_connector.aggregate_failed", collection=collection, error=str(e))
            raise

    async def a_aggregate(self, collection: str, pipeline: List[dict]) -> List[Dict[str, Any]]:
        return await q.a_aggregate(collection, pipeline)

    def update(self, collection: str, filter: dict, data: dict):
        try:
            col = self.db[collection]
            old = col.find_one(filter)
            if old is None:
                if "$setOnInsert" not in data:
                    error("mongodb_connector.pre_update_read_failed", collection=collection, filter=filter)
                    raise ValueError("Old document not found; archive failed; update aborted")
                old = {}
            archive_enabled = collection in ("user_status", "user_profiles")
            user_id = filter.get("user_id") if archive_enabled else None
            if archive_enabled and user_id is None:
                error("mongodb_connector.archive_missing_user_id", collection=collection, filter=filter)
                raise ValueError("Missing user_id; archive failed; update aborted")
            if "$set" in data and isinstance(data["$set"], dict):
                validate_update_set(collection, data["$set"])
            elif "$push" in data and isinstance(data["$push"], dict):
                validate_push(collection, data["$push"])
            elif "$setOnInsert" in data and isinstance(data["$setOnInsert"], dict):
                validate_set_on_insert(collection, data["$setOnInsert"])
            else:
                raise ValueError("Only $set, $push(email_verification.history) and $setOnInsert are allowed for auth strict mode")

            logs: Dict[str, Any] = {}
            if archive_enabled and "$set" in data and old:
                for k, v in data["$set"].items():
                    if k in old and old[k] != v:
                        logs[f"{k}_{Time.timestamp()}"] = old[k]
            if archive_enabled and logs:
                self.db["user_archive"].update_one({"_id": user_id}, {"$set": {**logs, "user_id": user_id}}, upsert=True)
            return col.update_one(filter, data, upsert=True)
        except PyMongoError as e:
            error("mongodb_connector.update_failed", collection=collection, error=str(e))
            raise

    async def a_update(self, collection: str, filter: dict, data: dict) -> bool:
        archive_enabled = collection in ("user_status", "user_profiles")
        user_id = filter.get("user_id") if archive_enabled else None
        if archive_enabled and user_id is None:
            raise ValueError("Missing user_id; archive failed")
        if "$set" in data and isinstance(data["$set"], dict):
            validate_update_set(collection, data["$set"])
        elif "$push" in data and isinstance(data["$push"], dict):
            validate_push(collection, data["$push"])
        elif "$setOnInsert" in data and isinstance(data["$setOnInsert"], dict):
            validate_set_on_insert(collection, data["$setOnInsert"])
        else:
            raise ValueError("Only $set, $push(email_verification.history) and $setOnInsert are allowed for auth strict mode")
        return await q.a_update(collection, filter, data)

    def ensure_indexes(self):
        try:
            # Heal user_chathistory wrong unique indexes
            try:
                uch = self.db["user_chathistory"]
                existing = list(uch.list_indexes())
                for idx in existing:
                    name = idx.get("name")
                    keys = idx.get("key")
                    unique = bool(idx.get("unique"))
                    if unique and keys and list(keys.items()) == [("user_id", 1)]:
                        warning("mongodb_connector.fix_wrong_index", collection="user_chathistory", index=name, key="user_id")
                        uch.drop_index(name)
                    if unique and keys and list(keys.items()) == [("user_id", 1), ("created_at", -1)]:
                        warning("mongodb_connector.fix_wrong_index", collection="user_chathistory", index=name, key="user_id_created_at")
                        uch.drop_index(name)
            except Exception as e:
                warning("mongodb_connector.inspect_indexes_failed", collection="user_chathistory", error=str(e))

            # user_status 索引（按设计清单）
            self.db["user_status"].create_index([("user_id", 1)], unique=True, name="user_id_unique")
            self.db["user_status"].create_index("auth.auth_username", name="auth_username_index")
            self.db["user_status"].create_index([("user_id", 1), ("email_verification.history.code", 1)], name="user_verif_code")
            # 保留：唯一(user_id, flow_id)
            self.db["user_status"].create_index([("user_id", 1), ("flow_id", 1)], unique=True, name="user_flow_unique")

            # user_chathistory indexes
            self.db["user_chathistory"].create_index("user_id", name="user_id_index")
            self.db["user_chathistory"].create_index("created_at", name="created_at_index")
            self.db["user_chathistory"].create_index([("user_id", 1), ("created_at", -1)], name="user_createdat_desc")

            # user_profiles 索引
            self.db["user_profiles"].create_index("user_id", unique=True, name="user_id_unique")
            self.db["user_profiles"].create_index("profile.email", name="profile_email_index")

            self.db["user_archive"].create_index("user_id", name="user_id_index")

            # auth_login_index 索引
            self.db["auth_login_index"].create_index("auth_username", unique=True, name="auth_username_unique")
            self.db["auth_login_index"].create_index("user_id", name="user_id_index")
        except Exception as e:
            error("mongodb_connector.ensure_indexes_failed", error=str(e))


