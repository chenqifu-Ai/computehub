#!/usr/bin/env python3
"""
Node Auto-Join Script
算力节点一键接入 ComputeHub 集群

使用方法:
    python join_cluster.py --gateway http://GATEWAY_IP:8000
"""

import argparse
import requests
import socket
import sys
import os
import json
from datetime import datetime

# 尝试获取 GPU 信息
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


def get_gpu_info():
    """获取 GPU 信息"""
    if not PYNVML_AVAILABLE:
        return {"gpu_model": "Unknown", "gpu_count": 0}
    
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        
        if device_count == 0:
            pynvml.nvmlShutdown()
            return {"gpu_model": "None", "gpu_count": 0}
        
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(gpu_name, bytes):
            gpu_name = gpu_name.decode('utf-8')
        
        pynvml.nvmlShutdown()
        
        return {
            "gpu_model": gpu_name,
            "gpu_count": device_count,
        }
    except Exception as e:
        return {"gpu_model": "Error", "gpu_count": 0, "error": str(e)}


def get_system_info():
    """获取系统信息"""
    info = {
        "hostname": socket.gethostname(),
        "cpu_cores": 0,
        "memory_gb": 0,
    }
    
    if PSUTIL_AVAILABLE:
        info["cpu_cores"] = psutil.cpu_count(logical=True)
        info["memory_gb"] = psutil.virtual_memory().total // (1024**3)
    else:
        # 备用方案：读取 /proc/cpuinfo
        try:
            with open('/proc/cpuinfo') as f:
                info["cpu_cores"] = len([line for line in f if 'processor' in line])
        except:
            pass
        
        # 读取内存
        try:
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        info["memory_gb"] = int(line.split()[1]) // (1024**2)
        except:
            pass
    
    return info


def get_location():
    """获取地理位置（简化版）"""
    # 可以通过 IP 定位 API 获取，这里使用默认值
    return {
        "country": "China",
        "city": "Unknown",
        "latitude": None,
        "longitude": None,
    }


def register_node(gateway_url: str, custom_name: str = None):
    """注册节点到集群"""
    print(f"🔍 检测硬件信息...")
    
    # 收集信息
    gpu_info = get_gpu_info()
    sys_info = get_system_info()
    location = get_location()
    
    # 生成节点名称
    node_name = custom_name or f"{sys_info['hostname']}-{gpu_info['gpu_model'].replace(' ', '-')}""
    
    print(f"📊 检测到:")
    print(f"   - GPU: {gpu_info['gpu_count']}x {gpu_info['gpu_model']}")
    print(f"   - CPU: {sys_info['cpu_cores']} 核心")
    print(f"   - 内存：{sys_info['memory_gb']} GB")
    print(f"   - 主机名：{sys_info['hostname']}")
    print()
    
    # 注册请求
    payload = {
        "name": node_name,
        "gpu_model": gpu_info['gpu_model'],
        "gpu_count": gpu_info['gpu_count'],
        "cpu_cores": sys_info['cpu_cores'],
        "memory_gb": sys_info['memory_gb'],
        **location,
    }
    
    print(f"📡 正在注册到集群 {gateway_url}...")
    
    try:
        response = requests.post(
            f"{gateway_url}/api/v1/nodes/register",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ 注册成功！")
            print()
            print(f"📋 节点信息:")
            print(f"   - 节点 ID: {data['id']}")
            print(f"   - 节点名称：{data['name']}")
            print(f"   - 状态：{data['status']}")
            print()
            
            # 保存节点配置
            config = {
                "node_id": data['id'],
                "node_name": data['name'],
                "gateway_url": gateway_url,
                "registered_at": datetime.now().isoformat(),
            }
            
            config_file = os.path.join(os.path.dirname(__file__), 'node_config.json')
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"💾 配置已保存到：{config_file}")
            print()
            print(f"🚀 下一步:")
            print(f"   1. 启动 Node Agent: python agent_api.py")
            print(f"   2. 启动心跳服务：python heartbeat_client.py")
            print()
            
            return data
        else:
            print(f"❌ 注册失败：{response.status_code}")
            print(f"   {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到 Gateway: {gateway_url}")
        print(f"   请检查网络或 Gateway 地址是否正确")
        return None
    except Exception as e:
        print(f"❌ 注册失败：{e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="ComputeHub Node Auto-Join")
    parser.add_argument("--gateway", required=True, help="Gateway URL (e.g., http://192.168.1.100:8000)")
    parser.add_argument("--name", help="Custom node name (optional)")
    args = parser.parse_args()
    
    print("🤖 ComputeHub 节点接入工具")
    print("=" * 50)
    print()
    
    register_node(args.gateway, args.name)


if __name__ == "__main__":
    main()
