import requests
import time
import random
import uuid
from datetime import datetime

API_URL = "http://localhost:5000"
NODE_ID = f"node_{uuid.uuid4().hex[:8]}"

def simulate_node():
    # 1. 注册节点
    print(f"🚀 [Node {NODE_ID}] Registering...")
    reg_data = {
        "node_id": NODE_ID,
        "hostname": "compute-node-01",
        "ip_address": "192.168.1.100",
        "gpu_model": "NVIDIA H100",
        "vram_total": 80,
        "region": "US-East"
    }
    try:
        resp = requests.post(f"{API_URL}/nodes/register", json=reg_data)
        print(f"✅ Registration Response: {resp.json()}")
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        return

    # 2. 模拟心跳上报 (发送 3 次)
    for i in range(3):
        print(f"💓 [Node {NODE_ID}] Sending heartbeat {i+1}/3...")
        heartbeat_data = {
            "node_id": NODE_ID,
            "gpu_temp": random.uniform(40.0, 85.0),
            "gpu_util": random.uniform(10.0, 95.0),
            "vram_used": random.randint(10, 70)
        }
        try:
            resp = requests.post(f"{API_URL}/nodes/heartbeat", json=heartbeat_data)
            print(f"✅ Heartbeat {i+1} Response: {resp.json()}")
        except Exception as e:
            print(f"❌ Heartbeat failed: {e}")
        time.sleep(1)

    # 3. 查询最终状态
    print("\n📊 Checking global status...")
    try:
        resp = requests.get(f"{API_URL}/nodes/status")
        print(f"✅ Final Status: {resp.json()}")
    except Exception as e:
        print(f"❌ Status check failed: {e}")

if __name__ == "__main__":
    simulate_node()
