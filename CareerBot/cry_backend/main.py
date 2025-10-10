"""
Career Bot Hub - Main Entry Point

This module serves as the main entry point for the Career Bot FastAPI application.
It imports the app factory from hub.hub and provides the application instance for uvicorn.

Usage:
    uvicorn main:app --reload
    or
    python main.py
"""
from __future__ import annotations

import os

from hub.hub import create_app
from hub.logger import info

# Create the FastAPI application instance
app = create_app()
info("main.app.initialized")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "1") == "1"

    info(
        "main.uvicorn.start",
        host=host,
        port=port,
        reload=reload,
    )

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
    )
