#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日投资汇报系统
每天自动发送持仓情况和次日计划
"""

import smtplib
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# 配置
REPORT_CONFIG = {
    "email": {
        "smtp_server": "smtp.qq.com",
        "smtp_port": 465,
        "from_email": "19525456@qq.com",
        "to_email": "19525456@qq.com",
        "password": "ormxhluuafwnbgei"
    },
    "positions": {
        "600460": {"name": "士兰微", "cost": 29.364, "volume": 1000},
        "000882": {"name": "华联股份", "cost": 1.779, "volume": 22600}
    },
    "total_capital": 1000000,
    "output_dir": Path.home() / ".openclaw" / "workspace" / "reports" / "daily"
}

def generate_daily_report():
    """生成每日汇报"""
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 持仓数据（模拟，实际应从 API 获取）
    positions_data = {
        "600460": {"current": 29.50, "change": 0.46},
        "000882": {"current": 1.58, "change": -11.19}
    }
    
    # 计算总盈亏
    total_cost = 0
    total_value = 0
    position_details = []
    
    for code, pos in REPORT_CONFIG["positions"].items():
        data = positions_data.get(code, {})
        current = data.get("current", pos["cost"])
        cost = pos["cost"]
        volume = pos["volume"]
        
        cost_amount = cost * volume
        value = current * volume
        profit = value - cost_amount
        profit_pct = (current - cost) / cost * 100
        
        total_cost += cost_amount
        total_value += value
        
        position_details.append({
            "code": code,
            "name": pos["name"],
            "cost": cost,
            "current": current,
            "volume": volume,
            "profit": profit,
            "profit_pct": profit_pct
        })
    
    total_profit = total_value - total_cost
    total_profit_pct = total_profit / total_cost * 100
    
    # 生成报告内容
    report = {
        "date": today,
        "total_cost": total_cost,
        "total_value": total_value,
        "total_profit": total_profit,
        "total_profit_pct": total_profit_pct,
        "positions": position_details,
        "cash": REPORT_CONFIG["total_capital"] - total_cost,
        "next_day": tomorrow
    }
    
    return report

def create_email_content(report):
    """创建邮件内容"""
    today = report["date"]
    tomorrow = report["next_day"]
    
    subject = f"📊 投资日报 - {today}"
    
    # HTML 内容
    html_content = f"""
<html>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        
        <!-- 标题 -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 24px;">📊 投资日报</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">{today}</p>
        </div>
        
        <!-- 总览 -->
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 15px 0; color: #2d3436; font-size: 18px;">💰 资产总览</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>总投入</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right;">¥{report['total_cost']:,.0f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>当前市值</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right;">¥{report['total_value']:,.0f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;"><strong>总盈亏</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right; color: {'#28a745' if report['total_profit'] > 0 else '#dc3545'};">
                        ¥{report['total_profit']:+,.0f} ({report['total_profit_pct']:+.2f}%)
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>现金保留</strong></td>
                    <td style="padding: 10px; text-align: right;">¥{report['cash']:,.0f}</td>
                </tr>
            </table>
        </div>
        
        <!-- 持仓详情 -->
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 15px 0; color: #2d3436; font-size: 18px;">📈 持仓详情</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #e9ecef;">
                    <th style="padding: 10px; text-align: left;">股票</th>
                    <th style="padding: 10px; text-align: right;">成本</th>
                    <th style="padding: 10px; text-align: right;">当前</th>
                    <th style="padding: 10px; text-align: right;">盈亏</th>
                </tr>
"""
    
    for pos in report["positions"]:
        color = '#28a745' if pos['profit'] > 0 else '#dc3545' if pos['profit'] < 0 else '#6c757d'
        html_content += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">
                        {pos['name']} ({pos['code']})<br>
                        <small style="color: #6c757d;">{pos['volume']:,}股</small>
                    </td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right;">¥{pos['cost']:.3f}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right;">¥{pos['current']:.2f}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right; color: {color};">
                        ¥{pos['profit']:+,.0f} ({pos['profit_pct']:+.2f}%)
                    </td>
                </tr>
"""
    
    html_content += f"""
            </table>
        </div>
        
        <!-- 次日计划 -->
        <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
            <h2 style="margin: 0 0 15px 0; color: #856404; font-size: 18px;">📋 次日计划 ({tomorrow})</h2>
            <ol style="margin: 0; padding-left: 20px; color: #856404;">
                <li><strong>持仓监控</strong>: 继续持有，等反弹/止盈</li>
                <li><strong>华联股份</strong>: 关注¥1.78 回本位</li>
                <li><strong>士兰微</strong>: 关注¥32.00 止盈位</li>
                <li><strong>新建仓</strong>: 观察比亚迪、茅台企稳信号</li>
                <li><strong>风控</strong>: 严格执行止损纪律</li>
            </ol>
        </div>
        
        <!-- 风险提示 -->
        <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <p style="margin: 0; color: #721c24; font-size: 14px;">
                <strong>⚠️ 风险提示:</strong> 投资有风险，入市需谨慎。本报告仅供参考，不构成投资建议。
            </p>
        </div>
        
        <!-- 底部 -->
        <div style="border-top: 2px solid #dee2e6; padding-top: 15px; margin-top: 20px; color: #6c757d; font-size: 12px; text-align: center;">
            <p style="margin: 0;">🤖 投资汇报系统自动生成</p>
            <p style="margin: 5px 0 0 0;">📧 如有疑问请联系</p>
        </div>
        
    </div>
</body>
</html>
"""
    
    # 纯文本内容
    text_content = f"""
📊 投资日报 - {today}
=====================================

💰 资产总览:
  总投入：¥{report['total_cost']:,.0f}
  当前市值：¥{report['total_value']:,.0f}
  总盈亏：¥{report['total_profit']:+,.0f} ({report['total_profit_pct']:+.2f}%)
  现金保留：¥{report['cash']:,.0f}

📈 持仓详情:
"""
    
    for pos in report["positions"]:
        status = "🟢" if pos['profit'] > 0 else "🔴" if pos['profit'] < 0 else "⚪"
        text_content += f"""
  {status} {pos['name']} ({pos['code']})
     成本：¥{pos['cost']:.3f} | 当前：¥{pos['current']:.2f}
     盈亏：¥{pos['profit']:+,.0f} ({pos['profit_pct']:+.2f}%)
"""
    
    text_content += f"""

📋 次日计划 ({tomorrow}):
  1. 持仓监控：继续持有，等反弹/止盈
  2. 华联股份：关注¥1.78 回本位
  3. 士兰微：关注¥32.00 止盈位
  4. 新建仓：观察比亚迪、茅台企稳信号
  5. 风控：严格执行止损纪律

---
🤖 投资汇报系统自动生成
"""
    
    return subject, text_content, html_content

def send_daily_email(subject, text_content, html_content):
    """发送邮件"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = REPORT_CONFIG["email"]["from_email"]
        msg["To"] = REPORT_CONFIG["email"]["to_email"]
        
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        server = smtplib.SMTP_SSL(REPORT_CONFIG["email"]["smtp_server"], REPORT_CONFIG["email"]["smtp_port"])
        server.login(REPORT_CONFIG["email"]["from_email"], REPORT_CONFIG["email"]["password"])
        server.sendmail(REPORT_CONFIG["email"]["from_email"], REPORT_CONFIG["email"]["to_email"], msg.as_string())
        server.quit()
        
        print(f"✅ 日报邮件已发送到 {REPORT_CONFIG['email']['to_email']}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
        return False

def save_report(report, text_content):
    """保存报告到文件"""
    output_dir = REPORT_CONFIG["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = output_dir / f"daily_report_{report['date']}.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    print(f"✅ 日报已保存：{filename}")
    return filename

def main():
    """主函数"""
    print("=" * 70)
    print("📊 每日投资汇报系统")
    print("=" * 70)
    
    # 生成报告
    report = generate_daily_report()
    
    # 创建邮件内容
    subject, text_content, html_content = create_email_content(report)
    
    # 发送邮件
    send_daily_email(subject, text_content, html_content)
    
    # 保存报告
    save_report(report, text_content)
    
    print("=" * 70)
    print("✅ 日报发送完成！")
    print("=" * 70)

if __name__ == "__main__":
    main()
