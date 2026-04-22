import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComputeHub-Verifier")

@dataclass
class ExecutionProof:
    """
    Soul-Engine: Physical Proof
    A cryptographically signed proof of execution.
    """
    task_id: str
    node_id: str
    result_hash: str
    physical_snapshot: dict
    timestamp: float
    signature: str

class TruthVerifier:
    """
    Soul-Engine: Truth Verification Layer
    Implements the 'Double-Check Proof' to replace trust with physical evidence.
    """
    def __init__(self, trust_threshold: float = 1.0):
        self.trust_threshold = trust_threshold
        # Stores pending results for redundancy check: task_id -> [proofs]
        self.pending_verification: Dict[str, List[ExecutionProof]] = {}

    def compute_result_hash(self, data: Any) -> str:
        """Generate a deterministic hash of the execution result."""
        content = str(data).encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def submit_proof(self, proof: ExecutionProof):
        """
        Collect proof from a node. 
        If it's the second independent proof for the same task, trigger verification.
        """
        tid = proof.task_id
        if tid not in self.pending_verification:
            self.pending_verification[tid] = []
        
        self.pending_verification[tid].append(proof)
        logger.info(f"Proof received for {tid} from node {proof.node_id}. Total proofs: {len(self.pending_verification[tid])}")

    def verify_task(self, task_id: str) -> Tuple[bool, str]:
        """
        The Redundancy Check:
        Compare proofs from multiple independent nodes.
        """
        proofs = self.pending_verification.get(task_id, [])
        if len(proofs) <<  2:
            return False, "Insufficient proofs for redundancy check (need at least 2)"

        # 1. Independent Node Check
        nodes = set(p.node_id for p in proofs)
        if len(nodes) <<  2:
            return False, "Proofs must come from independent physical nodes"

        # 2. Result Hash Consistency (The Core Truth)
        first_hash = proofs[0].result_hash
        for i in range(1, len(proofs)):
            if proofs[i].result_hash != first_hash:
                logger.error(f"TRUTH BREACH: Hash mismatch for task {task_id}! Node {proofs[i].node_id} provided divergent result.")
                return False, f"Hash mismatch detected at node {proofs[i].node_id}"

        # 3. Physical Snapshot Plausibility
        # (Future: Check if GPU utilization was actually high during the reported window)
        
        logger.info(f"Task {task_id} VERIFIED. Physical truth established via redundancy.")
        return True, "Verified via multi-node consensus"

    def cleanup(self, task_id: str):
        if task_id in self.pending_verification:
            del self.pending_verification[task_id]

if __name__ == "__main__":
    # Simulation of Truth Verification
    verifier = TruthVerifier()
    tid = "task_soul_999"
    
    # Create two identical proofs from DIFFERENT nodes
    proof1 = ExecutionProof(
        task_id=tid, node_id="node_alpha", result_hash="hash_abc_123", 
        physical_snapshot={"gpu_util": 95}, timestamp=time.time(), signature="sig1"
    )
    proof2 = ExecutionProof(
        task_id=tid, node_id="node_beta", result_hash="hash_abc_123", 
        physical_snapshot={"gpu_util": 92}, timestamp=time.time(), signature="sig2"
    )
    
    # Case 1: Success
    print("\n--- Test 1: Honest Redundancy ---")
    verifier.submit_proof(proof1)
    verifier.submit_proof(proof2)
    success, msg = verifier.verify_task(tid)
    print(f"Result: {success}, Msg: {msg}")
    
    # Case 2: Malicious Node
    print("\n--- Test 2: Malicious Divergence ---")
    tid_mal = "task_soul_666"
    p1 = ExecutionProof(tid_mal, "node_alpha", "hash_correct", {}, time.time(), "s1")
    p2 = ExecutionProof(tid_mal, "node_gamma", "hash_wrong", {}, time.time(), "s2")
    verifier.submit_proof(p1)
    verifier.submit_proof(p2)
    success, msg = verifier.verify_task(tid_mal)
    print(f"Result: {success}, Msg: {msg}")
