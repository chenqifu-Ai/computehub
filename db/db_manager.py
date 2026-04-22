import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-DB")

DB_PATH = "computehub_industrial.db"

class DBManager:
    """
    ComputeHub 工业级数据库管理器: 
    从 JSON 迁移到 SQLite，支持高频心跳写入和高效资源查询。
    """
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        with self.conn:
            # 节点表：存储物理硬件指纹和当前状态
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    hardware_fingerprint TEXT,
                    gpu_model TEXT,
                    memory_total_mb INTEGER,
                    status TEXT,
                    last_seen TIMESTAMP,
                    last_util FLOAT,
                    last_temp FLOAT,
                    os TEXT
                )
            """)
            # 心跳表：存储历史指标，用于真实结算 (Partition-like by node_id)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS heartbeats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT,
                    utilization FLOAT,
                    temperature FLOAT,
                    memory_used_mb FLOAT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY(node_id) REFERENCES nodes(node_id)
                )
            """)
            # 任务表：存储状态机流转记录
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_name TEXT,
                    matched_node TEXT,
                    status TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    final_cost FLOAT,
                    expected_util FLOAT
                )
            """)
            # 为心跳表创建索引，加速结算期间的范围查询
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_hb_node_time ON heartbeats(node_id, timestamp)")

    # --- 节点操作 ---
    def upsert_node(self, node_id: str, data: Dict):
        with self.conn:
            self.conn.execute("""
                INSERT INTO nodes (node_id, hardware_fingerprint, gpu_model, memory_total_mb, status, last_seen, last_util, last_temp, os)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    status=excluded.status,
                    last_seen=excluded.last_seen,
                    last_util=excluded.last_util,
                    last_temp=excluded.last_temp
            """, (
                node_id, 
                data.get("hardware_fingerprint"),
                data.get("gpu_model"),
                data.get("memory_total_mb"),
                data.get("status"),
                data.get("last_seen"),
                data.get("last_util"),
                data.get("last_temp"),
                data.get("os")
            ))

    def get_active_nodes(self, ttl_seconds: int = 30) -> List[Dict]:
        """获取所有在有效期内的在线节点"""
        cutoff = (datetime.utcnow() - timedelta(seconds=ttl_seconds)).isoformat()
        cur = self.conn.execute("SELECT * FROM nodes WHERE last_seen > ? AND status = 'ONLINE'", (cutoff,))
        return [dict(row) for row in cur.fetchall()]

    # --- 心跳操作 ---
    def add_heartbeat(self, node_id: str, metrics: Dict):
        with self.conn:
            self.conn.execute("""
                INSERT INTO heartbeats (node_id, utilization, temperature, memory_used_mb, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                node_id,
                metrics.get("utilization"),
                metrics.get("temperature"),
                metrics.get("memory_used_mb"),
                datetime.utcnow().isoformat()
            ))

    def get_utilization_range(self, node_id: str, start: datetime, end: datetime) -> List[float]:
        """获取特定时间段内的利用率序列，用于结算"""
        cur = self.conn.execute(
            "SELECT utilization FROM heartbeats WHERE node_id = ? AND timestamp BETWEEN ? AND ?",
            (node_id, start.isoformat(), end.isoformat())
        )
        return [row['utilization'] for row in cur.fetchall() if row['utilization'] is not None]

    # --- 任务操作 ---
    def update_task(self, task_id: str, data: Dict):
        # 简单的动态更新逻辑
        keys = data.keys()
        values = list(data.values())
        set_clause = ", ".join([f"{k} = ?" for k in keys])
        query = f"UPDATE tasks SET {set_clause} WHERE task_id = ?"
        with self.conn:
            self.conn.execute(query, (*values, task_id))

    def create_task(self, task_id: str, data: Dict):
        with self.conn:
            self.conn.execute("""
                INSERT INTO tasks (task_id, task_name, matched_node, status, start_time, expected_util)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                data.get("task_name"),
                data.get("matched_node"),
                data.get("status"),
                datetime.utcnow().isoformat(),
                data.get("expected_util")
            ))

if __name__ == "__main__":
    db = DBManager()
    print("✅ ComputeHub Industrial DB initialized.")
