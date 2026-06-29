#!/usr/bin/env python3
"""
Agent Cluster Coordinator — 多 Agent 集群管控系统

核心功能:
  1. Agent 心跳与健康监控
  2. 故障自动转移 (Failover)
  3. 任务分发与负载均衡
  4. 配置同步与状态共享

用法:
  python3 scripts/agent_coordinator.py [command]
  
  commands:
    start     - 启动集群管理器 (持续运行)
    status    - 显示集群状态
    register  - 注册新 agent
    heartbeat - 发送心跳
    task      - 分配任务
    config    - 同步配置
    
  示例:
    python3 agent_coordinator.py start
    python3 agent_coordinator.py status
    python3 agent_coordinator.py task --to arm --cmd "检查GPU"
"""

import json
import os
import sys
import time
import signal
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 集群状态存储
CLUSTER_DIR = Path("/root/.openclaw/workspace/reports/cluster")
HEARTBEAT_FILE = CLUSTER_DIR / "heartbeat.json"
TASK_QUEUE_FILE = CLUSTER_DIR / "task_queue.json"
CONFIG_SYNC_FILE = CLUSTER_DIR / "config_sync.json"

# Agent 注册表
AGENT_REGISTRY = {
    "main": {
        "name": "端智 (主控)",
        "host": "127.0.0.1",
        "gateway_port": 18789,
        "role": "coordinator",  # 集群协调器
        "capabilities": ["monitor", "control", "notification"],
        "status": "unknown",
        "last_heartbeat": None,
        "metadata": {
            "node": "local",
            "os": "android-termux",
            "arch": "arm64"
        }
    },
    "arm": {
        "name": "ARM Agent (端智)",
        "host": "36.250.122.43",
        "gateway_port": 18789,
        "ssh_port": 8022,
        "ssh_user": "computehub",
        "ssh_key": "~/.ssh/id_ed25519_computehub",
        "role": "coordinator",
        "capabilities": ["health_check", "remote_exec", "config_update", "cluster_management"],
        "status": "unknown",
        "last_heartbeat": None,
        "metadata": {
            "node": "ecs-p2ph",
            "ip": "36.250.122.43",
            "os": "linux-x64",
            "arch": "amd64",
            "gpu": "CPU only",
            "version": "1.3.34"
        }
    },
    "win": {
        "name": "windows-mobile",
        "host": "112.48.104.210",
        "gateway_port": 8383,
        "role": "compute",
        "capabilities": ["windows_exec", "gpu_tasks", "remote_control"],
        "status": "unknown",
        "last_heartbeat": None,
        "metadata": {
            "node": "windows-mobile",
            "ip": "112.48.104.210",
            "os": "windows",
            "arch": "amd64",
            "version": "1.3.30"
        }
    },
    "gpu1": {
        "name": "wanlida-temp",
        "host": "183.251.21.92",
        "ssh_port": 22,
        "ssh_user": "root",
        "role": "gpu_compute",
        "capabilities": ["gpu_tasks", "high_perf_compute", "training"],
        "status": "unknown",
        "last_heartbeat": None,
        "metadata": {
            "node": "wanlida-temp",
            "region": "cn-east",
            "ip": "183.251.21.92",
            "os": "linux",
            "gpu": "NVIDIA GeForce RTX 4060",
            "version": "1.3.34"
        }
    },
    "gpu2": {
        "name": "wanlida-opc01",
        "host": "183.251.21.92",
        "ssh_port": 22,
        "ssh_user": "root",
        "role": "compute",
        "capabilities": ["compute", "remote_control"],
        "status": "unknown",
        "last_heartbeat": None,
        "metadata": {
            "node": "wanlida-opc01",
            "ip": "183.251.21.92",
            "os": "linux",
            "version": "1.3.25"
        }
    },
    "mi": {
        "name": "worker-arm",
        "host": "36.248.233.174",
        "ssh_port": 22,
        "ssh_user": "computehub",
        "role": "compute",
        "capabilities": ["compute", "remote_control"],
        "status": "unknown",
        "last_heartbeat": None,
        "metadata": {
            "node": "worker-arm",
            "ip": "36.248.233.174",
            "os": "linux-arm",
            "version": "1.3.33"
        }
    }
}

# 集群运行状态
CLUSTER_STATE = {
    "coordinator": "main",
    "heartbeat_interval": 60,  # 秒
    "failover_threshold": 3,  # 连续失败次数
    "status": "running",
    "started_at": datetime.now().isoformat(),
    "last_check": None
}


class AgentCoordinator:
    """集群控制器"""
    
    def __init__(self):
        self.cluser_dir = CLUSTER_DIR
        self.cluser_dir.mkdir(parents=True, exist_ok=True)
        self.agents = AGENT_REGISTRY.copy()
        self.state = CLUSTER_STATE.copy()
        self.running = False
        self.threads = []
        
    def save_state(self):
        """保存集群状态"""
        CLUSTER_DIR.mkdir(parents=True, exist_ok=True)
        
        # 保存代理注册表
        with open(HEARTBEAT_FILE, "w") as f:
            json.dump(self.agents, f, indent=2, default=str)
        
        # 保存集群状态
        with open(CONFIG_SYNC_FILE, "w") as f:
            json.dump(self.state, f, indent=2)
            
    def load_state(self):
        """加载集群状态"""
        if HEARTBEAT_FILE.exists():
            with open(HEARTBEAT_FILE) as f:
                self.agents = json.load(f)
        if CONFIG_SYNC_FILE.exists():
            with open(CONFIG_SYNC_FILE) as f:
                self.state = json.load(f)
                
    def check_agent_health(self, agent_id: str) -> dict:
        """检查单个 agent 健康状态 (ComputeHub 集群节点)"""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}
            
        import subprocess
        import urllib.request
        
        # 本地 agent (ECS 主控)
        if agent["host"] == "127.0.0.1" or agent["host"] == "localhost":
            try:
                req = urllib.request.Request(
                    f"http://{agent['host']}:{agent['gateway_port']}/"
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    code = resp.status
                    agent["status"] = "healthy" if code < 500 else "degraded"
                    return {"agent": agent_id, "status": agent["status"], "code": code}
            except Exception as e:
                agent["status"] = "unhealthy"
                return {"agent": agent_id, "status": "unhealthy", "error": str(e)}
        
        # 所有远程节点通过 ECS SSH 查询 ComputeHub 集群状态
        elif agent_id in ["arm", "win", "gpu1", "gpu2", "mi"]:
            try:
                if agent_id == "arm":
                    # ECS 主控节点 - 检查 OpenClaw gateway + ComputeHub worker
                    cmd = f'ssh -i {agent["ssh_key"]} -p {agent["ssh_port"]} {agent["ssh_user"]}@{agent["host"]} "pgrep -f computehub | wc -l"'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                    
                    worker_count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
                    
                    if worker_count > 0:
                        agent["status"] = "healthy"
                    else:
                        agent["status"] = "unhealthy"
                    
                    return {"agent": agent_id, "status": agent["status"], "worker_count": worker_count, "type": "gateway+worker"}
                
                else:
                    # 其他节点状态 - 通过 ECS 查询 ComputeHub 节点信息
                    # 注意：这些是公网 IP，需要通过 ECS 的网络访问
                    node_ip = agent.get("metadata", {}).get("ip", "unknown")
                    cmd = f'ssh -i {agent["ssh_key"]} -p {agent["ssh_port"]} {agent["ssh_user"]}@{agent["host"]} "curl -s -o /dev/null -w \'%{{http_code}}\' --connect-timeout 3 http://{node_ip}:8383/ 2>/dev/null || echo unknown"'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                    output = result.stdout.strip()
                    
                    if "000" in output or "node_status:unknown" in output:
                        agent["status"] = "unreachable"  # 无法直接访问，需通过内网或 Tailscale
                    else:
                        agent["status"] = "healthy"
                    
                    return {"agent": agent_id, "status": agent["status"], "node_ip": agent.get("metadata", {}).get("ip", "unknown")}
                    
            except subprocess.TimeoutExpired:
                agent["status"] = "unreachable"
                return {"agent": agent_id, "status": "unreachable", "error": r"SSH timeout"}
            except Exception as e:
                agent["status"] = "unreachable"
                return {"agent": agent_id, "status": "unreachable", "error": str(e)}
        
        return {"agent": agent_id, "status": "unknown"}
        
    def check_all_agents(self):
        """检查所有 agent 状态"""
        results = {}
        for agent_id in self.agents:
            results[agent_id] = self.check_agent_health(agent_id)
            # 更新时间戳
            if results[agent_id]["status"] in ["healthy", "degraded"]:
                self.agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()
            elif self.agents[agent_id].get("status") == "healthy":
                # 从 healthy 变 unhealthy，记录时间
                pass
                
        self.save_state()
        return results
        
    def auto_failover(self, agent_id: str):
        """自动故障转移"""
        agent = self.agents.get(agent_id)
        if not agent or agent["status"] != "unhealthy":
            return False
            
        print(f"🚨 检测到 Agent {agent_id} 故障，启动自动故障转移...")
        
        # 1. 尝试重启 gateway
        if agent.get("ssh_host"):
            import subprocess
            try:
                # 通过 SSH 重启 gateway
                ssh_cmd = f"ssh -i {agent['ssh_key']} -p {agent['ssh_port']} {agent['ssh_user']}@{agent['host']} "
                ssh_cmd += f"\"pgrep -f 'openclaw-gateway' | xargs -r kill && sleep 3 && cd /home/computehub && nohup openclaw gateway > /tmp/openclaw-gw.log 2>&1 &\""
                
                result = subprocess.run(ssh_cmd, shell=True, timeout=30)
                if result.returncode == 0:
                    print(f"✅ Agent {agent_id} gateway 重启成功")
                    agent["status"] = "restarting"
                    self.save_state()
                    return True
            except Exception as e:
                print(f"❌ 自动重启失败: {e}")
        
        # 2. 通知其他 agent 接管任务
        print(f"📢 通知其他 agent 接管 {agent_id} 的任务...")
        self.notify_agents(agent_id, f"Agent {agent_id} 故障，请接管相关任务")
        
        return False
        
    def notify_agents(self, source: str, message: str):
        """通知所有 agent"""
        print(f"📢 从 {source} 发送通知: {message}")
        # TODO: 实现消息队列或 WebSocket 通知
        # 这里只是打印，后续可扩展为真正的消息系统
        
    def distribute_task(self, task: dict):
        """任务分发 - 基于 agent 能力"""
        capabilities = task.get("capabilities", [])
        best_agent = None
        best_score = 0
        
        for agent_id, agent in self.agents.items():
            score = 0
            for cap in capabilities:
                if cap in agent.get("capabilities", []):
                    score += 1
                    
            # 选择能力匹配度最高的 agent
            if score > best_score:
                best_score = score
                best_agent = agent_id
                
        if best_agent and best_score > 0:
            print(f"📤 任务分发给 Agent {best_agent} (匹配度: {best_score}/{len(capabilities)})")
            # TODO: 实际执行任务分发
            return best_agent
        else:
            print("❌ 没有合适的 agent 可执行此任务")
            return None
            
    def run_monitoring_loop(self):
        """监控循环 - 定期检查所有 agent"""
        print("🔄 启动集群监控循环...")
        
        while self.running:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 集群健康检查...")
                results = self.check_all_agents()
                
                # 处理故障 agent
                for agent_id, result in results.items():
                    if result["status"] == "unhealthy":
                        print(f"⚠️  Agent {agent_id}: {result['status']}")
                        self.auto_failover(agent_id)
                    elif result["status"] in ["healthy", "degraded"]:
                        print(f"✅ Agent {agent_id}: {result['status']}")
                        
            except Exception as e:
                print(f"❌ 监控循环错误: {e}")
                
            # 等待下一个心跳周期
            time.sleep(self.state.get("heartbeat_interval", 60))
            
    def start(self):
        """启动集群控制器"""
        print("🚀 启动 Agent 集群控制器...")
        self.running = True
        self.load_state()
        
        # 启动监控循环
        monitor_thread = threading.Thread(target=self.run_monitoring_loop, daemon=True)
        monitor_thread.start()
        self.threads.append(monitor_thread)
        
        print(f"✅ 集群控制器已启动 (ID: {self.state['coordinator']})")
        print(f"📊 监控 {len(self.agents)} 个 agent")
        print("💡 按 Ctrl+C 停止")
        
        # 保持运行
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 收到停止信号，正在关闭...")
            self.running = False
            for thread in self.threads:
                thread.join(timeout=5)
            print("✅ 集群控制器已停止")
            
    def status(self):
        """显示集群状态"""
        print("=" * 60)
        print("📊 Agent 集群状态")
        print("=" * 60)
        
        results = self.check_all_agents()
        
        for agent_id, agent in self.agents.items():
            health = results.get(agent_id, {})
            status_icon = "✅" if health.get("status") == "healthy" else "❌" if health.get("status") == "unhealthy" else "⚠️"
            
            print(f"\n{status_icon} {agent['name']} ({agent_id})")
            print(f"   角色: {agent['role']}")
            print(f"   状态: {health.get('status', 'unknown')}")
            print(f"   能力: {', '.join(agent.get('capabilities', []))}")
            print(f"   最后心跳: {agent.get('last_heartbeat', '从未')}")
            
        print("\n" + "=" * 60)
        self.save_state()
        
    def register_agent(self, agent_id: str, config: dict):
        """注册新 agent"""
        self.agents[agent_id] = {
            "name": config.get("name", agent_id),
            "host": config.get("host", "127.0.0.1"),
            "gateway_port": config.get("gateway_port", 18789),
            "role": config.get("role", "worker"),
            "capabilities": config.get("capabilities", []),
            "status": "unknown",
            "last_heartbeat": None,
            "metadata": config.get("metadata", {})
        }
        self.save_state()
        print(f"✅ Agent {agent_id} 已注册")
        
    def send_heartbeat(self, agent_id: str):
        """发送心跳"""
        if agent_id in self.agents:
            self.agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()
            self.save_state()
            print(f"✅ {agent_id} 心跳已发送")
        else:
            print(f"❌ Agent {agent_id} 未注册")


def main():
    coordinator = AgentCoordinator()
    
    if len(sys.argv) < 2:
        print("用法: python3 agent_coordinator.py [command]")
        print("  commands: start, status, register, heartbeat, task")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "start":
        coordinator.start()
    elif command == "status":
        coordinator.status()
    elif command == "register":
        # 简单注册示例
        agent_id = sys.argv[2] if len(sys.argv) > 2 else "new_agent"
        coordinator.register_agent(agent_id, {
            "name": agent_id,
            "host": "127.0.0.1",
            "role": "worker",
            "capabilities": ["execute"]
        })
    elif command == "heartbeat":
        agent_id = sys.argv[2] if len(sys.argv) > 2 else "main"
        coordinator.send_heartbeat(agent_id)
    elif command == "task":
        # 简单任务分发示例
        task = {"capabilities": ["monitor"], "command": "检查系统"}
        coordinator.distribute_task(task)
    else:
        print(f"❌ 未知命令: {command}")


if __name__ == "__main__":
    main()
