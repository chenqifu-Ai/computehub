#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度思考分析脚本 - 2026-03-27
按照AI智能体SOP流程：思考 → 代码 → 执行 → 学习
"""

import json
import os
from datetime import datetime, timedelta
import subprocess

class DeepAnalysis:
    def __init__(self):
        self.workspace = "/root/.openclaw/workspace"
        self.memory_dir = os.path.join(self.workspace, "memory")
        self.results_dir = os.path.join(self.workspace, "ai_agent/results")
        
    def load_recent_files(self):
        """加载最近的文件数据"""
        data = {}
        
        # 加载今日文件
        today_file = os.path.join(self.memory_dir, "daily-ideas-2026-03-27.md")
        if os.path.exists(today_file):
            with open(today_file, 'r', encoding='utf-8') as f:
                data['today'] = f.read()
        
        # 加载昨日文件
        yesterday_file = os.path.join(self.memory_dir, "daily-ideas-2026-03-26.md")
        if os.path.exists(yesterday_file):
            with open(yesterday_file, 'r', encoding='utf-8') as f:
                data['yesterday'] = f.read()
        
        # 加载MEMORY.md
        memory_file = os.path.join(self.workspace, "MEMORY.md")
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                data['memory'] = f.read()
        
        return data
    
    def analyze_execution_patterns(self, data):
        """分析执行模式"""
        analysis = {
            'sop_compliance': [],
            'efficiency_metrics': [],
            'problem_patterns': [],
            'success_patterns': []
        }
        
        # 分析SOP合规性
        if 'today' in data:
            content = data['today']
            
            # 检查是否按SOP流程执行
            if '修复中远海发监控任务' in content:
                if '生成Python脚本' not in content and '代码生成' not in content:
                    analysis['sop_compliance'].append("⚠️ 修复任务时未严格按SOP流程（缺少代码生成步骤）")
                else:
                    analysis['sop_compliance'].append("✅ 修复任务符合SOP流程")
        
        # 分析效率指标
        if 'memory' in data:
            # 检查错误记录
            if '错误总结' in data['memory']:
                analysis['efficiency_metrics'].append("📊 有错误记录，说明存在改进空间")
        
        # 分析问题模式
        if 'yesterday' in data:
            if '中远海发价格监控定时任务有错误' in data['yesterday']:
                analysis['problem_patterns'].append("🔄 定时任务配置问题重复出现")
        
        return analysis
    
    def evaluate_work_quality(self):
        """评估工作质量"""
        evaluation = {
            'completion_rate': 0,
            'sop_compliance_rate': 0,
            'error_reduction': 0,
            'user_satisfaction': 0
        }
        
        # 检查定时任务状态
        try:
            result = subprocess.run(['openclaw', 'cron', 'list'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                cron_data = json.loads(result.stdout)
                total_jobs = len(cron_data.get('jobs', []))
                error_jobs = sum(1 for job in cron_data.get('jobs', []) 
                               if job.get('state', {}).get('lastRunStatus') == 'error')
                
                if total_jobs > 0:
                    evaluation['completion_rate'] = ((total_jobs - error_jobs) / total_jobs) * 100
        except Exception as e:
            print(f"检查定时任务时出错: {e}")
        
        return evaluation
    
    def generate_insights(self, data, analysis, evaluation):
        """生成深度洞察"""
        insights = []
        
        # 执行模式洞察
        if analysis.get('problem_patterns'):
            insights.append({
                'type': 'problem_pattern',
                'title': '重复性问题识别',
                'content': '定时任务配置问题需要系统性解决，而不是临时修复'
            })
        
        # 效率洞察
        if evaluation['completion_rate'] < 90:
            insights.append({
                'type': 'efficiency',
                'title': '执行效率待提升',
                'content': f'任务完成率{evaluation["completion_rate"]:.1f}%，需要优化错误处理机制'
            })
        
        # 学习洞察
        if 'memory' in data and '深度思考总结' in data['memory']:
            insights.append({
                'type': 'learning',
                'title': '学习循环建立',
                'content': '已建立深度思考机制，需要持续应用'
            })
        
        return insights
    
    def generate_recommendations(self):
        """生成改进建议"""
        recommendations = [
            {
                'priority': 'high',
                'action': '建立定时任务配置模板',
                'reason': '避免重复的channel配置错误',
                'deadline': '2026-03-28'
            },
            {
                'priority': 'medium',
                'action': '完善SOP执行检查机制',
                'reason': '确保每个任务都严格按流程执行',
                'deadline': '2026-03-29'
            },
            {
                'priority': 'low',
                'action': '建立执行质量评估体系',
                'reason': '量化评估工作效果',
                'deadline': '2026-03-30'
            }
        ]
        
        return recommendations
    
    def run_analysis(self):
        """执行完整分析"""
        print("🔍 开始深度思考分析...")
        
        # 1. 数据收集
        data = self.load_recent_files()
        print("✅ 数据收集完成")
        
        # 2. 模式分析
        analysis = self.analyze_execution_patterns(data)
        print("✅ 模式分析完成")
        
        # 3. 质量评估
        evaluation = self.evaluate_work_quality()
        print("✅ 质量评估完成")
        
        # 4. 洞察生成
        insights = self.generate_insights(data, analysis, evaluation)
        print("✅ 洞察生成完成")
        
        # 5. 建议生成
        recommendations = self.generate_recommendations()
        print("✅ 建议生成完成")
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'data_sources': list(data.keys()),
            'analysis': analysis,
            'evaluation': evaluation,
            'insights': insights,
            'recommendations': recommendations
        }
        
        # 保存报告
        os.makedirs(self.results_dir, exist_ok=True)
        report_file = os.path.join(self.results_dir, "deep_analysis_report_2026-03-27.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📊 分析报告已保存: {report_file}")
        return report

if __name__ == "__main__":
    analyzer = DeepAnalysis()
    report = analyzer.run_analysis()
    
    # 输出关键发现
    print("\n" + "="*60)
    print("🎯 深度思考关键发现")
    print("="*60)
    
    for insight in report['insights']:
        print(f"\n📌 {insight['title']}")
        print(f"   {insight['content']}")
    
    print(f"\n📊 任务完成率: {report['evaluation']['completion_rate']:.1f}%")
    
    print("\n💡 改进建议:")
    for rec in report['recommendations']:
        print(f"   {rec['priority'].upper()}: {rec['action']} - {rec['reason']}")