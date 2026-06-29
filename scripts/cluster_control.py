#!/usr/bin/env python3
"""
Agent 集群管控系统 — Cluster Control System (CCS)

整合 agent_coordinator.py 和 agent_negotiator.py，提供完整的集群管控功能。

核心功能:
  1. Agent 注册与发现
  2. 健康监控与故障转移
  3. 任务协商与分发
  4. 配置同步与状态共享
  5. 集群状态可视化

用法:
  python3 scripts/cluster_control.py [command]
  
  示例:
    python3 cluster_control.py init              # 初始化集群
    python3 cluster_control.py status            # 查看集群状态
    python3 cluster_control.py negotiate --task "检查 GPU"
    python3 cluster_control.py failover --from main --to arm
    python3 cluster_control.py start             # 启动集群控制器
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 导入之前的模块
sys.path.append(str(Path(__file__).parent))

from agent_coordinator import AgentCoordinator, AGENT_REGISTRY, CLUSTER_DIR
from agent_negotiator import AgentNegotiator, Message

# 集群配置
CLUSTER_CONFIG = {
    "cluster_id": "computehub-cluster",
    "coordinator": "main",
    "heartbeat_interval": 60,  # 秒
    "failover_threshold": 3,   # 连续失败次数
    "auto_failover": True,
    "message_ttl": 3600,       # 消息存活时间 (秒)
    "voting_quorum": 0.5       # 投票法定人数比例
}

class ClusterControlSystem:
    """集群控制系统"""
    
    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.negotiator = AgentNegotiator()
        self.config = CLUSTER_CONFIG.copy()
        self.running = False
        
    def init_cluster(self):
        """初始化集群"""
        print("🚀 初始化 Agent 集群...")
        
        # 创建集群目录
        CLUSTER_DIR.mkdir(parents=True, exist_ok=True)
        
        # 保存集群配置
        config_file = CLUSTER_DIR / "cluster_config.json"
        with open(config_file, "w") as f:
            json.dump(self.config, f, indent=2)
            
        # 注册所有 agent
        for agent_id, agent_config in AGENT_REGISTRY.items():
            self.coordinator.register_agent(agent_id, agent_config)
            
        # 发送初始心跳
        for agent_id in AGENT_REGISTRY:
            self.coordinator.send_heartbeat(agent_id)
            
        print(f"✅ 集群初始化完成 ({len(AGENT_REGISTRY)} 个 agent)")
        return True
        
    def check_cluster_health(self) -> dict:
        """检查集群健康"""
        print("\n🔍 检查集群健康状态...")
        
        health = {
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "status": "healthy"
        }
        
        # 检查每个 agent
        for agent_id in AGENT_REGISTRY:
            health["agents"][agent_id] = self.coordinator.check_agent_health(agent_id)
            
            if health["agents"][agent_id]["status"] == "unhealthy":
                health["status"] = "degraded"
                
        # 检查协商状态
        health["negotiation_sessions"] = len(self.negotiator.sessions)
        
        return health
        
    def negotiate_task(self, task_name: str, required_capabilities: List[str]) -> dict:
        """协商任务执行"""
        print(f"\n🤝 协商任务: {task_name}")
        
        # 确定参与者 (基于能力匹配)
        participants = []
        for agent_id, agent in AGENT_REGISTRY.items():
            capabilities = agent.get("capabilities", [])
            match = sum(1 for cap in required_capabilities if cap in capabilities)
            if match > 0:
                participants.append(agent_id)
                
        if not participants:
            print("❌ 没有匹配的 agent")
            return {"status": "failed", "reason": "no_matching_agent"}
            
        # 发起协商
        task = {
            "name": task_name,
            "description": f"执行任务：{task_name}",
            "required_capabilities": required_capabilities,
            "priority": "high",
            "timestamp": datetime.now().isoformat()
        }
        
        # 选择主要执行者 (能力匹配度最高的)
        primary = max(participants, key=lambda a: sum(1 for cap in required_capabilities if cap in AGENT_REGISTRY[a].get("capabilities", [])))
        
        session = self.negotiator.propose_task(
            self.config["coordinator"],
            primary,
            task,
            participants
        )
        
        print(f"✅ 协商完成: {session.id}")
        print(f"   主要执行者: {primary}")
        print(f"   参与者: {', '.join(session.participants)}")
        print(f"   状态: {session.status}")
        
        return {
            "status": "completed",
            "session_id": session.id,
            "primary_executor": primary,
            "participants": session.participants,
            "result": session.result
        }
        
    def failover(self, from_agent: str, to_agent: str) -> dict:
        """执行故障转移"""
        print(f"\n🔄 执行故障转移: {from_agent} → {to_agent}")
        
        # 检查目标 agent 是否可用
        target_health = self.coordinator.check_agent_health(to_agent)
        if target_health["status"] != "healthy":
            return {"status": "failed", "reason": "target_agent_unhealthy"}
            
        # 创建故障转移协商
        task = {
            "name": "failover",
            "description": f"从 {from_agent} 转移到 {to_agent}",
            "type": "failover",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "timestamp": datetime.now().isoformat()
        }
        
        session = self.negotiator.propose_task(
            self.config["coordinator"],
            to_agent,
            task,
            [self.config["coordinator"], to_agent]
        )
        
        # 执行转移
        if session.result and session.result["approved"]:
            # 更新 agent 状态
            self.coordinator.agents[from_agent]["status"] = "failed"
            self.coordinator.agents[to_agent]["status"] = "active"
            self.coordinator.save_state()
            
            return {
                "status": "completed",
                "from": from_agent,
                "to": to_agent,
                "session_id": session.id
            }
        else:
            return {"status": "failed", "reason": "negotiation_failed"}
            
    def sync_config(self, config_update: dict) -> dict:
        """同步配置到所有 agent"""
        print("\n🔄 同步配置到所有 agent...")
        
        # 创建配置同步消息
        config_msg = {
            "type": "config_sync",
            "update": config_update,
            "timestamp": datetime.now().isoformat()
        }
        
        # 通知所有 agent
        for agent_id in AGENT_REGISTRY:
            self.negotiator.create_message(
                "config_sync",
                self.config["coordinator"],
                agent_id,
                config_msg
            )
            
        # 本地应用配置
        local_config_file = Path("/root/.openclaw/workspace/config/cluster_config.json")
        local_config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(local_config_file, "w") as f:
            json.dump(config_update, f, indent=2)
            
        print(f"✅ 配置已同步到 {len(AGENT_REGISTRY)} 个 agent")
        return {"status": "completed", "agents_count": len(AGENT_REGISTRY)}
        
    def show_cluster_dashboard(self):
        """显示集群仪表盘"""
        print("=" * 80)
        print("📊 Agent 集群控制面板")
        print("=" * 80)
        
        # 集群状态
        health = self.check_cluster_health()
        
        print(f"\n🏢 集群状态: {'✅ 健康' if health['status'] == 'healthy' else '⚠️ 降级'}")
        print(f"👥 Agent 数量: {len(AGENT_REGISTRY)}")
        print(f"📬 消息队列: {len(self.negotiator.message_queue)}")
        print(f"🗳️ 协商会话: {len(self.negotiator.sessions)}")
        
        # Agent 状态
        print("\n📋 Agent 状态:")
        print("-" * 60)
        
        for agent_id, agent in AGENT_REGISTRY.items():
            health_info = health["agents"].get(agent_id, {})
            status = health_info.get("status", "unknown")
            
            status_icon = "✅" if status == "healthy" else "❌" if status in ["unhealthy", "unreachable"] else "⚠️"
            print(f"{status_icon} {agent['name']:15} | {agent['role']:12} | {status:10} | {', '.join(agent.get('capabilities', []))}")
            
        # 活跃协商
        if self.negotiator.sessions:
            print("\n🗳️ 活跃协商会话:")
            for sid, session in self.negotiator.sessions.items():
                print(f"   {sid}: {session.type} - {session.status}")
                
        print("\n" + "=" * 80)
        
    def start(self):
        """启动集群控制器"""
        print("🚀 启动 Agent 集群控制器...")
        
        # 初始化集群
        self.init_cluster()
        
        # 启动心跳监控
        print(f"⏰ 心跳间隔: {self.config['heartbeat_interval']} 秒")
        print(f"🔄 自动故障转移: {'启用' if self.config['auto_failover'] else '禁用'}")
        
        # 开始监控循环
        self.running = True
        self.show_cluster_dashboard()
        
        # 保持运行
        try:
            while self.running:
                time.sleep(self.config["heartbeat_interval"])
                self.show_cluster_dashboard()
        except KeyboardInterrupt:
            print("\n🛑 正在关闭集群控制器...")
            self.running = False
            print("✅ 集群控制器已停止")


def main():
    ccs = ClusterControlSystem()
    
    if len(sys.argv) < 2:
        print("用法: python3 cluster_control.py [command]")
        print("\ncommands:")
        print("  init                  初始化集群")
        print("  status                查看集群状态")
        print("  negotiate --task NAME --caps CAP1,CAP2  协商任务")
        print("  failover --from AGENT --to AGENT        故障转移")
        print("  sync --config JSON                         同步配置")
        print("  dashboard              显示集群仪表盘")
        print("  start                  启动集群控制器")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "init":
        ccs.init_cluster()
    elif command == "status":
        health = ccs.check_cluster_health()
        print(json.dumps(health, indent=2))
    elif command == "negotiate":
        # 解析参数
        task_name = ""
        caps = []
        for i, arg in enumerate(sys.argv):
            if arg == "--task" and i + 1 < len(sys.argv):
                task_name = sys.argv[i + 1]
            elif arg == "--caps" and i + 1 < len(sys.argv):
                caps = sys.argv[i + 1].split(",")
                
        if not task_name:
            print("❌ 需要指定 --task NAME")
            sys.exit(1)
            
        result = ccs.negotiate_task(task_name, caps)
        print(json.dumps(result, indent=2))
    elif command == "failover":
        from_agent = to_agent = ""
        for i, arg in enumerate(sys.argv):
            if arg == "--from" and i + 1 < len(sys.argv):
                from_agent = sys.argv[i + 1]
            elif arg == "--to" and i + 1 < len(sys.argv):
                to_agent = sys.argv[i + 1]
                
        if not from_agent or not to_agent:
            print("❌ 需要指定 --from 和 --to")
            sys.exit(1)
            
        result = ccs.failover(from_agent, to_agent)
        print(json.dumps(result, indent=2))
    elif command == "sync":
        # 简单的配置同步示例
        config_update = {"heartbeat_interval": 30, "auto_failover": True}
        result = ccs.sync_config(config_update)
        print(json.dumps(result, indent=2))
    elif command == "dashboard":
        ccs.show_cluster_dashboard()
    elif command == "start":
        ccs.start()
    else:
        print(f"❌ 未知命令: {command}")


if __name__ == "__main__":
    main()
