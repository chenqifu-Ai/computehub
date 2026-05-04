#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百炼 API Token 用量统计脚本
记录每次 API 调用的 tokens 消耗，生成日报发送到邮箱
"""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置
TRACKING_FILE = Path.home() / ".openclaw" / "workspace" / "token-usage.json"
DAILY_REPORT_DIR = Path.home() / ".openclaw" / "workspace" / "reports"
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "from_email": "19525456@qq.com",
    "to_email": "19525456@qq.com",
    "password": "ormxhluuafwnbgei"  # 2026-04-05更新的邮箱授权码
}

def load_usage_data():
    """加载用量数据"""
    if TRACKING_FILE.exists():
        try:
            with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 读取用量数据失败: {e}")
            return {"daily": {}, "total": {"input": 0, "output": 0, "total": 0}}
    else:
        return {"daily": {}, "total": {"input": 0, "output": 0, "total": 0}}

def generate_daily_report(target_date=None):
    """生成日报"""
    if target_date is None:
        target_date = date.today().isoformat()
    
    data = load_usage_data()
    daily_data = data.get("daily", {}).get(target_date)
    
    if not daily_data:
        print(f"❌ 没有找到指定日期 {target_date} 的数据")
        return None
    
    report = f"📊 百炼 API Token 用量日报 - {target_date}\n\n"
    report += "=" * 50 + "\n\n"
    
    # 总体统计
    report += "🎯 总体统计:\n"
    report += f"   • 输入 tokens: {daily_data.get('input', 0):,}\n"
    report += f"   • 输出 tokens: {daily_data.get('output', 0):,}\n"
    report += f"   • 总计 tokens: {daily_data.get('total', 0):,}\n"
    report += f"   • API 调用次数: {daily_data.get('calls', 0):,}\n\n"
    
    # 任务详情
    tasks = daily_data.get("tasks", {})
    if tasks:
        report += "📋 任务详情:\n"
        for task_name, task_data in tasks.items():
            report += f"   • {task_name}: {task_data.get('total', 0):,} tokens ({task_data.get('calls', 0)}次调用)\n"
        report += "\n"
    
    # 累计统计
    total_data = data.get("total", {})
    report += "📈 累计统计:\n"
    report += f"   • 总输入 tokens: {total_data.get('input', 0):,}\n"
    report += f"   • 总输出 tokens: {total_data.get('output', 0):,}\n"
    report += f"   • 总计 tokens: {total_data.get('total', 0):,}\n\n"
    
    # 成本估算 (假设 $0.002/1K tokens)
    total_tokens = daily_data.get('total', 0)
    cost_usd = (total_tokens / 1000) * 0.002
    cost_cny = cost_usd * 7.0  # 假设汇率 7.0
    
    report += "💰 成本估算:\n"
    report += f"   • 当日成本: ${cost_usd:.4f} (约 ¥{cost_cny:.2f})\n"
    report += f"   • 平均每次调用: {total_tokens/daily_data.get('calls', 1):.0f} tokens\n\n"
    
    report += "⏰ 报告生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n"
    
    return report

def send_email(subject, content):
    """发送邮件"""
    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['from_email']
        msg['To'] = EMAIL_CONFIG['to_email']
        msg['Subject'] = subject
        
        # 添加文本内容
        msg.attach(MIMEText(content, 'plain', 'utf-8'))
        
        # 连接SMTP服务器发送
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['from_email'], EMAIL_CONFIG['password'])
            server.send_message(msg)
        
        print("✅ 邮件发送成功")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        # 发送日报模式
        target_date = date.today().isoformat()
        report = generate_daily_report(target_date)
        
        if report:
            subject = f"百炼 API Token 用量日报 - {target_date}"
            
            print("📧 正在发送 Token 用量日报...")
            print(report)
            
            if send_email(subject, report):
                # 保存报告文件
                os.makedirs(DAILY_REPORT_DIR, exist_ok=True)
                report_file = DAILY_REPORT_DIR / f"token_usage_report_{target_date}.txt"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"📁 报告已保存: {report_file}")
        else:
            # 没有今日数据，发送空报告说明
            empty_report = f"📊 百炼 API Token 用量日报 - {target_date}\n\n"
            empty_report += "=" * 50 + "\n\n"
            empty_report += "ℹ️  今日暂无 API Token 使用数据\n\n"
            empty_report += "可能原因:\n"
            empty_report += "• 今日未使用百炼 API\n"
            empty_report += "• Token 统计系统暂未记录\n\n"
            empty_report += "⏰ 报告生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n"
            
            subject = f"百炼 API Token 用量日报 - {target_date} (无数据)"
            
            print("📧 发送空数据报告...")
            print(empty_report)
            
            if send_email(subject, empty_report):
                report_file = DAILY_REPORT_DIR / f"token_usage_report_{target_date}_empty.txt"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(empty_report)
                print(f"📁 空报告已保存: {report_file}")
    
    elif len(sys.argv) > 1 and sys.argv[1] == "view":
        # 查看模式
        target_date = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()
        report = generate_daily_report(target_date)
        if report:
            print(report)
        else:
            print(f"❌ 没有找到日期 {target_date} 的数据")
    
    else:
        # 默认显示帮助
        print("Usage:")
        print("  python3 token-usage-tracker.py send    # 发送今日日报")
        print("  python3 token-usage-tracker.py view    # 查看今日数据")
        print("  python3 token-usage-tracker.py view YYYY-MM-DD  # 查看指定日期数据")

if __name__ == "__main__":
    main()