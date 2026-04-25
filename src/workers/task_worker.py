"""Celery Worker - 含 AI 调度后分析和历史记录"""
import json
import os
from datetime import datetime, timezone

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

    from src.core.database import SessionLocal
    from src.models.task import Task, TaskStatus

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_data.get("id")).first()
        if task:
            task.status = TaskStatus.COMPLETED if result.status.value == "COMPLETED" else TaskStatus.FAILED
            task.output = result.output
            task.error = result.error
            task.exit_code = result.exit_code
            task.duration_ms = result.duration * 1000
            task.completed_at = datetime.now(timezone.utc)
            db.commit()

            # 记录 AI 调度历史
            _record_execution_history(db, task_data, task)

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


def _record_execution_history(db, task_data: dict, task):
    """记录执行历史到数据库"""
    try:
        from src.models.task_history import TaskExecutionHistory

        payload = task_data.get("payload", {})
        if isinstance(payload, str):
            payload = json.loads(payload)

        history = TaskExecutionHistory(
            task_id=task.id,
            user_id=task.user_id,
            action=task.action,
            payload_summary=json.dumps({k: payload.get(k) for k in ["framework", "code_url"] if k in payload} or {}),
            framework=payload.get("framework", "python"),
            gpu_required=payload.get("gpu_required", 1),
            memory_required_gb=payload.get("memory_required_gb", 0),
            input_size_chars=len(task.payload or ""),
            strategy_used=task_data.get("_strategy_used", "round_robin"),
            ai_confidence=task_data.get("_ai_confidence"),
            scheduled_node=task.assigned_node,
            status=task.status.value if hasattr(task.status, 'value') else str(task.status),
            duration_ms=task.duration_ms,
            exit_code=task.exit_code,
        )
        db.add(history)
        db.commit()
    except Exception as e:
        from src.core.logging import logger
        logger.warning(f"⚠️  Failed to record execution history: {e}")
        db.rollback()
