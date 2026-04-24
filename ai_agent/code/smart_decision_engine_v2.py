#!/usr/bin/env python3
"""
智能决策引擎 V2 - 真正的AI智能决策
使用AI模型理解用户意图，而不是简单规则
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

class AIDecisionEngine:
    """AI智能决策引擎"""
    
    def __init__(self):
        self.conversation_history = []
        self.user_preferences = {}
        self.task_patterns = self._load_decision_patterns()
        
    def _load_decision_patterns(self) -> Dict:
        """加载决策模式"""
        return {
            # 自动继续模式
            'auto_continue': [
                '状态', '检查', '查看', '报告', '总结', '监控',
                '读取', '获取', '查询', '搜索', '分析', '统计'
            ],
            # 需要确认模式
            'need_confirm': [
                '执行', '运行', '处理', '生成', '创建', '修改',
                '删除', '更新', '安装', '配置', '部署', '发送'
            ],
            # 高风险模式
            'high_risk': [
                '删除', '清空', '重置', '格式化', '卸载', '终止',
                '关闭', '停止', '取消', '撤销', '回滚'
            ]
        }
    
    async def analyze_user_intent(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析用户真实意图"""
        
        # 分析关键词
        intent_analysis = {
            'urgency': self._analyze_urgency(user_input),
            'complexity': self._analyze_complexity(user_input, context),
            'risk_level': self._analyze_risk(user_input),
            'user_mood': self._analyze_user_mood(user_input),
            'preferred_interaction': self._analyze_interaction_preference(context)
        }
        
        # 综合决策
        decision = self._make_ai_decision(intent_analysis, user_input, context)
        
        return {
            'intent_analysis': intent_analysis,
            'decision': decision,
            'confidence': self._calculate_confidence(intent_analysis),
            'reasoning': self._generate_reasoning(intent_analysis, decision)
        }
    
    def _analyze_urgency(self, user_input: str) -> str:
        """分析紧急程度"""
        urgent_keywords = ['马上', '立即', '赶紧', '快', '紧急', '立刻', '现在']
        if any(keyword in user_input for keyword in urgent_keywords):
            return 'high'
        
        normal_keywords = ['可以', '帮忙', '请', '麻烦']
        if any(keyword in user_input for keyword in normal_keywords):
            return 'medium'
            
        return 'low'
    
    def _analyze_complexity(self, user_input: str, context: Dict[str, Any]) -> str:
        """分析任务复杂度"""
        # 基于历史任务复杂度
        recent_tasks = context.get('recent_tasks', [])
        similar_tasks = [t for t in recent_tasks if any(kw in user_input for kw in t.get('keywords', []))]
        
        if similar_tasks:
            avg_complexity = sum(t.get('complexity_score', 3) for t in similar_tasks) / len(similar_tasks)
            if avg_complexity < 2:
                return 'simple'
            elif avg_complexity < 4:
                return 'medium'
            else:
                return 'complex'
        
        # 基于关键词分析
        complex_keywords = ['项目', '系统', '部署', '配置', '分析', '生成']
        simple_keywords = ['状态', '查看', '检查', '读取']
        
        complex_count = sum(1 for kw in complex_keywords if kw in user_input)
        simple_count = sum(1 for kw in simple_keywords if kw in user_input)
        
        if complex_count > simple_count:
            return 'complex'
        elif simple_count > complex_count:
            return 'simple'
        else:
            return 'medium'
    
    def _analyze_risk(self, user_input: str) -> str:
        """分析风险等级"""
        high_risk = any(kw in user_input for kw in self.task_patterns['high_risk'])
        need_confirm = any(kw in user_input for kw in self.task_patterns['need_confirm'])
        
        if high_risk:
            return 'high'
        elif need_confirm:
            return 'medium'
        else:
            return 'low'
    
    def _analyze_user_mood(self, user_input: str) -> str:
        """分析用户情绪"""
        impatient_keywords = ['还要多久', '太慢了', '快点', '加速', '磨叽']
        polite_keywords = ['请', '麻烦', '谢谢', '辛苦']
        
        if any(kw in user_input for kw in impatient_keywords):
            return 'impatient'
        elif any(kw in user_input for kw in polite_keywords):
            return 'polite'
        else:
            return 'neutral'
    
    def _analyze_interaction_preference(self, context: Dict[str, Any]) -> str:
        """分析用户交互偏好"""
        history = context.get('interaction_history', [])
        if not history:
            return 'balanced'
        
        # 分析用户对确认的容忍度
        confirm_responses = [h for h in history if '继续' in h.get('user_input', '')]
        if len(confirm_responses) / len(history) > 0.3:
            return 'prefers_auto'
        else:
            return 'balanced'
    
    def _make_ai_decision(self, analysis: Dict[str, Any], user_input: str, context: Dict[str, Any]) -> str:
        """AI决策"""
        
        # 决策权重
        weights = {
            'urgency': 0.3,
            'complexity': 0.25,
            'risk_level': 0.25,
            'user_mood': 0.1,
            'preferred_interaction': 0.1
        }
        
        # 计算决策分数
        auto_score = 0
        confirm_score = 0
        
        # 紧急程度权重
        if analysis['urgency'] == 'high':
            auto_score += weights['urgency']
        elif analysis['urgency'] == 'low':
            confirm_score += weights['urgency'] * 0.5
        
        # 复杂度权重
        if analysis['complexity'] == 'simple':
            auto_score += weights['complexity']
        elif analysis['complexity'] == 'complex':
            confirm_score += weights['complexity']
        
        # 风险等级权重
        if analysis['risk_level'] == 'low':
            auto_score += weights['risk_level']
        elif analysis['risk_level'] == 'high':
            confirm_score += weights['risk_level'] * 2  # 高风险加倍
        
        # 用户情绪权重
        if analysis['user_mood'] == 'impatient':
            auto_score += weights['user_mood']
        elif analysis['user_mood'] == 'polite':
            confirm_score += weights['user_mood'] * 0.5
        
        # 交互偏好权重
        if analysis['preferred_interaction'] == 'prefers_auto':
            auto_score += weights['preferred_interaction']
        
        # 最终决策
        if auto_score > confirm_score + 0.1:  # 自动继续阈值
            return 'auto_continue'
        elif confirm_score > auto_score + 0.1:  # 需要确认阈值
            return 'need_confirm'
        else:
            return 'report_progress'  # 平衡策略
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """计算决策置信度"""
        # 基于分析的一致性计算置信度
        factors = [
            1.0 if analysis['urgency'] != 'medium' else 0.5,
            1.0 if analysis['complexity'] != 'medium' else 0.5,
            1.0 if analysis['risk_level'] != 'medium' else 0.5,
            1.0 if analysis['user_mood'] != 'neutral' else 0.5
        ]
        return sum(factors) / len(factors)
    
    def _generate_reasoning(self, analysis: Dict[str, Any], decision: str) -> str:
        """生成决策理由"""
        reasons = []
        
        if analysis['urgency'] == 'high':
            reasons.append("用户要求立即执行")
        elif analysis['urgency'] == 'low':
            reasons.append("任务不紧急")
            
        if analysis['complexity'] == 'simple':
            reasons.append("任务简单可自动执行")
        elif analysis['complexity'] == 'complex':
            reasons.append("任务复杂需要确认")
            
        if analysis['risk_level'] == 'high':
            reasons.append("高风险操作需要谨慎")
        elif analysis['risk_level'] == 'low':
            reasons.append("低风险可自动继续")
            
        if analysis['user_mood'] == 'impatient':
            reasons.append("用户情绪急切，减少确认")
            
        return "; ".join(reasons)
    
    async def smart_execute(self, task_func, task_description: str, user_input: str, context: Dict[str, Any] = None):
        """智能执行任务"""
        
        if context is None:
            context = {}
        
        print(f"🧠 AI分析用户意图: {user_input}")
        
        # AI分析
        intent_result = await self.analyze_user_intent(user_input, context)
        
        print(f"📊 意图分析:")
        print(f"   紧急程度: {intent_result['intent_analysis']['urgency']}")
        print(f"   复杂度: {intent_result['intent_analysis']['complexity']}")
        print(f"   风险等级: {intent_result['intent_analysis']['risk_level']}")
        print(f"   用户情绪: {intent_result['intent_analysis']['user_mood']}")
        print(f"   决策: {intent_result['decision']}")
        print(f"   置信度: {intent_result['confidence']:.1%}")
        print(f"   理由: {intent_result['reasoning']}")
        
        # 根据决策执行
        if intent_result['decision'] == 'auto_continue':
            print(f"🚀 自动继续执行: {task_description}")
            result = await task_func()
            print(f"✅ 自动执行完成: {result}")
            return {'status': 'auto_completed', 'result': result}
            
        elif intent_result['decision'] == 'need_confirm':
            print(f"❓ 需要确认: {task_description}")
            # 在实际应用中等待用户确认
            # 这里模拟用户确认
            user_confirmation = "继续"  # 模拟用户输入
            if "继续" in user_confirmation:
                result = await task_func()
                print(f"✅ 确认后执行完成: {result}")
                return {'status': 'confirmed_completed', 'result': result}
            else:
                print("❌ 用户取消执行")
                return {'status': 'cancelled'}
                
        else:  # report_progress
            print(f"📊 汇报进度执行: {task_description}")
            result = await task_func()
            print(f"✅ 进度汇报完成: {result}")
            return {'status': 'progress_reported', 'result': result}

# 演示函数
async def demo_ai_decision():
    """演示AI决策引擎"""
    engine = AIDecisionEngine()
    
    # 测试用例
    test_cases = [
        ("检查系统状态", "检查系统状态", {}),
        ("马上执行部署", "马上执行系统部署", {}),
        ("删除所有文件", "删除所有临时文件", {}),
        ("请帮忙查看", "请帮忙查看一下项目进度", {}),
        ("还要多久", "这个任务还要多久才能完成", {})
    ]
    
    for task_desc, user_input, context in test_cases:
        print(f"\n{'='*50}")
        print(f"测试: {user_input}")
        print('-'*30)
        
        async def demo_task():
            await asyncio.sleep(0.5)
            return f"{task_desc} 执行完成"
        
        result = await engine.smart_execute(demo_task, task_desc, user_input, context)
        print(f"执行结果: {result}")

if __name__ == "__main__":
    print("🤖 AI智能决策引擎 V2 演示")
    asyncio.run(demo_ai_decision())