from __future__ import annotations

"""HTTP router exposing prompt APIs."""

from fastapi import APIRouter

from interface_entry.http.prompts.routes import router as prompt_router

__all__ = ["get_router"]


def get_router() -> APIRouter:
    return prompt_router
