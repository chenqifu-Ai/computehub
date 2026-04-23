# ComputeHub Kernel - Load Balancer
# Distributes tasks across available nodes

import logging
import threading
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("computehub.kernel")


class NodeStatus(Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class NodeMetric:
    """Node capacity metrics for load balancing."""
    name: str
    id: str
    status: NodeStatus
    gpu_count: int = 0
    gpu_utilization: float = 0.0
    memory_gb: int = 0
    memory_utilization: float = 0.0
    cpu_cores: int = 0
    cpu_utilization: float = 0.0
    queue_depth: int = 0
    network_latency_ms: float = 0.0


class LoadBalancer:
    """
    Load balancer for distributing tasks across compute nodes.
    
    Strategies:
    1. Least Connections - assign to node with fewest active tasks
    2. Least Utilization - assign to node with lowest GPU/CPU utilization
    3. Round Robin - distribute evenly
    4. Geographical - prefer nearby nodes
    """
    
    def __init__(self, strategy: str = "least_utilization"):
        self._lock = threading.Lock()
        self._strategy = strategy
        self._nodes: dict[str, NodeMetric] = {}
        self._round_robin_index = 0
        
        logger.info(f"📊 Load balancer initialized: strategy={strategy}")
    
    def register_node(self, node: NodeMetric):
        """Register a compute node."""
        with self._lock:
            self._nodes[node.id] = node
            logger.info(f"📍 Node registered: {node.name} (GPU: {node.gpu_count}x, status: {node.status.value})")
    
    def unregister_node(self, node_id: str):
        """Remove a compute node."""
        with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                logger.info(f"📍 Node removed: {node_id}")
    
    def update_node_status(self, node_id: str, status: NodeStatus):
        """Update a node's status."""
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].status = status
    
    def update_metrics(self, node_id: str, gpu_util: float = None, 
                       memory_util: float = None, cpu_util: float = None,
                       queue_depth: int = None):
        """Update a node's resource metrics."""
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
        """
        Select the best node for the task.
        
        Returns:
            node_id: ID of selected node, or None if no suitable node
        """
        with self._lock:
            available = [
                n for n in self._nodes.values()
                if n.status == NodeStatus.ONLINE
                and n.gpu_count >= required_gpu
            ]
            
            if not available:
                logger.warning(f"⚠️  No available nodes for {required_gpu}x GPU")
                return None
            
            # Apply selection strategy
            if self._strategy == "least_utilization":
                selected = min(available, key=lambda n: n.gpu_utilization)
            elif self._strategy == "least_connections":
                selected = min(available, key=lambda n: n.queue_depth)
            elif self._strategy == "round_robin":
                selected = available[self._round_robin_index % len(available)]
                self._round_robin_index += 1
            else:
                selected = available[0]  # First available
            
            logger.info(f"🎯 Node selected: {selected.name} (GPU util: {selected.gpu_utilization:.1f}%)")
            return selected.id
    
    def get_node_list(self) -> list[dict]:
        """Get list of all registered nodes."""
        with self._lock:
            return [
                {
                    "id": n.id,
                    "name": n.name,
                    "status": n.status.value,
                    "gpu_count": n.gpu_count,
                    "gpu_utilization": n.gpu_utilization,
                    "memory_utilization": n.memory_utilization,
                    "cpu_utilization": n.cpu_utilization,
                    "queue_depth": n.queue_depth,
                }
                for n in self._nodes.values()
            ]
    
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
        """Change load balancing strategy."""
        valid = ["least_utilization", "least_connections", "round_robin", "geographical"]
        if strategy not in valid:
            logger.error(f"❌ Invalid strategy: {strategy}")
            return
        
        self._strategy = strategy
        logger.info(f"📊 Load balancer strategy changed: {strategy}")
