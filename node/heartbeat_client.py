#!/usr/bin/env python3
"""
Node Heartbeat Client
定期向 Gateway 发送心跳，报告节点状态

使用方法:
    python heartbeat_client.py --gateway http://GATEWAY_IP:8000 --node-id YOUR_NODE_ID
"""

import argparse
import requests
import time
import json
import os
import sys
from datetime import datetime

# 尝试导入监控库
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def get_metrics():
    """获取当前性能指标"""
    metrics = {
        "gpu_utilization": 0.0,
        "memory_utilization": 0.0,
        "network_latency_ms": 0.0,
        "gpu_temperature": None,
        "available_memory_gb": None,
    }
    
    # GPU 指标
    if PYNVML_AVAILABLE:
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            metrics["gpu_utilization"] = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
            metrics["gpu_temperature"] = pynvml.nvmlDeviceGetTemperature(handle, 0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            metrics["available_memory_gb"] = mem_info.free / (1024**3)
            pynvml.nvmlShutdown()
        except:
            pass
    
    # 系统内存
    if PSUTIL_AVAILABLE:
        try:
            metrics["memory_utilization"] = psutil.virtual_memory().percent
        except:
            pass
    
    return metrics


def send_heartbeat(gateway_url: str, node_id: str):
    """发送心跳到 Gateway"""
    metrics = get_metrics()
    
    payload = {
        "gpu_utilization": metrics["gpu_utilization"],
        "memory_utilization": metrics["memory_utilization"],
        "network_latency_ms": metrics["network_latency_ms"],
        "gpu_temperature": metrics["gpu_temperature"],
        "available_memory_gb": metrics["available_memory_gb"],
    }
    
    try:
        response = requests.post(
            f"{gateway_url}/api/v1/nodes/{node_id}/heartbeat",
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, f"Status: {response.status_code}"
            
    except Exception as e:
        return False, str(e)


def load_config():
    """加载节点配置"""
    config_file = os.path.join(os.path.dirname(__file__), 'node_config.json')
    
    if os.path.exists(config_file):
        with open(config_file) as f:
            return json.load(f)
    return None


def main():
    parser = argparse.ArgumentParser(description="Node Heartbeat Client")
    parser.add_argument("--gateway", help="Gateway URL")
    parser.add_argument("--node-id", help="Node ID")
    parser.add_argument("--interval", type=int, default=30, help="Heartbeat interval (seconds)")
    args = parser.parse_args()
    
    # 从配置文件加载
    config = load_config()
    
    gateway_url = args.gateway or (config["gateway_url"] if config else None)
    node_id = args.node_id or (config["node_id"] if config else None)
    
    if not gateway_url or not node_id:
        print("❌ 错误：需要指定 --gateway 和 --node-id，或先运行 join_cluster.py")
        sys.exit(1)
    
    print(f"💓 启动心跳服务")
    print(f"   Gateway: {gateway_url}")
    print(f"   Node ID: {node_id}")
    print(f"   间隔：{args.interval}秒")
    print()
    
    heartbeat_count = 0
    
    while True:
        try:
            success, result = send_heartbeat(gateway_url, node_id)
            
            if success:
                heartbeat_count += 1
                status = result.get("status", "unknown")
                gpu_util = result.get("metrics", {}).get("gpu_utilization", 0)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 心跳 #{heartbeat_count} | 状态：{status} | GPU: {gpu_util}%")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 心跳失败：{result}")
            
            time.sleep(args.interval)
            
        except KeyboardInterrupt:
            print("\n👋 心跳服务已停止")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 错误：{e}")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
