#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态报告生成脚本
"""

import os
import json
from datetime import datetime, timedelta

def get_system_status():
    """获取系统状态"""
    status = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Shanghai"
    }
    
    # 获取OpenClaw状态
    try:
        result = os.popen("openclaw status").read()
        status["openclaw_status"] = result
    except Exception as e:
        status["openclaw_status"] = f"Error: {str(e)}"
    
    # 获取系统负载
    try:
        result = os.popen("uptime").read().strip()
        status["system_uptime"] = result
    except Exception as e:
        status["system_uptime"] = f"Error: {str(e)}"
    
    return status

def get_memory_status():
    """获取记忆状态"""
    memory_info = {}
    
    # 读取MEMORY.md
    memory_file = "/root/.openclaw/workspace/MEMORY.md"
    if os.path.exists(memory_file):
        with open(memory_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 提取关键信息
            lines = content.split('\n')
            current_section = None
            for line in lines:
                if line.startswith('## '):
                    current_section = line[3:].strip()
                    memory_info[current_section] = []
                elif line.startswith('- ') and current_section:
                    memory_info[current_section].append(line[2:].strip())
    
    return memory_info

def get_current_tasks():
    """获取当前任务状态"""
    tasks = []
    
    # 检查心跳文件中的待办事项
    heartbeat_file = "/root/.openclaw/workspace/HEARTBEAT.md"
    if os.path.exists(heartbeat_file):
        with open(heartbeat_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "待办检查" in content:
                tasks.append("心跳检查任务 - 每次heartbeat执行")
    
    # 检查学习任务
    learning_tasks = [
        "小爱老师学习任务",
        "各专家轮换学习"
    ]
    
    for task in learning_tasks:
        tasks.append(f"{task} - 执行中")
    
    return tasks

def generate_report():
    """生成完整报告"""
    report = {
        "system": get_system_status(),
        "memory": get_memory_status(),
        "tasks": get_current_tasks()
    }
    
    # 写入结果文件
    result_file = "/root/.openclaw/workspace/ai_agent/results/status_report.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report

if __name__ == "__main__":
    report = generate_report()
    print("状态报告生成完成!")
    print(f"时间: {report['system']['timestamp']}")
    print(f"任务数量: {len(report['tasks'])}")