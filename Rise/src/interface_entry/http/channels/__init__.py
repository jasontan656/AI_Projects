from __future__ import annotations

from fastapi import APIRouter

from interface_entry.http.channels.routes import router

__all__ = ["get_router"]


def get_router() -> APIRouter:
    return router
