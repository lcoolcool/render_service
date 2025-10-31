"""Celery应用配置（Windows兼容）"""
from celery import Celery
from kombu import Queue
from app.config import settings

# 创建Celery应用实例
celery_app = Celery(
    "render_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 任务结果配置
    result_expires=3600,  # 结果保留1小时

    # 优先级队列配置
    task_default_priority=5,
    task_queue_max_priority=10,

    # 定义三个优先级队列
    task_queues=(
        Queue("high_priority", routing_key="high", priority=10),
        Queue("default", routing_key="default", priority=5),
        Queue("low_priority", routing_key="low", priority=1),
    ),

    # 任务路由
    task_routes={
        "app.celery_app.tasks.render_task": {
            "queue": "default",
        },
        "app.celery_app.tasks.generate_thumbnail": {
            "queue": "low_priority",
        },
    },

    # 任务重试配置
    task_acks_late=True,  # 任务执行后才确认
    task_reject_on_worker_lost=True,  # worker丢失时拒绝任务

    # Worker配置
    worker_prefetch_multiplier=1,  # 每次只取一个任务，确保优先级生效
    worker_max_tasks_per_child=50,  # 每个worker子进程最多执行50个任务后重启

    # 任务执行时间限制
    task_time_limit=3600 * 24,  # 硬限制：24小时
    task_soft_time_limit=3600 * 23,  # 软限制：23小时
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.celery_app"])
