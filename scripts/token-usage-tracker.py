#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百炼 API Token 用量统计脚本
记录每次 API 调用的 tokens 消耗，生成日报发送到邮箱
"""

from scripts.email_utils import send_email_safe
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置
TRACKING_FILE = Path.home() / ".openclaw" / "workspace" / "ai_agent" / "results" / "token_usage.jsonl"
DAILY_REPORT_DIR = Path.home() / ".openclaw" / "workspace" / "reports"
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "from_email": "19525456@qq.com",
    "to_email": "19525456@qq.com",
    "password": "ormxhluuafwnbgei"  # 2026-04-05更新的邮箱授权码
}

def load_usage_data():
    """从 JSONL 文件加载用量数据"""
    daily = {}
    total = {"input": 0, "output": 0, "total": 0, "calls": 0}
    
    if TRACKING_FILE.exists():
        try:
            for line in open(TRACKING_FILE, 'r', encoding='utf-8'):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    day = entry.get('time', '')[:10]
                    if not day:
                        continue
                    
                    if day not in daily:
                        daily[day] = {"input": 0, "output": 0, "total": 0, "calls": 0}
                    
                    inp = entry.get('prompt_tokens', 0)
                    out = entry.get('completion_tokens', 0)
                    tot = entry.get('total_tokens', 0)
                    
                    daily[day]['input'] += inp
                    daily[day]['output'] += out
                    daily[day]['total'] += tot
                    daily[day]['calls'] += 1
                    
                    total['input'] += inp
                    total['output'] += out
                    total['total'] += tot
                    total['calls'] += 1
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"❌ 读取用量数据失败: {e}")
            return None
    
    return {"daily": daily, "total": total}

def generate_daily_report(target_date=None, show_latest=False):
    """生成日报"""
    if target_date is None:
        target_date = date.today().isoformat()
    
    data = load_usage_data()
    if data is None:
        return None
    
    daily_data = data.get("daily", {}).get(target_date)
    
    if not daily_data:
        if show_latest:
            # 发送最近有数据的日期
            daily = data.get("daily", {})
            if daily:
                latest = sorted(daily.keys(), reverse=True)[0]
                daily_data = daily[latest]
                target_date = latest
            else:
                return None
    
    report = f"📊 百炼 API Token 用量日报 - {target_date}\n\n"
    report += "=" * 50 + "\n\n"
    
    report += "🎯 总体统计:\n"
    report += f"   • 输入 tokens: {daily_data.get('input', 0):,}\n"
    report += f"   • 输出 tokens: {daily_data.get('output', 0):,}\n"
    report += f"   • 总计 tokens: {daily_data.get('total', 0):,}\n"
    report += f"   • API 调用次数: {daily_data.get('calls', 0):,}\n\n"
    
    # 成本估算 (阿里云百炼: qwen-plus ¥0.008/1K tokens)
    total_tokens = daily_data.get('total', 0)
    cost_cny = total_tokens * 0.000008  # 估算 ¥0.008/1K tokens
    
    report += "💰 成本估算:\n"
    report += f"   • 当日成本: ¥{cost_cny:.4f}\n"
    report += f"   • 平均每次调用: {total_tokens/daily_data.get('calls', 1):.0f} tokens\n\n"
    
    report += "📈 累计统计:\n"
    report += f"   • 总输入 tokens: {data['total']['input']:,}\n"
    report += f"   • 总输出 tokens: {data['total']['output']:,}\n"
    report += f"   • 总计 tokens: {data['total']['total']:,}\n"
    report += f"   • 总调用次数: {data['total']['calls']:,}\n\n"
    
    report += "📅 最近记录:\n"
    for d in sorted(data['daily'].keys(), reverse=True)[:5]:
        info = data['daily'][d]
        mark = " ◀ 今天" if d == target_date else ""
        report += f"   • {d}: {info['total']:,} tokens ({info['calls']}次) - 输入 {info['input']} / 输出 {info['output']}{mark}\n"
    
    report += f"\n⏰ 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return report

def send_email(subject, content):
    """发送邮件"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['from_email']
        msg['To'] = EMAIL_CONFIG['to_email']
        msg['Subject'] = subject
        
        # 添加文本内容
        msg.attach(MIMEText(content, 'plain', 'utf-8'))
        
        # 连接SMTP服务器发送
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=30) as server:
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
        report = generate_daily_report(target_date, show_latest=True)
        
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
            # 没有数据，发送空报告说明
            empty_report = f"📊 百炼 API Token 用量日报 - {target_date}\n\n"
            empty_report += "ℹ️ 今日暂无 API Token 使用数据\n\n"
            empty_report += "可能原因: 今日未使用 API 或统计系统未记录\n\n"
            empty_report += f"⏰ 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
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


# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
