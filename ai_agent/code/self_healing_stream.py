#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自恢复Stream系统 - 自动检测故障，自动重启
确保公司永不停止，钱不白流
"""

import time
import subprocess
import threading
import os
from datetime import datetime

class SelfHealingStream:
    def __init__(self):
        self.streams = {
            "stock_monitor": {
                "script": "stock_monitor.py",
                "interval": 300,  # 5分钟
                "last_run": 0,
                "status": "stopped",
                "max_retries": 3
            },
            "expert_work": {
                "script": "expert_work_orchestrator.py", 
                "interval": 1800,  # 30分钟
                "last_run": 0,
                "status": "stopped",
                "max_retries": 3
            }
        }
        self.running = True
    
    def run_stream(self, stream_name, config):
        """运行单个Stream"""
        script_path = f"/root/.openclaw/workspace/ai_agent/code/{config['script']}"
        
        if not os.path.exists(script_path):
            print(f"❌ {stream_name}: 脚本不存在 {config['script']}")
            return False
        
        try:
            result = subprocess.run(["python3", script_path], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ {stream_name}: 执行成功 - {datetime.now().strftime('%H:%M:%S')}")
                return True
            else:
                print(f"❌ {stream_name}: 执行失败 - {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {stream_name}: 执行超时")
            return False
        except Exception as e:
            print(f"💥 {stream_name}: 异常错误 - {e}")
            return False
    
    def health_check(self):
        """健康检查 - 检测Stream状态"""
        current_time = time.time()
        
        for stream_name, config in self.streams.items():
            # 检查是否超过执行间隔
            if current_time - config["last_run"] > config["interval"]:
                print(f"🔍 {stream_name}: 需要执行，上次运行: {datetime.fromtimestamp(config['last_run']).strftime('%H:%M:%S')}")
                
                # 尝试执行Stream
                success = self.run_stream(stream_name, config)
                
                if success:
                    config["last_run"] = current_time
                    config["status"] = "running"
                    config["retry_count"] = 0  # 重置重试计数
                else:
                    config["retry_count"] = config.get("retry_count", 0) + 1
                    config["status"] = "failed"
                    
                    # 超过重试次数，标记为严重故障
                    if config["retry_count"] >= config["max_retries"]:
                        config["status"] = "critical"
                        print(f"🚨 {stream_name}: 严重故障，需要人工干预")
    
    def start_monitoring(self):
        """启动监控循环"""
        print("🚀 启动自恢复Stream监控系统...")
        print("🎯 目标: 自动检测故障，自动重启")
        print("⏰ 监控间隔: 每30秒")
        print("="*60)
        
        # 初始执行所有Stream
        for stream_name, config in self.streams.items():
            self.run_stream(stream_name, config)
            config["last_run"] = time.time()
        
        # 监控循环
        while self.running:
            try:
                self.health_check()
                time.sleep(30)  # 每30秒检查一次
                
            except KeyboardInterrupt:
                print("\n🛑 收到停止信号")
                break
            except Exception as e:
                print(f"💥 监控循环异常: {e}")
                time.sleep(60)  # 异常后等待1分钟
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        print("🛑 自恢复Stream监控已停止")

# 创建专家工作编排器（简化版）
def create_expert_orchestrator():
    """创建专家工作编排器"""
    orchestrator_content = """#!/usr/bin/env python3
import subprocess
import os
from datetime import datetime

scripts = [
    "financial_advisor_stock_analysis.py",
    "finance_expert_analysis.py",
    "legal_advisor_risk_check.py", 
    "network_expert_system_check.py"
]

print(f"👨‍💼 专家工作编排器启动 - {datetime.now().strftime('%H:%M:%S')}")

for script in scripts:
    script_path = f"/root/.openclaw/workspace/ai_agent/code/expert_scripts/{script}"
    if os.path.exists(script_path):
        result = subprocess.run(["python3", script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {script}: 执行成功")
        else:
            print(f"❌ {script}: 执行失败")

print("🎯 专家工作编排完成")
"""
    
    with open("/root/.openclaw/workspace/ai_agent/code/expert_work_orchestrator.py", "w") as f:
        f.write(orchestrator_content)

if __name__ == "__main__":
    # 创建专家编排器
    create_expert_orchestrator()
    
    # 启动自恢复Stream
    stream_system = SelfHealingStream()
    
    try:
        stream_system.start_monitoring()
    except Exception as e:
        print(f"💥 系统启动失败: {e}")
    finally:
        stream_system.stop_monitoring()