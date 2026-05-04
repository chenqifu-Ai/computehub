#!/usr/bin/env python3
"""
命令和动作记录系统
记录所有收到的命令和执行的动作
"""

import json
import time
from datetime import datetime

COMMAND_LOG = "/root/.openclaw/workspace/command_log.json"
ACTION_LOG = "/root/.openclaw/workspace/action_log.json"

def log_command(sender, command, context=None):
    """记录收到的命令"""
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "sender": sender,
        "command": command,
        "context": context or {},
        "status": "received"
    }
    
    # 读取现有日志
    try:
        with open(COMMAND_LOG, 'r') as f:
            logs = json.load(f)
    except:
        logs = []
    
    # 添加新记录
    logs.append(log_entry)
    
    # 保存日志
    with open(COMMAND_LOG, 'w') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    
    print(f"📝 命令已记录: {command[:50]}...")

def log_action(command_id, action_type, description, details=None):
    """记录执行的动作"""
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "command_id": command_id,
        "action_type": action_type,
        "description": description,
        "details": details or {},
        "status": "executed"
    }
    
    # 读取现有日志
    try:
        with open(ACTION_LOG, 'r') as f:
            logs = json.load(f)
    except:
        logs = []
    
    # 添加新记录
    logs.append(log_entry)
    
    # 保存日志
    with open(ACTION_LOG, 'w') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    
    print(f"🔧 动作已记录: {description}")

def search_commands(keyword):
    """搜索命令记录"""
    try:
        with open(COMMAND_LOG, 'r') as f:
            logs = json.load(f)
        
        results = []
        for log in logs:
            if keyword.lower() in str(log).lower():
                results.append(log)
        
        return results
    except:
        return []

def search_actions(keyword):
    """搜索动作记录"""
    try:
        with open(ACTION_LOG, 'r') as f:
            logs = json.load(f)
        
        results = []
        for log in logs:
            if keyword.lower() in str(log).lower():
                results.append(log)
        
        return results
    except:
        return []

if __name__ == "__main__":
    # 测试
    log_command("test_user", "测试命令", {"test": True})
    log_action("test_001", "test", "测试动作")
    print("✅ 命令记录系统已启动")