from __future__ import annotations

from fastapi import APIRouter

from interface_entry.http.stages.dto import StageRequest, StageResponse
from interface_entry.http.stages.routes import router as stage_router

__all__ = ["stage_router", "get_router", "StageRequest", "StageResponse"]


def get_router() -> APIRouter:
    return stage_router
