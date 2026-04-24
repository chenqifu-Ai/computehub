#!/usr/bin/env python3
"""
操作记录系统
所有操作必须记录，有迹可查
"""

import json
import time
from datetime import datetime

LOG_FILE = "/root/.openclaw/workspace/operation_log.json"

def log_operation(action_type, description, details=None, risk_level="low"):
    """记录操作"""
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "description": description,
        "details": details or {},
        "risk_level": risk_level,
        "user": "AI Agent"
    }
    
    # 读取现有日志
    try:
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
    except:
        logs = []
    
    # 添加新记录
    logs.append(log_entry)
    
    # 保存日志
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    
    print(f"📝 操作已记录: {description}")
    
    # 高风险操作额外提醒
    if risk_level in ["high", "critical"]:
        print(f"⚠️  高风险操作: {description}")

def search_operations(keyword):
    """搜索操作记录"""
    try:
        with open(LOG_FILE, 'r') as f:
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
    log_operation("system", "创建操作记录系统", {"file": LOG_FILE})
    print("✅ 操作记录系统已启动")