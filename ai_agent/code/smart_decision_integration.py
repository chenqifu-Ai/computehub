#!/usr/bin/env python3
"""
智能决策引擎集成示例 - 展示如何减少"继续"确认
"""

import asyncio
import time
from smart_decision_engine import SmartDecisionEngine, DecisionResult

class ContinuousFlowWithSmartDecision:
    """集成智能决策的连续流技能"""
    
    def __init__(self):
        self.decision_engine = SmartDecisionEngine()
        self.interaction_count = 0  # 记录交互次数
        
    async def execute_task_old_way(self, task_name: str, steps: int):
        """旧方式：每个步骤都需要确认"""
        print(f"\n=== 旧方式执行: {task_name} ===")
        
        for step in range(steps):
            # 每个步骤都需要确认
            print(f"\n步骤 {step + 1}/{steps} 完成")
            
            # 模拟用户确认（实际中需要等待用户输入）
            self.interaction_count += 1
            user_response = "继续"  # 模拟用户输入
            
            if "停止" in user_response:
                print("任务被用户停止")
                break
        
        print(f"✅ {task_name} 完成，交互次数: {self.interaction_count}")
        return self.interaction_count
    
    async def execute_task_new_way(self, task_name: str, steps: int, **kwargs):
        """新方式：智能决策减少确认"""
        print(f"\n=== 新方式执行: {task_name} ===")
        
        # 使用智能决策引擎
        summary = await self.decision_engine.execute_with_decision(
            self._task_step, task_name, steps, **kwargs
        )
        
        # 计算减少的交互次数
        old_interactions = steps  # 旧方式每个步骤都需要确认
        new_interactions = summary.get('confirm_required_steps', 0)
        reduction = ((old_interactions - new_interactions) / old_interactions) * 100
        
        print(f"\n📊 交互优化效果:")
        print(f"  旧方式交互次数: {old_interactions}")
        print(f"  新方式交互次数: {new_interactions}")
        print(f"  交互减少: {reduction:.1f}%")
        print(f"  自动继续率: {summary.get('auto_rate', 0):.1f}%")
        
        return summary
    
    def _task_step(self, step: int, **kwargs):
        """任务步骤执行函数"""
        task_name = kwargs.get('task_name', '任务')
        
        # 模拟任务执行
        time.sleep(0.3)  # 模拟工作
        
        # 模拟不同步骤的复杂度
        if step % 3 == 0:
            # 复杂步骤
            return f"{task_name} 复杂步骤 {step + 1} 完成"
        else:
            # 简单步骤
            return f"{task_name} 简单步骤 {step + 1} 完成"

# 实际连续流技能示例
class EmailAnalysisSkill:
    """邮件分析连续流技能（集成智能决策）"""
    
    def __init__(self):
        self.decision_engine = SmartDecisionEngine()
        
    async def analyze_emails_smart(self, email_count: int = 10):
        """智能邮件分析"""
        print(f"\n📧 开始智能邮件分析 ({email_count}封邮件)")
        
        # 使用智能决策执行
        summary = await self.decision_engine.execute_with_decision(
            self._analyze_email_step, "邮件分析", email_count,
            estimated_duration=email_count * 30,  # 每封邮件30秒
            risk_level='medium'
        )
        
        print(f"\n🎉 邮件分析完成！")
        print(f"   自动继续率: {summary.get('auto_rate', 0):.1f}%")
        print(f"   需要确认步骤: {summary.get('confirm_required_steps', 0)}")
        
        return summary
    
    def _analyze_email_step(self, step: int, **kwargs):
        """分析单封邮件"""
        email_id = step + 1
        
        # 模拟邮件分析
        time.sleep(0.5)  # 模拟分析时间
        
        # 模拟不同类型的邮件
        if email_id % 5 == 0:
            # 重要邮件（需要确认）
            return f"重要邮件 {email_id} 分析完成 - 需要处理"
        else:
            # 普通邮件（自动继续）
            return f"普通邮件 {email_id} 分析完成"

class FileProcessingSkill:
    """文件处理连续流技能"""
    
    def __init__(self):
        self.decision_engine = SmartDecisionEngine()
        
    async def process_files_smart(self, file_count: int = 8):
        """智能文件处理"""
        print(f"\n📁 开始智能文件处理 ({file_count}个文件)")
        
        summary = await self.decision_engine.execute_with_decision(
            self._process_file_step, "文件处理", file_count,
            estimated_duration=file_count * 20,  # 每个文件20秒
            risk_level='low'
        )
        
        print(f"\n✅ 文件处理完成！")
        print(f"   自动继续率: {summary.get('auto_rate', 0):.1f}%")
        
        return summary
    
    def _process_file_step(self, step: int, **kwargs):
        """处理单个文件"""
        file_id = step + 1
        
        # 模拟文件处理
        time.sleep(0.4)  # 模拟处理时间
        
        # 所有文件处理都是低风险，自动继续
        return f"文件 {file_id} 处理完成"

# 演示函数
async def demo_comparison():
    """新旧方式对比演示"""
    flow = ContinuousFlowWithSmartDecision()
    
    print("🤖 智能决策引擎集成演示")
    print("=" * 50)
    
    # 演示1: 简单任务对比
    print("\n1. 简单任务对比 (5个步骤)")
    print("-" * 30)
    
    # 旧方式
    old_count = await flow.execute_task_old_way("简单任务", 5)
    
    # 新方式
    new_summary = await flow.execute_task_new_way("简单任务", 5, risk_level='low')
    
    # 演示2: 邮件分析技能
    print("\n2. 邮件分析技能演示")
    print("-" * 30)
    
    email_skill = EmailAnalysisSkill()
    email_result = await email_skill.analyze_emails_smart(6)
    
    # 演示3: 文件处理技能
    print("\n3. 文件处理技能演示")
    print("-" * 30)
    
    file_skill = FileProcessingSkill()
    file_result = await file_skill.process_files_smart(4)
    
    # 总结
    print("\n" + "=" * 50)
    print("🎯 智能决策引擎集成总结")
    print("-" * 30)
    
    total_old_interactions = 5 + 6 + 4  # 三个演示任务的旧方式交互次数
    total_new_interactions = (
        new_summary.get('confirm_required_steps', 0) +
        email_result.get('confirm_required_steps', 0) +
        file_result.get('confirm_required_steps', 0)
    )
    
    total_reduction = ((total_old_interactions - total_new_interactions) / total_old_interactions) * 100
    
    print(f"总交互次数优化:")
    print(f"  旧方式: {total_old_interactions} 次确认")
    print(f"  新方式: {total_new_interactions} 次确认")
    print(f"  减少: {total_reduction:.1f}%")
    print(f"\n💡 效果: 用户交互负担大幅减轻！")

# 实际集成到现有连续流技能
async def integrate_with_existing_skills():
    """集成到现有连续流技能"""
    
    # 模拟现有的连续流技能
    existing_skills = [
        ("文档生成", 8, 'medium'),
        ("数据分析", 12, 'high'),
        ("系统检查", 5, 'low'),
        ("邮件发送", 3, 'low')
    ]
    
    engine = SmartDecisionEngine()
    
    print("\n🔧 集成到现有连续流技能")
    print("=" * 50)
    
    for skill_name, steps, risk_level in existing_skills:
        print(f"\n执行: {skill_name} ({steps}步)")
        
        # 使用智能决策执行
        summary = await engine.execute_with_decision(
            lambda step, **kw: f"{skill_name} 步骤 {step + 1} 完成",
            skill_name, steps,
            estimated_duration=steps * 30,
            risk_level=risk_level
        )
        
        print(f"   自动继续率: {summary.get('auto_rate', 0):.1f}%")
        print(f"   需要确认: {summary.get('confirm_required_steps', 0)}次")
    
    print("\n✅ 所有技能集成完成！")

if __name__ == "__main__":
    print("🚀 智能决策引擎集成演示")
    
    # 运行演示
    asyncio.run(demo_comparison())
    
    # 集成演示
    asyncio.run(integrate_with_existing_skills())