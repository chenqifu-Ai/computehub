#!/usr/bin/env python3
"""
任务流水线框架 - 核心引擎
实现数据流驱动的任务执行管道
"""

import asyncio
import json
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running" 
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    priority: int = 1  # 1-5, 5最高
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = None
    started_at: float = None
    completed_at: float = None
    result: Any = None
    error: str = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.metadata is None:
            self.metadata = {}

class PipelineStage:
    """流水线阶段基类"""
    
    def __init__(self, name: str, processor: Callable):
        self.name = name
        self.processor = processor
        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        
    async def process(self, task: Task) -> Task:
        """处理单个任务"""
        try:
            task.started_at = time.time()
            task.status = TaskStatus.RUNNING
            
            # 调用处理器函数
            result = await self.processor(task)
            task.result = result
            task.status = TaskStatus.SUCCESS
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            
        finally:
            task.completed_at = time.time()
            
        return task

class TaskPipeline:
    """任务流水线主类"""
    
    def __init__(self, name: str, max_workers: int = 5):
        self.name = name
        self.max_workers = max_workers
        self.stages: List[PipelineStage] = []
        self.tasks: Dict[str, Task] = {}
        self.is_running = False
        
    def add_stage(self, stage: PipelineStage):
        """添加处理阶段"""
        self.stages.append(stage)
        
    async def submit_task(self, task: Task):
        """提交任务到流水线"""
        self.tasks[task.id] = task
        
        if self.stages:
            await self.stages[0].input_queue.put(task)
        
    async def start(self):
        """启动流水线"""
        self.is_running = True
        
        # 为每个阶段创建工作协程
        workers = []
        for stage in self.stages:
            for i in range(self.max_workers):
                worker = asyncio.create_task(self._stage_worker(stage, i))
                workers.append(worker)
        
        # 等待所有工作协程完成
        await asyncio.gather(*workers)
        
    async def _stage_worker(self, stage: PipelineStage, worker_id: int):
        """阶段工作协程"""
        print(f"启动工作协程: {stage.name}-{worker_id}")
        
        while self.is_running:
            try:
                # 从输入队列获取任务
                task = await asyncio.wait_for(
                    stage.input_queue.get(), 
                    timeout=1.0
                )
                
                # 处理任务
                processed_task = await stage.process(task)
                
                # 如果有下一阶段，传递任务
                next_stage_index = self.stages.index(stage) + 1
                if next_stage_index < len(self.stages):
                    next_stage = self.stages[next_stage_index]
                    await next_stage.input_queue.put(processed_task)
                else:
                    # 最终阶段，任务完成
                    print(f"任务完成: {processed_task.name} - {processed_task.status}")
                    
            except asyncio.TimeoutError:
                # 队列超时，继续等待
                continue
            except Exception as e:
                print(f"工作协程错误: {e}")
                
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def get_pipeline_stats(self) -> Dict:
        """获取流水线统计信息"""
        stats = {
            "total_tasks": len(self.tasks),
            "stages_count": len(self.stages),
            "workers_count": self.max_workers * len(self.stages),
            "tasks_by_status": {}
        }
        
        for status in TaskStatus:
            stats["tasks_by_status"][status.value] = len([
                t for t in self.tasks.values() if t.status == status
            ])
            
        return stats

# 示例处理器函数
async def stock_data_collector(task: Task) -> Dict:
    """股票数据收集器"""
    print(f"收集股票数据: {task.name}")
    await asyncio.sleep(0.5)  # 模拟数据处理
    return {"price": 1.70, "change": -0.08, "volume": 1000000}

async def risk_analyzer(task: Task) -> Dict:
    """风险分析器"""
    print(f"分析风险: {task.name}")
    await asyncio.sleep(0.3)
    
    data = task.result
    risk_level = "低风险" if abs(data["change"]) < 0.05 else "中风险" if abs(data["change"]) < 0.1 else "高风险"
    
    return {
        "risk_level": risk_level,
        "suggestion": "持有" if data["change"] > -0.05 else "观察" if data["change"] > -0.1 else "考虑止损"
    }

async def decision_maker(task: Task) -> str:
    """决策生成器"""
    print(f"生成决策: {task.name}")
    await asyncio.sleep(0.2)
    
    analysis = task.result
    return f"决策: {analysis['suggestion']} (风险等级: {analysis['risk_level']})"

# 使用示例
async def demo_pipeline():
    """演示流水线运行"""
    
    # 创建流水线
    pipeline = TaskPipeline("股票监控流水线", max_workers=3)
    
    # 添加处理阶段
    pipeline.add_stage(PipelineStage("数据收集", stock_data_collector))
    pipeline.add_stage(PipelineStage("风险分析", risk_analyzer))
    pipeline.add_stage(PipelineStage("决策生成", decision_maker))
    
    # 创建示例任务
    tasks = [
        Task("task_001", "华联股份监控", priority=5),
        Task("task_002", "中远海发监控", priority=4),
        Task("task_003", "市场整体分析", priority=3)
    ]
    
    # 启动流水线
    pipeline_task = asyncio.create_task(pipeline.start())
    
    # 提交任务
    for task in tasks:
        await pipeline.submit_task(task)
    
    # 等待一段时间让任务处理
    await asyncio.sleep(3)
    
    # 停止流水线
    pipeline.is_running = False
    await pipeline_task
    
    # 输出统计信息
    stats = pipeline.get_pipeline_stats()
    print(f"\n流水线统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    print("🚀 启动任务流水线演示...")
    asyncio.run(demo_pipeline())