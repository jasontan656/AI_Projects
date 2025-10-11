# -*- coding: utf-8 -*-
import os
import time
from pathlib import Path

import psutil
import pytest
import structlog
import logging
from structlog.stdlib import ProcessorFormatter, LoggerFactory, add_log_level


BASE = Path(__file__).resolve().parents[1]
LOGS = BASE / "logs"
RESULTS = BASE / "results"
LOGS.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

debug_fh = logging.FileHandler(LOGS / "debug.log", encoding="utf-8")
debug_fh.setLevel(logging.DEBUG)
error_fh = logging.FileHandler(LOGS / "error.log", encoding="utf-8")
error_fh.setLevel(logging.ERROR)

fmt = ProcessorFormatter(processor=structlog.processors.JSONRenderer())
debug_fh.setFormatter(fmt)
error_fh.setFormatter(fmt)
root_logger.addHandler(debug_fh)
root_logger.addHandler(error_fh)

structlog.configure(
    processors=[
        add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.dict_tracebacks,
        ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=LoggerFactory(),
    cache_logger_on_first_use=True,
)

_debug_log_path = LOGS / "debug.log"


@pytest.fixture(scope="session", autouse=True)
def _announce_session_start():
    logger = structlog.get_logger("session")
    logger.info("session_start", base=str(BASE))
    yield
    logger.info("session_end")


@pytest.fixture()
def resource_monitor():
    proc = psutil.Process()
    start = {
        "cpu": psutil.cpu_percent(interval=None),
        "rss": proc.memory_info().rss,
        "handles": getattr(proc, "num_handles", lambda: None)() if hasattr(proc, "num_handles") else None,
        "threads": proc.num_threads(),
    }
    t0 = time.time()
    yield start
    elapsed = time.time() - t0
    end = {
        "cpu": psutil.cpu_percent(interval=None),
        "rss": proc.memory_info().rss,
        "threads": proc.num_threads(),
        "elapsed": elapsed,
    }
    logger = structlog.get_logger("resource")
    logger.info("resource_usage", start=start, end=end)


def pytest_configure(config):
    # Ensure reports write to expected default locations if options omitted
    if not config.getoption("json_report_file", default=None):
        config.option.json_report_file = str(RESULTS / "report.json")
