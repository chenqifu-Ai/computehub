from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime
import uvicorn
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid

# Import Scheduler modules
from scheduler.state_machine import TaskStateMachine, TaskStatus
from scheduler.engine import SchedulingEngine

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Gateway")

DB_CONFIG = {
    "dbname": os.getenv("CH_DB_NAME", "computehub"),
    "user": os.getenv("CH_DB_USER", "postgres"),
    "password": os.getenv("CH_DB_PASS", "postgres"),
    "host": os.getenv("CH_DB_HOST", "localhost"),
    "port": os.getenv("CH_DB_PORT", "5432")
}

def get_db_conn():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

app = FastAPI(title="ComputeHub Deterministic Gateway", version="1.0.0-alpha")
scheduler = SchedulingEngine()

# --- Models ---
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

class TaskRequest(BaseModel):
    task_name: str
    memory_mb: int
    duration_sec: int
    priority: int = 1

class TaskResponse(BaseModel):
    task_id: str
    status: str
    matched_node: Optional[str] = None

# --- Static Files ---
app.mount("/static", StaticFiles(directory="/root/.openclaw/workspace/ai_agent/code/computehub/web"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("/root/.openclaw/workspace/ai_agent/code/computehub/web/dashboard.html")

# --- API Implementation ---

@app.post("/api/v1/node/register")
async def register_node(reg: NodeRegistration):
    conn = get_db_conn()
    if not conn: raise HTTPException(status_code=500, detail="Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO nodes (node_id, hardware_fingerprint, os, gpu_model, memory_total_mb, status)
                   VALUES (%s, %s, %s, %s, %s, 'REGISTERED')
                   ON CONFLICT (node_id) DO UPDATE SET os = EXCLUDED.os, gpu_model = EXCLUDED.gpu_model, memory_total_mb = EXCLUDED.memory_total_mb;""",
                (reg.node_id, reg.hardware_fingerprint, reg.os, reg.gpu_model, reg.memory_total_mb)
            )
            conn.commit()
        return {"status": "success", "node_id": reg.node_id}
    finally:
        conn.close()

@app.post("/api/v1/node/heartbeat")
async def receive_heartbeat(hb: HeartbeatPacket):
    conn = get_db_conn()
    if not conn: raise HTTPException(status_code=500, detail="Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT node_id FROM nodes WHERE node_id = %s", (hb.node_id,))
            if not cur.fetchone(): raise HTTPException(status_code=403, detail="Node not registered")
            
            # 新增：在 nodes 表中更新最近一次的心跳快照，方便 Dashboard 直接读取
            metrics = hb.metrics
            cur.execute(
                "UPDATE nodes SET last_seen = CURRENT_TIMESTAMP, status = %s, last_util = %s, last_temp = %s WHERE node_id = %s",
                (hb.status, metrics.get('utilization'), metrics.get('temperature'), hb.node_id)
            )
            
            cur.execute("INSERT INTO node_heartbeats (node_id, temperature, utilization, power_draw, memory_used_mb) VALUES (%s, %s, %s, %s, %s)",
                        (hb.node_id, metrics.get('temperature'), metrics.get('utilization'), metrics.get('power_draw'), metrics.get('memory_used')))
            conn.commit()
        return {"status": "acknowledged"}
    finally:
        conn.close()

@app.post("/api/v1/tasks/submit")
async def submit_task(req: TaskRequest, background_tasks: BackgroundTasks):
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    current_state = TaskStatus.PENDING
    logger.info(f"Task {task_id} submitted: {req.task_name}")
    current_state = TaskStateMachine.transition(current_state, TaskStatus.MATCHING)
    requirements = {"memory_mb": req.memory_mb}
    matched_node = scheduler.find_best_node(requirements)
    if not matched_node:
        logger.error(f"Task {task_id} failed to match any physical node.")
        return TaskResponse(task_id=task_id, status=TaskStatus.FAILED.value)
    current_state = TaskStateMachine.transition(current_state, TaskStatus.DEPLOYING)
    background_tasks.add_task(simulate_node_execution, task_id, matched_node, req)
    return TaskResponse(task_id=task_id, status=current_state.value, matched_node=matched_node)

async def simulate_node_execution(task_id: str, node_id: str, req: TaskRequest):
    logger.info(f"Pushing task {task_id} to node {node_id}...")
    import time
    time.sleep(2)
    logger.info(f"Task {task_id} is now EXECUTING on {node_id}")
    time.sleep(req.duration_sec)
    logger.info(f"Task {task_id} execution finished. Verifying physical snapshot...")
    time.sleep(1)
    logger.info(f"Task {task_id} COMPLETED successfully.")

@app.get("/api/v1/nodes/status")
async def get_all_nodes():
    conn = get_db_conn()
    if not conn: raise HTTPException(status_code=500, detail="Database unavailable")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 增加最后一次利用率和温度的读取
            cur.execute("SELECT * FROM nodes")
            nodes = cur.fetchall()
        return {"total_nodes": len(nodes), "nodes": nodes}
    finally:
        conn.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
