import subprocess
import json
import uuid
import platform
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Node")

class PhysicalMonitor:
    """
    ComputeHub 物理监控原点：负责采集真实的硬件指标
    """
    def __init__(self):
        self.node_id = self._generate_hardware_fingerprint()
        logger.info(f"Node initialized. Hardware Fingerprint: {self.node_id}")

    def _generate_hardware_fingerprint(self):
        """
        生成基于硬件唯一标识的指纹，防止节点伪造
        """
        try:
            # 尝试获取 GPU UUID (NVIDIA)
            result = subprocess.check_output(["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader"], encoding='utf-8')
            gpu_uuid = result.strip().split('\n')[0]
            return f"node_{gpu_uuid}"
        except Exception:
            # 退而求其次，使用机器 ID 和平台信息
            node_info = f"{platform.node()}_{platform.processor()}_{uuid.getnode()}"
            return f"node_{node_info}"

    def get_gpu_metrics(self):
        """
        采集 NVIDIA GPU 实时物理指标
        """
        try:
            # 采集 温度, 显存利用率, 功耗, 显存总量, 显存已用
            cmd = "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,power.draw,memory.total,memory.used --format=csv,noheader,nounits"
            result = subprocess.check_output(cmd.split(), encoding='utf-8').strip()
            metrics = result.split(',')
            
            return {
                "temperature": int(metrics[0]),
                "utilization": int(metrics[1]),
                "power_draw": float(metrics[2]),
                "memory_total": int(metrics[3]),
                "memory_used": int(metrics[4]),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to collect GPU metrics: {e}")
            return None

    def create_heartbeat_packet(self):
        """
        构建心跳数据包
        """
        metrics = self.get_gpu_metrics()
        if not metrics:
            return None
            
        return {
            "node_id": self.node_id,
            "status": "ONLINE",
            "metrics": metrics,
            "os": platform.system(),
            "version": "1.0.0-alpha"
        }

if __name__ == "__main__":
    monitor = PhysicalMonitor()
    print("Starting ComputeHub Physical Monitor... (Press Ctrl+C to stop)")
    try:
        while True:
            packet = monitor.create_heartbeat_packet()
            if packet:
                print(f"Heartbeat Packet: {json.dumps(packet, indent=2)}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
