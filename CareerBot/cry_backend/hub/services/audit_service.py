from __future__ import annotations

from typing import Any, Dict

import asyncio

from shared_utilities.mango_db.db_queue_manager import a_insert
from shared_utilities.time import Time
from hub.logger import error


class AuditService:
    """
    Audit service for logging tool invocations and orchestrator decisions.

    Note: Audit failures are logged as errors but do not block the main request flow.
    This is intentional to prevent audit issues from breaking user-facing functionality.
    Monitor error logs to ensure audit data is being captured correctly.
    """

    async def log_invocation(self, record: Dict[str, Any]) -> bool:
        record = {**record}
        record.setdefault("created_at", Time.now())
        asyncio.create_task(self._insert_with_error_log("tool_invocations", record))
        return True

    async def log_decision(self, record: Dict[str, Any]) -> bool:
        record = {**record}
        record.setdefault("created_at", Time.now())
        asyncio.create_task(self._insert_with_error_log("orchestrator_decisions", record))
        return True

    async def _insert_with_error_log(self, collection: str, document: Dict[str, Any]) -> None:
        """
        Insert audit record with explicit error logging.
        Failures are logged as ERROR (not debug) to ensure visibility.
        """
        try:
            await a_insert(collection, document)
        except (RuntimeError, ValueError, OSError) as exc:
            error(
                "audit.insert_failed",
                collection=collection,
                error=str(exc),
                document_preview=str(document)[:200],
            )


__all__ = ["AuditService"]
