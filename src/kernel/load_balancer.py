"""负载均衡器 - 2策略：least_connections / round_robin"""
import threading
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from src.core.logging import logger


class NodeStatus(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class NodeMetric:
    """节点指标"""
    id: str
    name: str = ""
    status: NodeStatus = NodeStatus.OFFLINE
    gpu_count: int = 0
    gpu_utilization: float = 0.0
    memory_gb: int = 0
    memory_utilization: float = 0.0
    cpu_cores: int = 0
    cpu_utilization: float = 0.0
    queue_depth: int = 0


class LoadBalancer:
    """负载均衡器 - 支持2种调度策略"""

    VALID_STRATEGIES = ("least_connections", "round_robin")

    def __init__(self, strategy: str = "least_connections"):
        self._lock = threading.Lock()
        self._strategy = strategy if strategy in self.VALID_STRATEGIES else "least_connections"
        self._nodes: dict[str, NodeMetric] = {}
        self._round_robin_index = 0
        logger.info(f"📊 Load balancer initialized: strategy={self._strategy}")

    def register_node(self, node: NodeMetric):
        with self._lock:
            self._nodes[node.id] = node
            logger.info(f"📍 Node registered: {node.name} (GPU: {node.gpu_count}x, status: {node.status.value})")

    def unregister_node(self, node_id: str):
        with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                logger.info(f"📍 Node removed: {node_id}")

    def update_node_status(self, node_id: str, status: NodeStatus):
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].status = status

    def update_metrics(self, node_id: str, gpu_util: float = None,
                       memory_util: float = None, cpu_util: float = None,
                       queue_depth: int = None):
        with self._lock:
            if node_id in self._nodes:
                node = self._nodes[node_id]
                if gpu_util is not None:
                    node.gpu_utilization = gpu_util
                if memory_util is not None:
                    node.memory_utilization = memory_util
                if cpu_util is not None:
                    node.cpu_utilization = cpu_util
                if queue_depth is not None:
                    node.queue_depth = queue_depth

    def select_node(self, required_gpu: int = 1) -> Optional[str]:
        """选择一个可用节点"""
        with self._lock:
            available = [n for n in self._nodes.values()
                         if n.status == NodeStatus.ONLINE and n.gpu_count >= required_gpu]

            if not available:
                logger.warning(f"⚠️  No available nodes for {required_gpu}x GPU")
                return None

            if self._strategy == "least_connections":
                selected = min(available, key=lambda n: n.queue_depth)
            elif self._strategy == "round_robin":
                idx = self._round_robin_index % len(available)
                selected = available[idx]
                self._round_robin_index += 1
            else:
                selected = available[0]

            logger.info(f"🎯 Node selected: {selected.name} (queue: {selected.queue_depth})")
            return selected.id

    def get_node_list(self) -> list[dict]:
        with self._lock:
            return [{
                "id": n.id, "name": n.name,
                "status": n.status.value,
                "gpu_count": n.gpu_count,
                "gpu_utilization": n.gpu_utilization,
                "memory_utilization": n.memory_utilization,
                "cpu_utilization": n.cpu_utilization,
                "queue_depth": n.queue_depth,
            } for n in self._nodes.values()]

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def online_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.status == NodeStatus.ONLINE)

    @property
    def strategy(self) -> str:
        return self._strategy

    def set_strategy(self, strategy: str):
        if strategy not in self.VALID_STRATEGIES:
            logger.error(f"❌ Invalid strategy: {strategy}")
            return
        self._strategy = strategy
        logger.info(f"📊 Strategy changed: {strategy}")
