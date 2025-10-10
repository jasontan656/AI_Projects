from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from shared_utilities.mango_db.db_queue_manager import a_insert, a_find
from shared_utilities.time import Time


class FormService:
    async def issue_submission(self, step_id: str, ttl_minutes: int = 10) -> Dict[str, Any]:
        sid = Time.timestamp()
        doc = {
            "submission_id": sid,
            "step_id": step_id,
            "errors": {},
            "expires_at": Time.now_plus(timedelta(minutes=ttl_minutes)),
        }
        await a_insert("form_submissions", doc)
        return doc

    async def validate_submission(self, submission_id: str) -> bool:
        docs = await a_find("form_submissions", {"submission_id": submission_id})
        if not docs:
            return False
        doc = docs[0]
        return doc.get("expires_at", Time.now()) > Time.now()


__all__ = ["FormService"]
