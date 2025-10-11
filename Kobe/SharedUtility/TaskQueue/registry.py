#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TaskQueue registry utilities.

Provides a stable API for extensions to:
- register Celery tasks with project-standard defaults
- query allowed task names from environment
- send tasks by name with optional allowlist enforcement

Environment variables:
- ALLOWED_TASKS: Comma-separated task names; when empty, all slug-valid names are allowed.
"""

from __future__ import annotations

import os
from typing import Callable, Iterable, Set

from .app import app


def _parse_allowed_tasks(raw: str | None) -> Set[str]:
    if not raw:
        return set()
    # Split by comma, trim whitespace, drop empties
    parts = [p.strip() for p in raw.split(",")]
    return {p for p in parts if p}


def get_allowed_tasks_from_env() -> Set[str]:
    """Return the set of allowed task names from ALLOWED_TASKS.

    Empty set means no explicit restriction at this layer (router/schema may still validate slug).
    """
    return _parse_allowed_tasks(os.getenv("ALLOWED_TASKS"))


def is_task_name_allowed(task_name: str, allowed: Iterable[str] | None = None) -> bool:
    """Check whether a task name is allowed by the environment allowlist.

    When allowlist is empty or None, treat as allowed (policy: open by default).
    """
    allowed_set: Set[str] = set(allowed) if allowed is not None else get_allowed_tasks_from_env()
    if not allowed_set:
        return True
    return task_name in allowed_set


def send_task(task_name: str, **kwargs):  # returns celery.result.AsyncResult
    """Send a task by name through the shared Celery app with allowlist enforcement."""
    if not is_task_name_allowed(task_name):
        raise ValueError(f"Task '{task_name}' is not allowed by ALLOWED_TASKS")
    return app.send_task(task_name, kwargs=kwargs)


def task(**celery_task_kwargs) -> Callable[[Callable[..., object]], object]:
    """Decorator to register a Celery task with project-default reliability settings.

    Usage:
        from Kobe.SharedUtility.TaskQueue.registry import task

        @task(name="my_task")
        def my_task(...):
            ...
    """

    default_kwargs = dict(
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
        retry_jitter=True,
        max_retries=5,
    )
    merged = {**default_kwargs, **celery_task_kwargs}

    def _decorator(func: Callable[..., object]):
        return app.task(**merged)(func)

    return _decorator


