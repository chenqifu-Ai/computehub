# ComputeHub Kernel - Task Scheduler
# Coordinates kernel + load balancer for task dispatch

import logging
import threading
from typing import Optional
from datetime import datetime

from src.kernel.kernel import DeterministicKernel, TaskUnit, TaskPriority
from src.kernel.load_balancer import LoadBalancer, NodeStatus, NodeMetric

logger = logging.getLogger("computehub.scheduler")


class TaskScheduler:
    """
    High-level task scheduler that coordinates kernel and load balancer.
    
    Workflow:
        1. Receive task
        2. Select best node via LoadBalancer
        3. Dispatch to Kernel's linear queue
        4. Track execution
    """
    
    def __init__(self, strategy: str = "least_utilization", queue_size: int = 1000):
        self._kernel = DeterministicKernel(queue_size=queue_size)
        self._lb = LoadBalancer(strategy=strategy)
        self._running = False
        self._task_counter = 0
        self._lock = threading.Lock()
        
        logger.info("🎯 TaskScheduler initialized")
    
    def start(self):
        """Start the scheduler."""
        self._kernel.start()
        self._running = True
        logger.info("✅ TaskScheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        self._kernel.stop()
        logger.info("⏹️  TaskScheduler stopped")
    
    def register_node(self, node_id: str, name: str, gpu_count: int = 1,
                      cpu_cores: int = 4, memory_gb: int = 16, 
                      status: NodeStatus = NodeStatus.ONLINE):
        """Register a compute node."""
        metric = NodeMetric(
            id=node_id, name=name, status=status,
            gpu_count=gpu_count, cpu_cores=cpu_cores, memory_gb=memory_gb
        )
        self._lb.register_node(metric)
    
    def submit_task(self, task_id: str, action: str, payload: dict = None,
                    priority: TaskPriority = TaskPriority.MEDIUM) -> dict:
        """
        Submit a task for execution.
        
        Returns:
            dict with task_id, status, assigned_node
        """
        if not self._running:
            return {"error": "Scheduler not running"}
        
        with self._lock:
            self._task_counter += 1
        
        # Select node
        required_gpu = payload.get("gpu_required", 1) if payload else 1
        node_id = self._lb.select_node(required_gpu)
        
        # Create task unit
        task = TaskUnit(
            id=task_id,
            action=action,
            payload=payload or {},
            priority=priority,
        )
        
        # Dispatch to kernel
        self._kernel.submit(task)
        
        result = {
            "task_id": task_id,
            "status": "SCHEDULED",
            "assigned_node": node_id,
            "priority": priority.name,
        }
        
        logger.info(f"📤 Task submitted: {task_id} -> {action} (node: {node_id})")
        return result
    
    def get_status(self) -> dict:
        """Get complete scheduler status."""
        kernel_status = self._kernel.get_status()
        node_list = self._lb.get_node_list()
        
        return {
            "status": "RUNNING" if self._running else "STOPPED",
            "kernel": kernel_status,
            "load_balancer": {
                "strategy": self._lb.strategy,
                "node_count": self._lb.node_count,
                "online_count": self._lb.online_count,
                "nodes": node_list,
            },
            "task_counter": self._task_counter,
        }
    
    @property
    def kernel(self) -> DeterministicKernel:
        return self._kernel
    
    @property
    def load_balancer(self) -> LoadBalancer:
        return self._lb
