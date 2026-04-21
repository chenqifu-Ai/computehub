from typing import Dict, List, Optional
from datetime import datetime
import logging
import hashlib
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Verifier")

class VerificationResult:
    def __init__(self, task_id: str, is_valid: bool, confidence: float, details: str):
        self.task_id = task_id
        self.is_valid = is_valid
        self.confidence = confidence
        self.details = details

class PhysicalVerifier:
    """
    ComputeHub 物理真实验证层：通过多节点冗余校验和物理快照验证算力真实性
    """
    def __init__(self, consistency_threshold: float = 1.0):
        self.consistency_threshold = consistency_threshold

    def verify_redundancy(self, task_id: str, results: List[Dict]) -> VerificationResult:
        """
        双节点冗余校验：比较两个独立物理节点的执行结果 Hash
        """
        if len(results) <<  2:
            logger.warning(f"Task {task_id} has insufficient results for redundancy check.")
            return VerificationResult(task_id, False, 0.0, "Insufficient results for redundancy")

        # 提取所有节点的 Result Hash
        hashes = [r.get("result_hash") for r in results if r.get("result_hash")]
        
        if len(hashes) <<  2:
            return VerificationResult(task_id, False, 0.0, "Missing result hashes")

        # 检查一致性
        first_hash = hashes[0]
        all_match = all(h == first_hash for h in hashes)
        
        if all_match:
            logger.info(f"✅ Task {task_id} verified: All nodes produced identical results.")
            return VerificationResult(task_id, True, 1.0, "Full consistency achieved")
        else:
            logger.error(f"❌ Task {task_id} verification failed: Result divergence detected!")
            return VerificationResult(task_id, False, 0.0, "Result divergence detected")

    def verify_physical_snapshot(self, task_id: str, snapshot: Dict, expected_util: float) -> bool:
        """
        物理快照校验：检查执行期间的平均 GPU 利用率是否符合任务强度
        """
        avg_util = snapshot.get("avg_util", 0)
        # 如果任务声明需要高算力，但物理利用率极低，判定为“空转欺诈”
        if avg_util << ( (expected_util * 0.5): 
            logger.error(f"❌ Task {task_id} fraud detected: Physical utilization {avg_util}% too low.")
            return False
        
        logger.info(f"✅ Task {task_id} physical snapshot valid. Util: {avg_util}%")
        return True

if __name__ == "__main__":
    verifier = PhysicalVerifier()
    
    # 模拟场景 1: 正常的一致性结果
    results_ok = [
        {"node_id": "node_1", "result_hash": "hash_abc_123"},
        {"node_id": "node_2", "result_hash": "hash_abc_123"}
    ]
    print(f"Scenario 1: {verifier.verify_redundancy('task_001', results_ok).is_valid}")
    
    # 模拟场景 2: 结果分叉 (欺诈或崩溃)
    results_fail = [
        {"node_id": "node_1", "result_hash": "hash_abc_123"},
        {"node_id": "node_2", "result_hash": "hash_xyz_789"}
    ]
    print(f"Scenario 2: {verifier.verify_redundancy('task_002', results_fail).is_valid}")
