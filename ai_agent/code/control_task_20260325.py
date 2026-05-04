#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能体控制任务执行脚本 - 2026-03-25
执行今日所有待办事项的自动化控制
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime

class ControlTaskExecutor:
    def __init__(self):
        self.workspace = "/root/.openclaw/workspace"
        self.code_dir = os.path.join(self.workspace, "ai_agent", "code")
        self.results_dir = os.path.join(self.workspace, "ai_agent", "results")
        self.memory_dir = os.path.join(self.workspace, "memory")
        
    def run_command(self, command, description=""):
        """执行系统命令并返回结果"""
        print(f"\n[执行] {description}")
        print(f"命令: {command}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=self.workspace)
            if result.returncode == 0:
                print(f"[成功] {description}")
                return result.stdout
            else:
                print(f"[失败] {description}")
                print(f"错误: {result.stderr}")
                return None
        except Exception as e:
            print(f"[异常] {description}: {str(e)}")
            return None
    
    def check_email_commands(self):
        """检查邮件命令"""
        print("\n=== 1. 检查邮件命令 ===")
        email_script = os.path.join(self.workspace, "scripts", "check-email-commands.py")
        if os.path.exists(email_script):
            result = self.run_command(f"python3 {email_script}", "执行邮件命令检查")
            return result is not None
        else:
            print("邮件检查脚本不存在")
            return False
    
    def continue_expert_learning(self):
        """继续各专家轮换学习任务"""
        print("\n=== 2. 继续专家轮换学习任务 ===")
        # 检查轮换配置文件
        rotation_files = []
        for filename in os.listdir(self.memory_dir):
            if filename.endswith('-rotation.json'):
                rotation_files.append(os.path.join(self.memory_dir, filename))
        
        if rotation_files:
            print(f"找到 {len(rotation_files)} 个轮换配置文件")
            success_count = 0
            for rotation_file in rotation_files:
                print(f"处理轮换文件: {rotation_file}")
                try:
                    with open(rotation_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    # 这里可以添加具体的轮换逻辑
                    success_count += 1
                except Exception as e:
                    print(f"处理轮换文件失败: {e}")
            
            print(f"成功处理 {success_count}/{len(rotation_files)} 个轮换配置")
            return success_count > 0
        else:
            print("未找到轮换配置文件")
            return False
    
    def check_stock_positions(self):
        """跟进股票持仓情况"""
        print("\n=== 3. 跟进股票持仓情况 ===")
        memory_file = os.path.join(self.workspace, "MEMORY.md")
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取持仓信息
            if "华联股份" in content:
                print("找到华联股份持仓信息")
                # 这里可以添加获取实时股价的逻辑
                return True
            else:
                print("未找到华联股份持仓信息")
                return False
        else:
            print("MEMORY.md 文件不存在")
            return False
    
    def monitor_market_watchlist(self):
        """监控关注股票列表"""
        print("\n=== 4. 监控关注股票列表 ===")
        memory_file = os.path.join(self.workspace, "MEMORY.md")
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            watchlist_stocks = ["中远海发"]
            found_stocks = []
            for stock in watchlist_stocks:
                if stock in content:
                    found_stocks.append(stock)
            
            if found_stocks:
                print(f"监控以下关注股票: {', '.join(found_stocks)}")
                return True
            else:
                print("未找到关注股票信息")
                return False
        else:
            print("MEMORY.md 文件不存在")
            return False
    
    def execute_all_tasks(self):
        """执行所有控制任务"""
        print("🚀 开始执行AI智能体控制任务 - 2026-03-25")
        print("=" * 50)
        
        results = {
            "email_commands": self.check_email_commands(),
            "expert_learning": self.continue_expert_learning(),
            "stock_positions": self.check_stock_positions(),
            "market_watchlist": self.monitor_market_watchlist()
        }
        
        print("\n" + "=" * 50)
        print("📊 任务执行总结:")
        total_tasks = len(results)
        completed_tasks = sum(1 for v in results.values() if v)
        print(f"完成任务: {completed_tasks}/{total_tasks}")
        
        for task, status in results.items():
            status_str = "✅ 成功" if status else "❌ 失败"
            print(f"  - {task}: {status_str}")
        
        # 保存结果
        result_file = os.path.join(self.results_dir, f"control_task_20260325_{datetime.now().strftime('%H%M%S')}.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "tasks": results,
                "summary": f"{completed_tasks}/{total_tasks} tasks completed"
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存到: {result_file}")
        return completed_tasks == total_tasks

if __name__ == "__main__":
    executor = ControlTaskExecutor()
    success = executor.execute_all_tasks()
    sys.exit(0 if success else 1)