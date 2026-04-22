import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComputeHub-Settlement")

@dataclass
class BillingRecord:
    task_id: str
    node_id: str
    total_energy_units: float
    duration: float
    settlement_amount: float
    verified: bool

class PhysicalSettlementEngine:
    """
    Soul-Engine: Truth-Based Settlement
    Implements billing based on actual physical GPU utilization rather than wall-clock time.
    """
    def __init__(self, token_price: float = 0.001):
        self.token_price = token_price # 1 Unit = X Tokens
        self.billing_history: Dict[str, BillingRecord] = {}

    def calculate_physical_cost(self, telemetry_logs: List[dict]) -> float:
        """
        The Soul Logic: 
        Cost = Integral of (GPU_Utilization * Time) dt
        This eliminates 'Idling Fraud' where nodes claim to work but CPU/GPU is idle.
        """
        if not telemetry_logs:
            return 0.0
        
        total_weighted_util = 0.0
        time_interval = 0.0
        
        for i in range(len(telemetry_logs) - 1):
            curr = telemetry_logs[i]
            nxt = telemetry_logs[i+1]
            
            # Use GPU utilization from the telemetry snapshot
            gpu_util = curr.get("gpu", {}).get("utilization", 0) 
            if isinstance(gpu_util, dict): # handle multi-gpu
                gpu_util = sum(v.get("utilization", 0) for v in gpu_util.values()) / max(len(gpu_util), 1)
            
            delta_t = float(nxt["timestamp"]) - float(curr["timestamp"])
            total_weighted_util += (gpu_util / 100.0) * delta_t
            time_interval += delta_t
            
        return total_weighted_util * self.token_price

    def settle_task(self, task_id: str, node_id: str, telemetry_logs: List[dict], is_verified: bool):
        """
        Settle the task based on physical evidence.
        If not verified by TruthVerifier, settlement is blocked.
        """
        if not is_verified:
            logger.error(f"SETTLEMENT BLOCKED: Task {task_id} failed verification. No tokens released.")
            return None

        cost = self.calculate_physical_cost(telemetry_logs)
        duration = telemetry_logs[-1]["timestamp"] - telemetry_logs[0]["timestamp"] if telemetry_logs else 0
        
        record = BillingRecord(
            task_id=task_id,
            node_id=node_id,
            total_energy_units=cost / self.token_price if self.token_price > 0 else 0,
            duration=duration,
            settlement_amount=cost,
            verified=True
        )
        
        self.billing_history[task_id] = record
        logger.info(f"SETTLED: Task {task_id} on Node {node_id} | Amount: {cost:.4f} Tokens | Duration: {duration:.2f}s")
        return record

if __name__ == "__main__":
    # Simulation of Physical Settlement
    settler = PhysicalSettlementEngine()
    
    # Mock Telemetry Logs (Simulating a task that runs for 10s with varying util)
    logs = [
        {"timestamp": 1000, "gpu": {"utilization": 90}},
        {"timestamp": 1002, "gpu": {"utilization": 95}},
        {"timestamp": 1004, "gpu": {"utilization": 10}}, # Dropped util
        {"timestamp": 1006, "gpu": {"utilization": 92}},
        {"timestamp": 1008, "gpu": {"utilization": 98}},
        {"timestamp": 1010, "gpu": {"utilization": 95}},
    ]
    
    # Case 1: Verified execution
    print("\n--- Test 1: Verified Settlement ---")
    rec = settler.settle_task("task_soul_1", "node_alpha", logs, is_verified=True)
    print(f"Settlement Result: {rec}")
    
    # Case 2: Unverified execution (Fraud)
    print("\n--- Test 2: Unverified (Fraud) Settlement ---")
    rec_fraud = settler.settle_task("task_soul_2", "node_beta", logs, is_verified=False)
    print(f"Settlement Result: {rec_fraud}")
