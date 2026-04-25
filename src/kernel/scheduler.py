"""简化调度器"""
import uuid
import threading
from datetime import datetime, timezone
from typing import Optional

from src.core.logging import logger
from src.kernel.load_balancer import LoadBalancer, NodeMetric, NodeStatus
from src.models.task import Task, TaskStatus


class Scheduler:
    """调度器 - 协调 LoadBalancer 分配任务到节点"""

    def __init__(self, strategy: str = "least_connections"):
        self._lb = LoadBalancer(strategy=strategy)
        self._running = False
        self._lock = threading.Lock()
        self._task_counter = 0
        logger.info("🎯 Scheduler initialized")

    def register_node(self, node_id: str, name: str, gpu_count: int = 0,
                      cpu_cores: int = 0, memory_gb: int = 0, status: NodeStatus = NodeStatus.ONLINE):
        metric = NodeMetric(
            id=node_id, name=name, gpu_count=gpu_count,
            cpu_cores=cpu_cores, memory_gb=memory_gb, status=status,
        )
        self._lb.register_node(metric)

    def update_node_metrics(self, node_id: str, **metrics):
        self._lb.update_metrics(node_id, **metrics)

    def schedule(self, task: Task) -> Optional[str]:
        """为任务选择一个节点"""
        with self._lock:
            self._task_counter += 1

        # 解析资源需求
        import json
        try:
            payload = json.loads(task.payload) if isinstance(task.payload, str) else task.payload
        except (json.JSONDecodeError, TypeError):
            payload = {}
        required_gpu = payload.get("gpu_required", 1)

        node_id = self._lb.select_node(required_gpu=required_gpu)
        if node_id:
            # 更新 LB 队列深度（模拟）
            self._lb.update_metrics(node_id, queue_depth=1)
            logger.info(f"📤 Task {task.id} scheduled -> node {node_id}")
        else:
            logger.warning(f"⚠️  No node available for task {task.id}")

        return node_id

    def get_status(self) -> dict:
        kernel_status = "RUNNING" if self._running else "STOPPED"
        return {
            "status": kernel_status,
            "load_balancer": {
                "strategy": self._lb.strategy,
                "node_count": self._lb.node_count,
                "online_count": self._lb.online_count,
            },
            "task_counter": self._task_counter,
        }

    @property
    def load_balancer(self) -> LoadBalancer:
        return self._lb
