#!/usr/bin/env python3
"""
工作流执行器 - 基于task_pipeline的简化版本
"""

import asyncio
import json
from datetime import datetime

class WorkflowExecutor:
    """工作流执行器"""
    
    def __init__(self, name: str):
        self.name = name
        self.tasks = []
        self.results = {}
        
    def add_task(self, task_name: str, task_func, *args, **kwargs):
        """添加任务"""
        self.tasks.append({
            'name': task_name,
            'func': task_func,
            'args': args,
            'kwargs': kwargs
        })
        
    async def execute_sequential(self):
        """顺序执行工作流"""
        print(f"🚀 开始执行工作流: {self.name}")
        
        for i, task in enumerate(self.tasks, 1):
            print(f"\n[{i}/{len(self.tasks)}] 执行任务: {task['name']}")
            
            try:
                # 执行任务
                if asyncio.iscoroutinefunction(task['func']):
                    result = await task['func'](*task['args'], **task['kwargs'])
                else:
                    result = task['func'](*task['args'], **task['kwargs'])
                
                self.results[task['name']] = {
                    'status': 'success',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                }
                print(f"✅ {task['name']}: 完成")
                
            except Exception as e:
                self.results[task['name']] = {
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                print(f"❌ {task['name']}: 失败 - {e}")
        
        print(f"\n🎉 工作流执行完成: {self.name}")
        return self.results
    
    def get_summary(self):
        """获取执行摘要"""
        success_count = sum(1 for r in self.results.values() if r['status'] == 'success')
        failed_count = len(self.results) - success_count
        
        return {
            'workflow_name': self.name,
            'total_tasks': len(self.tasks),
            'success_tasks': success_count,
            'failed_tasks': failed_count,
            'success_rate': success_count / len(self.tasks) * 100 if self.tasks else 0,
            'execution_time': datetime.now().isoformat()
        }

# 示例任务函数
def stock_monitor_task():
    """股票监控任务"""
    print("执行股票监控...")
    return {"status": "监控完成", "stocks": ["000882", "601866"]}

def learning_task():
    """学习任务"""
    print("执行专家学习...")
    return {"status": "学习推进", "experts": ["finance", "ceo"]}

def system_check_task():
    """系统检查任务"""
    print("执行系统检查...")
    return {"status": "系统正常", "checks": ["cpu", "memory", "disk"]}

# 使用示例
async def demo_workflow():
    """演示工作流"""
    
    # 创建工作流
    workflow = WorkflowExecutor("日常监控工作流")
    
    # 添加任务
    workflow.add_task("股票监控", stock_monitor_task)
    workflow.add_task("专家学习", learning_task)
    workflow.add_task("系统检查", system_check_task)
    
    # 执行工作流
    results = await workflow.execute_sequential()
    
    # 输出摘要
    summary = workflow.get_summary()
    print(f"\n📊 工作流摘要: {json.dumps(summary, indent=2, ensure_ascii=False)}")
    
    return results

if __name__ == "__main__":
    print("测试工作流执行器...")
    asyncio.run(demo_workflow())