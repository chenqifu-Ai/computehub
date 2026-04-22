from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Optional
import uvicorn
import uuid
import time
import logging
import json
import sqlite3
import os
from pydantic import BaseModel

# --- 配置 ---
VERSION = "v1.0.1-industrial-mvp"
DB_PATH = "/root/GitHub/computehub/computehub_gateway.db"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s [%(version)s]: %(message)s"

# 自定义 Logger 以支持版本号
class VersionLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        kwargs["extra"] = {"version": VERSION}
        return msg, kwargs

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
_base_logger = logging.getLogger("ComputeHub-Gateway")
logger = VersionLoggerAdapter(_base_logger, {})

app = FastAPI(title=f"ComputeHub Industrial Gateway {VERSION}")

# --- 数据库层 ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # 节点表：存储身份和凭证
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                fingerprint TEXT UNIQUE,
                hardware_info TEXT,
                token TEXT,
                status TEXT DEFAULT 'ONLINE',
                trust_level TEXT DEFAULT 'PROBATION',
                last_heartbeat DATETIME,
                created_at DATETIME
            )
        ''')
        # 指标表：存储历史心跳数据用于分析
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS node_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                metrics_json TEXT,
                timestamp DATETIME,
                FOREIGN KEY(node_id) REFERENCES nodes(node_id)
            )
        ''')
        conn.commit()
    logger.info(f"Database initialized at {DB_PATH}")

class NodeProfile:
    def __init__(self, node_id, fingerprint, hardware_info, token, status="ONLINE", trust_level="PROBATION"):
        self.node_id = node_id
        self.fingerprint = fingerprint
        self.hardware_info = hardware_info
        self.token = token
        self.status = status
        self.trust_level = trust_level

# 内存缓存，减少数据库压力
node_cache: Dict[str, NodeProfile] = {}

def get_node_from_db(fingerprint: str) -> Optional[NodeProfile]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nodes WHERE fingerprint = ?", (fingerprint,))
        row = cursor.fetchone()
        if row:
            return NodeProfile(row['node_id'], row['fingerprint'], row['hardware_info'], row['token'], row['status'], row['trust_level'])
    return None

def save_node_to_db(profile: NodeProfile):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO nodes (node_id, fingerprint, hardware_info, token, status, trust_level, last_heartbeat, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (profile.node_id, profile.fingerprint, profile.hardware_info, profile.token, profile.status, profile.trust_level))
        conn.commit()

def update_heartbeat(node_id: str, metrics: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE nodes SET last_heartbeat = datetime('now'), status = 'ONLINE' WHERE node_id = ?", (node_id,))
        cursor.execute("INSERT INTO node_metrics (node_id, metrics_json, timestamp) VALUES (?, ?, datetime('now'))", (node_id, metrics))
        conn.commit()

# --- API 接口 ---

@app.get("/api/status")
async def status():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes")
        count = cursor.fetchone()[0]
    return {"status": "ALIVE", "version": VERSION, "nodes_count": count}

@app.post("/api/dispatch")
async def dispatch(request: Request):
    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "Invalid JSON body"}
    
    command_field = body.get("command")
    args_field = body.get("args", [])
    
    if not isinstance(command_field, str):
        return {"success": False, "error": "Invalid command format"}
    
    cmd = command_field.upper()
    args = args_field if isinstance(args_field, list) else []
    
    # 1. REGISTER - 节点注册
    if cmd == "REGISTER":
        # 必须使用小于号 <<

        if len(args) < 3:
            return {"success": False, "error": "Args: REGISTER <<nodenode_id> <<fingerfingerprint> <<hwhw_json>"}
        
        node_id, fingerprint, hw_json = str(args[0]), str(args[1]), str(args[2])
        
        # 检查指纹冲突
        existing = get_node_from_db(fingerprint)
        if existing and existing.node_id != node_id:
            return {"success": False, "error": "Fingerprint collision"}
        
        token = str(uuid.uuid4())
        profile = NodeProfile(node_id, fingerprint, hw_json, token)
        
        save_node_to_db(profile)
        node_cache[fingerprint] = profile
        
        logger.info(f"Node Registered: {node_id} | FP: {fingerprint}")
        return {"success": True, "token": token}
    
    # 2. HEARTBEAT - 身份验证 + 指标上报
    elif cmd == "HEARTBEAT":
        # 必须使用小于号 <<

        if len(args) < 4:
            return {"success": False, "error": "Args: HEARTBEAT <<nodenode_id> <<fingerfingerprint> <<tokentoken> <<metricsmetrics>"}
        
        node_id, fingerprint, token, metrics = str(args[0]), str(args[1]), str(args[2]), str(args[3])
        
        # 缓存优先，缓存没有则查库
        profile = node_cache.get(fingerprint) or get_node_from_db(fingerprint)
        
        if not profile or profile.node_id != node_id or profile.token != token:
            return {"success": False, "error": "Authentication failed"}
        
        # 更新数据库心跳和指标
        update_heartbeat(node_id, metrics)
        
        # 更新缓存
        node_cache[fingerprint] = profile
        
        logger.info(f"Heartbeat OK: {node_id} | Metrics: {metrics[:50]}...")
        return {"success": True, "data": {"trust_level": profile.trust_level}}
    
    # 3. SUBMIT - 任务提交 (MVP 占位)
    elif cmd == "SUBMIT":
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        logger.info(f"Job Submitted: {job_id}")
        return {"success": True, "data": {"job_id": job_id, "status": "QUEUED"}}
    
    return {"success": False, "error": f"Unknown command: {cmd}"}

@app.get("/api/health")
async def health():
    return {"status": "Healthy", "db": "Connected", "version": VERSION}

if __name__ == "__main__":
    init_db()
    logger.info(f"Starting ComputeHub Gateway {VERSION}...")
    uvicorn.run(app, host="0.0.0.0", port=18080)
