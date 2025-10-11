#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Celery application configuration for Kobe TaskQueue (default-aligned).

- 使用 Celery 默认交换机/队列（exchange='celery', queue='celery', routing_key='celery'）。
- 不定义自定义 Exchange/Queue/Routes，避免发布/消费不对齐。
- Broker 由 RABBITMQ_URL 控制，结果后端按配置启用（默认开启，可用环境覆盖）。
"""

from __future__ import annotations

from celery import Celery
from .config import load_settings


settings = load_settings()


def _build_celery() -> Celery:
    app = Celery("kobe_taskqueue")

    broker_url = settings.rabbitmq_url
    result_backend = settings.redis_url if settings.enable_result_backend else None

    app.conf.update(
        broker_url=broker_url,
        result_backend=result_backend,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        task_acks_late=True,
        task_default_delivery_mode="persistent",
        task_publish_retry=True,
        broker_connection_retry_on_startup=True,
        broker_transport_options={"confirm_publish": True},
        worker_prefetch_multiplier=settings.prefetch,
        task_time_limit=settings.time_limit,
        task_soft_time_limit=settings.soft_time_limit,
        # 强制对齐默认队列名称（Celery 默认即为 'celery'），显式设置以减少歧义
        task_default_queue="celery",
    )

    # 不做任何自定义路由与队列声明，保持与 Celery 默认完全一致

    # Ensure task module is registered
    app.autodiscover_tasks(["Kobe.SharedUtility.TaskQueue"])
    return app


app = _build_celery()
