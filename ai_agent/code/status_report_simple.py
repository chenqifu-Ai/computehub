#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版状态报告生成脚本
"""

import os
import json
from datetime import datetime

def main():
    # 基本系统信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # OpenClaw状态（简化）
    try:
        openclaw_version = os.popen("openclaw --version 2>/dev/null || echo 'Unknown'").read().strip()
    except:
        openclaw_version = "Unknown"
    
    # 系统负载（简化）
    try:
        uptime = os.popen("uptime 2>/dev/null | head -1").read().strip()
    except:
        uptime = "Unknown"
    
    # 当前任务状态
    tasks = [
        "心跳检查任务 - 每次heartbeat执行",
        "小爱老师学习任务 - 执行中", 
        "各专家轮换学习 - 执行中"
    ]
    
    # 股票持仓摘要
    stock_info = "华联股份(000882): 22,600股 @ ¥1.779, 当前价 ¥1.70 (-4.44%)"
    
    report = {
        "timestamp": timestamp,
        "openclaw_version": openclaw_version,
        "system_uptime": uptime,
        "current_tasks": tasks,
        "stock_position": stock_info
    }
    
    # 保存结果
    result_file = "/root/.openclaw/workspace/ai_agent/results/status_report.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("状态报告生成完成!")
    print(f"时间: {timestamp}")

if __name__ == "__main__":
    main()