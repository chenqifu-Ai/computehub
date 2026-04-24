#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChargeCloud OPC - 任务调度器
Task Scheduler - 管理定时任务和自动化调度

创建时间：2026-04-19
作者：小智 (数据智能体)
版本：v1.0
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import schedule

# 导入工作流执行器
from workflow_executor import WorkflowExecutor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    REALTIME = "realtime"
    ONE_TIME = "one_time"


@dataclass
class ScheduledTask:
    """定时任务定义"""
    id: str
    name: str
    task_type: TaskType
    schedule_time: str  # 时间表达式 (如 "09:00", "Monday 10:00")
    agent_id: str
    task_description: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    fail_count: int = 0


class TaskScheduler:
    """
    任务调度器
    负责管理和调度所有定时任务
    """
    
    def __init__(self, executor: WorkflowExecutor = None):
        """
        初始化任务调度器
        
        Args:
            executor: 工作流执行器实例
        """
        self.executor = executor or WorkflowExecutor()
        
        # 任务列表
        self.tasks: List[ScheduledTask] = []
        
        # 调度器状态
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
        # 任务历史
        self.task_history: List[Dict] = []
        
        logger.info("任务调度器已初始化")
    
    def load_daily_tasks(self):
        """加载每日定时任务"""
        logger.info("加载每日定时任务...")
        
        daily_tasks = [
            # 06:00 - 数据采集
            ScheduledTask(
                id="daily_0600_data_collection",
                name="数据采集",
                task_type=TaskType.DAILY,
                schedule_time="06:00",
                agent_id="data_agent",
                task_description="采集夜间数据并生成数据报告"
            ),
            
            # 07:00 - 部门日报
            ScheduledTask(
                id="daily_0700_department_reports",
                name="部门日报",
                task_type=TaskType.DAILY,
                schedule_time="07:00",
                agent_id="marketing_agent",  # 多个智能体，分别创建
                task_description="生成部门日报（营销/运营/财务/风控）"
            ),
            
            # 08:00 - 数据汇总
            ScheduledTask(
                id="daily_0800_data_summary",
                name="数据汇总",
                task_type=TaskType.DAILY,
                schedule_time="08:00",
                agent_id="data_agent",
                task_description="汇总各部门数据生成公司日报"
            ),
            
            # 09:00 - CEO 审阅
            ScheduledTask(
                id="daily_0900_ceo_review",
                name="CEO 审阅",
                task_type=TaskType.DAILY,
                schedule_time="09:00",
                agent_id="ceo_agent",
                task_description="审阅日报并发出当日工作指令"
            ),
            
            # 12:00 - 合规检查
            ScheduledTask(
                id="daily_1200_compliance_check",
                name="合规检查",
                task_type=TaskType.DAILY,
                schedule_time="12:00",
                agent_id="risk_agent",
                task_description="午间合规检查（数据/合同/安全）"
            ),
            
            # 18:00 - 部门晚报
            ScheduledTask(
                id="daily_1800_evening_reports",
                name="部门晚报",
                task_type=TaskType.DAILY,
                schedule_time="18:00",
                agent_id="operations_agent",
                task_description="生成部门晚报"
            ),
            
            # 20:00 - 经营日报
            ScheduledTask(
                id="daily_2000_daily_summary",
                name="经营日报",
                task_type=TaskType.DAILY,
                schedule_time="20:00",
                agent_id="ceo_agent",
                task_description="生成经营日报并发送管理层"
            ),
            
            # 22:00 - 数据备份
            ScheduledTask(
                id="daily_2200_data_backup",
                name="数据备份",
                task_type=TaskType.DAILY,
                schedule_time="22:00",
                agent_id="data_agent",
                task_description="数据备份和归档"
            ),
        ]
        
        self.tasks.extend(daily_tasks)
        logger.info(f"已加载 {len(daily_tasks)} 个每日任务")
    
    def load_weekly_tasks(self):
        """加载每周定时任务"""
        logger.info("加载每周定时任务...")
        
        weekly_tasks = [
            # 周一 09:00 - 周计划
            ScheduledTask(
                id="weekly_monday_0900_plan",
                name="周计划",
                task_type=TaskType.WEEKLY,
                schedule_time="Monday 09:00",
                agent_id="ceo_agent",
                task_description="制定本周工作重点和计划"
            ),
            
            # 周一 10:00 - 周战略会议
            ScheduledTask(
                id="weekly_monday_1000_strategy",
                name="周战略会议",
                task_type=TaskType.WEEKLY,
                schedule_time="Monday 10:00",
                agent_id="ceo_agent",
                task_description="周战略会议"
            ),
            
            # 周五 14:00 - 周复盘
            ScheduledTask(
                id="weekly_friday_1400_review",
                name="周复盘",
                task_type=TaskType.WEEKLY,
                schedule_time="Friday 14:00",
                agent_id="ceo_agent",
                task_description="本周工作总结和复盘"
            ),
            
            # 周五 16:00 - 财务汇总
            ScheduledTask(
                id="weekly_friday_1600_financial",
                name="财务汇总",
                task_type=TaskType.WEEKLY,
                schedule_time="Friday 16:00",
                agent_id="finance_agent",
                task_description="本周财务汇总"
            ),
        ]
        
        self.tasks.extend(weekly_tasks)
        logger.info(f"已加载 {len(weekly_tasks)} 个每周任务")
    
    def load_monthly_tasks(self):
        """加载每月定时任务"""
        logger.info("加载每月定时任务...")
        
        monthly_tasks = [
            # 1 日 10:00 - 月度战略
            ScheduledTask(
                id="monthly_1st_1000_strategy",
                name="月度战略",
                task_type=TaskType.MONTHLY,
                schedule_time="1st 10:00",
                agent_id="ceo_agent",
                task_description="月度战略规划会议"
            ),
            
            # 1 日 14:00 - 财务报表
            ScheduledTask(
                id="monthly_1st_1400_financial_report",
                name="财务报表",
                task_type=TaskType.MONTHLY,
                schedule_time="1st 14:00",
                agent_id="finance_agent",
                task_description="生成上月财务报表"
            ),
            
            # 5 日 10:00 - 预算差异分析
            ScheduledTask(
                id="monthly_5th_1000_budget_variance",
                name="预算差异分析",
                task_type=TaskType.MONTHLY,
                schedule_time="5th 10:00",
                agent_id="finance_agent",
                task_description="预算执行差异分析"
            ),
            
            # 25 日 10:00 - 月度经营分析
            ScheduledTask(
                id="monthly_25th_1000_analysis",
                name="月度经营分析",
                task_type=TaskType.MONTHLY,
                schedule_time="25th 10:00",
                agent_id="ceo_agent",
                task_description="月度经营分析"
            ),
        ]
        
        self.tasks.extend(monthly_tasks)
        logger.info(f"已加载 {len(monthly_tasks)} 个每月任务")
    
    def load_realtime_tasks(self):
        """加载实时任务"""
        logger.info("加载实时任务...")
        
        realtime_tasks = [
            # 设备监控 (每 5 分钟)
            ScheduledTask(
                id="realtime_equipment_monitor",
                name="设备监控",
                task_type=TaskType.REALTIME,
                schedule_time="*/5 * * * *",  # cron 表达式
                agent_id="operations_agent",
                task_description="设备状态实时监控"
            ),
            
            # 风险扫描 (实时)
            ScheduledTask(
                id="realtime_risk_scan",
                name="风险扫描",
                task_type=TaskType.REALTIME,
                schedule_time="*/1 * * * *",
                agent_id="risk_agent",
                task_description="实时风险扫描"
            ),
        ]
        
        self.tasks.extend(realtime_tasks)
        logger.info(f"已加载 {len(realtime_tasks)} 个实时任务")
    
    def load_all_tasks(self):
        """加载所有任务"""
        logger.info("加载所有定时任务...")
        
        self.load_daily_tasks()
        self.load_weekly_tasks()
        self.load_monthly_tasks()
        self.load_realtime_tasks()
        
        logger.info(f"总共加载 {len(self.tasks)} 个任务")
    
    def schedule_task(self, task: ScheduledTask):
        """
        调度单个任务
        
        Args:
            task: 定时任务
        """
        logger.info(f"调度任务：{task.name} ({task.schedule_time})")
        
        if task.task_type == TaskType.DAILY:
            schedule.every().day.at(task.schedule_time).do(
                self._execute_task, task
            )
        elif task.task_type == TaskType.WEEKLY:
            # 解析周几和时间
            parts = task.schedule_time.split()
            day = parts[0]
            time_str = parts[1] if len(parts) > 1 else "00:00"
            
            if day == "Monday":
                schedule.every().monday.at(time_str).do(self._execute_task, task)
            elif day == "Tuesday":
                schedule.every().tuesday.at(time_str).do(self._execute_task, task)
            elif day == "Wednesday":
                schedule.every().wednesday.at(time_str).do(self._execute_task, task)
            elif day == "Thursday":
                schedule.every().thursday.at(time_str).do(self._execute_task, task)
            elif day == "Friday":
                schedule.every().friday.at(time_str).do(self._execute_task, task)
            elif day == "Saturday":
                schedule.every().saturday.at(time_str).do(self._execute_task, task)
            elif day == "Sunday":
                schedule.every().sunday.at(time_str).do(self._execute_task, task)
        
        elif task.task_type == TaskType.MONTHLY:
            # 每月任务简化处理，在每日检查中执行
            logger.warning(f"每月任务需要特殊处理：{task.name}")
        
        elif task.task_type == TaskType.REALTIME:
            # 实时任务使用固定间隔
            schedule.every(5).minutes.do(
                self._execute_task, task
            )
        
        logger.info(f"任务已调度：{task.name}")
    
    def _execute_task(self, task: ScheduledTask):
        """
        执行任务
        
        Args:
            task: 定时任务
        """
        logger.info(f"执行任务：{task.name}")
        
        task.last_run = datetime.now()
        task.run_count += 1
        
        try:
            # 加载智能体
            agent = self.executor.load_agent(task.agent_id)
            
            # 执行任务
            from ai_agent import TaskPriority
            result = agent.run(task.task_description, priority=TaskPriority.HIGH)
            
            logger.info(f"任务完成：{task.name} - {result.status}")
            
            # 记录历史
            self.task_history.append({
                "task_id": task.id,
                "task_name": task.name,
                "executed_at": task.last_run.isoformat(),
                "status": result.status,
                "error": result.error
            })
            
        except Exception as e:
            logger.error(f"任务失败：{task.name} - {e}")
            task.fail_count += 1
            
            # 记录历史
            self.task_history.append({
                "task_id": task.id,
                "task_name": task.name,
                "executed_at": task.last_run.isoformat(),
                "status": "failed",
                "error": str(e)
            })
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行中")
            return
        
        logger.info("启动任务调度器...")
        
        # 加载所有任务
        self.load_all_tasks()
        
        # 调度所有任务
        for task in self.tasks:
            if task.enabled:
                self.schedule_task(task)
        
        # 启动调度线程
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("任务调度器已启动")
    
    def _run_scheduler(self):
        """运行调度器主循环"""
        logger.info("调度器主循环启动")
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """停止调度器"""
        logger.info("停止任务调度器...")
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("任务调度器已停止")
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            "running": self.running,
            "total_tasks": len(self.tasks),
            "enabled_tasks": sum(1 for t in self.tasks if t.enabled),
            "task_history_size": len(self.task_history),
            "next_run": schedule.next_run().isoformat() if schedule.next_run() else None
        }
    
    def get_task_list(self) -> List[Dict]:
        """获取任务列表"""
        return [
            {
                "id": task.id,
                "name": task.name,
                "type": task.task_type.value,
                "schedule": task.schedule_time,
                "agent": task.agent_id,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "run_count": task.run_count,
                "fail_count": task.fail_count
            }
            for task in self.tasks
        ]


def main():
    """测试主函数"""
    print("=" * 60)
    print("ChargeCloud OPC - 任务调度器")
    print("=" * 60)
    
    # 创建调度器
    scheduler = TaskScheduler()
    
    print("\n加载所有任务...")
    scheduler.load_all_tasks()
    
    print("\n调度器状态:")
    print(json.dumps(scheduler.get_status(), indent=2, ensure_ascii=False))
    
    print("\n任务列表:")
    for task in scheduler.get_task_list():
        print(f"  {task['schedule']:20} {task['name']:15} ({task['agent']})")
    
    print("\n✅ 任务调度器就绪!")
    print("\n提示：调用 scheduler.start() 启动调度器")


if __name__ == '__main__':
    main()
