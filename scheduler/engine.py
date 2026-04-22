import logging
from typing import Dict, List, Optional, Tuple
import time

from .state_machine import TaskStateMachine, TaskState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComputeHub-Scheduler")

class SchedulerEngine:
    """
    Soul-Engine: Robust Scheduling
    Implements L3 Latency Matching and Regional Circuit Breaking.
    """
    def __init__(self, registry):
        self.registry = registry # Reference to api.registry.NodeRegistry
        self.fsm = TaskStateMachine()
        # latency_matrix[node_id] = latency_ms
        self.latency_matrix: Dict[str, float] = {}
        # region_health[region] = error_rate (0.0 to 1.0)
        self.region_health: Dict[str, float] = {}

    def update_latency(self, node_id: str, latency: float):
        self.latency_matrix[node_id] = latency

    def report_node_failure(self, node_id: str, region: str):
        """Update regional health for circuit breaking"""
        # Simplified: increase error rate for the region
        current_error = self.region_health.get(region, 0.0)
        self.region_health[region] = min(1.0, current_error + 0.1)
        logger.warning(f"Region {region} health degraded: {self.region_health[region]}")

    def _is_region_broken(self, region: str) -> bool:
        return self.region_health.get(region, 0.0) > 0.3

    def match_node(self, task_id: str, requirements: dict) -> Optional[str]:
        """
        L3 Matching Logic:
        1. Filter by hardware requirements
        2. Filter by Region Circuit Breaker
        3. Sort by minimum physical latency
        """
        nodes = self.registry.get_all_nodes()
        candidates = []

        for node in nodes:
            node_id = node["node_id"]
            # 1. Hardware Check (simplified)
            if not self._check_requirements(node, requirements):
                continue
            
            # 2. Circuit Breaker Check
            region = node["hardware_info"].get("region", "global")
            if self._is_region_broken(region):
                logger.info(f"Circuit Breaker: Skipping node {node_id} in broken region {region}")
                continue
            
            # 3. Latency Score
            latency = self.latency_matrix.get(node_id, 9999.0)
            candidates.append((node_id, latency))

        if not candidates:
            return None

        # Sort by latency ASC
        candidates.sort(key=lambda x: x[1])
        best_node = candidates[0][0]
        logger.info(f"L3 Match: Task {task_id} -> Node {best_node} (Latency: {candidates[0][1]}ms)")
        return best_node

    def _check_requirements(self, node: dict, reqs: dict) -> bool:
        # Simplified hardware matching logic
        hw = node["hardware_info"]
        # Example: match GPU model if requested
        if "gpu" in reqs and reqs["gpu"] not in str(hw.get("gpus", "")):
            return False
        return True

    def schedule_task(self, task_name: str, requirements: dict) -> Tuple[Optional[str], str]:
        """
        The Scheduling Pipeline:
        Create Task -> Match Node -> Transition to DISPATCHED
        """
        task_id = self.fsm.create_task(task_name, requirements)
        
        node_id = self.match_node(task_id, requirements)
        if not node_id:
            self.fsm.transition(task_id, TaskState.FAILED, "No suitable physical node found")
            return None, task_id

        # Anchor the node and transition state
        # (TaskContext updated via fsm)
        ctx = self.fsm.active_tasks[task_id]
        ctx.assigned_node = node_id
        
        if self.fsm.transition(task_id, TaskState.DISPATCHED, f"Matched to node {node_id}"):
            return node_id, task_id
        
        return None, task_id

if __name__ == "__main__":
    # Mock Registry for testing
    class MockRegistry:
        def get_all_nodes(self):
            return [
                {"node_id": "node_A", "hardware_info": {"region": "US-East", "gpus": ["A100"]}},
                {"node_id": "node_B", "hardware_info": {"region": "US-East", "gpus": ["A100"]}},
                {"node_id": "node_C", "hardware_info": {"region": "EU-West", "gpus": ["A100"]}},
            ]
    
    reg = MockRegistry()
    engine = SchedulerEngine(reg)
    
    # Setup latency
    engine.update_latency("node_A", 120.0)
    engine.update_latency("node_B", 45.0)
    engine.update_latency("node_C", 10.0)
    
    # Test 1: Optimal match (should be node_C)
    print("\n--- Test 1: Optimal Latency Match ---")
    node, tid = engine.schedule_task("Training-1", {"gpu": "A100"})
    print(f"Result: Task {tid} assigned to {node}")
    
    # Test 2: Circuit Breaker (break EU-West)
    print("\n--- Test 2: Regional Circuit Breaker ---")
    engine.report_node_failure("node_C", "EU-West")
    engine.report_node_failure("node_C", "EU-West")
    engine.report_node_failure("node_C", "EU-West")
    engine.report_node_failure("node_C", "EU-West")
    
    node, tid = engine.schedule_task("Training-2", {"gpu": "A100"})
    print(f"Result: Task {tid} assigned to {node} (Expected: node_B)")
