import pg8000
import os

# 数据库连接配置 (从环境或配置文件读取)
DB_CONFIG = {
    "user": "postgres",
    "password": "your_password", # 实际执行时需替换或从环境变量读取
    "host": "your_remote_db_host", # 实际执行时需替换
    "database": "computehub",
    "port": 5432
}

def init_db():
    try:
        print(f"Connecting to PostgreSQL at {DB_CONFIG['host']}...")
        conn = pg8000.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 1. 创建节点表 (Nodes) - 存储算力提供者信息
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id VARCHAR(64) PRIMARY KEY,
                hostname VARCHAR(255),
                ip_address VARCHAR(45),
                gpu_model VARCHAR(100),
                vram_total INTEGER,
                status VARCHAR(20) DEFAULT 'offline',
                last_heartbeat TIMESTAMP,
                region VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. 创建任务表 (Tasks) - 存储算力需求
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64),
                task_type VARCHAR(50),
                required_vram INTEGER,
                priority INTEGER DEFAULT 1,
                status VARCHAR(20) DEFAULT 'pending',
                assigned_node VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. 创建心跳记录表 (Heartbeats) - 用于物理验证
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS heartbeats (
                id SERIAL PRIMARY KEY,
                node_id VARCHAR(64) REFERENCES nodes(node_id),
                gpu_temp FLOAT,
                gpu_util FLOAT,
                vram_used INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        print("✅ ComputeHub Database initialized successfully!")
        print("Created tables: nodes, tasks, heartbeats")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

if __name__ == "__main__":
    init_db()
