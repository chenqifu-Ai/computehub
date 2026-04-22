import requests
import time
import uuid
import json
import logging
import platform
import subprocess
import threading
from typing import Dict, Any

# --- 配置 ---
GATEWAY_URL = "http://localhost:18080/api/dispatch"
NODE_ID = f"node_{uuid.uuid4().hex[:8]}"
# 模拟设备指纹：实际应使用硬件 ID (如 MAC 或 CPU ID)
FINGERPRINT = f"fp_{platform.node()}_{platform.machine()}"
HEARTBEAT_INTERVAL = 10  # 秒

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ComputeHub-Node")

class HardwareCollector:
    """硬件指标采集器"""
    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        metrics = {
            "cpu_usage": 0,
            "mem_used": 0,
            "gpu_info": "N/A",
            "gpu_util": 0,
            "vram_used": 0,
            "timestamp": time.time()
        }
        try:
            # 简单的内存采集 (Linux)
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if "MemTotal" in line: metrics["mem_total"] = int(line.split()[1])
                    if "MemAvailable" in line: metrics["mem_avail"] = int(line.split()[1])
            
            # 尝试采集 NVIDIA GPU 指标
            gpu_res = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True
            )
            if gpu_res.returncode == 0:
                metrics["gpu_info"] = "NVIDIA"
                parts = gpu_res.stdout.strip().split(',')
                if len(parts) >= 2:
                    metrics["gpu_util"] = int(parts[0])
                    metrics["vram_used"] = int(parts[1])
        except Exception as e:
            logger.debug(f"Metrics collection partial failure: {e}")
            
        return metrics

class ComputeNode:
    def __init__(self):
        self.node_id = NODE_ID
        self.fingerprint = FINGERPRINT
        self.token = None
        self.hardware_info = json.dumps({
            "os": platform.system(),
            "node": platform.node(),
            "arch": platform.machine()
        })
        self.is_running = False

    def register(self):
        """节点注册获取 Token"""
        logger.info(f"Registering node {self.node_id}...")
        payload = {
            "command": "REGISTER",
            "args": [self.node_id, self.fingerprint, self.hardware_info]
        }
        try:
            response = requests.post(GATEWAY_URL, json=payload, timeout=5).json()
            if response.get("success"):
                self.token = response.get("token")
                logger.info(f"Registration successful. Token: {self.token}")
                return True
            else:
                logger.error(f"Registration failed: {response.get('error')}")
        except Exception as e:
            logger.error(f"Connection error during registration: {e}")
        return False

    def send_heartbeat(self):
        """发送心跳和硬件指标"""
        if not self.token:
            return
            
        metrics = HardwareCollector.get_metrics()
        payload = {
            "command": "HEARTBEAT",
            "args": [self.node_id, self.fingerprint, self.token, json.dumps(metrics)]
        }
        try:
            response = requests.post(GATEWAY_URL, json=payload, timeout=5).json()
            if response.get("success"):
                logger.info(f"Heartbeat sent. Trust Level: {response['data'].get('trust_level')}")
            else:
                logger.warning(f"Heartbeat rejected: {response.get('error')}")
                # 如果 Token 失效，尝试重新注册
                if "token" in response.get("error", "").lower():
                    self.register()
        except Exception as e:
            logger.error(f"Heartbeat connection error: {e}")

    def run(self):
        """启动节点主循环"""
        if not self.register():
            logger.error("Could not register node. Exiting.")
            return

        self.is_running = True
        logger.info("Node is now ONLINE. Starting heartbeat loop...")
        
        try:
            while self.is_running:
                self.send_heartbeat()
                time.sleep(HEARTBEAT_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Stopping node...")
            self.is_running = False

if __name__ == "__main__":
    node = ComputeNode()
    node.run()
