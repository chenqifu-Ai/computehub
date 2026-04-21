import requests
import time
import json
import platform
import uuid
from node.monitor import PhysicalMonitor

class ComputeHubNodeClient:
    """
    ComputeHub 节点客户端：负责将本地物理指标同步至远程网关
    """
    def __init__(self, gateway_url="http://localhost:8000"):
        self.gateway_url = gateway_url
        self.monitor = PhysicalMonitor()
        self.node_id = self.monitor.node_id
        self.api_key = "alpha-test-key" # 预留 API Key 位置

    def register(self):
        """
        执行节点注册，将物理指纹同步到网关
        """
        print(f"[*] Registering node {self.node_id} to gateway...")
        payload = {
            "node_id": self.node_id,
            "hardware_fingerprint": self.node_id, # 这里简化使用 node_id 作为指纹
            "os": platform.system(),
            "gpu_model": "NVIDIA-Generic", # 实际可从 nvidia-smi 采集
            "memory_total_mb": 24576 # 模拟 24GB 显存
        }
        try:
            resp = requests.post(f"{self.gateway_url}/api/v1/node/register", json=payload, timeout=5)
            if resp.status_code == 200:
                print("[+] Registration successful!")
                return True
            else:
                print(f"[-] Registration failed: {resp.text}")
        except Exception as e:
            print(f"[-] Connection error during registration: {e}")
        return False

    def send_heartbeat(self):
        """
        发送物理心跳包
        """
        packet = self.monitor.create_heartbeat_packet()
        if not packet:
            print("[-] No metrics available, skipping heartbeat.")
            return False
            
        try:
            resp = requests.post(f"{self.gateway_url}/api/v1/node/heartbeat", json=packet, timeout=5)
            if resp.status_code == 200:
                print(f"[+] Heartbeat sent: {packet['metrics']['temperature']}C | {packet['metrics']['utilization']}%")
                return True
            else:
                print(f"[-] Heartbeat rejected: {resp.text}")
        except Exception as e:
            print(f"[-] Connection error during heartbeat: {e}")
        return False

    def run(self, interval=5):
        """
        启动节点运行循环
        """
        if not self.register():
            print("[!] Critical: Could not register node. Exiting.")
            return

        print(f"[*] Node {self.node_id} is now online. Sending heartbeats every {interval}s...")
        try:
            while True:
                self.send_heartbeat()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[*] Node shutting down.")

if __name__ == "__main__":
    # 允许通过命令行修改网关地址
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    client = ComputeHubNodeClient(gateway_url=url)
    client.run()
