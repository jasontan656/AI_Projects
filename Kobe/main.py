#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""FastAPI app entry with RichLogger initialization.

Action-narrative comments explain intent and flow using ASCII to avoid
mojibake on terminals with limited encodings.
"""

from __future__ import annotations  # Enable forward-annotation typing; no runtime effect.

# Use standard logging as the unified app logging API.
import logging  # Provide getLogger for module-level logger usage.
# Read simple runtime settings from environment (HOST/PORT/RELOAD/LOG_LEVEL).
import os  # Access environment variables in a portable way.
from pathlib import Path  # Resolve and switch working directory reliably.

# FastAPI app object and JSON response helpers.
from fastapi import FastAPI  # Create the ASGI application instance.
from fastapi.responses import JSONResponse  # Shape explicit JSON responses.

# Uvicorn is used to serve the ASGI app when running this module directly.
import uvicorn  # Also usable via CLI: `uvicorn Kobe.main:app`.

# RichLogger: centralized pretty logging and rich tracebacks per project charter.
from Kobe.SharedUtility.RichLogger import init_logging, install_traceback
try:  # Optional dependency per project constitution
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional
    load_dotenv = None
try:  # Optional metrics
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:  # pragma: no cover
    Instrumentator = None


# Create the application object with the conventional name `app` for uvicorn.
app = FastAPI()  # 使用第三方库类 FastAPI 创建应用实例；便于 `uvicorn Kobe.main:app` 发现（libraries）


@app.get("/health")
def healthcheck() -> JSONResponse:
    """Simple health probe with a stable JSON contract.

    Returns HTTP 200 and a body {"status": "ok"} without auth requirements.
    """
    return JSONResponse({"status": "ok"})  # 使用第三方库类 JSONResponse 返回固定 JSON（libraries）


def _bootstrap_logging_once() -> None:
    """Initialize unified logging and rich tracebacks once at import time.

    - Respects LOG_LEVEL when provided; defaults to INFO otherwise.
    - Avoids duplicate handlers by relying on RichLogger's idempotent init.
    """
    # Load .env early to make env vars available for logging level and others
    if load_dotenv is not None:
        try:
            env_path = Path(__file__).resolve().parent / ".env"  # 使用 pathlib 组合 .env 文件路径（modules）
            if env_path.exists():
                load_dotenv(env_path)  # 在 dotenv 上调用函数 load_dotenv 预加载环境变量（libraries）
        except Exception:
            pass

    init_logging(level=os.getenv("LOG_LEVEL", "INFO"))  # 使用模块函数 init_logging 以 LOG_LEVEL 初始化统一日志（modules/libraries）
    install_traceback()  # 使用模块函数 install_traceback 安装更友好的 Rich traceback（modules）
    logging.getLogger(__name__).info("App logging initialized.")


# Perform bootstrap on import so both CLI and worker modes benefit uniformly.
_bootstrap_logging_once()

# Pydantic v3 is mandated by BackendConstitution; no compatibility shim needed.

# Include API routers after logging is ready so route import side-effects are logged
try:
    from .routers.task import router as task_router  # noqa: WPS433 - local import intended

    app.include_router(task_router)  # 在对象 app 上调用方法 include_router 挂载 /task 路由（method call）
except Exception:  # pragma: no cover - keep app importable when partial deps missing
    # In early bootstrap or minimal environments we still want /health to work.
    pass

# Expose Prometheus metrics at /metrics when available
if Instrumentator is not None:
    try:
        Instrumentator().instrument(app).expose(app)  # 在对象 Instrumentator 上链式调用 instrument/expose 暴露 /metrics（libraries）
    except Exception:
        pass


if __name__ == "__main__":
    # Resolve runtime settings from env for a frictionless local dev loop.
    host = os.getenv("UVICORN_HOST", "127.0.0.1")  # 使用 os.getenv 读取主机；缺省回环地址（libraries）
    port_str = os.getenv("UVICORN_PORT", "8000")  # 使用 os.getenv 读取端口字符串（libraries）
    reload_flag = os.getenv("UVICORN_RELOAD", "0")  # 使用 os.getenv 读取热重载开关（libraries）

    try:
        port = int(port_str)  # 使用 python 内置函数 int 把端口字符串转换为整数（builtins）
    except ValueError:
        port = 8000

    reload = reload_flag.lower() in {"1", "true", "yes", "on"}  # 使用字符串 lower 与集合成员测试解析布尔（builtins）

    # Ensure process starts from the Kobe/ directory for consistent relative paths.
    kobe_dir = Path(__file__).resolve().parent  # 使用 pathlib 定位 Kobe 目录（modules）
    if Path.cwd() != kobe_dir:
        os.chdir(kobe_dir)  # 在 os 模块上调用 chdir 切换工作目录（libraries）

    # Limit uvicorn's file watcher to the Kobe/ directory only when reload is enabled.
    watch_dirs = [str(kobe_dir)] if reload else None  # 使用条件表达式在启用热重载时限制监控目录（assignment）

    logging.getLogger(__name__).info(
        "Starting uvicorn server",
        extra={
            "host": host,
            "port": port,
            "reload": reload,
            "cwd": str(Path.cwd()),
            "watch_dirs": watch_dirs,
        },
    )

    # Run the embedded server; for production prefer CLI: `uvicorn Kobe.main:app`.
    uvicorn.run(  # 使用第三方库函数 uvicorn.run 启动 ASGI 服务（libraries）
        app,
        host=host,
        port=port,
        reload=reload,
        reload_dirs=watch_dirs,
    )
