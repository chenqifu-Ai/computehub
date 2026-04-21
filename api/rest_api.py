from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime
import uvicorn
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Gateway")

# 数据库配置 (从环境变量读取，默认本地)
DB_CONFIG = {
    "dbname": os.getenv("CH_DB_NAME", "computehub"),
    "user": os.getenv("CH_DB_USER", "postgres"),
    "password": os.getenv("CH_DB_PASS", "postgres"),
    "host": os.getenv("CH_DB_HOST", "localhost"),
    "port": os.getenv("CH_DB_PORT", "5432")
}

def get_db_conn():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

app = FastAPI(title="ComputeHub Deterministic Gateway", version="1.0.0-alpha")

class NodeRegistration(BaseModel):
    node_id: str
    hardware_fingerprint: str
    os: str
    gpu_model: Optional[str] = "Unknown"
    memory_total_mb: Optional[int] = 0

class HeartbeatPacket(BaseModel):
    node_id: str
    status: str
    metrics: dict
    version: str

@app.post("/api/v1/node/register")
async def register_node(reg: NodeRegistration):
    conn = get_db_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nodes (node_id, hardware_fingerprint, os, gpu_model, memory_total_mb, status)
                VALUES (%s, %s, %s, %s, %s, 'REGISTERED')
                ON CONFLICT (node_id) DO UPDATE SET 
                    os = EXCLUDED.os, 
                    gpu_model = EXCLUDED.gpu_model,
                    memory_total_mb = EXCLUDED.memory_total_mb;
                """,
                (reg.node_id, reg.hardware_fingerprint, reg.os, reg.gpu_model, reg.memory_total_mb)
            )
            conn.commit()
        logger.info(f"Node Registered/Updated in DB: {reg.node_id}")
        return {"status": "success", "node_id": reg.node_id}
    except Exception as e:
        conn.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/v1/node/heartbeat")
async def receive_heartbeat(hb: HeartbeatPacket):
    conn = get_db_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        with conn.cursor() as cur:
            # 1. 校验节点是否存在
            cur.execute("SELECT node_id FROM nodes WHERE node_id = %s", (hb.node_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=403, detail="Node not registered")
            
            # 2. 更新节点状态
            cur.execute(
                "UPDATE nodes SET last_seen = CURRENT_TIMESTAMP, status = %s WHERE node_id = %s",
                (hb.status, hb.node_id)
            )
            
            # 3. 写入心跳时序数据
            metrics = hb.metrics
            cur.execute(
                """
                INSERT INTO node_heartbeats (node_id, temperature, utilization, power_draw, memory_used_mb)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (hb.node_id, metrics.get('temperature'), metrics.get('utilization'), 
                 metrics.get('power_draw'), metrics.get('memory_used'))
            )
            conn.commit()
        return {"status": "acknowledged"}
    except Exception as e:
        conn.rollback()
        logger.error(f"Heartbeat error: {e}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/v1/nodes/status")
async def get_all_nodes():
    conn = get_db_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM nodes")
            nodes = cur.fetchall()
        return {"total_nodes": len(nodes), "nodes": nodes}
    finally:
        conn.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
