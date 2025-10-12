from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .models import QueryRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram-curation", tags=["TelegramCuration"])


class StartIngestRequest(BaseModel):
    sourceDir: str = Field(..., description="Path to original Telegram exports")
    workspaceDir: str = Field(..., description="Path to workspace for intermediate outputs")


@router.post("/ingest/start")
async def start_ingest(request: StartIngestRequest) -> dict[str, Any]:
    """Start ingestion for a channel export (asynchronous).

    Spec reference: Tech_Decisions.md §3.2; returns a task id.
    """
    logger.info("start_ingest: request", extra=request.model_dump())
    # In a full implementation we'd dispatch a Celery task here.
    task_id = "telegram.ingest_channel:demo"
    return {"task_id": task_id}


@router.get("/task/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Return pseudo task status for demo purposes.

    In production, query Celery backend and return progress metrics.
    """
    logger.info("get_task_status", extra={"task_id": task_id})
    return {"task_id": task_id, "status": "PENDING", "progress": 0, "stats": {}}


@router.post("/slices/query")
async def query_slices(req: QueryRequest) -> dict[str, Any]:
    """Query knowledge slices.

    This is a placeholder that returns an empty hit list.
    """
    logger.info("query_slices", extra=req.model_dump())
    return {"hits": []}

