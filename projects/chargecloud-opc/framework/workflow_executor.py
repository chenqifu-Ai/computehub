#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChargeCloud OPC - 工作流执行器
Workflow Executor - 管理多智能体协作和工作流执行

创建时间：2026-04-19
作者：小智 (数据智能体)
版本：v1.0
"""

import os
import json
import yaml
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入 AI 智能体框架
from ai_agent import AIAgent, TaskPriority, Task

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str
    name: str
    agent_id: str  # 负责的智能体
    task: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowExecutor:
    """
    工作流执行器
    负责调度和执行多智能体协作的工作流
    """
    
    def __init__(self, agents_dir: str = None):
        """
        初始化工作流执行器
        
        Args:
            agents_dir: 智能体配置目录
        """
        self.agents_dir = agents_dir or "/root/.openclaw/workspace/projects/chargecloud-opc/agents"
        
        # 智能体实例缓存
        self.agents: Dict[str, AIAgent] = {}
        
        # 工作流队列
        self.workflow_queue: List[Workflow] = []
        self.current_workflow: Optional[Workflow] = None
        
        # 执行线程池
        self.executor = ThreadPoolExecutor(max_workers=6)  # 6 个智能体
        
        # 工作流历史
        self.workflow_history: List[Workflow] = []
        
        logger.info("工作流执行器已初始化")
    
    def load_agent(self, agent_id: str) -> AIAgent:
        """
        加载智能体
        
        Args:
            agent_id: 智能体 ID
        
        Returns:
            AIAgent: 智能体实例
        """
        if agent_id in self.agents:
            return self.agents[agent_id]
        
        # 查找配置文件
        config_path = os.path.join(self.agents_dir, f"{agent_id}/config.yaml")
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"智能体配置不存在：{config_path}")
        
        # 创建智能体实例
        agent = AIAgent(config_path)
        self.agents[agent_id] = agent
        
        logger.info(f"智能体已加载：{agent_id}")
        return agent
    
    def load_all_agents(self):
        """加载所有智能体"""
        agent_ids = [
            "ceo_agent",
            "marketing_agent",
            "operations_agent",
            "finance_agent",
            "data_agent",
            "risk_agent"
        ]
        
        logger.info(f"开始加载 {len(agent_ids)} 个智能体...")
        
        for agent_id in agent_ids:
            try:
                self.load_agent(agent_id)
                logger.info(f"✅ {agent_id}")
            except Exception as e:
                logger.error(f"❌ {agent_id} 失败：{e}")
        
        logger.info(f"智能体加载完成：{len(self.agents)}/{len(agent_ids)}")
    
    def create_workflow(self, name: str, description: str, steps: List[Dict]) -> Workflow:
        """
        创建工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述
            steps: 步骤列表
        
        Returns:
            Workflow: 工作流对象
        """
        workflow_steps = []
        
        for i, step_data in enumerate(steps):
            step = WorkflowStep(
                id=f"step_{i+1}",
                name=step_data.get('name', f'Step {i+1}'),
                agent_id=step_data.get('agent_id'),
                task=step_data.get('task'),
                dependencies=step_data.get('dependencies', [])
            )
            workflow_steps.append(step)
        
        workflow = Workflow(
            id=f"workflow_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            description=description,
            steps=workflow_steps
        )
        
        self.workflow_queue.append(workflow)
        logger.info(f"工作流已创建：{workflow.id} - {workflow.name}")
        
        return workflow
    
    def execute_workflow(self, workflow: Workflow) -> Workflow:
        """
        执行工作流
        
        Args:
            workflow: 工作流对象
        
        Returns:
            Workflow: 执行后的工作流
        """
        logger.info(f"开始执行工作流：{workflow.id}")
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        self.current_workflow = workflow
        
        # 构建步骤依赖图
        step_map = {step.id: step for step in workflow.steps}
        completed_steps = set()
        
        try:
            # 并行执行无依赖的步骤
            while len(completed_steps) < len(workflow.steps):
                # 找出可以执行的步骤
                ready_steps = []
                for step in workflow.steps:
                    if step.id in completed_steps:
                        continue
                    
                    # 检查依赖是否都已完成
                    deps_satisfied = all(
                        dep in completed_steps for dep in step.dependencies
                    )
                    
                    if deps_satisfied:
                        ready_steps.append(step)
                
                if not ready_steps:
                    # 死锁检测
                    remaining = [s for s in workflow.steps if s.id not in completed_steps]
                    raise Exception(f"工作流死锁：{len(remaining)} 个步骤无法执行")
                
                # 并行执行就绪步骤
                futures = {}
                for step in ready_steps:
                    future = self.executor.submit(self._execute_step, step)
                    futures[future] = step
                
                # 等待所有步骤完成
                for future in as_completed(futures):
                    step = futures[future]
                    try:
                        result = future.result()
                        step.status = "completed"
                        step.result = result
                        step.completed_at = datetime.now()
                        completed_steps.add(step.id)
                        logger.info(f"步骤完成：{step.id} - {step.name}")
                    except Exception as e:
                        step.status = "failed"
                        step.error = str(e)
                        step.completed_at = datetime.now()
                        logger.error(f"步骤失败：{step.id} - {e}")
                        
                        # 如果是关键步骤失败，可以选择终止工作流
                        if step.id.startswith("step_1"):  # 第一步失败
                            raise Exception(f"关键步骤失败：{step.name} - {e}")
            
            # 所有步骤完成
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            logger.info(f"工作流完成：{workflow.id}")
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now()
            logger.error(f"工作流失败：{workflow.id} - {e}")
        
        # 移动到历史
        self.workflow_history.append(workflow)
        if workflow in self.workflow_queue:
            self.workflow_queue.remove(workflow)
        
        self.current_workflow = None
        return workflow
    
    def _execute_step(self, step: WorkflowStep) -> Any:
        """
        执行单个工作流步骤
        
        Args:
            step: 工作流步骤
        
        Returns:
            Any: 执行结果
        """
        logger.info(f"执行步骤：{step.id} - {step.name}")
        
        step.started_at = datetime.now()
        step.status = "running"
        
        # 加载智能体
        agent = self.load_agent(step.agent_id)
        
        # 执行任务
        task = agent.run(step.task, priority=TaskPriority.HIGH)
        
        if task.status == "completed":
            return task.result
        else:
            raise Exception(task.error or "任务执行失败")
    
    def execute_daily_operations(self) -> Workflow:
        """
        执行日常运营工作流
        
        Returns:
            Workflow: 执行的工作流
        """
        logger.info("执行日常运营工作流...")
        
        # 定义日常运营步骤
        steps = [
            {
                "name": "数据采集",
                "agent_id": "data_agent",
                "task": "采集夜间数据并生成数据报告",
                "dependencies": []
            },
            {
                "name": "营销日报",
                "agent_id": "marketing_agent",
                "task": "生成营销日报（新增用户、ROI、活动效果）",
                "dependencies": ["step_1"]
            },
            {
                "name": "运营日报",
                "agent_id": "operations_agent",
                "task": "生成运营日报（设备状态、订单处理、客户满意度）",
                "dependencies": ["step_1"]
            },
            {
                "name": "财务日报",
                "agent_id": "finance_agent",
                "task": "生成财务日报（收支明细、现金流）",
                "dependencies": ["step_1"]
            },
            {
                "name": "风控检查",
                "agent_id": "risk_agent",
                "task": "执行午间合规检查",
                "dependencies": ["step_1"]
            },
            {
                "name": "CEO 审阅",
                "agent_id": "ceo_agent",
                "task": "审阅各部门日报并发出当日指令",
                "dependencies": ["step_2", "step_3", "step_4", "step_5"]
            }
        ]
        
        workflow = self.create_workflow(
            name="日常运营",
            description="每日例行运营工作流",
            steps=steps
        )
        
        return self.execute_workflow(workflow)
    
    def execute_decision_workflow(self, issue: str) -> Workflow:
        """
        执行重大决策工作流
        
        Args:
            issue: 决策议题
        
        Returns:
            Workflow: 执行的工作流
        """
        logger.info(f"执行重大决策工作流：{issue}")
        
        # 定义决策步骤
        steps = [
            {
                "name": "问题识别",
                "agent_id": "data_agent",
                "task": f"分析识别问题：{issue}",
                "dependencies": []
            },
            {
                "name": "分析评估",
                "agent_id": "ceo_agent",
                "task": f"组织相关部门分析问题：{issue}",
                "dependencies": ["step_1"]
            },
            {
                "name": "方案制定",
                "agent_id": "ceo_agent",
                "task": f"制定解决方案（2-3 个备选）：{issue}",
                "dependencies": ["step_2"]
            },
            {
                "name": "风险评估",
                "agent_id": "risk_agent",
                "task": f"评估方案风险：{issue}",
                "dependencies": ["step_3"]
            },
            {
                "name": "财务测算",
                "agent_id": "finance_agent",
                "task": f"测算投入产出比：{issue}",
                "dependencies": ["step_3"]
            },
            {
                "name": "CEO 决策",
                "agent_id": "ceo_agent",
                "task": f"综合评估并做出决策：{issue}",
                "dependencies": ["step_4", "step_5"]
            },
            {
                "name": "执行监控",
                "agent_id": "operations_agent",
                "task": f"执行决策并监控进度：{issue}",
                "dependencies": ["step_6"]
            },
            {
                "name": "效果评估",
                "agent_id": "data_agent",
                "task": f"评估执行效果：{issue}",
                "dependencies": ["step_7"]
            }
        ]
        
        workflow = self.create_workflow(
            name="重大决策",
            description=f"重大决策工作流：{issue}",
            steps=steps
        )
        
        return self.execute_workflow(workflow)
    
    def get_status(self) -> Dict:
        """获取执行器状态"""
        return {
            "agents_loaded": len(self.agents),
            "workflow_queue_size": len(self.workflow_queue),
            "workflow_history_size": len(self.workflow_history),
            "current_workflow": self.current_workflow.name if self.current_workflow else None,
            "executor_status": "running"
        }


def main():
    """测试主函数"""
    print("=" * 60)
    print("ChargeCloud OPC - 工作流执行器")
    print("=" * 60)
    
    # 创建执行器
    executor = WorkflowExecutor()
    
    print("\n加载所有智能体...")
    executor.load_all_agents()
    
    print("\n执行器状态:")
    print(json.dumps(executor.get_status(), indent=2, ensure_ascii=False))
    
    print("\n测试日常运营工作流...")
    # workflow = executor.execute_daily_operations()
    # print(f"工作流状态：{workflow.status}")
    
    print("\n✅ 工作流执行器就绪!")


if __name__ == '__main__':
    main()
