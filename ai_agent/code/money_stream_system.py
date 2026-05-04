#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
赚钱Stream系统 - 公司永不停止，钱不白流
24/7自动赚钱，实时监控，故障自愈
"""

import time
import subprocess
import threading
from datetime import datetime

class MoneyStreamSystem:
    def __init__(self):
        self.running = True
        self.streams = {}
    
    def stock_monitor_stream(self):
        """股票监控Stream"""
        while self.running:
            try:
                print(f"💰 [{datetime.now().strftime('%H:%M:%S')}] 股票监控Stream执行...")
                result = subprocess.run([
                    "python3", "/root/.openclaw/workspace/ai_agent/code/stock_monitor.py"
                ], capture_output=True, text=True)
                
                if "无预警" in result.stdout:
                    print("✅ 股票监控正常")
                else:
                    print("🚨 股票监控发现预警")
                
                # 5分钟监控一次
                time.sleep(300)
                
            except Exception as e:
                print(f"❌ 股票监控Stream错误: {e}")
                time.sleep(60)  # 错误后等待1分钟重试
    
    def expert_work_stream(self):
        """专家工作Stream"""
        expert_scripts = [
            "financial_advisor_stock_analysis.py",
            "finance_expert_analysis.py", 
            "legal_advisor_risk_check.py",
            "network_expert_system_check.py",
            "marketing_expert_analysis.py",
            "ceo_advisor_strategy.py",
            "hr_expert_performance.py"
        ]
        
        while self.running:
            try:
                for script in expert_scripts:
                    script_path = f"/root/.openclaw/workspace/ai_agent/code/expert_scripts/{script}"
                    if os.path.exists(script_path):
                        result = subprocess.run(["python3", script_path], capture_output=True, text=True)
                        print(f"👨‍💻 [{datetime.now().strftime('%H:%M:%S')}] {script} 执行完成")
                
                # 30分钟执行一轮专家工作
                time.sleep(1800)
                
            except Exception as e:
                print(f"❌ 专家工作Stream错误: {e}")
                time.sleep(300)  # 错误后等待5分钟重试
    
    def start_all_streams(self):
        """启动所有赚钱Stream"""
        print("🚀 启动赚钱Stream系统...")
        
        # 启动股票监控Stream
        stock_thread = threading.Thread(target=self.stock_monitor_stream)
        stock_thread.daemon = True
        stock_thread.start()
        self.streams["stock"] = stock_thread
        
        # 启动专家工作Stream
        expert_thread = threading.Thread(target=self.expert_work_stream)
        expert_thread.daemon = True
        expert_thread.start()
        self.streams["expert"] = expert_thread
        
        print("✅ 所有赚钱Stream已启动")
        
        # 主线程保持运行
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_all_streams()
    
    def stop_all_streams(self):
        """停止所有Stream"""
        print("🛑 停止赚钱Stream系统...")
        self.running = False

if __name__ == "__main__":
    import os
    
    stream_system = MoneyStreamSystem()
    
    print("="*60)
    print("💰 赚钱Stream系统启动")
    print("="*60)
    print("🎯 目标: 公司永不停止，钱不白流")
    print("⏰ 时间: 24/7自动运行")
    print("👥 专家: 7个专家自动工作")
    print("="*60)
    
    stream_system.start_all_streams()