#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stream守护进程 - 真正的后台Stream
简单、有效、不阻塞
"""

import time
import subprocess
import sys
from datetime import datetime

def log(message):
    """简单的日志函数"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

def run_task(task_name, command, timeout=30):
    """运行单个任务"""
    try:
        log(f"🎯 开始: {task_name}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0:
            log(f"✅ 完成: {task_name}")
            return True
        else:
            log(f"❌ 失败: {task_name} - {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        log(f"⏰ 超时: {task_name}")
        return False
    except Exception as e:
        log(f"💥 异常: {task_name} - {e}")
        return False

def stream_daemon():
    """Stream守护进程主循环"""
    log("🚀 Stream守护进程启动")
    log("🎯 目标: 公司永不停止，钱不白流")
    log("⏰ 运行模式: 24/7后台运行")
    
    # 任务配置
    tasks = [
        ("股票监控", "cd /root/.openclaw/workspace/ai_agent/code && python3 stock_monitor.py", 300),  # 5分钟
        ("专家工作", "cd /root/.openclaw/workspace/ai_agent/code/expert_scripts && python3 financial_advisor_stock_analysis.py", 1800),  # 30分钟
    ]
    
    last_run = {}
    
    while True:
        current_time = time.time()
        
        for task_name, command, interval in tasks:
            # 检查是否需要执行
            if task_name not in last_run or current_time - last_run[task_name] >= interval:
                # 异步执行（不等待）
                import threading
                thread = threading.Thread(target=run_task, args=(task_name, command, 30))
                thread.daemon = True
                thread.start()
                
                last_run[task_name] = current_time
        
        # 简单的状态报告（每10分钟）
        if int(current_time) % 600 == 0:  # 每10分钟
            log("📊 Stream运行正常")
        
        time.sleep(10)  # 每10秒检查一次

if __name__ == "__main__":
    try:
        stream_daemon()
    except KeyboardInterrupt:
        log("🛑 Stream守护进程停止")
    except Exception as e:
        log(f"💥 Stream守护进程异常: {e}")
        # 异常后自动重启（简单的自愈）
        time.sleep(60)
        log("🔄 Stream守护进程重启")
        stream_daemon()