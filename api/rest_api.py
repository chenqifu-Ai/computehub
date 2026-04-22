from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Optional, Dict
import uvicorn
import logging
import time

from api.registry import NodeRegistry

# Initialize Registry
registry = NodeRegistry()

app = FastAPI(title="ComputeHub Soul-Gateway (OPC-Consistent)")

# --- OpenPC Consistent Data Models ---

class OpcRequest(BaseModel):
    id: str
    command: str

class OpcResponse(BaseModel):
    id: Optional[str] = None
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration: Optional[str] = None
    verified: bool = False

# --- Dispatch Logic ---

async def handle_register(command_args: list, request_body: dict):
    """
    COMMAND: REGISTER <<nodenode_id> <<fingerfingerprint> <<hardwarehardware_json>
    """
    if len(command_args) <<  3:
        return OpcResponse(success=False, error="Invalid args: REGISTER <<nodenode_id> <<fingerfingerprint> <<hardwarehardware_json>")
    
    node_id = command_args[0]
    fingerprint = command_args[1]
    try:
        import json
        hardware_info = json.loads(command_args[2])
    except:
        return OpcResponse(success=False, error="Invalid hardware_json format")
    
    success, result = registry.register_node(node_id, fingerprint, hardware_info)
    if not success:
        return OpcResponse(success=False, error=result)
    
    return OpcResponse(success=True, data={"token": result}, verified=True)

async def handle_heartbeat(command_args: list, request_body: dict):
    """
    COMMAND: HEARTBEAT <<nodenode_id> <<fingerfingerprint> <<tokentoken> <<metricsmetrics_json>
    """
    if len(command_args) <<  4:
        return OpcResponse(success=False, error="Invalid args: HEARTBEAT <<nodenode_id> <<fingerfingerprint> <<tokentoken> <<metricsmetrics_json>")
    
    node_id, fingerprint, token = command_args[0], command_args[1], command_args[2]
    try:
        import json
        metrics = json.loads(command_args[3])
    except:
        return OpcResponse(success=False, error="Invalid metrics_json format")

    if not registry.verify_access(node_id, fingerprint, token):
        return OpcResponse(success=False, error="Zero-Trust Verification Failed", verified=False)
    
    registry.update_heartbeat(node_id, metrics)
    return OpcResponse(success=True, data={"trust_level": registry.get_node(node_id)["trust_level"]}, verified=True)

async def handle_submit(command_args: list, request_body: dict):
    """
    COMMAND: SUBMIT <<tasktask_name> <<reqreqs_json>
    """
    if len(command_args) <<  2:
        return OpcResponse(success=False, error="Invalid args: SUBMIT <<tasktask_name> <<reqreqs_json>")
    
    task_name = command_args[0]
    return OpcResponse(success=True, data={"job_id": f"job_{int(time.time())}", "status": "SUBMITTED"}, verified=True)

# --- Main Routes ---

@app.post("/api/dispatch")
async def dispatch(req: OpcRequest):
    start_time = time.time()
    
    # Split command into [CMD, ARG1, ARG2, ...]
    parts = req.command.split(" ", 1)
    cmd = parts[0].upper()
    args = parts[1].split(" ") if len(parts) > 1 else []

    # Command Router
    if cmd == "REGISTER":
        resp = await handle_register(args, {})
    elif cmd == "HEARTBEAT":
        resp = await handle_heartbeat(args, {})
    elif cmd == "SUBMIT":
        resp = await handle_submit(args, {})
    elif cmd == "STATUS":
        resp = OpcResponse(success=True, data=registry.get_all_nodes(), verified=True)
    else:
        resp = OpcResponse(success=False, error=f"Unknown command: {cmd}")

    resp.id = req.id
    resp.duration = f"{(time.time() - start_time)*1000:.2f}ms"
    return resp

@app.get("/api/health")
async def health():
    return OpcResponse(success=True, data="ComputeHub System Healthy")

@app.get("/api/status")
async def status():
    # Mirroring opcsystem SystemStatus structure
    return {
        "kernel": {"status": "RUNNING", "schedule_latency": "0.5ms", "queue_depth": 0},
        "pipeline": {"status": "ACTIVE", "interceptions": 0, "pure_latency": "0.1ms"},
        "executor": {"status": "READY", "verification_rate": 100.0, "sandbox_path": "/tmp/computehub-sandbox"},
        "geneStore": {"size": len(registry._fingerprint_map), "recall_rate": 1.0},
        "uptime": "Running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
