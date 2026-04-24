#!/usr/bin/env python3
"""
股票监控系统调度器

功能：
- 根据时间表自动执行不同的监控任务
- 整合数据抓取、监控、分析功能
- 支持定时任务

作者：小智
日期：2026-03-25
"""

import os
import sys
import time
import subprocess
from datetime import datetime, time as dt_time

def run_script(script_name):
    """运行指定的Python脚本"""
    script_path = f"/root/.openclaw/workspace/ai_agent/code/{script_name}"
    if os.path.exists(script_path):
        try:
            result = subprocess.run([sys.executable, script_path], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"✅ {script_name} 执行成功")
                return True
            else:
                print(f"❌ {script_name} 执行失败: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"⏰ {script_name} 执行超时")
            return False
        except Exception as e:
            print(f"💥 {script_name} 执行异常: {e}")
            return False
    else:
        print(f"⚠️ 脚本不存在: {script_path}")
        return False

def is_time_in_range(current_time, start_str, end_str):
    """检查当前时间是否在指定范围内"""
    current = dt_time.fromisoformat(current_time)
    start = dt_time.fromisoformat(start_str)
    end = dt_time.fromisoformat(end_str)
    return start <= current <= end

def get_current_time():
    """获取当前时间字符串"""
    return datetime.now().strftime('%H:%M')

def main():
    """主调度函数"""
    current_time = get_current_time()
    print(f"⏰ 股票监控调度器启动 - 当前时间: {current_time}")
    
    # 定义监控时间表
    schedule = {
        'pre_market': {'start': '08:20', 'end': '09:10'},
        'call_auction': '09:15',
        'market_open': '09:30',
        'intraday_morning': {'start': '10:00', 'end': '11:00'},
        'intraday_afternoon': {'start': '14:30', 'end': '15:00'}
    }
    
    tasks_executed = []
    
    # 盘前监控 (08:20-09:10)
    if is_time_in_range(current_time, schedule['pre_market']['start'], schedule['pre_market']['end']):
        print("🌅 执行盘前监控任务...")
        run_script('pre_market_monitor_20260326.py')
        tasks_executed.extend(['盘前综合分析', '盘前预警检查'])
    
    # 集合竞价分析 (09:15)
    elif current_time == schedule['call_auction']:
        print("🎯 执行集合竞价分析...")
        run_script('fetch_realtime_data.py')
        run_script('call_auction.py')
        tasks_executed.extend(['实时数据抓取', '集合竞价分析'])
    
    # 开盘监控 (09:30)
    elif current_time == schedule['market_open']:
        print("🔔 执行开盘监控...")
        run_script('fetch_realtime_data.py')
        run_script('stock_monitor_system.py')
        tasks_executed.extend(['开盘数据抓取', '开盘预警检查'])
    
    # 盘中监控上午 (10:00-11:00)
    elif is_time_in_range(current_time, schedule['intraday_morning']['start'], schedule['intraday_morning']['end']):
        print("📈 执行盘中监控(上午)...")
        run_script('fetch_realtime_data.py')
        run_script('stock_monitor_system.py')
        tasks_executed.extend(['盘中数据抓取', '盘中预警检查'])
    
    # 盘中监控下午 (14:30-15:00)
    elif is_time_in_range(current_time, schedule['intraday_afternoon']['start'], schedule['intraday_afternoon']['end']):
        print("📉 执行盘中监控(下午)...")
        run_script('fetch_realtime_data.py')
        run_script('stock_monitor_system.py')
        tasks_executed.extend(['盘中数据抓取', '盘中预警检查'])
    
    # 非交易时间的手动执行
    else:
        print("🕒 非交易时间，执行完整监控流程...")
        run_script('fetch_realtime_data.py')
        run_script('stock_monitor_system.py')
        run_script('call_auction.py')
        tasks_executed.extend(['实时数据抓取', '预警检查', '集合竞价分析'])
    
    if tasks_executed:
        print(f"✅ 今日已执行任务: {', '.join(tasks_executed)}")
    else:
        print("ℹ️ 无任务需要执行")
    
    print("🏁 股票监控调度器完成")

if __name__ == "__main__":
    main()