from typing import Dict, List, Optional
from datetime import datetime
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Settlement")

STORAGE_FILE = "computehub_storage.json"

class SettlementEngine:
    """
    ComputeHub 算力结算引擎 (Lightweight Version):
    基于物理利用率的真实计费，适配 JSON 存储。
    """
    def __init__(self, rate_per_gpu_hour: float = 0.03):
        self.rate_per_gpu_hour = rate_per_gpu_hour

    def _load_storage(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"nodes": {}, "heartbeats": {}}
        return {"nodes": {}, "heartbeats": {}}

    def calculate_cost(self, task_id: str, node_id: str, start_time: datetime, end_time: datetime) -> float:
        """
        真实算力度量计费：
        从 JSON 存储中提取该节点在任务执行期间的所有心跳，计算加权平均利用率。
        Cost = (Duration in Hours) * (Avg Utilization / 100) * (Rate)
        """
        storage = self._load_storage()
        heartbeats = storage.get("heartbeats", {}).get(node_id, [])
        
        if not heartbeats:
            logger.warning(f"No heartbeat records for task {task_id} on node {node_id}")
            return 0.0
        
        # 过滤出时间范围内的心跳记录
        relevant_utils = []
        for hb in heartbeats:
            hb_time = datetime.fromisoformat(hb["timestamp"])
            if start_time <= hb_time <= end_time:
                # 获取 metrics 中的 utilization
                # 处理两种可能的数据结构: 直接在 hb 里或在 hb['metrics'] 里
                util = hb.get("utilization") or hb.get("metrics", {}).get("utilization")
                if util is not None:
                    relevant_utils.append(util)
        
        if not relevant_utils:
            logger.warning(f"No heartbeat records within time range for task {task_id}")
            return 0.0
        
        # 计算平均利用率
        avg_util = sum(relevant_utils) / len(relevant_utils)
        
        # 计算时长 (小时)
        duration_hours = (end_time - start_time).total_seconds() / 3600
        
        # 最终计费: 剔除空转，仅为实际贡献的算力付费
        final_cost = duration_hours * (avg_util / 100) * self.rate_per_gpu_hour
        
        logger.info(f"Settlement for {task_id}: Avg Util {avg_util:.2f}%, Duration {duration_hours:.4f}h, Cost ${final_cost:.6f}")
        return final_cost

if __name__ == "__main__":
    # 模拟计费
    engine = SettlementEngine()
    # 假设存储中已有数据，此处为简单演示逻辑
    start = datetime.utcnow()
    end = datetime.utcnow() # 实际使用时会有时间差
    cost = engine.calculate_cost("task_test_01", "node_test_01", start, end)
    print(f"Calculated Cost: ${cost:.6f}")
