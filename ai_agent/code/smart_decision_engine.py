#!/usr/bin/env python3
"""
智能决策引擎 - 消除"继续"依赖，实现真正的智能自动化
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

class TaskComplexity(Enum):
    """任务复杂度等级"""
    SIMPLE = "simple"      # 简单任务: <30秒
    MEDIUM = "medium"      # 中等任务: 30秒-5分钟
    COMPLEX = "complex"    # 复杂任务: >5分钟

class DecisionResult(Enum):
    """决策结果"""
    AUTO_CONTINUE = "auto_continue"    # 自动继续
    REPORT_PROGRESS = "report_progress" # 汇报进度后继续
    REQUEST_CONFIRM = "request_confirm" # 需要确认
    STOP_AND_REPORT = "stop_and_report" # 停止并报告

class SmartDecisionEngine:
    """智能决策引擎"""
    
    def __init__(self):
        self.user_preferences = {
            "auto_continue_threshold": 0.7,  # 自动继续阈值
            "progress_report_interval": 60,  # 进度汇报间隔(秒)
            "max_auto_duration": 300,        # 最大自动执行时间(秒)
        }
        self.task_history = []
        self.user_feedback_history = []
        
    def analyze_task_complexity(self, task_description: str, estimated_duration: int) -> TaskComplexity:
        """分析任务复杂度"""
        if estimated_duration < 30:
            return TaskComplexity.SIMPLE
        elif estimated_duration <= 300:  # 5分钟
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.COMPLEX
    
    def should_continue(self, task_state: Dict[str, Any]) -> DecisionResult:
        """智能判断是否需要继续确认"""
        
        # 获取任务信息
        task_name = task_state.get('name', 'unknown')
        step_number = task_state.get('step', 0)
        total_steps = task_state.get('total_steps', 1)
        estimated_duration = task_state.get('estimated_duration', 0)
        risk_level = task_state.get('risk_level', 'low')
        
        # 分析任务复杂度
        complexity = self.analyze_task_complexity(task_name, estimated_duration)
        
        # 决策规则
        if complexity == TaskComplexity.SIMPLE:
            # 简单任务：完全自动继续
            return DecisionResult.AUTO_CONTINUE
            
        elif complexity == TaskComplexity.MEDIUM:
            # 中等任务：关键节点汇报进度
            if step_number == 0:  # 开始
                return DecisionResult.REPORT_PROGRESS
            elif step_number == total_steps - 1:  # 结束
                return DecisionResult.REPORT_PROGRESS
            else:
                return DecisionResult.AUTO_CONTINUE
                
        elif complexity == TaskComplexity.COMPLEX:
            # 复杂任务：关键节点需要确认
            if risk_level == 'high':
                # 高风险任务：每个步骤都需要确认
                return DecisionResult.REQUEST_CONFIRM
            else:
                # 普通复杂任务：关键节点确认
                if step_number == 0 or step_number == total_steps // 2 or step_number == total_steps - 1:
                    return DecisionResult.REQUEST_CONFIRM
                else:
                    return DecisionResult.REPORT_PROGRESS
        
        # 默认情况：自动继续
        return DecisionResult.AUTO_CONTINUE
    
    def generate_auto_response(self, decision: DecisionResult, task_state: Dict[str, Any]) -> str:
        """根据决策生成自动响应"""
        
        task_name = task_state.get('name', '任务')
        step_number = task_state.get('step', 0)
        total_steps = task_state.get('total_steps', 1)
        
        if decision == DecisionResult.AUTO_CONTINUE:
            return f"🚀 自动继续执行 {task_name} 第{step_number + 1}/{total_steps}步..."
            
        elif decision == DecisionResult.REPORT_PROGRESS:
            progress = (step_number / total_steps) * 100
            return f"📊 {task_name} 进度: {progress:.1f}% ({step_number}/{total_steps}) - 继续执行..."
            
        elif decision == DecisionResult.REQUEST_CONFIRM:
            return f"❓ {task_name} 第{step_number + 1}/{total_steps}步需要确认，继续吗？"
            
        elif decision == DecisionResult.STOP_AND_REPORT:
            return f"⚠️ {task_name} 遇到问题需要处理，请检查..."
        
        return "继续执行..."
    
    def learn_from_feedback(self, user_response: str, task_state: Dict[str, Any]):
        """从用户反馈中学习"""
        
        # 记录用户反馈
        feedback = {
            'timestamp': datetime.now().isoformat(),
            'task_state': task_state,
            'user_response': user_response,
            'decision_made': task_state.get('last_decision')
        }
        self.user_feedback_history.append(feedback)
        
        # 根据反馈调整偏好
        if '继续' in user_response or '好的' in user_response:
            # 用户同意继续，提高自动继续阈值
            self.user_preferences['auto_continue_threshold'] = min(
                0.9, self.user_preferences['auto_continue_threshold'] + 0.05
            )
        elif '停止' in user_response or '等等' in user_response:
            # 用户要求停止，降低自动继续阈值
            self.user_preferences['auto_continue_threshold'] = max(
                0.3, self.user_preferences['auto_continue_threshold'] - 0.1
            )
    
    async def execute_with_decision(self, task_func, task_name: str, steps: int, **kwargs):
        """使用智能决策执行任务"""
        
        print(f"🎯 开始执行任务: {task_name} (共{steps}步)")
        
        for step in range(steps):
            # 构建任务状态
            task_state = {
                'name': task_name,
                'step': step,
                'total_steps': steps,
                'estimated_duration': kwargs.get('estimated_duration', 60),
                'risk_level': kwargs.get('risk_level', 'low'),
                'start_time': datetime.now()
            }
            
            # 智能决策
            decision = self.should_continue(task_state)
            task_state['last_decision'] = decision.value
            
            # 生成响应
            response = self.generate_auto_response(decision, task_state)
            print(response)
            
            # 根据决策执行
            if decision == DecisionResult.REQUEST_CONFIRM:
                # 需要用户确认的情况
                # 在实际应用中，这里会等待用户输入
                # 现在模拟用户确认
                user_input = "继续"  # 模拟用户输入
                self.learn_from_feedback(user_input, task_state)
                
                if '停止' in user_input:
                    print("任务已停止")
                    break
            
            # 执行任务步骤
            try:
                if asyncio.iscoroutinefunction(task_func):
                    result = await task_func(step, **kwargs)
                else:
                    result = task_func(step, **kwargs)
                
                print(f"✅ 步骤 {step + 1} 完成: {result}")
                
                # 记录任务历史
                self.task_history.append({
                    'task': task_name,
                    'step': step,
                    'result': result,
                    'decision': decision.value,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"❌ 步骤 {step + 1} 失败: {e}")
                # 错误处理决策
                error_decision = self.handle_error(e, task_state)
                if error_decision == DecisionResult.STOP_AND_REPORT:
                    break
        
        print(f"🎉 任务 {task_name} 执行完成！")
        return self.get_execution_summary(task_name)
    
    def handle_error(self, error: Exception, task_state: Dict[str, Any]) -> DecisionResult:
        """错误处理决策"""
        error_type = type(error).__name__
        
        # 简单错误：自动重试或继续
        if error_type in ['ConnectionError', 'TimeoutError']:
            print(f"🔄 遇到 {error_type}，自动重试...")
            return DecisionResult.AUTO_CONTINUE
        
        # 严重错误：停止并报告
        elif error_type in ['PermissionError', 'MemoryError']:
            print(f"⚠️ 遇到严重错误 {error_type}，停止执行")
            return DecisionResult.STOP_AND_REPORT
        
        # 默认：需要确认
        else:
            print(f"❓ 遇到未知错误 {error_type}，需要确认")
            return DecisionResult.REQUEST_CONFIRM
    
    def get_execution_summary(self, task_name: str) -> Dict[str, Any]:
        """获取执行摘要"""
        task_records = [r for r in self.task_history if r['task'] == task_name]
        
        if not task_records:
            return {}
        
        auto_count = sum(1 for r in task_records if r['decision'] == 'auto_continue')
        confirm_count = sum(1 for r in task_records if r['decision'] == 'request_confirm')
        
        return {
            'task_name': task_name,
            'total_steps': len(task_records),
            'auto_continue_steps': auto_count,
            'confirm_required_steps': confirm_count,
            'auto_rate': auto_count / len(task_records) * 100,
            'completion_time': datetime.now().isoformat()
        }

# 示例任务函数
def sample_task(step: int, **kwargs):
    """示例任务函数"""
    import time
    time.sleep(0.5)  # 模拟任务执行
    return f"步骤 {step + 1} 完成"

async def sample_async_task(step: int, **kwargs):
    """示例异步任务函数"""
    await asyncio.sleep(0.5)  # 模拟异步任务
    return f"异步步骤 {step + 1} 完成"

# 演示函数
async def demo():
    """演示智能决策引擎"""
    engine = SmartDecisionEngine()
    
    print("\n=== 演示1: 简单任务 (自动继续) ===")
    result1 = await engine.execute_with_decision(
        sample_task, "简单数据处理", 3,
        estimated_duration=10, risk_level='low'
    )
    
    print("\n=== 演示2: 中等任务 (进度汇报) ===")
    result2 = await engine.execute_with_decision(
        sample_async_task, "中等复杂度分析", 5,
        estimated_duration=120, risk_level='medium'
    )
    
    print("\n=== 执行摘要 ===")
    print(f"任务1: {json.dumps(result1, indent=2, ensure_ascii=False)}")
    print(f"任务2: {json.dumps(result2, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    print("🤖 智能决策引擎演示")
    asyncio.run(demo())