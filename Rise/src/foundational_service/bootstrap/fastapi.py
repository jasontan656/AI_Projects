"""FastAPI integration helpers."""

from __future__ import annotations

from fastapi import FastAPI

__all__ = ["create_base_app", "create_app"]


def create_base_app() -> FastAPI:
    """Return the base FastAPI instance used across services."""

    return FastAPI(title="Rise Infra Base", version="1.0.0")


def create_app() -> FastAPI:
    """Alias matching legacy entrypoints."""

    return create_base_app()
