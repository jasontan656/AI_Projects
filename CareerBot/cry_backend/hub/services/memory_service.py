from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Optional

from shared_utilities.mango_db.db_queue_manager import a_find, a_update


_TEST_MODE = os.getenv("HUB_TEST_MODE") == "1"
_TEST_MEMORY: Dict[tuple[str, str], Dict[str, Any]] = {}
_TEST_LOCK = asyncio.Lock()


class MemoryService:
    @staticmethod
    def _key(user_id: str, session_id: str) -> Dict[str, str]:
        return {"user_id": user_id, "session_id": session_id}

    async def get_context(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        if _TEST_MODE:
            async with _TEST_LOCK:
                return _TEST_MEMORY.get((user_id, session_id))
        docs = await a_find("session_memory", self._key(user_id, session_id))
        return docs[0] if docs else None

    async def set_context(self, user_id: str, session_id: str, context: Dict[str, Any]) -> bool:
        if _TEST_MODE:
            async with _TEST_LOCK:
                _TEST_MEMORY[(user_id, session_id)] = {
                    **self._key(user_id, session_id),
                    "context": context,
                }
                return True
        doc = {**self._key(user_id, session_id), "context": context}
        return await a_update("session_memory", self._key(user_id, session_id), {"$set": doc})

    async def append_memory(self, user_id: str, session_id: str, item: Dict[str, Any]) -> bool:
        if _TEST_MODE:
            async with _TEST_LOCK:
                doc = _TEST_MEMORY.setdefault(
                    (user_id, session_id),
                    {**self._key(user_id, session_id), "messages": []},
                )
                doc.setdefault("messages", []).append(item)
                return True
        update = {
            "$setOnInsert": {**self._key(user_id, session_id)},
            "$push": {"messages": item},
        }
        return await a_update("session_memory", self._key(user_id, session_id), update)


__all__ = ["MemoryService"]
