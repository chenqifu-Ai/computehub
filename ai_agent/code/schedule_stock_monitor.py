#!/usr/bin/env python3
"""
股票监控定时任务设置
"""

import subprocess
import os
from pathlib import Path

def setup_cron_jobs():
    """设置定时监控任务"""
    
    # 股票监控脚本路径
    monitor_script = "/root/.openclaw/workspace/ai_agent/code/stock_monitor_000882.py"
    
    # 定时任务配置
    cron_jobs = [
        # 每30分钟监控一次（交易时间）
        "*/30 9-15 * * 1-5 python3 {}".format(monitor_script),
        # 每日开盘前检查（9:00）
        "0 9 * * 1-5 python3 {}".format(monitor_script),
        # 每日收盘后总结（15:30）
        "30 15 * * 1-5 python3 {}".format(monitor_script),
        # 周末检查（周六日10:00）
        "0 10 * * 6,7 python3 {}".format(monitor_script)
    ]
    
    # 添加到crontab
    try:
        # 获取当前crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_cron = result.stdout if result.returncode == 0 else ""
        
        # 移除已有的股票监控任务
        lines = current_cron.split('\n')
        filtered_lines = [line for line in lines if 'stock_monitor_000882' not in line and line.strip()]
        
        # 添加新任务
        new_cron = '\n'.join(filtered_lines + cron_jobs + [''])
        
        # 写入新的crontab
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        process.communicate(new_cron)
        
        print("✅ 股票监控定时任务设置完成")
        print("📅 定时任务安排:")
        for job in cron_jobs:
            print(f"   • {job}")
        
        return True
        
    except Exception as e:
        print(f"❌ 设置定时任务失败: {e}")
        return False

def check_current_cron():
    """检查当前的crontab配置"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📋 当前crontab配置:")
            print(result.stdout)
        else:
            print("ℹ️ 当前没有crontab配置")
    except Exception as e:
        print(f"❌ 检查crontab失败: {e}")

if __name__ == "__main__":
    print("🔄 设置华联股份监控定时任务...")
    check_current_cron()
    setup_cron_jobs()
    print("\n✅ 监控系统配置完成")