#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一技能仪表盘系统
确保所有技能展示完全一致
"""

import json
from datetime import datetime

class UnifiedSkillsDashboard:
    def __init__(self):
        self.skills_data = self.load_skills_data()
        self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def load_skills_data(self):
        """加载统一的技能数据"""
        return {
            "system_skills": {
                "memory-wings": {
                    "name": "记忆翅膀",
                    "status": "✅ 活跃",
                    "description": "全局状态快照与自动恢复",
                    "features": ["跨对话框同步", "关机重启恢复", "自动状态保存"],
                    "category": "系统管理"
                },
                "continuous-flow": {
                    "name": "连续流执行", 
                    "status": "✅ 活跃",
                    "description": "智能决策引擎 + 自动化执行",
                    "features": ["零交互自动化", "邮件自动化", "智能决策"],
                    "category": "系统管理"
                },
                "email-automation": {
                    "name": "邮件自动化",
                    "status": "✅ 就绪", 
                    "description": "邮件发送与管理",
                    "features": ["一键发送", "HTML模板", "错误重试"],
                    "category": "系统管理"
                }
            },
            "professional_skills": {
                "ceo-advisor": {
                    "name": "CEO顾问",
                    "status": "✅ 就绪",
                    "description": "企业战略规划与决策",
                    "features": ["商业分析", "战略制定", "决策支持"],
                    "category": "专业领域"
                },
                "finance-advisor": {
                    "name": "金融顾问",
                    "status": "✅ 就绪",
                    "description": "投资理财分析",
                    "features": ["金融知识", "投资分析", "风险管理"],
                    "category": "专业领域"
                },
                "finance-expert": {
                    "name": "财务专家",
                    "status": "✅ 就绪",
                    "description": "企业财务管理",
                    "features": ["税务筹划", "成本控制", "预算编制"],
                    "category": "专业领域"
                },
                "hr-expert": {
                    "name": "人力资源专家",
                    "status": "✅ 就绪",
                    "description": "招聘与薪酬管理",
                    "features": ["招聘流程", "薪酬设计", "绩效考核"],
                    "category": "专业领域"
                },
                "legal-advisor": {
                    "name": "法律顾问",
                    "status": "✅ 就绪",
                    "description": "法律风险防范",
                    "features": ["合同审核", "合规审查", "知识产权"],
                    "category": "专业领域"
                },
                "marketing-expert": {
                    "name": "营销专家",
                    "status": "✅ 就绪",
                    "description": "市场推广策略",
                    "features": ["品牌建设", "数字营销", "客户获取"],
                    "category": "专业领域"
                },
                "network-expert": {
                    "name": "网络专家",
                    "status": "⚠️ 禁用",
                    "description": "网络技术安全",
                    "features": ["网络架构", "安全防护", "故障排查"],
                    "category": "专业领域"
                }
            },
            "technical_skills": {
                "web-automation": {
                    "name": "Web自动化",
                    "status": "✅ 就绪",
                    "description": "网页操作与数据抓取",
                    "features": ["表单填写", "数据抓取", "登录流程"],
                    "category": "技术能力"
                },
                "xiaoh-teacher": {
                    "name": "小爱老师",
                    "status": "✅ 就绪",
                    "description": "学习任务管理",
                    "features": ["知识整理", "学习计划", "进度跟踪"],
                    "category": "技术能力"
                }
            }
        }
    
    def generate_dashboard(self, format_type="markdown"):
        """生成统一格式的仪表盘"""
        if format_type == "markdown":
            return self._generate_markdown_dashboard()
        elif format_type == "text":
            return self._generate_text_dashboard()
        else:
            return self._generate_markdown_dashboard()
    
    def _generate_markdown_dashboard(self):
        """生成Markdown格式仪表盘"""
        dashboard = f"# 🎯 小智技能仪表盘\n\n"
        dashboard += f"*最后更新: {self.last_update}*\n\n"
        
        # 系统管理技能
        dashboard += "## 🔧 系统管理技能\n\n"
        for skill_id, skill in self.skills_data["system_skills"].items():
            dashboard += f"### {skill['status']} {skill['name']}\n"
            dashboard += f"**功能**: {skill['description']}\n"
            dashboard += f"**特性**: {', '.join(skill['features'])}\n\n"
        
        # 专业领域技能
        dashboard += "## 🏢 专业领域技能\n\n"
        for skill_id, skill in self.skills_data["professional_skills"].items():
            dashboard += f"### {skill['status']} {skill['name']}\n"
            dashboard += f"**功能**: {skill['description']}\n"
            dashboard += f"**特性**: {', '.join(skill['features'])}\n\n"
        
        # 技术能力技能
        dashboard += "## 🛠️ 技术能力技能\n\n"
        for skill_id, skill in self.skills_data["technical_skills"].items():
            dashboard += f"### {skill['status']} {skill['name']}\n"
            dashboard += f"**功能**: {skill['description']}\n"
            dashboard += f"**特性**: {', '.join(skill['features'])}\n\n"
        
        # 统计信息
        total_skills = len(self.skills_data["system_skills"]) + len(self.skills_data["professional_skills"]) + len(self.skills_data["technical_skills"])
        active_skills = sum(1 for category in self.skills_data.values() for skill in category.values() if "✅" in skill["status"])
        disabled_skills = sum(1 for category in self.skills_data.values() for skill in category.values() if "⚠️" in skill["status"])
        
        dashboard += f"## 📊 统计信息\n\n"
        dashboard += f"- **总技能数**: {total_skills}\n"
        dashboard += f"- **活跃/就绪技能**: {active_skills}\n"
        dashboard += f"- "禁用技能": {disabled_skills}\n"
        
        return dashboard
    
    def _generate_text_dashboard(self):
        """生成文本格式仪表盘"""
        dashboard = f"小智技能仪表盘 ({self.last_update})\n\n"
        
        # 系统管理技能
        dashboard += "🔧 系统管理技能:\n"
        for skill_id, skill in self.skills_data["system_skills"].items():
            dashboard += f"  {skill['status']} {skill['name']}: {skill['description']}\n"
        
        # 专业领域技能
        dashboard += "\n🏢 专业领域技能:\n"
        for skill_id, skill in self.skills_data["professional_skills"].items():
            dashboard += f"  {skill['status']} {skill['name']}: {skill['description']}\n"
        
        # 技术能力技能
        dashboard += "\n🛠️ 技术能力技能:\n"
        for skill_id, skill in self.skills_data["technical_skills"].items():
            dashboard += f"  {skill['status']} {skill['name']}: {skill['description']}\n"
        
        return dashboard

def main():
    """主函数 - 测试仪表盘生成"""
    dashboard = UnifiedSkillsDashboard()
    
    # 生成并显示仪表盘
    print("=== 统一技能仪表盘 ===")
    print(dashboard.generate_dashboard("markdown"))
    
    # 保存到文件
    with open("/root/.openclaw/workspace/skills/dashboard.md", "w", encoding="utf-8") as f:
        f.write(dashboard.generate_dashboard("markdown"))
    
    print("✅ 仪表盘已保存到: /root/.openclaw/workspace/skills/dashboard.md")

if __name__ == "__main__":
    main()