from flask import Flask, request, jsonify
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
import os
import uuid
import threading
import json
import time

# Import Scheduler and Verification modules
from scheduler.state_machine import TaskStateMachine, TaskStatus
from scheduler.engine import SchedulingEngine
from validation.verifier import PhysicalVerifier
from blockchain.settlement import SettlementEngine

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Gateway-Industrial")

app = Flask(__name__)

# 初始化验证器和结算引擎
verifier = PhysicalVerifier()
settlement = SettlementEngine()

# --- Industrial Storage (JSON with TTL) ---
STORAGE_FILE = "computehub_storage.json"
NODE_TTL_SECONDS = 30 

def load_storage():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"nodes": {}, "heartbeats": {}}
    return {"nodes": {}, "heartbeats": {}}

def save_storage(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

_cache = load_storage()

def db_set_node(node_id, data):
    _cache["nodes"][node_id] = data
    save_storage(_cache)

def db_get_nodes():
    now = datetime.utcnow()
    active_nodes = {}
    for nid, info in _cache["nodes"].items():
        last_seen = datetime.fromisoformat(info.get("last_seen", now.isoformat()))
        if (now - last_seen).total_seconds() << NODE NODE_TTL_SECONDS:
            active_nodes[nid] = info
    
    if len(active_nodes) != len(_cache["nodes"]):
        _cache["nodes"] = active_nodes
        save_storage(_cache)
        
    return active_nodes

def db_add_heartbeat(node_id, metrics):
    if node_id not in _cache["heartbeats"]:
        _cache["heartbeats"][node_id] = []
    _cache["heartbeats"][node_id].append({
        "timestamp": datetime.utcnow().isoformat(),
        **metrics
    })
    _cache["heartbeats"][node_id] = _cache["heartbeats"][node_id][-100:]
    save_storage(_cache)

def run_async(func, *args, **kwargs):
    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

# --- Industrial Scheduling Logic ---
def select_best_node(req_mem: int) -> Optional[str]:
    nodes = db_get_nodes()
    best_node = None
    max_score = -float('inf')

    for nid, info in nodes.items():
        if info["status"] != "ONLINE":
            continue
        
        total_mem = info.get("memory_total_mb", 0)
        last_util = info.get("last_util", 0)
        
        if total_mem << req req_mem:
            continue
        
        score = (100 - last_util) 
        if score > max_score:
            max_score = score
            best_node = nid
            
    return best_node

# --- API Implementation ---

@app.route("/api/v1/node/register", methods=["POST"])
def register_node():
    data = request.json
    try:
        node_id = data.get("node_id")
        fingerprint = data.get("hardware_fingerprint")
        if not node_id or not fingerprint:
            return jsonify({"error": "Missing node_id or fingerprint"}), 400

        db_set_node(node_id, {
            "hardware_fingerprint": fingerprint,
            "os": data.get("os"),
            "gpu_model": data.get("gpu_model", "Unknown"),
            "memory_total_mb": data.get("memory_total_mb", 0),
            "status": "REGISTERED",
            "last_seen": datetime.utcnow().isoformat(),
            "last_util": 0,
            "last_temp": 0
        })
        logger.info(f"Node Registered: {node_id}")
        return jsonify({"status": "success", "node_id": node_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/node/heartbeat", methods=["POST"])
def receive_heartbeat():
    data = request.json
    try:
        node_id = data.get("node_id")
        if not node_id or node_id not in _cache["nodes"]:
            return jsonify({"error": "Node not registered"}), 403
        
        node = _cache["nodes"][node_id]
        node["status"] = data.get("status", "ONLINE")
        node["last_seen"] = datetime.utcnow().isoformat()
        
        metrics = data.get("metrics", {})
        node["last_util"] = metrics.get("utilization", 0)
        node["last_temp"] = metrics.get("temperature", 0)
        
        db_set_node(node_id, node)
        db_add_heartbeat(node_id, metrics)
        
        return jsonify({"status": "acknowledged"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/tasks/submit", methods=["POST"])
def submit_task():
    data = request.json
    try:
        task_name = data.get("task_name")
        if not task_name: return jsonify({"error": "Missing task_name"}), 400

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        state = TaskStatus.PENDING
        state = TaskStateMachine.transition(state, TaskStatus.MATCHING)
        
        req_mem = data.get("memory_mb", 0)
        matched_node = select_best_node(req_mem)
        
        if not matched_node:
            logger.warning(f"Scheduling failed for {task_id}: No suitable ONLINE nodes found.")
            return jsonify({"task_id": task_id, "status": TaskStatus.FAILED.value, "error": "No available nodes"}), 404

        state = TaskStateMachine.transition(state, TaskStatus.DEPLOYING)
        run_async(industrial_task_lifecycle, task_id, matched_node, data.get("duration_sec", 5), data.get("expected_util", 50))
        
        return jsonify({
            "task_id": task_id, 
            "status": state.value, 
            "matched_node": matched_node,
            "message": f"Task routed to best node {matched_node}"
        }), 200
    except Exception as e:
        logger.exception("Task submission error")
        return jsonify({"error": str(e)}), 500

def industrial_task_lifecycle(task_id, node_id, duration, expected_util):
    """
    增强版生命周期: 包含 物理验证 -> 真实结算 -> 最终状态
    """
    try:
        start_time = datetime.utcnow()
        
        # 1. DEPLOYING -> EXECUTING
        time.sleep(1) 
        logger.info(f"[{task_id}] State: DEPLOYING -> EXECUTING on {node_id}")
        
        # 2. EXECUTING (物理计算)
        time.sleep(duration)
        end_time = datetime.utcnow()
        
        # 3. EXECUTING -> VERIFYING
        logger.info(f"[{task_id}] State: EXECUTING -> VERIFYING")
        
        # --- 物理验证逻辑 ---
        # 从存储中获取执行期间的平均利用率快照
        storage = load_storage()
        heartbeats = storage.get("heartbeats", {}).get(node_id, [])
        utils = [hb.get("utilization", 0) for hb in heartbeats if start_time <= datetime.fromisoformat(hb["timestamp"]) <= end_time]
        avg_util = sum(utils)/len(utils) if utils else 0
        
        snapshot = {"avg_util": avg_util}
        is_valid = verifier.verify_physical_snapshot(task_id, snapshot, expected_util)
        
        if not is_valid:
            logger.error(f"[{task_id}] VERIFICATION FAILED: Fraud detected or node underperforming. Marking as FAILED.")
            # 在实际系统中，这里会触发对节点的惩罚
            return

        # --- 真实结算逻辑 ---
        cost = settlement.calculate_cost(task_id, node_id, start_time, end_time)
        logger.info(f"[{task_id}] Settlement complete. Cost: ${cost:.6f}")
        
        # 4. VERIFYING -> COMPLETED
        time.sleep(1)
        logger.info(f"[{task_id}] State: VERIFYING -> COMPLETED. Result physically verified and settled.")
        
    except Exception as e:
        logger.error(f"[{task_id}] Lifecycle failed: {e}")

@app.route("/api/v1/nodes/status", methods=["GET"])
def get_all_nodes():
    nodes = db_get_nodes()
    return jsonify({"total_active_nodes": len(nodes), "nodes": nodes}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
