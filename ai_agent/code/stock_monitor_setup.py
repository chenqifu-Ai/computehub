#!/usr/bin/env python3
"""
使用OpenClaw内置定时任务设置股票监控
"""

import json
import os
from pathlib import Path

def create_openclaw_schedule():
    """创建OpenClaw定时任务配置"""
    
    schedule_config = {
        "version": "1.0",
        "schedules": [
            {
                "name": "华联股份每30分钟监控",
                "description": "交易时间段每30分钟检查华联股份股价",
                "cron": "*/30 9-15 * * 1-5",
                "command": "python3 /root/.openclaw/workspace/ai_agent/code/stock_monitor_000882.py",
                "enabled": True,
                "channel": "cron-event"
            },
            {
                "name": "华联股份开盘检查",
                "description": "每日开盘前检查持仓情况",
                "cron": "0 9 * * 1-5",
                "command": "python3 /root/.openclaw/workspace/ai_agent/code/stock_monitor_000882.py",
                "enabled": True,
                "channel": "cron-event"
            },
            {
                "name": "华联股份收盘总结",
                "description": "每日收盘后生成持仓报告",
                "cron": "30 15 * * 1-5",
                "command": "python3 /root/.openclaw/workspace/ai_agent/code/stock_monitor_000882.py",
                "enabled": True,
                "channel": "cron-event"
            },
            {
                "name": "华联股份周末检查",
                "description": "周末检查持仓状态",
                "cron": "0 10 * * 6,7",
                "command": "python3 /root/.openclaw/workspace/ai_agent/code/stock_monitor_000882.py",
                "enabled": True,
                "channel": "cron-event"
            }
        ]
    }
    
    # 保存配置
    config_file = Path("/root/.openclaw/workspace/config/stock_monitor_schedule.json")
    config_file.parent.mkdir(exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(schedule_config, f, ensure_ascii=False, indent=2)
    
    print("✅ OpenClaw股票监控定时任务配置已保存")
    print(f"📁 配置文件: {config_file}")
    
    return config_file

def create_manual_schedule_script():
    """创建手动执行监控的脚本"""
    
    script_content = '''#!/bin/bash
# 华联股份监控手动执行脚本

echo "📊 执行华联股份持仓监控..."
cd /root/.openclaw/workspace
python3 ai_agent/code/stock_monitor_000882.py

echo ""
echo "✅ 监控完成"
'''
    
    script_file = Path("/root/.openclaw/workspace/scripts/stock_monitor.sh")
    script_file.parent.mkdir(exist_ok=True)
    
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # 设置执行权限
    os.chmod(script_file, 0o755)
    
    print(f"✅ 手动监控脚本已创建: {script_file}")
    print(f"💡 使用方法: {script_file}")

if __name__ == "__main__":
    print("🔄 创建华联股份监控系统...")
    
    # 创建定时任务配置
    config_file = create_openclaw_schedule()
    
    # 创建手动执行脚本
    create_manual_schedule_script()
    
    print("\n📋 监控计划安排:")
    print("   • 每30分钟监控一次 (交易时间 9:00-15:00)")
    print("   • 每日开盘检查 (9:00)")
    print("   • 每日收盘总结 (15:30)")
    print("   • 周末检查 (10:00)")
    print("\n✅ 华联股份监控系统配置完成")