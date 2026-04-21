import requests
import time
import json
import uuid
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Demo")

def run_full_cycle_demo(gateway_url="http://localhost:8000"):
    """
    ComputeHub 全链路功能演示：
    物理注册 -> 实时心跳 -> 任务提交 -> 自动调度 -> 状态流转
    """
    logger.info("=== Starting ComputeHub End-to-End Demo ===")

    # 1. 模拟物理节点注册
    node_id = f"node_{uuid.uuid4().hex[:8]}"
    reg_payload = {
        "node_id": node_id,
        "hardware_fingerprint": f"fp_{uuid.uuid4().hex}",
        "os": "Linux",
        "gpu_model": "NVIDIA A100",
        "memory_total_mb": 40960
    }
    
    logger.info(f"Step 1: Registering Node {node_id}...")
    try:
        requests.post(f"{gateway_url}/api/v1/node/register", json=reg_payload)
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        return

    # 2. 发送物理心跳 (使其在调度器中可见)
    logger.info(f"Step 2: Sending Physical Heartbeat for {node_id}...")
    hb_payload = {
        "node_id": node_id,
        "status": "ONLINE",
        "metrics": {
            "temperature": 42,
            "utilization": 10,
            "power_draw": 120.5,
            "memory_used": 2048
        },
        "version": "1.0.0-alpha"
    }
    requests.post(f"{gateway_url}/api/v1/node/heartbeat", json=hb_payload)

    # 3. 提交算力任务
    logger.info("Step 3: Submitting Compute Task...")
    task_payload = {
        "task_name": "LLM_FineTuning_Test",
        "memory_mb": 8192,
        "duration_sec": 5,
        "priority": 1
    }
    
    try:
        resp = requests.post(f"{gateway_url}/api/v1/tasks/submit", json=task_payload)
        task_res = resp.json()
        task_id = task_res.get("task_id")
        matched_node = task_res.get("matched_node")
        
        logger.info(f"✅ Task Submitted! ID: {task_id}")
        logger.info(f"✅ Scheduler matched Task to Node: {matched_node}")
        
        if matched_node != node_id:
            logger.warning(f"Warning: Task matched to a different node {matched_node}")
            
    except Exception as e:
        logger.error(f"Task submission failed: {e}")
        return

    # 4. 验证节点状态
    logger.info("Step 4: Verifying System State...")
    time.sleep(1)
    status_resp = requests.get(f"{gateway_url}/api/v1/nodes/status").json()
    logger.info(f"Total Online Nodes: {status_resp['total_nodes']}")

    logger.info("=== Demo Cycle Completed Successfully ===")

if __name__ == "__main__":
    run_full_cycle_demo()
