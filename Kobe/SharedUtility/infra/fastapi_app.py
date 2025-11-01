"""
Base FastAPI factory per 02.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

from fastapi import FastAPI


def create_base_app() -> FastAPI:
    app = FastAPI(title="Kobe Infra Base", version="1.0.0")
    return app


# 为对齐 WorkPlan/16.md 接口锚点，提供 create_app 别名
def create_app() -> FastAPI:
    return create_base_app()


