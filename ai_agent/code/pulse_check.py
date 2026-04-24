#!/usr/bin/env python3
"""
10分钟脉搏系统检查脚本
检查股票监控、专家学习、任务执行、系统健康状态
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

def check_system_health():
    """检查系统健康状态"""
    health = {}
    
    # 磁盘空间
    try:
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            health['disk'] = {
                'size': parts[1],
                'used': parts[2],
                'available': parts[3],
                'use_percent': parts[4]
            }
    except Exception as e:
        health['disk_error'] = str(e)
    
    # 内存使用
    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line.startswith('Mem:'):
                parts = line.split()
                health['memory'] = {
                    'total_mb': parts[1],
                    'used_mb': parts[2],
                    'free_mb': parts[3]
                }
    except Exception as e:
        health['memory_error'] = str(e)
    
    return health

def check_cron_tasks():
    """检查定时任务状态"""
    try:
        # 读取cron任务列表
        result = subprocess.run(
            ['openclaw', 'cron', 'list'],
            capture_output=True, text=True
        )
        return result.stdout[:2000]  # 限制长度
    except Exception as e:
        return f"检查失败: {e}"

def check_memory_files():
    """检查记忆文件"""
    memory_dir = Path("/root/.openclaw/workspace/memory")
    today = datetime.now().strftime("%Y-%m-%d")
    today_file = memory_dir / f"{today}.md"
    
    files = list(memory_dir.glob("*.md")) if memory_dir.exists() else []
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    recent_files = []
    for f in files[:5]:
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            recent_files.append(f"{f.name} ({mtime.strftime('%m-%d %H:%M')})")
        except:
            recent_files.append(f.name)
    
    return {
        'today_exists': today_file.exists(),
        'recent_files': recent_files,
        'total_files': len(files)
    }

def check_expert_learning():
    """检查专家学习状态"""
    skills_dir = Path("/root/.openclaw/workspace/skills")
    
    experts = [
        'finance-advisor', 'finance-expert', 'hr-expert',
        'legal-advisor', 'marketing-expert', 'network-expert',
        'ceo-advisor'
    ]
    
    expert_status = {}
    for expert in experts:
        ref_dir = skills_dir / expert / 'references'
        if ref_dir.exists():
            files = list(ref_dir.glob('*'))
            expert_status[expert] = len(files)
        else:
            expert_status[expert] = 0
    
    return expert_status

def check_stock_data():
    """检查股票数据"""
    stock_dir = Path("/root/.openclaw/workspace/projects/stock-trading")
    
    if stock_dir.exists():
        files = list(stock_dir.rglob('*'))
        py_files = [f for f in files if f.suffix == '.py']
        return {
            'project_exists': True,
            'total_files': len(files),
            'python_files': len(py_files)
        }
    return {'project_exists': False}

def generate_pulse_report():
    """生成脉搏报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    health = check_system_health()
    memory = check_memory_files()
    experts = check_expert_learning()
    stock = check_stock_data()
    
    # 统计专家学习进度
    total_refs = sum(experts.values())
    active_experts = sum(1 for v in experts.values() if v > 0)
    
    # 生成报告
    report = f"""
📊 【10分钟脉搏系统报告】{timestamp}

🔹 系统健康状态
   - 磁盘使用: {health.get('disk', {}).get('use_percent', 'N/A')}
   - 内存使用: {health.get('memory', {}).get('used_mb', 'N/A')}MB / {health.get('memory', {}).get('total_mb', 'N/A')}MB

🔹 记忆文件状态
   - 今日文件: {'✅ 存在' if memory['today_exists'] else '❌ 未创建'}
   - 总记忆文件: {memory['total_files']} 个
   - 最近更新: {', '.join(memory['recent_files'][:3]) if memory['recent_files'] else '无'}

🔹 专家学习状态 ({active_experts}/7 活跃)
   - 金融顾问: {experts.get('finance-advisor', 0)} 篇
   - 财务专家: {experts.get('finance-expert', 0)} 篇
   - 人力资源: {experts.get('hr-expert', 0)} 篇
   - 法律顾问: {experts.get('legal-advisor', 0)} 篇
   - 营销专家: {experts.get('marketing-expert', 0)} 篇
   - 网络专家: {experts.get('network-expert', 0)} 篇
   - CEO顾问: {experts.get('ceo-advisor', 0)} 篇
   - 总计: {total_refs} 篇学习文档

🔹 股票监控系统
   - 项目状态: {'✅ 存在' if stock['project_exists'] else '❌ 未找到'}
   - Python脚本: {stock.get('python_files', 0)} 个

💡 系统状态: {'正常' if memory['today_exists'] and stock['project_exists'] else '需要关注'}
"""
    
    return report

if __name__ == "__main__":
    print("🤖 正在执行10分钟脉搏系统检查...\n")
    report = generate_pulse_report()
    print(report)
    
    # 保存报告
    report_file = Path("/root/.openclaw/workspace/ai_agent/results/pulse_report_latest.txt")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 报告已保存至: {report_file}")
