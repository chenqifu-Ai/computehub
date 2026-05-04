#!/usr/bin/env python3
"""
🔴 CEO定时检查脚本
每10分钟检查码神抓取进度
"""

from pathlib import Path
from datetime import datetime
import json

def check_capture_progress():
    data_file = Path("/root/.openclaw/workspace/skills/network-expert/data/captured_data.json")
    log_file = Path("/root/.openclaw/workspace/skills/network-expert/data/capture_log.md")
    
    print(f"🔍 CEO检查码神抓取进度 - {datetime.now().strftime('%H:%M:%S')}")
    print("="*70)
    
    if data_file.exists():
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        platforms = data.get("平台数", 0)
        entries = data.get("数据条目", 0)
        duration = data.get("实际用时", "未知")
        
        print(f"✅ 码神已抓取数据！")
        print(f"   平台数: {platforms}个")
        print(f"   数据条目: {entries}条")
        print(f"   实际用时: {duration}")
        print(f"   数据文件: {data_file}")
        
        # 评估是否达标
        if platforms >= 5 and entries >= 20:
            print(f"
🎉 码神达标！完成任务！")
            return True
        else:
            print(f"
⚠️ 码神进度不足！继续抓取！")
            return False
    else:
        print(f"❌ 码神未开始抓取！")
        print(f"   数据文件不存在！")
        print(f"
🔴 立即催促码神执行！")
        return False

if __name__ == "__main__":
    check_capture_progress()
