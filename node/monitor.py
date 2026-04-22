#!/usr/bin/env python3
"""
物理心跳监控系统 - 简化版（无外部依赖）
"""
import platform
import uuid
import json
import time
import logging
import subprocess
import os
from typing import Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("ComputeHub-Monitor")

class PhysicalMonitor:
    """物理硬件监控器"""
    
    def __init__(self):
        self.node_id = f"node_{platform.node()}_{uuid.uuid4().hex[:8]}"
        self.fingerprint = self._generate_hardware_fingerprint()
        logger.info(f"PhysicalMonitor initialized for node: {self.node_id}")
    
    def _generate_hardware_fingerprint(self) -> str:
        """生成硬件唯一指纹"""
        fingerprint_data = {
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "platform": platform.platform(),
            "boot_id": self._get_boot_id()
        }
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, json.dumps(fingerprint_data, sort_keys=True)))
    
    def _get_boot_id(self) -> str:
        """获取系统启动ID"""
        try:
            if os.path.exists('/proc/sys/kernel/random/boot_id'):
                with open('/proc/sys/kernel/random/boot_id', 'r') as f:
                    return f.read().strip()
        except:
            pass
        return str(uuid.uuid4())
    
    def get_cpu_metrics(self) -> Dict[str, Any]:
        """获取CPU指标"""
        try:
            # 读取/proc/stat获取CPU信息
            with open('/proc/stat', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('cpu '):
                        parts = line.split()
                        total = sum(int(x) for x in parts[1:])
                        idle = int(parts[4])
                        usage = 100 * (total - idle) / total if total > 0 else 0
                        return {
                            "usage_percent": round(usage, 1),
                            "cores": os.cpu_count() or 1
                        }
        except Exception as e:
            logger.error(f"Failed to get CPU metrics: {e}")
        return {"usage_percent": 0, "cores": 1}
    
    def get_memory_metrics(self) -> Dict[str, Any]:
        """获取内存指标"""
        try:
            # 读取/proc/meminfo获取内存信息
            mem_info = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        mem_info[key.strip()] = value.strip()
            
            total = int(mem_info.get('MemTotal', '0 kB').split()[0]) * 1024
            free = int(mem_info.get('MemFree', '0 kB').split()[0]) * 1024
            available = int(mem_info.get('MemAvailable', '0 kB').split()[0]) * 1024
            
            return {
                "total": total,
                "free": free,
                "available": available,
                "used": total - free,
                "usage_percent": round(100 * (total - available) / total, 1) if total > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get memory metrics: {e}")
            return {"total": 0, "free": 0, "used": 0, "usage_percent": 0}
    
    def get_gpu_metrics(self) -> Dict[str, Any]:
        """获取GPU指标"""
        try:
            # 尝试使用nvidia-smi获取GPU信息
            result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.total,memory.used,memory.free,driver_version', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                gpus = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 8:
                            gpus.append({
                                "id": int(parts[0]),
                                "name": parts[1],
                                "temperature": float(parts[2]),
                                "utilization": float(parts[3]),
                                "memory_total": int(parts[4]),
                                "memory_used": int(parts[5]),
                                "memory_free": int(parts[6]),
                                "driver": parts[7]
                            })
                
                return {
                    "gpu_count": len(gpus),
                    "gpus": gpus,
                    "source": "nvidia-smi"
                }
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        except Exception as e:
            logger.warning(f"GPU metrics unavailable: {e}")
        
        return {"gpu_count": 0, "gpus": [], "source": "none"}
    
    def get_network_metrics(self) -> Dict[str, Any]:
        """获取网络指标"""
        try:
            # 读取/proc/net/dev获取网络信息
            net_info = {}
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()[2:]  # 跳过前两行标题
                for line in lines:
                    if ':' in line:
                        interface, data = line.split(':', 1)
                        interface = interface.strip()
                        parts = data.split()
                        if len(parts) >= 16:
                            net_info[interface] = {
                                "bytes_recv": int(parts[0]),
                                "bytes_sent": int(parts[8])
                            }
            
            return {
                "interfaces": net_info,
                "total_bytes_recv": sum(info["bytes_recv"] for info in net_info.values()),
                "total_bytes_sent": sum(info["bytes_sent"] for info in net_info.values())
            }
        except Exception as e:
            logger.error(f"Failed to get network metrics: {e}")
            return {"interfaces": {}, "total_bytes_recv": 0, "total_bytes_sent": 0}
    
    def get_disk_metrics(self) -> Dict[str, Any]:
        """获取磁盘指标"""
        try:
            # 使用df命令获取磁盘使用情况
            result = subprocess.run(['df', '/'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        return {
                            "total": int(parts[1]) * 1024,
                            "used": int(parts[2]) * 1024,
                            "free": int(parts[3]) * 1024,
                            "usage_percent": int(parts[4].replace('%', ''))
                        }
        except Exception as e:
            logger.error(f"Failed to get disk metrics: {e}")
        
        return {"total": 0, "used": 0, "free": 0, "usage_percent": 0}
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """收集所有物理指标"""
        timestamp = time.time()
        
        metrics = {
            "timestamp": timestamp,
            "node_id": self.node_id,
            "fingerprint": self.fingerprint,
            "cpu": self.get_cpu_metrics(),
            "memory": self.get_memory_metrics(),
            "gpu": self.get_gpu_metrics(),
            "network": self.get_network_metrics(),
            "disk": self.get_disk_metrics(),
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "hostname": platform.node()
            }
        }
        
        logger.info(f"Collected metrics for node {self.node_id}")
        return metrics
    
    def generate_heartbeat_payload(self) -> str:
        """生成心跳负载数据"""
        metrics = self.collect_all_metrics()
        return json.dumps(metrics)

# 测试函数
def test_monitor():
    """测试监控器"""
    monitor = PhysicalMonitor()
    print(f"Node ID: {monitor.node_id}")
    print(f"Hardware Fingerprint: {monitor.fingerprint}")
    
    # 收集指标
    metrics = monitor.collect_all_metrics()
    print("\n=== Physical Metrics ===")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    
    # 生成心跳负载
    heartbeat = monitor.generate_heartbeat_payload()
    print(f"\nHeartbeat payload size: {len(heartbeat)} bytes")
    
    return metrics

if __name__ == "__main__":
    test_monitor()