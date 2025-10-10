#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Celery application configuration for Kobe TaskQueue.

RabbitMQ is the broker. Redis can optionally serve as result backend.
Queues are durable with publisher confirms enabled. A DLX/DLQ is defined for
robust failure handling (basic skeleton; fine-tune in infra as needed).
"""

from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from .config import load_settings


settings = load_settings()  # 使用模块函数 load_settings 读取环境配置，然后绑定到变量 settings（使用模块函数）


def _build_celery() -> Celery:
    app = Celery("kobe_taskqueue")  # 使用第三方库类 Celery 创建任务应用实例（libraries）

    broker_url = settings.rabbitmq_url  # 使用赋值把配置中的 RabbitMQ 连接串绑定到变量 broker_url（assignment）
    result_backend = settings.redis_url if settings.enable_result_backend else None  # 使用条件表达式按需启用 Redis 结果后端（assignment）

    app.conf.update(  # 在对象 app.conf 上调用方法 update 批量设置 Celery 行为（method call）
        broker_url=broker_url,
        result_backend=result_backend,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        task_acks_late=True,  # 任务执行完成后再 ack，提升可靠性（control: 失败可重投）
        task_default_delivery_mode="persistent",  # 持久化消息（2）避免 Broker 重启丢失（libraries）
        task_publish_retry=True,
        broker_connection_retry_on_startup=True,
        broker_transport_options={"confirm_publish": True},  # 启用 Publisher Confirms（libraries）
        worker_prefetch_multiplier=settings.prefetch,  # 使用配置 prefetch 控制 Worker 预取（modules）
        task_time_limit=settings.time_limit,  # 硬超时（modules）
        task_soft_time_limit=settings.soft_time_limit,  # 软超时（modules）
        task_default_queue=settings.default_queue,  # 默认队列名称（assignment）
    )

    # Exchanges & queues
    tasks_ex = Exchange("tasks", type="direct", durable=True)  # 使用第三方库类 Exchange 声明直连交换机 tasks，持久化（libraries）
    dlx_ex = Exchange(settings.dlx_name, type="direct", durable=True)  # 声明死信交换机 DLX（libraries）

    default_q = Queue(  # 使用第三方库类 Queue 声明默认队列；绑定 DLX/路由键（libraries）
        settings.default_queue,
        exchange=tasks_ex,
        routing_key=settings.default_queue,
        durable=True,
        queue_arguments={"x-dead-letter-exchange": settings.dlx_name, "x-dead-letter-routing-key": settings.dlq_name},
    )
    sharded_q = Queue(  # 声明分片队列；用于分片任务路由（libraries）
        settings.sharded_queue,
        exchange=tasks_ex,
        routing_key=settings.sharded_queue,
        durable=True,
        queue_arguments={"x-dead-letter-exchange": settings.dlx_name, "x-dead-letter-routing-key": settings.dlq_name},
    )
    dlq = Queue(  # 声明死信队列；承接失败/拒收/超时消息（libraries）
        settings.dlq_name,
        exchange=dlx_ex,
        routing_key=settings.dlq_name,
        durable=True,
    )

    app.conf.task_queues = (default_q, sharded_q, dlq)  # 使用赋值把队列集合绑定到配置（assignment）

    # Simple route map for demo tasks
    app.conf.task_routes = {  # 使用赋值设置路由表；分片任务走分片队列（assignment）
        "Kobe.SharedUtility.TaskQueue.tasks.demo_sharded_job": {"queue": settings.sharded_queue, "routing_key": settings.sharded_queue},
    }

    # Ensure task module is registered
    app.autodiscover_tasks(["Kobe.SharedUtility.TaskQueue"])  # 在对象 app 上调用方法 autodiscover_tasks 自动发现任务（method call）
    return app


app = _build_celery()  # 使用模块函数 _build_celery 构建并绑定 Celery 应用（modules）
