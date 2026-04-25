"""Celery Worker - 异步任务执行"""
import json
import os

from celery import Celery

from src.core.config import config

redis_url = os.getenv("COMPUTEHUB_REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("computehub", broker=redis_url, backend=redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=config.executor_timeout + 30,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, name="execute_task", max_retries=3, default_retry_delay=5)
def execute_task(self, task_data: dict):
    """执行任务（Celery 异步）"""
    from src.executor.executor import Executor
    executor = Executor(sandbox_path=config.executor_sandbox)
    result = executor.execute(task_data, timeout=config.executor_timeout)

    # 更新数据库
    from src.core.database import SessionLocal
    from src.models.task import Task, TaskStatus

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_data.get("id")).first()
        if task:
            from datetime import datetime, timezone
            task.status = TaskStatus.COMPLETED if result.status.value == "COMPLETED" else TaskStatus.FAILED
            task.output = result.output
            task.error = result.error
            task.exit_code = result.exit_code
            task.duration_ms = result.duration * 1000
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
        return {
            "task_id": task_data.get("id"),
            "status": result.status.value,
            "output": result.output[:1000],
            "exit_code": result.exit_code,
            "duration_ms": result.duration * 1000,
        }
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()
