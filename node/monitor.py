import subprocess
import json
import uuid
import platform
import time
import logging
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Node")

class PhysicalMonitor:
    def __init__(self, gateway_url="http://localhost:8000"):
        self.gateway_url = gateway_url
        self.node_id = self._generate_hardware_fingerprint()
        logger.info(f"Node initialized. ID: {self.node_id} | Gateway: {self.gateway_url}")
        self._register_node()

    def _generate_hardware_fingerprint(self):
        try:
            result = subprocess.check_output(["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader"], encoding='utf-8')
            gpu_uuid = result.strip().split('\n')[0]
            return f"node_{gpu_uuid}"
        except Exception:
            # For LAN simulation, we add a random suffix to ensure distinct node IDs on same machine
            import random
            node_info = f"{platform.node()}_{random.randint(1000,9999)}"
            return f"node_{node_info}"

    def _register_node(self):
        payload = {
            "node_id": self.node_id,
            "hardware_fingerprint": self.node_id, 
            "os": platform.system(),
            "gpu_model": "Virtual-GPU-Alpha",
            "memory_total_mb": 16384
        }
        try:
            resp = requests.post(f"{self.gateway_url}/api/v1/node/register", json=payload)
            logger.info(f"Registration response: {resp.status_code} - {resp.json()}")
        except Exception as e:
            logger.error(f"Registration failed: {e}")

    def get_gpu_metrics(self):
        import random
        return {
            "temperature": random.randint(40, 75),
            "utilization": random.randint(0, 100),
            "power_draw": random.uniform(50.0, 250.0),
            "memory_total": 16384,
            "memory_used": random.randint(1024, 8192),
            "timestamp": datetime.utcnow().isoformat()
        }

    def send_heartbeat(self):
        metrics = self.get_gpu_metrics()
        payload = {
            "node_id": self.node_id,
            "status": "ONLINE",
            "metrics": metrics,
            "version": "1.0.0-alpha"
        }
        try:
            requests.post(f"{self.gateway_url}/api/v1/node/heartbeat", json=payload)
            logger.info(f"Heartbeat sent: Util {metrics['utilization']}% | Temp {metrics['temperature']}C")
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    monitor = PhysicalMonitor(gateway_url=url)
    try:
        while True:
            monitor.send_heartbeat()
            time.sleep(5)
    except KeyboardInterrupt:
        pass
