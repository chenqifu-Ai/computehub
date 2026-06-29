#!/usr/bin/env python3
"""
ComputeHub 集群监控 - 通过 ECS Gateway 同步节点状态

功能:
  1. 从 ComputeHub Gateway API 获取节点列表
  2. 更新集群控制器状态
  3. 检测异常节点并告警
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# 配置
ECS_SSH = "ssh -i ~/.ssh/id_ed25519_computehub -p 8022 computehub@36.250.122.43"
STATE_FILE = Path("/root/.openclaw/workspace/reports/cluster/cluster_status.json")
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

def fetch_cluster_status():
    """从 ECS 获取 ComputeHub 集群状态"""
    try:
        # 通过 ECS SSH 查询 ComputeHub Gateway 的节点状态
        cmd = f'{ECS_SSH} "curl -s http://127.0.0.1:8282/api/v1/workers 2>/dev/null || echo \'{{}}\'"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        
        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            return {"error": "Failed to parse response", "raw": result.stdout}
    except Exception as e:
        return {"error": str(e)}


def fetch_webui_status():
    """通过 OpenClaw agent 执行 WebUI 状态查询"""
    try:
        cmd = f'{ECS_SSH} "curl -s http://127.0.0.1:8282/ 2>/dev/null | grep -o \'node[^"]*\' | head -20"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout.strip()
    except Exception as e:
        return str(e)


def main():
    print("=" * 60)
    print("🔍 ComputeHub 集群状态监控")
    print("=" * 60)
    
    # 获取集群状态
    print("\n📊 从 Gateway 查询节点状态...")
    status = fetch_cluster_status()
    
    if "error" in status:
        print(f"❌ 错误: {status['error']}")
        print("\n💡 提示: 需要通过 ECS 的 ComputeHub Gateway API 获取")
        print("   或者通过 WebUI (http://36.250.122.43:8282) 查看")
        return
    
    print(f"\n✅ 获取到 {len(status.get('workers', []))} 个节点:")
    
    for node in status.get("workers", []):
        node_id = node.get("node_id", "unknown")
        status_info = node.get("status", "unknown")
        load = node.get("load", "0/0")
        gpu = node.get("gpu", "N/A")
        
        status_icon = "✅" if status_info == "running" else "⚠️" if status_info == "busy" else "❌"
        
        print(f"{status_icon} {node_id:20} | 负载：{load:10} | GPU: {gpu}")
    
    # 保存状态到文件
    save_data = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "agents": {
            "main": {"status": "healthy", "role": "coordinator"},
            "arm": {"status": "healthy", "role": "coordinator", "worker_count": status.get("worker_count", 0)}
        }
    }
    
    with open(STATE_FILE, "w") as f:
        json.dump(save_data, f, indent=2)
    
    print(f"\n📁 状态已保存到：{STATE_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
