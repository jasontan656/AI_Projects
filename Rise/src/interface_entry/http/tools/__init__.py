from __future__ import annotations

from fastapi import APIRouter

from interface_entry.http.tools.dto import ToolRequest, ToolResponse
from interface_entry.http.tools.routes import router as tool_router

__all__ = ["tool_router", "get_router", "ToolRequest", "ToolResponse"]


def get_router() -> APIRouter:
    return tool_router
