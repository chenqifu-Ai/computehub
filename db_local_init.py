import sqlite3
import os
from datetime import datetime

# 数据库文件路径
DB_PATH = "/root/.openclaw/workspace/ai_agent/results/computehub_local.db"

def get_connection():
    """获取数据库连接，确保目录存在"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_local_db():
    """初始化本地模拟数据库 (SQLite)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. 创建节点表 (Nodes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                hostname TEXT,
                ip_address TEXT,
                gpu_model TEXT,
                vram_total INTEGER,
                status TEXT DEFAULT 'offline',
                last_heartbeat TEXT,
                region TEXT,
                created_at TEXT
            );
        """)

        # 2. 创建任务表 (Tasks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                user_id TEXT,
                task_type TEXT,
                required_vram INTEGER,
                priority INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                assigned_node TEXT,
                created_at TEXT,
                updated_at TEXT
            );
        """)

        # 3. 创建心跳记录表 (Heartbeats)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                gpu_temp REAL,
                gpu_util REAL,
                vram_used INTEGER,
                timestamp TEXT,
                FOREIGN KEY (node_id) REFERENCES nodes(node_id)
            );
        """)

        conn.commit()
        print(f"✅ ComputeHub Local DB initialized at: {DB_PATH}")
        conn.close()
    except Exception as e:
        print(f"❌ Local DB initialization failed: {e}")

if __name__ == "__main__":
    init_local_db()
