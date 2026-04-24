#!/usr/bin/env python3
"""
公司运作状态检查脚本
检查系统状态、任务执行、股票监控、专家学习等
"""

import json
import subprocess
import os
from datetime import datetime

def run_command(cmd):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def check_openclaw_status():
    """检查OpenClaw系统状态"""
    print("=== OpenClaw系统状态检查 ===")
    
    # 检查gateway状态
    stdout, stderr, code = run_command("openclaw gateway status")
    if code == 0:
        print("✅ Gateway服务: 运行正常")
        print(f"状态信息: {stdout[:100]}...")
    else:
        print("❌ Gateway服务: 异常")
        print(f"错误: {stderr}")
    
    # 检查cron任务
    stdout, stderr, code = run_command("openclaw cron list")
    if code == 0:
        print("\n✅ Cron任务: 可访问")
        # 解析cron任务数量
        if stdout:
            lines = stdout.split('\n')
            enabled_tasks = [line for line in lines if 'enabled: true' in line.lower()]
            print(f"已启用任务数: {len(enabled_tasks)}")
    else:
        print("\n❌ Cron任务: 检查失败")
    
    return code == 0

def check_stock_monitoring():
    """检查股票监控系统"""
    print("\n=== 股票监控系统检查 ===")
    
    # 检查股票监控文件
    stock_files = [
        "/root/.openclaw/workspace/ai_agent/code/stock_monitor.py",
        "/root/.openclaw/workspace/ai_agent/code/hualian_monitor.py",
        "/root/.openclaw/workspace/ai_agent/code/cosco_monitor.py"
    ]
    
    for file_path in stock_files:
        if os.path.exists(file_path):
            print(f"✅ {os.path.basename(file_path)}: 存在")
        else:
            print(f"❌ {os.path.basename(file_path)}: 缺失")
    
    # 检查定时任务
    stdout, stderr, code = run_command("crontab -l | grep -i stock")
    if code == 0 and stdout:
        print("✅ 股票监控定时任务: 已配置")
        print(f"任务数量: {len(stdout.split('\\n'))}")
    else:
        print("⚠️ 股票监控定时任务: 未找到或未配置")
    
    return True

def check_expert_learning():
    """检查专家学习任务"""
    print("\n=== 专家学习系统检查 ===")
    
    # 检查专家技能目录
    expert_dirs = [
        "ceo-advisor", "finance-advisor", "finance-expert", 
        "hr-expert", "legal-advisor", "marketing-expert", "network-expert"
    ]
    
    base_path = "/root/.openclaw/workspace/skills"
    active_experts = []
    
    for expert in expert_dirs:
        expert_path = os.path.join(base_path, expert)
        if os.path.exists(expert_path):
            active_experts.append(expert)
            print(f"✅ {expert}: 技能目录存在")
            
            # 检查references目录
            ref_path = os.path.join(expert_path, "references")
            if os.path.exists(ref_path):
                ref_files = [f for f in os.listdir(ref_path) if f.endswith('.md')]
                print(f"   学习文件数: {len(ref_files)}")
        else:
            print(f"❌ {expert}: 技能目录缺失")
    
    print(f"\n活跃专家数量: {len(active_experts)}")
    return len(active_experts) > 0

def check_email_system():
    """检查邮件命令系统"""
    print("\n=== 邮件命令系统检查 ===")
    
    # 检查邮件配置文件
    config_files = [
        "/root/.openclaw/workspace/config/email.conf",
        "/root/.openclaw/workspace/config/163_email.conf"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ {os.path.basename(config_file)}: 存在")
        else:
            print(f"❌ {os.path.basename(config_file)}: 缺失")
    
    # 检查邮件检查脚本
    script_path = "/root/.openclaw/workspace/scripts/check-email-commands.py"
    if os.path.exists(script_path):
        print("✅ 邮件检查脚本: 存在")
    else:
        print("❌ 邮件检查脚本: 缺失")
    
    return True

def generate_report():
    """生成综合报告"""
    print("\n" + "="*50)
    print("📊 公司运作状态综合报告")
    print("="*50)
    
    # 执行各项检查
    openclaw_ok = check_openclaw_status()
    stock_ok = check_stock_monitoring()
    expert_ok = check_expert_learning()
    email_ok = check_email_system()
    
    # 总体评估
    print("\n=== 总体评估 ===")
    if all([openclaw_ok, stock_ok, expert_ok, email_ok]):
        print("✅ 所有系统运行正常")
        status = "良好"
    else:
        print("⚠️ 部分系统需要关注")
        status = "需关注"
    
    # 生成时间戳
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = {
        "timestamp": current_time,
        "overall_status": status,
        "systems": {
            "openclaw": openclaw_ok,
            "stock_monitoring": stock_ok,
            "expert_learning": expert_ok,
            "email_commands": email_ok
        }
    }
    
    # 保存报告
    report_file = "/root/.openclaw/workspace/ai_agent/results/company_status_report.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 报告已保存至: {report_file}")
    return report

if __name__ == "__main__":
    print("开始检查公司运作状态...")
    report = generate_report()
    print("\n检查完成！")