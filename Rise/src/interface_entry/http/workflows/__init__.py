from __future__ import annotations

from fastapi import APIRouter

from interface_entry.http.workflows.dto import WorkflowRequest, WorkflowResponse
from interface_entry.http.workflows.routes import router as workflow_router

__all__ = ["workflow_router", "get_router", "WorkflowRequest", "WorkflowResponse"]


def get_router() -> APIRouter:
    return workflow_router
