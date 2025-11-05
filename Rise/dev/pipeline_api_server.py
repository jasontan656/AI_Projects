from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interface_entry.http.pipeline_nodes import get_router as get_pipeline_node_router

app = FastAPI(title="Rise Pipeline API Dev", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(get_pipeline_node_router())


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
