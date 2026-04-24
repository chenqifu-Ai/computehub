#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公司架构深度回顾分析 - 2026-03-27
从3月10日开始的公司架构整理
"""

import json
import os
import re
from datetime import datetime, timedelta

class CompanyArchitectureReview:
    def __init__(self):
        self.workspace = "/root/.openclaw/workspace"
        self.memory_dir = os.path.join(self.workspace, "memory")
        self.results_dir = os.path.join(self.workspace, "ai_agent/results")
        
    def collect_company_files(self):
        """收集公司相关文件"""
        company_files = {}
        
        # 搜索memory目录中3月10日后的文件
        for filename in os.listdir(self.memory_dir):
            if filename.endswith('.md') and '2026-03' in filename:
                # 提取日期
                date_match = re.search(r'2026-03-(\d{2})', filename)
                if date_match:
                    day = int(date_match.group(1))
                    if day >= 10:  # 3月10日及以后
                        filepath = os.path.join(self.memory_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # 检查是否包含公司相关内容
                        company_keywords = ['公司', '架构', '组织', '部门', '项目', '员工', '团队', '系统']
                        if any(keyword in content for keyword in company_keywords):
                            company_files[filename] = {
                                'date': f"2026-03-{day:02d}",
                                'content': content
                            }
        
        return company_files
    
    def extract_architecture_info(self, files):
        """提取架构信息"""
        architecture = {
            'departments': [],
            'projects': [],
            'systems': [],
            'employees': [],
            'timeline': []
        }
        
        for filename, file_data in files.items():
            content = file_data['content']
            date = file_data['date']
            
            # 提取部门信息
            dept_patterns = [
                r'投资部', r'技术部', r'学习部', r'财务部', r'市场部',
                r'股票监控组', r'风险控制组', r'自动化开发组'
            ]
            for pattern in dept_patterns:
                if re.search(pattern, content):
                    architecture['departments'].append({
                        'name': pattern.replace('r', '').replace('\\', ''),
                        'found_in': filename,
                        'date': date
                    })
            
            # 提取项目信息
            project_patterns = [
                r'股票监控系统', r'邮件命令系统', r'专家学习系统', 
                r'自动化运维系统', r'投资管理系统'
            ]
            for pattern in project_patterns:
                if re.search(pattern, content):
                    architecture['projects'].append({
                        'name': pattern.replace('r', '').replace('\\', ''),
                        'found_in': filename,
                        'date': date
                    })
            
            # 提取系统信息
            system_patterns = [
                r'定时任务', r'监控系统', r'预警系统', r'学习任务'
            ]
            for pattern in system_patterns:
                if re.search(pattern, content):
                    architecture['systems'].append({
                        'name': pattern.replace('r', '').replace('\\', ''),
                        'found_in': filename,
                        'date': date
                    })
            
            # 提取时间线信息
            timeline_items = re.findall(r'\d{2}:\d{2}.*?(?:完成|进行|开始|建立)', content)
            for item in timeline_items:
                architecture['timeline'].append({
                    'time': item.split()[0],
                    'event': item,
                    'file': filename,
                    'date': date
                })
        
        return architecture
    
    def analyze_architecture_evolution(self, architecture):
        """分析架构演进"""
        analysis = {
            'department_growth': len(architecture['departments']),
            'project_complexity': len(architecture['projects']),
            'system_maturity': len(architecture['systems']),
            'timeline_density': len(architecture['timeline']),
            'evolution_stages': []
        }
        
        # 分析发展阶段
        dates = sorted(set(item['date'] for item in architecture['departments'] + 
                          architecture['projects'] + architecture['systems']))
        
        for date in dates:
            stage_info = {
                'date': date,
                'departments': [d for d in architecture['departments'] if d['date'] == date],
                'projects': [p for p in architecture['projects'] if p['date'] == date],
                'systems': [s for s in architecture['systems'] if s['date'] == date]
            }
            analysis['evolution_stages'].append(stage_info)
        
        return analysis
    
    def generate_reconstruction_plan(self, architecture, analysis):
        """生成重建计划"""
        plan = {
            'immediate_actions': [],
            'short_term_goals': [],
            'long_term_vision': []
        }
        
        # 立即行动
        if analysis['department_growth'] > 0:
            plan['immediate_actions'].append({
                'action': '重建部门架构文档',
                'priority': 'high',
                'reason': f'发现{analysis["department_growth"]}个部门需要重新组织'
            })
        
        if analysis['project_complexity'] > 0:
            plan['immediate_actions'].append({
                'action': '整理项目清单',
                'priority': 'high',
                'reason': f'发现{analysis["project_complexity"]}个项目需要重新规划'
            })
        
        # 短期目标
        plan['short_term_goals'].append({
            'goal': '建立完整的公司架构文档',
            'timeline': '3天',
            'deliverables': ['组织架构图', '部门职责说明', '项目路线图']
        })
        
        # 长期愿景
        plan['long_term_vision'].append({
            'vision': '构建自动化智能公司',
            'description': '所有业务流程实现AI驱动自动化',
            'key_metrics': ['自动化率≥90%', '错误率≤1%', '响应时间≤5分钟']
        })
        
        return plan
    
    def run_analysis(self):
        """执行完整分析"""
        print("🔍 开始公司架构深度回顾...")
        
        # 1. 收集文件
        company_files = self.collect_company_files()
        print(f"✅ 收集到{len(company_files)}个相关文件")
        
        # 2. 提取架构信息
        architecture = self.extract_architecture_info(company_files)
        print("✅ 架构信息提取完成")
        
        # 3. 分析演进
        analysis = self.analyze_architecture_evolution(architecture)
        print("✅ 演进分析完成")
        
        # 4. 生成重建计划
        plan = self.generate_reconstruction_plan(architecture, analysis)
        print("✅ 重建计划生成完成")
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'files_analyzed': list(company_files.keys()),
            'architecture': architecture,
            'analysis': analysis,
            'reconstruction_plan': plan
        }
        
        # 保存报告
        os.makedirs(self.results_dir, exist_ok=True)
        report_file = os.path.join(self.results_dir, "company_architecture_review_2026-03-27.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📊 分析报告已保存: {report_file}")
        return report

if __name__ == "__main__":
    reviewer = CompanyArchitectureReview()
    report = reviewer.run_analysis()
    
    # 输出关键发现
    print("\n" + "="*60)
    print("🏢 公司架构回顾关键发现")
    print("="*60)
    
    print(f"\n📁 分析文件数量: {len(report['files_analyzed'])}")
    print(f"🏗️ 发现部门: {report['analysis']['department_growth']}个")
    print(f"📋 发现项目: {report['analysis']['project_complexity']}个")
    print(f"⚙️ 发现系统: {report['analysis']['system_maturity']}个")
    
    print("\n🚀 立即行动:")
    for action in report['reconstruction_plan']['immediate_actions']:
        print(f"   {action['priority'].upper()}: {action['action']} - {action['reason']}")
        
    print("\n📅 短期目标:")
    for goal in report['reconstruction_plan']['short_term_goals']:
        print(f"   {goal['goal']} ({goal['timeline']})")