#!/usr/bin/env python3
"""
AI智能决策通用技能包
让所有智能体都能使用AI决策能力
"""

import asyncio
from smart_decision_engine_v2 import AIDecisionEngine

class AIDecisionSkill:
    """AI智能决策通用技能"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.ai_engine = AIDecisionEngine()
        self.skill_context = {
            'agent_name': agent_name,
            'recent_tasks': [],
            'interaction_history': [],
            'domain_knowledge': self._load_domain_knowledge(agent_name)
        }
    
    def _load_domain_knowledge(self, agent_name: str) -> dict:
        """加载领域知识"""
        domain_knowledge = {
            'finance-expert': {
                'keywords': ['股票', '投资', '财务', '分析', '风险', '收益', '市场'],
                'complex_tasks': ['投资分析', '风险评估', '财务规划'],
                'high_risk_tasks': ['交易执行', '资金操作', '重大决策']
            },
            'ceo-advisor': {
                'keywords': ['战略', '决策', '管理', '规划', '业务', '组织', '领导'],
                'complex_tasks': ['战略规划', '组织架构', '业务决策'],
                'high_risk_tasks': ['重大投资', '人事调整', '战略转向']
            },
            'legal-advisor': {
                'keywords': ['法律', '合同', '风险', '合规', '诉讼', '法规', '条款'],
                'complex_tasks': ['合同审核', '法律分析', '风险评估'],
                'high_risk_tasks': ['诉讼决策', '重大签约', '法律纠纷']
            },
            'hr-expert': {
                'keywords': ['招聘', '培训', '薪酬', '绩效', '员工', '组织', '发展'],
                'complex_tasks': ['薪酬设计', '绩效评估', '组织发展'],
                'high_risk_tasks': ['人事调整', '薪酬改革', '组织变革']
            },
            'marketing-expert': {
                'keywords': ['营销', '市场', '品牌', '推广', '客户', '销售', '广告'],
                'complex_tasks': ['营销策略', '品牌建设', '市场分析'],
                'high_risk_tasks': ['重大投资', '品牌重塑', '市场进入']
            },
            'network-expert': {
                'keywords': ['网络', '安全', '系统', '运维', '架构', '性能', '故障'],
                'complex_tasks': ['架构设计', '安全评估', '性能优化'],
                'high_risk_tasks': ['系统变更', '安全事件', '重大升级']
            },
            'finance-advisor': {
                'keywords': ['理财', '投资', '保险', '银行', '基金', '证券', '规划'],
                'complex_tasks': ['理财规划', '投资组合', '风险评估'],
                'high_risk_tasks': ['重大投资', '保险决策', '财务规划']
            }
        }
        
        return domain_knowledge.get(agent_name, {
            'keywords': [],
            'complex_tasks': [],
            'high_risk_tasks': []
        })
    
    async def smart_execute_task(self, task_description: str, user_input: str, task_func, **kwargs):
        """智能执行任务"""
        
        # 增强用户输入分析
        enhanced_input = self._enhance_input_analysis(user_input, task_description)
        
        print(f"🧠 {self.agent_name} AI分析: {enhanced_input}")
        
        # 使用AI决策引擎
        result = await self.ai_engine.smart_execute(
            task_func, 
            task_description, 
            enhanced_input,
            self.skill_context
        )
        
        # 更新技能上下文
        self._update_skill_context(task_description, user_input, result)
        
        return result
    
    def _enhance_input_analysis(self, user_input: str, task_description: str) -> str:
        """增强输入分析"""
        
        # 添加领域关键词分析
        domain_keywords = self.skill_context['domain_knowledge']['keywords']
        found_keywords = [kw for kw in domain_keywords if kw in user_input]
        
        # 添加任务复杂度分析
        complex_tasks = self.skill_context['domain_knowledge']['complex_tasks']
        high_risk_tasks = self.skill_context['domain_knowledge']['high_risk_tasks']
        
        # 构建增强输入
        enhanced_parts = [user_input]
        
        if found_keywords:
            enhanced_parts.append(f"领域关键词: {', '.join(found_keywords)}")
        
        if any(task in task_description for task in complex_tasks):
            enhanced_parts.append("复杂领域任务")
        
        if any(task in task_description for task in high_risk_tasks):
            enhanced_parts.append("高风险领域任务")
        
        return " | ".join(enhanced_parts)
    
    def _update_skill_context(self, task_description: str, user_input: str, result: dict):
        """更新技能上下文"""
        
        # 记录任务历史
        task_record = {
            'agent': self.agent_name,
            'task_description': task_description,
            'user_input': user_input,
            'result': result,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        self.skill_context['recent_tasks'].append(task_record)
        
        # 保持最近20个任务
        if len(self.skill_context['recent_tasks']) > 20:
            self.skill_context['recent_tasks'] = self.skill_context['recent_tasks'][-20:]
        
        # 记录交互历史
        interaction_record = {
            'agent': self.agent_name,
            'user_input': user_input,
            'decision': result.get('status', 'unknown'),
            'timestamp': asyncio.get_event_loop().time()
        }
        
        self.skill_context['interaction_history'].append(interaction_record)
        
        # 保持最近50次交互
        if len(self.skill_context['interaction_history']) > 50:
            self.skill_context['interaction_history'] = self.skill_context['interaction_history'][-50:]
    
    def get_skill_summary(self) -> dict:
        """获取技能摘要"""
        return {
            'agent_name': self.agent_name,
            'total_tasks': len(self.skill_context['recent_tasks']),
            'recent_interactions': len(self.skill_context['interaction_history']),
            'domain_knowledge': len(self.skill_context['domain_knowledge']['keywords']),
            'auto_completed': sum(1 for t in self.skill_context['recent_tasks'] 
                                if t['result'].get('status') == 'auto_completed')
        }

# 专家智能体包装器
class ExpertAgentWithAISkill:
    """带AI决策技能的专家智能体"""
    
    def __init__(self, agent_name: str, expert_func):
        self.agent_name = agent_name
        self.expert_func = expert_func
        self.ai_skill = AIDecisionSkill(agent_name)
    
    async def smart_consult(self, user_query: str, **kwargs):
        """智能咨询"""
        
        async def expert_task():
            """专家任务"""
            return await self.expert_func(user_query, **kwargs)
        
        # 使用AI决策执行
        result = await self.ai_skill.smart_execute_task(
            f"{self.agent_name}咨询",
            user_query,
            expert_task,
            **kwargs
        )
        
        return result
    
    async def smart_analyze(self, analysis_target: str, user_input: str, **kwargs):
        """智能分析"""
        
        async def analysis_task():
            """分析任务"""
            return f"{self.agent_name}分析完成: {analysis_target}"
        
        result = await self.ai_skill.smart_execute_task(
            f"{self.agent_name}分析",
            user_input,
            analysis_task,
            **kwargs
        )
        
        return result

# 演示函数
async def demo_ai_skill():
    """演示AI决策技能"""
    
    # 模拟金融专家
    async def finance_expert(query: str, **kwargs):
        await asyncio.sleep(1)
        return f"金融分析完成: {query}"
    
    # 创建带AI技能的金融专家
    finance_agent = ExpertAgentWithAISkill("finance-expert", finance_expert)
    
    print("🧠 AI决策技能演示 - 金融专家")
    print("=" * 50)
    
    # 测试用例
    test_cases = [
        ("马上分析股票投资风险", "分析股票投资风险"),
        ("请帮忙查看财务报告", "查看财务报告"),
        ("执行重大投资决策", "重大投资决策")
    ]
    
    for user_input, task_desc in test_cases:
        print(f"\n📊 测试: {user_input}")
        print("-" * 30)
        
        result = await finance_agent.smart_consult(user_input)
        print(f"结果: {result}")
    
    # 显示技能摘要
    summary = finance_agent.ai_skill.get_skill_summary()
    print(f"\n📈 技能摘要: {summary}")

if __name__ == "__main__":
    asyncio.run(demo_ai_skill())