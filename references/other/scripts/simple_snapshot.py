#!/usr/bin/env python3
"""
简单快照测试脚本
"""

import json
from datetime import datetime
import os

def create_simple_snapshot():
    """创建简单快照"""
    snapshot_dir = "/root/.openclaw/workspace/snapshots"
    os.makedirs(snapshot_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"simple_snapshot_{timestamp}.json"
    filepath = os.path.join(snapshot_dir, filename)
    
    snapshot_data = {
        "timestamp": timestamp,
        "type": "daily_report_snapshot",
        "status": "success",
        "daily_report_sent": True,
        "pulse_report_sent": True,
        "system_health": "good"
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 简单快照创建成功: {filename}")
    return filepath

if __name__ == "__main__":
    create_simple_snapshot()