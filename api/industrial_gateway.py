import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio
import json
from datetime import datetime

# Import existing industrial components
from db.db_manager import DBManager
from scheduler.state_machine import TaskStateMachine, TaskStatus
from validation.verifier import PhysicalVerifier
from blockchain.settlement import SettlementEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-FastAPI-Industrial")

app = FastAPI(title="ComputeHub High-Performance Gateway")
db = DBManager()
verifier = PhysicalVerifier()
settlement = SettlementEngine()

# --- Pydantic Models for Fast Validation ---
class NodeRegistration(BaseModel):
    node_id: str
    hardware_fingerprint: str
    gpu_model: str = "Unknown"
    memory_total_mb: int = 0
    os: str = "Linux"

class TaskSubmission(BaseModel):
    task_name: str
    memory_mb: int = 0
    duration_sec: int = 5
    expected_util: float = 50.0
    priority: int = 1

# --- WebSocket Connection Manager for Stream Heartbeats ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, node_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[node_id] = websocket
        logger.info(f"WebSocket connected: {node_id}")

    def disconnect(self, node_id: str):
        if node_id in self.active_connections:
            del self.active_connections[node_id]
            logger.info(f"WebSocket disconnected: {node_id}")

    async def send_command(self, node_id: str, message: Dict):
        if node_id in self.active_connections:
            await self.active_connections[node_id].send_json(message)

manager = ConnectionManager()

# --- API Endpoints ---

@app.post("/api/v2/node/register")
async def register_node(reg: NodeRegistration):
    db.upsert_node(reg.node_id, {
        "hardware_fingerprint": reg.hardware_fingerprint,
        "gpu_model": reg.gpu_model,
        "memory_total_mb": reg.memory_total_mb,
        "os": reg.os,
        "status": "REGISTERED",
        "last_seen": datetime.utcnow().isoformat()
    })
    return {"status": "success", "node_id": reg.node_id}

@app.post("/api/v2/tasks/submit")
async def submit_task(task: TaskSubmission):
    task_id = f"task_{uuid.uuid4().hex[:8]}" if 'uuid' in globals() else f"task_{int(datetime.utcnow().timestamp())}"
    
    # 1. Matching (Using SQLite Optimized Query)
    nodes = db.get_active_nodes()
    best_node = None
    max_score = -float('inf')
    
    for nid, info in nodes.items() if isinstance(nodes, dict) else [(n['node_id'], n) for n in nodes]:
        if info.get("memory_total_mb", 0) >= task.memory_mb:
            score = 100 - info.get("last_util", 0)
            if score > max_score:
                max_score = score
                best_node = nid

    if not best_node:
        return {"status": "failed", "error": "No suitable online nodes"}

    # 2. Lifecycle start (Async)
    asyncio.create_task(industrial_lifecycle(task_id, best_node, task))
    
    return {"task_id": task_id, "matched_node": best_node, "status": "DEPLOYING"}

async def industrial_lifecycle(task_id, node_id, task):
    try:
        start_time = datetime.utcnow()
        logger.info(f"[{task_id}] DEPLOYING -> EXECUTING on {node_id}")
        
        # 模拟执行
        await asyncio.sleep(task.duration_sec)
        end_time = datetime.utcnow()
        
        # 物理验证
        utils = db.get_utilization_range(node_id, start_time, end_time)
        avg_util = sum(utils)/len(utils) if utils else 0
        
        if not verifier.verify_physical_snapshot(task_id, {"avg_util": avg_util}, task.expected_util):
            logger.error(f"[{task_id}] Fraud detected! Avg Util {avg_util}% << Expected Expected {task.expected_util}%")
            return

        # 真实结算
        cost = settlement.calculate_cost(task_id, node_id, start_time, end_time)
        logger.info(f"[{task_id}] VERIFYING -> COMPLETED. Cost: ${cost:.6f}")
        
    except Exception as e:
        logger.error(f"[{task_id}] Lifecycle Error: {e}")

# --- High Performance Heartbeat Stream ---
@app.websocket("/ws/heartbeat/{node_id}")
async def websocket_endpoint(websocket: WebSocket, node_id: str):
    await manager.connect(node_id, websocket)
    try:
        while True:
            # 接收实时心跳数据
            data = await websocket.receive_json()
            # 快速写入 SQLite
            db.add_heartbeat(node_id, data.get("metrics", {}))
            # 更新节点状态
            db.upsert_node(node_id, {
                "status": "ONLINE",
                "last_seen": datetime.utcnow().isoformat(),
                "last_util": data.get("metrics", {}).get("utilization", 0),
                "last_temp": data.get("metrics", {}).get("temperature", 0)
            })
            # 实时响应
            await websocket.send_json({"status": "ack", "time": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        manager.disconnect(node_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
