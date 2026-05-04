#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChargeCloud OPC - AI 智能体管理系统主入口
Main Entry Point - AI Agent Management System

创建时间：2026-04-19
作者：小智 (数据智能体)
版本：v1.0

使用方法:
    python main.py              # 启动完整系统
    python main.py --test       # 测试模式
    python main.py --status     # 查看状态
    python main.py --daily      # 执行日常运营
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

# 添加框架路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_agent import AIAgent, TaskPriority
from workflow_executor import WorkflowExecutor
from task_scheduler import TaskScheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            '/root/.openclaw/workspace/projects/chargecloud-opc/logs/system.log',
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)


class ChargeCloudSystem:
    """
    ChargeCloud OPC 系统主类
    整合所有组件，提供统一管理接口
    """
    
    def __init__(self):
        """初始化系统"""
        self.project_root = "/root/.openclaw/workspace/projects/chargecloud-opc"
        self.agents_dir = os.path.join(self.project_root, "agents")
        
        # 核心组件
        self.executor: WorkflowExecutor = None
        self.scheduler: TaskScheduler = None
        
        # 系统状态
        self.status = "initialized"
        self.started_at = None
        
        logger.info("ChargeCloud OPC 系统已初始化")
    
    def initialize(self):
        """初始化系统组件"""
        logger.info("初始化系统组件...")
        
        # 创建工作流执行器
        self.executor = WorkflowExecutor(self.agents_dir)
        
        # 创建任务调度器
        self.scheduler = TaskScheduler(self.executor)
        
        logger.info("系统组件初始化完成")
    
    def start(self):
        """启动系统"""
        logger.info("启动 ChargeCloud OPC 系统...")
        
        # 初始化组件
        self.initialize()
        
        # 加载所有智能体
        logger.info("加载所有智能体...")
        self.executor.load_all_agents()
        
        # 启动任务调度器
        logger.info("启动任务调度器...")
        self.scheduler.start()
        
        # 更新状态
        self.status = "running"
        self.started_at = datetime.now()
        
        logger.info("=" * 60)
        logger.info("✅ ChargeCloud OPC 系统启动成功!")
        logger.info("=" * 60)
        logger.info(f"启动时间：{self.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"智能体数量：{len(self.executor.agents)}")
        logger.info(f"任务数量：{len(self.scheduler.tasks)}")
        logger.info("=" * 60)
    
    def stop(self):
        """停止系统"""
        logger.info("停止 ChargeCloud OPC 系统...")
        
        if self.scheduler:
            self.scheduler.stop()
        
        self.status = "stopped"
        logger.info("系统已停止")
    
    def execute_daily_operations(self):
        """执行日常运营"""
        logger.info("执行日常运营工作流...")
        
        if not self.executor:
            self.initialize()
        
        workflow = self.executor.execute_daily_operations()
        
        logger.info(f"日常运营完成：{workflow.status}")
        return workflow
    
    def execute_decision(self, issue: str):
        """执行重大决策"""
        logger.info(f"执行重大决策：{issue}")
        
        if not self.executor:
            self.initialize()
        
        workflow = self.executor.execute_decision_workflow(issue)
        
        logger.info(f"决策流程完成：{workflow.status}")
        return workflow
    
    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            "system_status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "uptime_hours": (datetime.now() - self.started_at).total_seconds() / 3600 if self.started_at else 0,
            "executor": self.executor.get_status() if self.executor else None,
            "scheduler": self.scheduler.get_status() if self.scheduler else None,
            "agents": {
                agent_id: agent.get_status()
                for agent_id, agent in self.executor.agents.items()
            } if self.executor else None
        }
    
    def print_status(self):
        """打印系统状态"""
        status = self.get_status()
        
        print("\n" + "=" * 60)
        print("🤖 ChargeCloud OPC - 系统状态")
        print("=" * 60)
        
        print(f"\n系统状态：{status['system_status']}")
        print(f"启动时间：{status['started_at']}")
        print(f"运行时长：{status['uptime_hours']:.2f} 小时")
        
        if status['executor']:
            print(f"\n📊 工作流执行器:")
            print(f"   智能体数量：{status['executor']['agents_loaded']}")
            print(f"   工作流队列：{status['executor']['workflow_queue_size']}")
            print(f"   历史工作流：{status['executor']['workflow_history_size']}")
        
        if status['scheduler']:
            print(f"\n⏰ 任务调度器:")
            print(f"   总任务数：{status['scheduler']['total_tasks']}")
            print(f"   启用任务：{status['scheduler']['enabled_tasks']}")
            print(f"   下次运行：{status['scheduler']['next_run']}")
        
        if status['agents']:
            print(f"\n🤖 智能体列表:")
            for agent_id, agent_status in status['agents'].items():
                print(f"   {agent_id:20} {agent_status['role']:25} {agent_status['status']}")
        
        print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='ChargeCloud OPC - AI 智能体管理系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py              启动完整系统
  python main.py --test       测试模式
  python main.py --status     查看系统状态
  python main.py --daily      执行日常运营
  python main.py --decision "议题"  执行重大决策
        """
    )
    
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--status', action='store_true', help='查看系统状态')
    parser.add_argument('--daily', action='store_true', help='执行日常运营')
    parser.add_argument('--decision', type=str, help='执行重大决策')
    parser.add_argument('--config', type=str, help='指定配置文件')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 ChargeCloud OPC - AI 智能体管理系统")
    print("=" * 60)
    print(f"版本：v1.0")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 创建系统实例
    system = ChargeCloudSystem()
    
    try:
        if args.test:
            # 测试模式
            print("\n🧪 测试模式...")
            system.initialize()
            system.print_status()
            
            # 测试单个智能体
            print("\n测试 CEO 智能体...")
            ceo_agent = system.executor.load_agent("ceo_agent")
            print(f"CEO 智能体状态：{ceo_agent.get_status()}")
        
        elif args.status:
            # 查看状态
            print("\n📊 系统状态...")
            system.initialize()
            system.print_status()
        
        elif args.daily:
            # 执行日常运营
            print("\n📋 执行日常运营...")
            system.initialize()
            workflow = system.execute_daily_operations()
            print(f"\n✅ 日常运营完成：{workflow.status}")
        
        elif args.decision:
            # 执行重大决策
            print(f"\n🎯 执行重大决策：{args.decision}")
            system.initialize()
            workflow = system.execute_decision(args.decision)
            print(f"\n✅ 决策流程完成：{workflow.status}")
        
        else:
            # 启动完整系统
            print("\n🚀 启动完整系统...")
            system.start()
            
            # 保持运行
            print("\n系统运行中... (Ctrl+C 停止)")
            print("日志文件：/root/.openclaw/workspace/projects/chargecloud-opc/logs/system.log")
            
            try:
                while True:
                    import time
                    time.sleep(60)
                    
                    # 每分钟打印一次状态
                    logger.info(f"系统运行正常 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    
            except KeyboardInterrupt:
                print("\n\n收到停止信号...")
                system.stop()
                print("系统已停止")
    
    except Exception as e:
        logger.error(f"系统错误：{e}")
        print(f"\n❌ 系统错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
