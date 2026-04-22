from typing import Dict, List, Optional
from datetime import datetime
import logging
import os
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Scheduler")

class SchedulingEngine:
    """
    ComputeHub 物理感知调度引擎 (Ultra-Light Version)
    完全脱离 psycopg2 依赖，直接使用 JSON 缓存进行匹配
    """
    def __init__(self, storage_file="computehub_storage.json"):
        self.storage_file = storage_file

    def _load_nodes(self) -> Dict:
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as f:
                    data = json.load(f)
                    return data.get("nodes", {})
            except Exception:
                return {}
        return {}

    def find_best_node(self, requirements: Dict) -> Optional[str]:
        nodes = self._load_nodes()
        if not nodes:
            logger.warning("No nodes found in storage.")
            return None

        req_mem = requirements.get("memory_mb", 0)
        
        # 调度逻辑：ONLINE -> Memory -> Utilization -> Temperature
        best_node = None
        best_score = float('inf')

        for node_id, info in nodes.items():
            if info.get("status") != "ONLINE":
                continue
            
            # 物理显存必须满足要求
            if info.get("memory_total_mb", 0) < req_mem:
                continue
            
            # 评分函数：Utilization * 0.7 + Temperature * 0.3 (越低越好)
            util = info.get("last_util", 100)
            temp = info.get("last_temp", 100)
            score = util * 0.7 + temp * 0.3
            
            if score < best_score:
                best_score = score
                best_node = node_id

        if best_node:
            logger.info(f"Matched node {best_node} with score {best_score:.2f}")
        else:
            logger.warning("No suitable ONLINE node found for requirements.")
            
        return best_node
