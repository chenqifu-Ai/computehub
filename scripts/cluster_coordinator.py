#!/usr/bin/env python3
"""
Agent Cluster Coordinator v2 — 基于 ComputeHub 真实数据

从 ComputeHub Gateway API (http://127.0.0.1:8282) 同步节点状态
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

CLUSTER_DIR = Path("/root/.openclaw/workspace/reports/cluster")
CLUSTER_DIR.mkdir(parents=True, exist_ok=True)

ECS_SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519_computehub")
ECS_SSH = f"ssh -i {ECS_SSH_KEY} -p 8022 computehub@36.250.122.43"

# 角色映射
ROLE_MAP = {
    "ecs-p2ph": "coordinator",
    "windows-mobile": "compute",
    "wanlida-temp": "gpu_compute",
    "wanlida-opc01": "compute",
    "worker-arm": "compute"
}

CAP_MAP = {
    "ecs-p2ph": ["health_check", "remote_exec", "config_update", "cluster_management"],
    "windows-mobile": ["windows_exec", "gpu_tasks", "remote_control"],
    "wanlida-temp": ["gpu_tasks", "high_perf_compute", "training"],
    "wanlida-opc01": ["compute", "remote_control"],
    "worker-arm": ["compute", "remote_control"]
}


class ClusterCoordinator:
    def __init__(self):
        self.agents = {}
        self.state = {
            "coordinator": "main",
            "heartbeat_interval": 60,
            "failover_threshold": 3,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "last_check": None
        }

    def fetch_nodes(self):
        """从 ComputeHub Gateway 获取节点数据"""
        try:
            cmd = f'{ECS_SSH} "curl -s \'http://127.0.0.1:8282/api/v1/nodes/list\'"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            data = json.loads(result.stdout)
            if data.get("success"):
                return data.get("data", [])
        except Exception as e:
            print(f"  ❌ 获取节点数据失败: {e}")
        return []

    def sync_agents(self, nodes):
        """同步节点到 Agent 注册表"""
        self.agents = {}
        for node in nodes:
            nid = node.get("node_id", "unknown")
            self.agents[nid] = {
                "name": nid.replace("-", " ").title(),
                "host": node.get("ip_address", "unknown"),
                "role": ROLE_MAP.get(nid, "compute"),
                "capabilities": CAP_MAP.get(nid, ["compute"]),
                "status": "healthy" if node.get("status") == "online" else "unhealthy",
                "last_heartbeat": datetime.now().isoformat(),
                "metadata": {
                    "node": nid,
                    "ip": node.get("ip_address", "N/A"),
                    "region": node.get("region", "N/A"),
                    "gpu": node.get("gpu_type", "N/A"),
                    "version": node.get("version", "N/A"),
                    "active_tasks": node.get("active_tasks", 0),
                    "max_tasks": 8,
                    "load": f"{node.get('active_tasks', 0)}/8"
                }
            }
        self.save_state()
        return self.agents

    def save_state(self):
        CLUSTER_DIR.mkdir(parents=True, exist_ok=True)
        with open(CLUSTER_DIR / "agents.json", "w") as f:
            json.dump(self.agents, f, indent=2, default=str)
        with open(CLUSTER_DIR / "cluster_state.json", "w") as f:
            json.dump(self.state, f, indent=2)

    def check_ecs_gateway(self):
        """检查 ECS OpenClaw Gateway"""
        try:
            cmd = f'{ECS_SSH} "curl -s -o /dev/null -w \'%{{http_code}}\' --connect-timeout 5 http://127.0.0.1:18789/"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            code = result.stdout.strip()
            return "healthy" if code.isdigit() and int(code) < 500 else "unhealthy"
        except:
            return "unreachable"

    def show_dashboard(self):
        """显示集群仪表盘"""
        print("=" * 80)
        print("📊 Agent 集群控制面板 (基于 ComputeHub 实时数据)")
        print("=" * 80)

        # OpenClaw Gateway
        gw = self.check_ecs_gateway()
        icon = "✅" if gw == "healthy" else "❌"
        print(f"\n{icon} OpenClaw Gateway: {gw} (ECS 36.250.122.43:18789)")

        # 同步节点
        print("\n📡 同步 ComputeHub 节点数据...")
        nodes = self.fetch_nodes()
        if nodes:
            print(f"✅ 获取到 {len(nodes)} 个 ComputeHub 节点")
            self.sync_agents(nodes)

        # 显示
        print("\n📋 节点状态:")
        print("-" * 80)
        print(f"{'节点':20} {'角色':15} {'IP':20} {'GPU':12} {'负载':10} {'版本':10} {'状态'}")
        print("-" * 80)

        for name, info in self.agents.items():
            meta = info.get("metadata", {})
            status = info["status"]
            icon = "✅" if status == "healthy" else "❌"
            active = meta.get("active_tasks", 0)

            # 用不同颜色标记负载
            load_bar = ""
            if active > 0:
                bars = min(8, active)
                load_bar = "█" * bars + "░" * (8 - bars)

            print(f"{name:20} | {info['role']:15} | {meta.get('ip', 'N/A'):20} | {meta.get('gpu', 'N/A'):12} | {load_bar} | {meta.get('version', 'N/A'):10} | {icon} {active} active")

        print("\n" + "=" * 80)

    def run_loop(self):
        """运行监控循环"""
        print("🚀 启动集群监控循环...")
        self.show_dashboard()

        while True:
            time.sleep(self.state.get("heartbeat_interval", 60))
            print("\n" + "=" * 80)
            self.show_dashboard()


if __name__ == "__main__":
    coordinator = ClusterCoordinator()
    coordinator.show_dashboard()
