#!/usr/bin/env python3
"""
状态快照与恢复系统
创建当前状态快照，重启时自动恢复
"""

import json
import os
import time
from datetime import datetime
import shutil

class SnapshotSystem:
    """状态快照系统"""
    
    def __init__(self, snapshot_dir="/root/.openclaw/workspace/snapshots"):
        self.snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)
        
    def create_snapshot(self, snapshot_data):
        """创建状态快照"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"snapshot_{timestamp}.json"
        filepath = os.path.join(self.snapshot_dir, filename)
        
        # 添加快照时间戳
        snapshot_data["snapshot_timestamp"] = timestamp
        snapshot_data["snapshot_version"] = "1.0"
        
        # 保存快照
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
        
        # 更新最新快照链接
        latest_link = os.path.join(self.snapshot_dir, "latest_snapshot.json")
        if os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(filename, latest_link)
        
        print(f"✅ 快照创建成功: {filename}")
        return filepath
    
    def load_latest_snapshot(self):
        """加载最新快照"""
        latest_link = os.path.join(self.snapshot_dir, "latest_snapshot.json")
        
        if not os.path.exists(latest_link):
            print("⚠️  没有找到最新快照")
            return None
        
        try:
            # 解析符号链接获取实际文件
            actual_file = os.path.realpath(latest_link)
            with open(actual_file, 'r', encoding='utf-8') as f:
                snapshot_data = json.load(f)
            
            print(f"✅ 快照加载成功: {os.path.basename(actual_file)}")
            return snapshot_data
            
        except Exception as e:
            print(f"❌ 快照加载失败: {e}")
            return None
    
    def get_snapshot_status(self):
        """获取快照系统状态"""
        if not os.path.exists(self.snapshot_dir):
            return {"status": "未初始化", "snapshot_count": 0}
        
        snapshots = [f for f in os.listdir(self.snapshot_dir) 
                    if f.startswith("snapshot_") and f.endswith(".json")]
        
        latest_exists = os.path.exists(os.path.join(self.snapshot_dir, "latest_snapshot.json"))
        
        return {
            "status": "运行中",
            "snapshot_count": len(snapshots),
            "latest_snapshot": latest_exists,
            "snapshot_dir": self.snapshot_dir
        }
    
    def cleanup_old_snapshots(self, keep_count=10):
        """清理旧快照，保留指定数量"""
        snapshots = [f for f in os.listdir(self.snapshot_dir) 
                    if f.startswith("snapshot_") and f.endswith(".json")]
        
        if len(snapshots) <= keep_count:
            print(f"✅ 当前有 {len(snapshots)} 个快照，无需清理")
            return
        
        # 按时间排序，删除最旧的
        snapshots.sort()
        to_delete = snapshots[:-keep_count]
        
        for snapshot in to_delete:
            filepath = os.path.join(self.snapshot_dir, snapshot)
            os.remove(filepath)
            print(f"🗑️  删除旧快照: {snapshot}")
        
        print(f"✅ 清理完成，保留 {keep_count} 个最新快照")

def create_current_snapshot():
    """创建当前状态快照"""
    snapshot_system = SnapshotSystem()
    
    # 收集当前状态数据
    current_state = {
        "system_info": {
            "timestamp": datetime.now().isoformat(),
            "openclaw_version": "1.0",
            "model": "ollama-cloud/deepseek-v3.1:671b"
        },
        "session_data": {
            "current_conversation": "状态快照系统讨论",
            "active_skills": ["continuous-flow-execution", "habit-smart-assistant"],
            "recent_tasks": ["智能决策引擎演示", "习惯智能助手开发"]
        },
        "user_preferences": {
            "response_speed": "fast",
            "detail_level": "concise",
            "preferred_skills": ["智能决策", "邮件自动化", "零交互执行"]
        },
        "learning_data": {
            "new_knowledge": ["状态快照技术", "系统恢复机制"],
            "skill_improvements": ["连续流执行优化", "习惯智能助手开发"]
        },
        "project_status": {
            "openremoteai": "开发完成",
            "habit_smart_assistant": "设计阶段",
            "snapshot_system": "开发中"
        }
    }
    
    # 创建快照
    snapshot_path = snapshot_system.create_snapshot(current_state)
    
    # 显示状态
    status = snapshot_system.get_snapshot_status()
    print(f"📊 快照系统状态: {status}")
    
    return snapshot_path

def restore_from_snapshot():
    """从快照恢复状态"""
    snapshot_system = SnapshotSystem()
    
    snapshot_data = snapshot_system.load_latest_snapshot()
    
    if snapshot_data:
        print("🎯 恢复以下状态:")
        print(f"   会话: {snapshot_data['session_data']['current_conversation']}")
        print(f"   活跃技能: {', '.join(snapshot_data['session_data']['active_skills'])}")
        print(f"   用户偏好: {snapshot_data['user_preferences']['response_speed']}响应")
        
        return snapshot_data
    else:
        print("⚠️  无法恢复状态，使用默认配置")
        return None

if __name__ == "__main__":
    # 测试快照系统
    print("🚀 测试状态快照系统...")
    
    # 创建当前快照
    snapshot_path = create_current_snapshot()
    
    # 尝试恢复
    restored_data = restore_from_snapshot()
    
    if restored_data:
        print("✅ 状态快照系统测试成功!")
    else:
        print("❌ 状态快照系统测试失败")