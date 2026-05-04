#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表盘式项目状态监控系统
用表盘方式展现各项目运行状态
"""

import os
import time
import subprocess
from datetime import datetime

def get_stock_status():
    """获取股票状态"""
    try:
        result = subprocess.run([
            "python3", "/root/.openclaw/workspace/ai_agent/code/stock_monitor.py"
        ], capture_output=True, text=True, timeout=10)
        
        if "无预警" in result.stdout:
            return "🟢 正常", "无预警"
        else:
            return "🔴 异常", "有预警"
    except:
        return "⚫ 离线", "监控失败"

def get_expert_status():
    """获取专家系统状态"""
    log_dir = "/root/.openclaw/workspace/expert_work_logs"
    
    if not os.path.exists(log_dir):
        return "⚫ 离线", "日志目录不存在"
    
    # 检查最近的工作报告
    report_files = [f for f in os.listdir(log_dir) if "report" in f]
    
    if len(report_files) > 0:
        # 检查最新报告的时间
        latest_report = max(report_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)))
        report_time = os.path.getmtime(os.path.join(log_dir, latest_report))
        
        if time.time() - report_time < 3600:  # 1小时内
            return "🟢 正常", f"{len(report_files)}个报告"
        else:
            return "🟡 警告", "报告较旧"
    else:
        return "🔴 异常", "无工作报告"

def get_stream_status():
    """获取Stream守护进程状态"""
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        
        if "stream_daemon.py" in result.stdout:
            return "🟢 运行中", "后台守护"
        else:
            return "🔴 停止", "未运行"
    except:
        return "⚫ 未知", "状态检查失败"

def get_mail_status():
    """获取邮件系统状态"""
    conf_file = "/root/.openclaw/workspace/config/email.conf"
    
    if os.path.exists(conf_file):
        return "🟢 就绪", "配置正常"
    else:
        return "🔴 异常", "配置缺失"

def create_dashboard():
    """创建表盘式监控面板"""
    print("\n" + "="*60)
    print("🎛️  证券公司 - 表盘式状态监控")
    print("="*60)
    
    # 获取各系统状态
    stock_status, stock_detail = get_stock_status()
    expert_status, expert_detail = get_expert_status()
    stream_status, stream_detail = get_stream_status()
    mail_status, mail_detail = get_mail_status()
    
    # 表盘显示
    print(f"\n📊 股票监控系统: {stock_status}")
    print(f"   📈 状态: {stock_detail}")
    
    print(f"\n👥 专家工作系统: {expert_status}")
    print(f"   💼 状态: {expert_detail}")
    
    print(f"\n🔄 Stream守护进程: {stream_status}")
    print(f"   ⚙️  状态: {stream_detail}")
    
    print(f"\n📧 邮件通知系统: {mail_status}")
    print(f"   ✉️  状态: {mail_detail}")
    
    # 总体状态
    overall_status = "🟢 正常"
    if "🔴" in stock_status + expert_status + stream_status + mail_status:
        overall_status = "🔴 异常"
    elif "🟡" in stock_status + expert_status + stream_status + mail_status:
        overall_status = "🟡 警告"
    
    print(f"\n" + "="*60)
    print(f"🎯 总体状态: {overall_status}")
    print(f"⏰ 更新时间: {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)
    
    # 表盘指示器
    print("\n🎛️ 表盘指示器:")
    print("🟢 正常 | 🟡 警告 | 🔴 异常 | ⚫ 离线")
    
    return {
        "stock": {"status": stock_status, "detail": stock_detail},
        "expert": {"status": expert_status, "detail": expert_detail},
        "stream": {"status": stream_status, "detail": stream_detail},
        "mail": {"status": mail_status, "detail": mail_detail},
        "overall": overall_status,
        "timestamp": datetime.now().isoformat()
    }

def save_dashboard_report(dashboard_data):
    """保存表盘报告"""
    report_dir = "/root/.openclaw/workspace/ai_agent/results"
    os.makedirs(report_dir, exist_ok=True)
    
    import json
    report_file = os.path.join(report_dir, f"dashboard_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
    
    return report_file

if __name__ == "__main__":
    # 创建表盘监控
    dashboard_data = create_dashboard()
    
    # 保存报告
    report_file = save_dashboard_report(dashboard_data)
    print(f"\n📊 表盘报告已保存: {report_file}")
    
    print("\n🎯 表盘监控系统就绪！")