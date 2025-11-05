from __future__ import annotations

"""HTTP router exposing pipeline node APIs."""

from fastapi import APIRouter

from interface_entry.http.pipeline_nodes.routes import router as pipeline_node_router

__all__ = ["pipeline_node_router", "get_router"]


def get_router() -> APIRouter:
    return pipeline_node_router
