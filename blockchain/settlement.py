from typing import Dict, List, Optional
from datetime import datetime
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Settlement")

DB_CONFIG = {
    "dbname": os.getenv("CH_DB_NAME", "computehub"),
    "user": os.getenv("CH_DB_USER", "postgres"),
    "password": os.getenv("CH_DB_PASS", "postgres"),
    "host": os.getenv("CH_DB_HOST", "localhost"),
    "port": os.getenv("CH_DB_PORT", "5432")
}

class SettlementEngine:
    """
    ComputeHub 算力结算引擎：基于物理利用率的真实计费
    """
    def __init__(self, rate_per_gpu_hour: float = 0.03):
        self.rate_per_gpu_hour = rate_per_gpu_hour

    def calculate_cost(self, task_id: str, node_id: str, start_time: datetime, end_time: datetime) -> float:
        """
        真实算力度量计费：
        从数据库提取该节点在任务执行期间的所有心跳，计算加权平均利用率。
        Cost = (Duration in Hours) * (Avg Utilization / 100) * (Rate)
        """
        conn = self._get_conn()
        if not conn: return 0.0

        try:
            with conn.cursor() as cur:
                # 获取任务期间的所有心跳记录
                cur.execute(
                    "SELECT utilization FROM node_heartbeats WHERE node_id = %s AND timestamp BETWEEN %s AND %s",
                    (node_id, start_time, end_time)
                )
                records = cur.fetchall()
                
                if not records:
                    logger.warning(f"No heartbeat records for task {task_id} on node {node_id}")
                    return 0.0
                
                # 计算平均利用率
                utils = [r[0] for r in records if r[0] is not None]
                avg_util = sum(utils) / len(utils) if utils else 0
                
                # 计算时长 (小时)
                duration_hours = (end_time - start_time).total_seconds() / 3600
                
                # 最终计费: 剔除空转，仅为实际贡献的算力付费
                final_cost = duration_hours * (avg_util / 100) * self.rate_per_gpu_hour
                
                logger.info(f"Settlement for {task_id}: Avg Util {avg_util:.2f}%, Duration {duration_hours:.4f}h, Cost ${final_cost:.6f}")
                return final_cost
        except Exception as e:
            logger.error(f"Settlement error for {task_id}: {e}")
            return 0.0
        finally:
            conn.close()

    def _get_conn(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            logger.error(f"DB connection failed: {e}")
            return None

if __name__ == "__main__":
    # 模拟计费
    engine = SettlementEngine()
    start = datetime(2026, 4, 22, 6, 0, 0)
    end = datetime(2026, 4, 22, 7, 0, 0)
    cost = engine.calculate_cost("task_test_01", "node_test_01", start, end)
    print(f"Calculated Cost: ${cost:.6f}")
