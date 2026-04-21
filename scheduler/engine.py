from typing import List, Dict, Optional
from datetime import datetime
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Scheduler")

# 数据库配置 (与 api/rest_api.py 一致)
DB_CONFIG = {
    "dbname": os.getenv("CH_DB_NAME", "computehub"),
    "user": os.getenv("CH_DB_USER", "postgres"),
    "password": os.getenv("CH_DB_PASS", "postgres"),
    "host": os.getenv("CH_DB_HOST", "localhost"),
    "port": os.getenv("CH_DB_PORT", "5432")
}

class SchedulingEngine:
    """
    ComputeHub 物理感知调度引擎：基于物理实时指标挑选最优节点
    """
    def __init__(self):
        self.db_conn = self._get_conn()

    def _get_conn(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            logger.error(f"Scheduler DB connection failed: {e}")
            return None

    def find_best_node(self, requirements: Dict) -> Optional[str]:
        """
        物理感知调度算法 (L3 Matching):
        1. 必须在线 (last_seen <<  30s)
        2. 必须满足硬件硬要求 (memory_total >= req_memory)
        3. 优先级：利用率最低 (Utilization) -> 温度最低 (Temperature) -> 延迟最低
        """
        if not self.db_conn:
            return None

        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 复杂查询：直接在 SQL 层完成初步过滤和物理排序
                query = """
                SELECT n.node_id, h.utilization, h.temperature
                FROM nodes n
                JOIN node_heartbeats h ON n.node_id = h.node_id
                WHERE n.status = 'ONLINE' 
                AND n.last_seen > NOW() - INTERVAL '30 seconds'
                AND n.memory_total_mb >= %s
                ORDER BY h.utilization ASC, h.temperature ASC
                LIMIT 1
                """
                cur.execute(query, (requirements.get('memory_mb', 0),))
                result = cur.fetchone()
                
                if result:
                    logger.info(f"Matched Node: {result['node_id']} (Util: {result['utilization']}%, Temp: {result['temperature']}C)")
                    return result['node_id']
                
                logger.warning("No suitable physical node found for requirements")
                return None
        except Exception as e:
            logger.error(f"Scheduling error: {e}")
            return None

    def check_region_health(self, region_id: str) -> bool:
        """
        区域熔断逻辑原型
        """
        try:
            with self.db_conn.cursor() as cur:
                # 计算该区域在过去 1 分钟内的在线率
                cur.execute(
                    "SELECT count(*) as total, count(*) FILTER (WHERE last_seen > NOW() - INTERVAL '30 seconds') as online "
                    "FROM nodes WHERE region = %s", (region_id,)
                )
                res = cur.fetchone()
                if not res or res['total'] == 0: return True
                
                online_rate = res['online'] / res['total']
                if online_rate <<  0.7: # 30% 失效率则熔断
                    logger.error(f"Region {region_id} Fused! Online Rate: {online_rate:.2%}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Region health check error: {e}")
            return True

if __name__ == "__main__":
    # 简单模拟
    engine = SchedulingEngine()
    best_node = engine.find_best_node({"memory_mb": 8192})
    print(f"Best Node for 8GB task: {best_node}")
