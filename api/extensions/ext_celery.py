from datetime import timedelta

import pytz
from celery import Celery, Task  # type: ignore
from celery.schedules import crontab  # type: ignore
from configs import dify_config
from dify_app import DifyApp

"""
Celery扩展
    应用上下文集成：通过 FlaskTask 确保任务执行时有正确的应用上下文
    灵活的配置：所有关键参数都从 dify_config 中读取，便于环境适配
    多种调度方式：
        timedelta: 固定间隔执行
        crontab: 类似 Linux crontab 的定时规则
    高可用支持：通过 Redis Sentinel 配置实现高可用
    完善的日志配置：支持自定义日志格式和日志文件输出
"""
def init_app(app: DifyApp) -> Celery:
    class FlaskTask(Task):
        """
        定义一层：Flask类
        确保 Celery 任务在执行时拥有 Flask 应用上下文
        """
        def __call__(self, *args: object, **kwargs: object) -> object:
            """ 重写：在执行任务前激活 Flask 应用上下文 """
            with app.app_context():
                return self.run(*args, **kwargs)

    # Celery的broker参数
    broker_transport_options = {}
    if dify_config.CELERY_USE_SENTINEL:
        # 配置 Redis Sentinel 相关参数
        broker_transport_options = {
            "master_name": dify_config.CELERY_SENTINEL_MASTER_NAME,
            "sentinel_kwargs": {
                "socket_timeout": dify_config.CELERY_SENTINEL_SOCKET_TIMEOUT,
                "password": dify_config.CELERY_SENTINEL_PASSWORD,
            },
        }

    celery_app = Celery(
        app.name,
        task_cls=FlaskTask, # 使用自定义任务类
        broker=dify_config.CELERY_BROKER_URL,
        backend=dify_config.CELERY_BACKEND,
        task_ignore_result=True, # 忽略任务结果
    )

    # Add SSL options to the Celery configuration
    ssl_options = {
        "ssl_cert_reqs": None,
        "ssl_ca_certs": None,
        "ssl_certfile": None,
        "ssl_keyfile": None,
    }

    # 更新配置
    celery_app.conf.update(
        result_backend=dify_config.CELERY_RESULT_BACKEND,
        broker_transport_options=broker_transport_options,
        broker_connection_retry_on_startup=True,
        worker_log_format=dify_config.LOG_FORMAT,
        worker_task_log_format=dify_config.LOG_FORMAT,
        worker_hijack_root_logger=False,
        timezone=pytz.timezone(dify_config.LOG_TZ or "UTC"),
    )

    if dify_config.BROKER_USE_SSL:
        celery_app.conf.update(
            broker_use_ssl=ssl_options,  # Add the SSL options to the broker configuration
        )

    if dify_config.LOG_FILE:
        celery_app.conf.update(
            worker_logfile=dify_config.LOG_FILE,
        )

    celery_app.set_default()
    # 将Celery实例挂载到Flask扩展中
    app.extensions["celery"] = celery_app

    # 导入任务模块
    imports = [
        "schedule.clean_embedding_cache_task",
        "schedule.clean_unused_datasets_task",
        "schedule.create_tidb_serverless_task",
        "schedule.update_tidb_serverless_status_task",
        "schedule.clean_messages",
        "schedule.mail_clean_document_notify_task",
        "schedule.queue_monitor_task",
    ]
    day = dify_config.CELERY_BEAT_SCHEDULER_TIME
    # 定时任务调度表
    beat_schedule = {
        "clean_embedding_cache_task": {
            "task": "schedule.clean_embedding_cache_task.clean_embedding_cache_task",
            "schedule": timedelta(days=day),
        },
        "clean_unused_datasets_task": {
            "task": "schedule.clean_unused_datasets_task.clean_unused_datasets_task",
            "schedule": timedelta(days=day),
        },
        "create_tidb_serverless_task": {
            "task": "schedule.create_tidb_serverless_task.create_tidb_serverless_task",
            "schedule": crontab(minute="0", hour="*"),
        },
        "update_tidb_serverless_status_task": {
            "task": "schedule.update_tidb_serverless_status_task.update_tidb_serverless_status_task",
            "schedule": timedelta(minutes=10),
        },
        "clean_messages": {
            "task": "schedule.clean_messages.clean_messages",
            "schedule": timedelta(days=day),
        },
        # every Monday
        "mail_clean_document_notify_task": {
            "task": "schedule.mail_clean_document_notify_task.mail_clean_document_notify_task",
            "schedule": crontab(minute="0", hour="10", day_of_week="1"),
        },
        "datasets-queue-monitor": {
            "task": "schedule.queue_monitor_task.queue_monitor_task",
            "schedule": timedelta(
                minutes=dify_config.QUEUE_MONITOR_INTERVAL if dify_config.QUEUE_MONITOR_INTERVAL else 30
            ),
        },
    }
    # 调度配置更新
    celery_app.conf.update(beat_schedule=beat_schedule, imports=imports)

    return celery_app
