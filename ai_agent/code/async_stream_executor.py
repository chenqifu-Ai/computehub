#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步Stream执行器 - 真正的非阻塞Stream
任务队列 + 工作线程 + 结果回调
"""

import threading
import queue
import subprocess
import time
from datetime import datetime

class AsyncStreamExecutor:
    def __init__(self, max_workers=3):
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.workers = []
        self.running = True
        self.max_workers = max_workers
    
    def worker_loop(self, worker_id):
        """工作线程循环"""
        print(f"👷 Worker {worker_id} 启动")
        
        while self.running:
            try:
                # 获取任务（非阻塞，超时1秒）
                task = self.task_queue.get(timeout=1)
                
                if task is None:  # 停止信号
                    break
                
                task_name, command, timeout = task
                print(f"🎯 Worker {worker_id} 执行: {task_name}")
                
                # 执行任务（带超时）
                try:
                    result = subprocess.run(
                        command, 
                        shell=True, 
                        capture_output=True, 
                        text=True, 
                        timeout=timeout
                    )
                    
                    # 将结果放入结果队列
                    self.result_queue.put({
                        "task": task_name,
                        "success": result.returncode == 0,
                        "output": result.stdout,
                        "error": result.stderr,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"✅ Worker {worker_id} 完成: {task_name}")
                    
                except subprocess.TimeoutExpired:
                    self.result_queue.put({
                        "task": task_name,
                        "success": False,
                        "output": "",
                        "error": f"任务超时 ({timeout}秒)",
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"⏰ Worker {worker_id} 超时: {task_name}")
                
                except Exception as e:
                    self.result_queue.put({
                        "task": task_name,
                        "success": False,
                        "output": "",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"💥 Worker {worker_id} 错误: {task_name} - {e}")
                
                finally:
                    self.task_queue.task_done()
                    
            except queue.Empty:
                # 队列为空，继续等待
                continue
        
        print(f"🛑 Worker {worker_id} 停止")
    
    def start_workers(self):
        """启动工作线程"""
        for i in range(self.max_workers):
            worker = threading.Thread(target=self.worker_loop, args=(i+1,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        print(f"🚀 启动 {self.max_workers} 个工作线程")
    
    def submit_task(self, task_name, command, timeout=30):
        """提交任务到队列"""
        self.task_queue.put((task_name, command, timeout))
        print(f"📥 提交任务: {task_name}")
    
    def get_results(self):
        """获取执行结果"""
        results = []
        while not self.result_queue.empty():
            try:
                results.append(self.result_queue.get_nowait())
            except queue.Empty:
                break
        return results
    
    def stop(self):
        """停止执行器"""
        self.running = False
        
        # 发送停止信号给所有工作线程
        for _ in range(self.max_workers):
            self.task_queue.put(None)
        
        # 等待所有任务完成
        self.task_queue.join()
        print("🛑 异步Stream执行器已停止")

# Stream任务定义
STREAM_TASKS = [
    ("股票监控", "cd /root/.openclaw/workspace/ai_agent/code && python3 stock_monitor.py", 30),
    ("金融顾问分析", "cd /root/.openclaw/workspace/ai_agent/code/expert_scripts && python3 financial_advisor_stock_analysis.py", 30),
    ("财务专家分析", "cd /root/.openclaw/workspace/ai_agent/code/expert_scripts && python3 finance_expert_analysis.py", 30),
    ("法律顾问检查", "cd /root/.openclaw/workspace/ai_agent/code/expert_scripts && python3 legal_advisor_risk_check.py", 30),
    ("网络专家检查", "cd /root/.openclaw/workspace/ai_agent/code/expert_scripts && python3 network_expert_system_check.py", 30)
]

def run_async_stream():
    """运行异步Stream演示"""
    executor = AsyncStreamExecutor(max_workers=3)
    executor.start_workers()
    
    print("="*60)
    print("🔄 异步Stream执行器启动")
    print("🎯 特征: 非阻塞、超时控制、结果回调")
    print("⏰ 工作线程: 3个")
    print("="*60)
    
    # 提交所有任务
    for task_name, command, timeout in STREAM_TASKS:
        executor.submit_task(task_name, command, timeout)
    
    # 等待任务执行并收集结果
    time.sleep(5)  # 给任务一些执行时间
    
    # 获取并显示结果
    results = executor.get_results()
    print(f"\n📊 执行结果 ({len(results)} 个任务):")
    
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['task']}: {result['success']}")
        if result["error"]:
            print(f"   错误: {result['error']}")
    
    # 停止执行器
    executor.stop()
    
    print("\n🎉 异步Stream演示完成")

if __name__ == "__main__":
    run_async_stream()