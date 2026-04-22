import logging
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
import time
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComputeHub-Gateway")

@dataclass
class NodeProfile:
    node_id: str
    fingerprint: str
    hardware_info: dict
    status: str = "OFFLINE"
    last_seen: float = 0.0
    session_token: Optional[str] = None
    trust_level: str = "PROBATION"  # PROBATION, TRUSTED, BANNED

class NodeRegistry:
    """
    Soul-Engine: Identity Anchoring (Inspired by OpenPC Gene Store)
    Manages the mapping between Physical Fingerprints and Node Identities.
    """
    def __init__(self):
        # fingerprint -> NodeProfile
        self._fingerprint_map: Dict[str, NodeProfile] = {}
        # node_id -> fingerprint
        self._id_map: Dict[str, str] = {}

    def register_node(self, node_id: str, fingerprint: str, hardware_info: dict) -> (bool, str):
        """
        Strict Admission Control:
        1. Check if fingerprint is already bound to another node_id (Anti-spoofing)
        2. Create/Update node profile
        3. Issue session token
        """
        # Check for fingerprint collision (Identity Theft Detection)
        if fingerprint in self._fingerprint_map:
            existing_node = self._fingerprint_map[fingerprint]
            if existing_node.node_id != node_id:
                logger.warning(f"CRITICAL: Fingerprint collision! Node {node_id} tried to use fingerprint of {existing_node.node_id}")
                return False, "Fingerprint already bound to another identity"

        # Create or update profile
        token = str(uuid.uuid4())
        profile = NodeProfile(
            node_id=node_id,
            fingerprint=fingerprint,
            hardware_info=hardware_info,
            session_token=token,
            last_seen=time.time()
        )
        
        self._fingerprint_map[fingerprint] = profile
        self._id_map[node_id] = fingerprint
        
        logger.info(f"Node {node_id} admitted. Fingerprint anchored. Token issued.")
        return True, token

    def verify_access(self, node_id: str, fingerprint: str, token: str) -> bool:
        """
        Zero-Trust Verification:
        Must match NodeID + Fingerprint + SessionToken
        """
        fp = self._id_map.get(node_id)
        if not fp or fp != fingerprint:
            logger.error(f"Access Denied: Identity mismatch for node {node_id}")
            return False
        
        profile = self._fingerprint_map.get(fingerprint)
        if not profile or profile.session_token != token:
            logger.error(f"Access Denied: Invalid session token for node {node_id}")
            return False
            
        return True

    def update_heartbeat(self, node_id: str, metrics: dict):
        """Update physical state and update trust level based on stability"""
        fp = self._id_map.get(node_id)
        if fp:
            profile = self._fingerprint_map[fp]
            profile.last_seen = time.time()
            profile.status = "ONLINE"
            # Simple trust elevation logic: if online for long enough, move to TRUSTED
            if time.time() - profile.last_seen > 3600: # Example: 1 hour stability
                profile.trust_level = "TRUSTED"
                
    def get_all_nodes(self):
        return [asdict(p) for p in self._fingerprint_map.values()]

    def get_node(self, node_id: str):
        fp = self._id_map.get(node_id)
        return asdict(self._fingerprint_map[fp]) if fp else None
