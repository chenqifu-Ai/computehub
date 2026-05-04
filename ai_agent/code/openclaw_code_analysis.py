#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw代码结构分析工具
分析192.168.1.19服务器上的OpenClaw代码
"""

import os
import json
import subprocess
from pathlib import Path

def analyze_local_openclaw():
    """分析本地OpenClaw目录结构"""
    openclaw_path = "/root/.openclaw"
    
    print("🔍 开始分析本地OpenClaw目录结构...")
    print(f"📁 目录: {openclaw_path}")
    
    # 分析目录结构
    structure = {}
    for root, dirs, files in os.walk(openclaw_path):
        level = root.replace(openclaw_path, '').count(os.sep)
        indent = ' ' * 2 * level
        rel_path = os.path.relpath(root, openclaw_path)
        
        if level <= 3:  # 只显示前3级目录
            structure[rel_path] = {
                'dirs': [],
                'files': [],
                'size': sum(os.path.getsize(os.path.join(root, f)) for f in files)
            }
            
            for dir_name in dirs:
                if level < 2:  # 只显示直接子目录
                    structure[rel_path]['dirs'].append(dir_name)
            
            for file_name in files:
                if file_name.endswith(('.py', '.js', '.json', '.md', '.sh')):
                    structure[rel_path]['files'].append(file_name)
    
    return structure

def analyze_workspace():
    """分析workspace目录"""
    workspace_path = "/root/.openclaw/workspace"
    
    print(f"\n📊 分析Workspace目录: {workspace_path}")
    
    projects = []
    skills = []
    ai_agent_files = []
    
    # 分析项目目录
    projects_dir = os.path.join(workspace_path, "projects")
    if os.path.exists(projects_dir):
        projects = [d for d in os.listdir(projects_dir) 
                   if os.path.isdir(os.path.join(projects_dir, d))]
    
    # 分析技能目录
    skills_dir = os.path.join(workspace_path, "skills")
    if os.path.exists(skills_dir):
        skills = [d for d in os.listdir(skills_dir) 
                 if os.path.isdir(os.path.join(skills_dir, d))]
    
    # 分析AI Agent代码
    ai_agent_dir = os.path.join(workspace_path, "ai_agent")
    if os.path.exists(ai_agent_dir):
        code_dir = os.path.join(ai_agent_dir, "code")
        results_dir = os.path.join(ai_agent_dir, "results")
        
        if os.path.exists(code_dir):
            ai_agent_files = [f for f in os.listdir(code_dir) 
                            if f.endswith('.py') and os.path.isfile(os.path.join(code_dir, f))]
    
    return {
        'projects': projects,
        'skills': skills,
        'ai_agent_files': ai_agent_files[:20],  # 只显示前20个文件
        'total_ai_agent_files': len(ai_agent_files) if ai_agent_files else 0
    }

def analyze_config():
    """分析配置文件"""
    config_path = "/root/.openclaw/openclaw.json"
    
    print(f"\n⚙️  分析配置文件: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 提取关键配置信息
        key_configs = {
            'model': config.get('model', '未知'),
            'thinking': config.get('thinking', '关闭'),
            'skills': list(config.get('skills', {}).keys())[:5],  # 前5个技能
            'agents': list(config.get('agents', {}).keys())[:5],  # 前5个Agent
            'extensions': list(config.get('extensions', {}).keys())
        }
        
        return key_configs
        
    except Exception as e:
        return {'error': f"配置文件读取失败: {e}"}

def generate_report():
    """生成分析报告"""
    print("=" * 60)
    print("🤖 OpenClaw代码结构分析报告")
    print("=" * 60)
    
    # 分析本地结构
    local_structure = analyze_local_openclaw()
    
    print(f"\n📁 主要目录结构:")
    for path, info in local_structure.items():
        if path == '.':
            print(f"  📍 根目录 (大小: {info['size']/1024:.1f}KB)")
        else:
            print(f"  📂 {path}/ (大小: {info['size']/1024:.1f}KB)")
            if info['dirs']:
                print(f"    ├─ 子目录: {', '.join(info['dirs'][:5])}{'...' if len(info['dirs']) > 5 else ''}")
            if info['files']:
                print(f"    └─ 文件: {', '.join(info['files'][:5])}{'...' if len(info['files']) > 5 else ''}")
    
    # 分析workspace
    workspace_info = analyze_workspace()
    
    print(f"\n🎯 Workspace项目:")
    print(f"  项目数量: {len(workspace_info['projects'])}")
    if workspace_info['projects']:
        print(f"  项目列表: {', '.join(workspace_info['projects'][:10])}{'...' if len(workspace_info['projects']) > 10 else ''}")
    
    print(f"\n🛠️  技能系统:")
    print(f"  技能数量: {len(workspace_info['skills'])}")
    if workspace_info['skills']:
        print(f"  技能列表: {', '.join(workspace_info['skills'][:10])}{'...' if len(workspace_info['skills']) > 10 else ''}")
    
    print(f"\n🤖 AI Agent代码:")
    print(f"  代码文件总数: {workspace_info['total_ai_agent_files']}")
    if workspace_info['ai_agent_files']:
        print(f"  示例文件: {', '.join(workspace_info['ai_agent_files'][:10])}{'...' if len(workspace_info['ai_agent_files']) > 10 else ''}")
    
    # 分析配置
    config_info = analyze_config()
    
    print(f"\n⚙️  系统配置:")
    if 'error' in config_info:
        print(f"  ❌ {config_info['error']}")
    else:
        print(f"  当前模型: {config_info['model']}")
        print(f"  思考模式: {config_info['thinking']}")
        print(f"  启用技能: {', '.join(config_info['skills'][:5])}{'...' if len(config_info['skills']) > 5 else ''}")
        print(f"  注册Agent: {', '.join(config_info['agents'][:5])}{'...' if len(config_info['agents']) > 5 else ''}")
        print(f"  扩展组件: {', '.join(config_info['extensions'][:5])}{'...' if len(config_info['extensions']) > 5 else ''}")
    
    # 尝试连接远程服务器
    print(f"\n🌐 远程服务器连接测试:")
    print(f"  目标服务器: 192.168.1.19")
    
    # Ping测试
    ping_result = subprocess.run(['ping', '-c', '2', '192.168.1.19'], 
                               capture_output=True, text=True)
    if ping_result.returncode == 0:
        print("  ✅ 服务器在线")
        # 提取ping时间
        lines = ping_result.stdout.split('\n')
        if len(lines) >= 3:
            time_line = lines[-2]
            print(f"  📶 网络延迟: {time_line.split('/')[-3]}ms")
    else:
        print("  ❌ 服务器离线或无法连接")
    
    print("\n" + "=" * 60)
    print("📋 分析完成 - 建议下一步:")
    print("1. 检查192.168.1.19的OpenClaw安装状态")
    print("2. 确认Termux环境下的目录结构")
    print("3. 建立SSH密钥认证以便自动化访问")
    print("4. 制定代码同步和部署策略")
    print("=" * 60)

def main():
    """主函数"""
    generate_report()
    
    # 保存报告到文件
    report_file = "/root/.openclaw/workspace/ai_agent/results/openclaw_code_analysis_20260407.md"
    
    # 重定向输出到文件
    original_stdout = sys.stdout
    with open(report_file, 'w', encoding='utf-8') as f:
        sys.stdout = f
        generate_report()
        sys.stdout = original_stdout
    
    print(f"\n✅ 分析报告已保存到: {report_file}")

if __name__ == "__main__":
    import sys
    main()