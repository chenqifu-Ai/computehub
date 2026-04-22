"""
Celery Workers - 异步任务执行
"""

from celery import Celery
from backend.core.config import settings
import structlog
import httpx
import asyncio

logger = structlog.get_logger()

# 创建 Celery 应用
celery_app = Celery(
    'computehub',
    broker=settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else 'redis://localhost:6379/0',
    backend=settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else 'redis://localhost:6379/0',
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=7200,  # 2 小时最大执行时间
    task_soft_time_limit=6900,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3)
def execute_remote_task(self, task_id: str, node_id: str, task_data: dict):
    """
    在远程节点执行任务
    
    流程:
    1. 发送任务到节点 Agent
    2. 监控执行进度
    3. 获取执行结果
    4. 更新任务状态
    """
    logger.info("Executing remote task", task_id=task_id, node_id=node_id)
    
    try:
        # TODO: 通过 gRPC/HTTP 发送任务到节点
        # 当前使用 HTTP 作为临时方案
        node_url = f"http://node-{node_id[:8]}.local:8080/execute"
        
        # 模拟任务执行（实际应该调用节点 API）
        # 这里只是示例，实际实现需要节点 Agent 配合
        logger.info("Task sent to node", node_url=node_url)
        
        # 模拟执行延迟
        # asyncio.sleep(1)  # 实际应该等待节点返回
        
        result = {
            "status": "completed",
            "task_id": task_id,
            "node_id": node_id,
            "result_path": f"/results/{task_id}/output.tar.gz",
            "execution_time_seconds": 120,
            "gpu_utilization_avg": 85.5,
        }
        
        logger.info("Task executed successfully", result=result)
        return result
        
    except Exception as exc:
        logger.error("Task execution failed", error=str(exc))
        # 重试逻辑
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True)
def monitor_task_progress(self, task_id: str, node_id: str):
    """
    监控任务执行进度
    
    定期查询节点获取任务进度
    """
    logger.debug("Monitoring task progress", task_id=task_id)
    
    try:
        # TODO: 查询节点获取进度
        progress = {
            "task_id": task_id,
            "status": "executing",
            "progress_percent": 45,
            "eta_seconds": 300,
        }
        
        return progress
        
    except Exception as exc:
        logger.error("Failed to monitor task", error=str(exc))


@celery_app.task
def cleanup_completed_tasks():
    """
    定期清理已完成的任务
    
    删除超过 7 天的已完成任务
    """
    logger.info("Cleaning up completed tasks")
    
    # TODO: 查询并清理旧任务
    # 归档结果文件
    # 释放存储空间
    
    return {"status": "ok", "cleaned_count": 0}


@celery_app.task
def check_node_health():
    """
    定期检查节点健康状态
    
    每 30 秒检查一次所有在线节点
    """
    logger.debug("Running node health check")
    
    # TODO: 查询所有在线节点
    # 发送心跳请求
    # 更新节点状态
    # 标记超时节点为 offline
    
    return {"status": "ok", "checked_nodes": 0}


# 定时任务配置（在 Celery Beat 中使用）
CELERY_BEAT_SCHEDULE = {
    'check-node-health': {
        'task': 'backend.workers.executor.check_node_health',
        'schedule': 30.0,  # 每 30 秒
    },
    'cleanup-completed-tasks': {
        'task': 'backend.workers.executor.cleanup_completed_tasks',
        'schedule': 3600.0,  # 每小时
    },
}
