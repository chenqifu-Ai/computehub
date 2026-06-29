#!/usr/bin/env python3
"""
Agent 协商协议 — Agent Negotiation Protocol (ANP)

核心机制:
  1. 消息总线 (Message Bus) — 基于文件的轻量级消息队列
  2. 状态同步 (State Sync) — 共享配置 + 心跳状态
  3. 协商流程 (Negotiation) — 任务分配 + 故障协商 + 资源协商
  4. 仲裁机制 (Arbitration) — 主 agent 决策 + 投票机制

用法:
  python3 scripts/agent_negotiator.py [command]
  
  示例:
    python3 agent_negotiator.py start          # 启动协商进程
    python3 agent_negotiator.py propose --from main --to arm --task "修复 ECS"
    python3 agent_negotiator.py vote --id T123 --result approve
    python3 agent_negotiator.py status          # 查看协商状态
"""

import json
import os
import sys
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

# 协商数据存储
MSG_DIR = Path("/root/.openclaw/workspace/reports/cluster/messages")
MSG_DIR.mkdir(parents=True, exist_ok=True)

# 消息类型
MSG_TYPES = {
    "heartbeat": "心跳",
    "task_proposal": "任务提案",
    "task_vote": "任务投票",
    "status_update": "状态更新",
    "config_sync": "配置同步",
    "failover_request": "故障转移请求",
    "ack": "确认消息"
}

@dataclass
class Message:
    """协商消息"""
    id: str
    type: str
    from_agent: str
    to_agent: Optional[str]  # None = broadcast
    timestamp: str
    payload: dict
    signature: str = ""
    
    def sign(self, agent_id: str, secret: str):
        """消息签名"""
        content = f"{self.id}:{self.type}:{self.from_agent}:{self.timestamp}:{json.dumps(self.payload, sort_keys=True)}"
        self.signature = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()[:16]
        return self
    
    def verify(self, secret: str) -> bool:
        """验证签名"""
        content = f"{self.id}:{self.type}:{self.from_agent}:{self.timestamp}:{json.dumps(self.payload, sort_keys=True)}"
        expected = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()[:16]
        return self.signature == expected

@dataclass
class NegotiationSession:
    """协商会话"""
    id: str
    type: str  # task, failover, config
    proposer: str
    status: str  # pending, voting, completed, rejected
    participants: List[str]
    votes: Dict[str, str]  # agent_id -> approve/reject/abstain
    proposal: dict
    deadline: str
    result: Optional[dict] = None
    
    def add_vote(self, agent: str, vote: str):
        """添加投票"""
        self.votes[agent] = vote
        # 检查是否达到法定人数
        quorum = max(2, len(self.participants) // 2 + 1)
        if len(self.votes) >= quorum:
            self.status = "completed"
            # 计算结果
            approve_count = sum(1 for v in self.votes.values() if v == "approve")
            self.result = {"approved": approve_count >= quorum, "votes": self.votes.copy()}
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        deadline = datetime.fromisoformat(self.deadline)
        return datetime.now() > deadline


class AgentNegotiator:
    """Agent 协商器"""
    
    def __init__(self):
        self.secret = "cluster-secret-2026"  # 生产环境应更安全
        self.sessions: Dict[str, NegotiationSession] = {}
        self.message_queue: List[Message] = []
        
    def create_message(self, msg_type: str, from_agent: str, to_agent: str, payload: dict) -> Message:
        """创建协商消息"""
        msg_id = hashlib.md5(f"{from_agent}:{msg_type}:{datetime.now().isoformat()}:{str(payload)}".encode()).hexdigest()[:12]
        msg = Message(
            id=msg_id,
            type=msg_type,
            from_agent=from_agent,
            to_agent=to_agent,
            timestamp=datetime.now().isoformat(),
            payload=payload
        ).sign(from_agent, self.secret)
        
        # 保存到消息队列
        self.message_queue.append(msg)
        self.save_message(msg)
        
        return msg
    
    def save_message(self, msg: Message):
        """保存消息到文件"""
        msg_file = MSG_DIR / f"{msg.timestamp.replace(':', '-')[:19]}_{msg.id}.json"
        with open(msg_file, "w") as f:
            json.dump(asdict(msg), f, indent=2)
    
    def propose_task(self, from_agent: str, to_agent: str, task: dict, participants: List[str]) -> NegotiationSession:
        """发起任务提案"""
        session_id = f"T{int(time.time())}"
        session = NegotiationSession(
            id=session_id,
            type="task",
            proposer=from_agent,
            status="voting",
            participants=participants,
            votes={},
            proposal=task,
            deadline=datetime.now().isoformat()
        )
        
        # 创建提案消息
        proposal_msg = self.create_message(
            "task_proposal",
            from_agent,
            to_agent,
            {
                "session_id": session_id,
                "task": task,
                "participants": participants,
                "deadline": session.deadline
            }
        )
        
        # 自动回复提案 (模拟其他 agent 的响应)
        time.sleep(0.1)  # 模拟网络延迟
        for participant in participants:
            if participant != from_agent:
                # 检查 agent 能力
                capabilities = task.get("required_capabilities", [])
                agent_caps = self._get_agent_capabilities(participant)
                match = sum(1 for cap in capabilities if cap in agent_caps)
                
                if match >= len(capabilities) * 0.5:
                    vote = "approve"
                else:
                    vote = "abstain"
                
                session.add_vote(participant, vote)
                self.create_message(
                    "task_vote",
                    participant,
                    from_agent,
                    {"session_id": session_id, "vote": vote}
                )
        
        # 记录会话
        self.sessions[session_id] = session
        
        # 发送完成通知
        if session.status == "completed":
            self.create_message(
                "ack",
                from_agent,
                None,
                {"session_id": session_id, "result": session.result}
            )
        
        return session
    
    def _get_agent_capabilities(self, agent_id: str) -> List[str]:
        """获取 agent 能力 (简化版，实际应从 agent 注册表获取)"""
        capabilities_map = {
            "main": ["monitor", "control", "notification"],
            "arm": ["health_check", "remote_exec", "config_update"],
            "win": ["windows_exec", "gpu_tasks", "remote_control"],
            "mi": ["task_dispatch", "load_balance", "resource_mgmt"]
        }
        return capabilities_map.get(agent_id, [])
    
    def handle_heartbeat(self, agent_id: str, status: str, metadata: dict = None):
        """处理心跳消息"""
        self.create_message(
            "heartbeat",
            agent_id,
            None,  # 广播
            {
                "status": status,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
        )
        
    def start_negotiation_loop(self):
        """启动协商循环"""
        print("🔄 启动 Agent 协商循环...")
        
        while True:
            # 检查过期会话
            expired_sessions = [sid for sid, s in self.sessions.items() if s.is_expired()]
            for sid in expired_sessions:
                self.sessions[sid].status = "rejected"
                print(f"⏰ 会话 {sid} 已过期")
                
            # 清理过期会话
            for sid in expired_sessions:
                del self.sessions[sid]
                
            time.sleep(5)  # 每 5 秒检查一次
            
    def show_status(self):
        """显示协商状态"""
        print("=" * 60)
        print("📊 Agent 协商状态")
        print("=" * 60)
        
        print(f"\n活跃会话: {len(self.sessions)}")
        for sid, session in self.sessions.items():
            status_icon = "✅" if session.status == "completed" else "⏳" if session.status == "voting" else "❌"
            print(f"\n{status_icon} 会话 {sid} ({session.type})")
            print(f"   状态: {session.status}")
            print(f"   提案者: {session.proposer}")
            print(f"   参与者: {', '.join(session.participants)}")
            print(f"   投票: {session.votes}")
            if session.result:
                print(f"   结果: {'通过' if session.result['approved'] else '拒绝'}")
        
        print(f"\n消息队列: {len(self.message_queue)} 条")
        print("=" * 60)


def main():
    negotiator = AgentNegotiator()
    
    if len(sys.argv) < 2:
        print("用法: python3 agent_negotiator.py [command]")
        print("  commands: start, propose, vote, status")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "start":
        negotiator.start_negotiation_loop()
    elif command == "propose":
        # 示例: main 向 arm 发起任务
        task = {
            "name": "修复 ECS Gateway",
            "description": "重启 ECS 上的 OpenClaw gateway",
            "required_capabilities": ["health_check", "remote_exec"],
            "priority": "high",
            "deadline": datetime.now().isoformat()
        }
        participants = ["main", "arm", "mi"]
        session = negotiator.propose_task("main", "arm", task, participants)
        print(f"✅ 任务提案已创建: {session.id}")
        print(f"   状态: {session.status}")
        print(f"   投票: {session.votes}")
    elif command == "status":
        negotiator.show_status()
    else:
        print(f"❌ 未知命令: {command}")


if __name__ == "__main__":
    main()
