#!/usr/bin/env python3
"""
Stream系统专项检查脚本
检查数据流处理、实时监控、流水线执行等Stream相关功能
"""

import json
import os
import subprocess
from datetime import datetime

def run_command(cmd):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def check_stock_stream():
    """检查股票价格流系统"""
    print("=== 股票价格流系统检查 ===")
    
    # 检查股票监控脚本
    stock_scripts = [
        "stock_monitor.py",
        "hualian_monitor.py", 
        "cosco_monitor.py",
        "stock_stream_processor.py"
    ]
    
    base_path = "/root/.openclaw/workspace/ai_agent/code"
    stream_scripts = []
    
    for script in stock_scripts:
        script_path = os.path.join(base_path, script)
        if os.path.exists(script_path):
            stream_scripts.append(script)
            print(f"✅ {script}: 存在")
            
            # 检查脚本内容是否包含流处理逻辑
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if any(keyword in content.lower() for keyword in ['stream', 'real-time', '实时', '流']):
                    print(f"   包含流处理逻辑")
        else:
            print(f"❌ {script}: 缺失")
    
    # 检查定时任务中的流处理
    stdout, stderr, code = run_command("crontab -l")
    if code == 0 and stdout:
        stream_tasks = [line for line in stdout.split('\n') if 'stream' in line.lower() or 'monitor' in line.lower()]
        print(f"流处理定时任务数: {len(stream_tasks)}")
        for task in stream_tasks[:3]:  # 显示前3个
            print(f"   {task[:80]}...")
    
    return len(stream_scripts) > 0

def check_task_stream():
    """检查任务执行流系统"""
    print("\n=== 任务执行流系统检查 ===")
    
    # 检查任务流水线脚本
    task_scripts = [
        "task_pipeline.py",
        "workflow_executor.py", 
        "batch_processor.py"
    ]
    
    base_path = "/root/.openclaw/workspace/ai_agent/code"
    pipeline_scripts = []
    
    for script in task_scripts:
        script_path = os.path.join(base_path, script)
        if os.path.exists(script_path):
            pipeline_scripts.append(script)
            print(f"✅ {script}: 存在")
        else:
            print(f"❌ {script}: 缺失")
    
    # 检查是否有连续执行框架
    continuous_files = [
        "continuous_flow_skill.py",
        "stream_processor.py"
    ]
    
    for file in continuous_files:
        file_path = os.path.join(base_path, file)
        if os.path.exists(file_path):
            print(f"✅ {file}: 连续流框架存在")
        else:
            print(f"❌ {file}: 连续流框架缺失")
    
    return len(pipeline_scripts) > 0

def check_learning_stream():
    """检查学习进度流系统"""
    print("\n=== 学习进度流系统检查 ===")
    
    # 检查专家学习进度跟踪
    expert_dirs = [
        "ceo-advisor", "finance-advisor", "finance-expert", 
        "hr-expert", "legal-advistor", "marketing-expert", "network-expert"
    ]
    
    base_path = "/root/.openclaw/workspace/skills"
    learning_streams = []
    
    for expert in expert_dirs:
        expert_path = os.path.join(base_path, expert)
        if os.path.exists(expert_path):
            # 检查学习进度文件
            progress_files = [
                "learning_progress.json",
                "study_tracker.md",
                "knowledge_base.md"
            ]
            
            has_progress = False
            for progress_file in progress_files:
                file_path = os.path.join(expert_path, progress_file)
                if os.path.exists(file_path):
                    has_progress = True
                    break
            
            if has_progress:
                learning_streams.append(expert)
                print(f"✅ {expert}: 学习进度跟踪存在")
            else:
                print(f"⚠️ {expert}: 学习进度跟踪缺失")
        else:
            print(f"❌ {expert}: 技能目录缺失")
    
    print(f"有学习进度跟踪的专家数: {len(learning_streams)}/{len(expert_dirs)}")
    return len(learning_streams) > 0

def check_stream_infrastructure():
    """检查Stream基础设施"""
    print("\n=== Stream基础设施检查 ===")
    
    # 检查消息队列/流处理组件
    components = [
        ("Redis", "redis-cli ping", "PONG"),
        ("消息队列", "python3 -c \"import queue; print('OK')\"", "OK"),
        ("定时任务", "openclaw cron list", "enabled"),
    ]
    
    available_components = []
    
    for name, cmd, expected in components:
        stdout, stderr, code = run_command(cmd)
        if code == 0 and expected in stdout:
            available_components.append(name)
            print(f"✅ {name}: 可用")
        else:
            print(f"❌ {name}: 不可用或未配置")
    
    # 检查流处理库
    stream_libs = [
        "asyncio", "aiohttp", "websockets", "concurrent.futures"
    ]
    
    for lib in stream_libs:
        stdout, stderr, code = run_command(f"python3 -c \"import {lib}; print('OK')\"")
        if code == 0:
            print(f"✅ {lib}: Python库可用")
        else:
            print(f"❌ {lib}: Python库不可用")
    
    return len(available_components) > 0

def generate_stream_report():
    """生成Stream系统专项报告"""
    print("\n" + "="*60)
    print("🌊 Stream系统专项检查报告")
    print("="*60)
    
    # 执行各项检查
    stock_stream_ok = check_stock_stream()
    task_stream_ok = check_task_stream()
    learning_stream_ok = check_learning_stream()
    infrastructure_ok = check_stream_infrastructure()
    
    # 总体评估
    print("\n=== Stream系统总体评估 ===")
    
    stream_score = sum([stock_stream_ok, task_stream_ok, learning_stream_ok, infrastructure_ok])
    max_score = 4
    
    if stream_score == max_score:
        print("✅ Stream系统: 优秀 (4/4)")
        overall_status = "优秀"
    elif stream_score >= 3:
        print("✅ Stream系统: 良好 (3/4)")
        overall_status = "良好"
    elif stream_score >= 2:
        print("⚠️ Stream系统: 一般 (2/4)")
        overall_status = "一般"
    else:
        print("❌ Stream系统: 需改进 (1/4)")
        overall_status = "需改进"
    
    # 生成时间戳
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = {
        "timestamp": current_time,
        "overall_status": overall_status,
        "stream_score": f"{stream_score}/{max_score}",
        "systems": {
            "stock_stream": stock_stream_ok,
            "task_stream": task_stream_ok,
            "learning_stream": learning_stream_ok,
            "infrastructure": infrastructure_ok
        },
        "recommendations": []
    }
    
    # 添加改进建议
    if not stock_stream_ok:
        report["recommendations"].append("需要建立股票价格实时流监控系统")
    if not task_stream_ok:
        report["recommendations"].append("需要建立任务执行流水线框架")
    if not learning_stream_ok:
        report["recommendations"].append("需要完善专家学习进度跟踪系统")
    if not infrastructure_ok:
        report["recommendations"].append("需要配置Stream处理基础设施")
    
    # 保存报告
    report_file = "/root/.openclaw/workspace/ai_agent/results/stream_system_report.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Stream系统报告已保存至: {report_file}")
    
    # 显示改进建议
    if report["recommendations"]:
        print("\n💡 改进建议:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"{i}. {rec}")
    
    return report

if __name__ == "__main__":
    print("开始检查Stream系统状态...")
    report = generate_stream_report()
    print("\nStream系统检查完成！")