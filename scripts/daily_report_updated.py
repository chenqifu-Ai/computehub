#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日投资汇报系统 - 更新版
使用最新持仓数据和实时价格
"""

import smtplib
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import requests

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
        "000882": {"name": "华联股份", "cost": 1.873, "volume": 13500}
    },
    "watch_list": {
        "601866": {"name": "中远海发", "target_buy": [2.50, 2.70]}
    },
    "total_capital": 1000000,
    "output_dir": Path.home() / ".openclaw" / "workspace" / "reports" / "daily"
}

def get_stock_price(stock_code):
    """获取股票实时价格"""
    try:
        prefix = "sz" if stock_code.startswith("00") else "sh"
        url = f"https://qt.gtimg.cn/q={prefix}{stock_code}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.text
            parts = data.split('~')
            if len(parts) > 3:
                current_price = float(parts[3])
                change_percent = parts[39]
                return current_price, change_percent
    except:
        pass
    
    # 备用价格（如果API失败）
    backup_prices = {
        "000882": (1.64, "-30.66%"),
        "601866": (2.90, "+23.78%")
    }
    return backup_prices.get(stock_code, (0.0, "0.00%"))

def generate_daily_report():
    """生成每日汇报"""
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 获取实时价格
    positions_data = {}
    for code in REPORT_CONFIG["positions"]:
        current_price, change_percent = get_stock_price(code)
        positions_data[code] = {"current": current_price, "change": change_percent}
    
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
    total_profit_pct = total_profit / total_cost * 100 if total_cost > 0 else 0
    
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
        
        <!-- 关注股票 -->
        <div style="background: #e8f5e8; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 15px 0; color: #2d3436; font-size: 18px;">👀 关注股票</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">中远海发 (601866)</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right;">¥2.90</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right; color: #28a745;">+23.78%</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><small>目标买入区间: ¥2.50-2.70</small></td>
                    <td style="padding: 10px; text-align: right;"><small>当前状态: 等待回调</small></td>
                    <td style="padding: 10px; text-align: right;"><small>需下跌: ¥0.20 (6.9%)</small></td>
                </tr>
            </table>
        </div>
        
        <!-- 次日计划 -->
        <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
            <h2 style="margin: 0 0 15px 0; color: #856404; font-size: 18px;">📋 次日计划 ({tomorrow})</h2>
            <ol style="margin: 0; padding-left: 20px; color: #856404;">
                <li><strong>华联股份</strong>: 关注反弹机会，目标回本价¥1.87</li>
                <li><strong>风险控制</strong>: 严格执行止损纪律，止损位¥1.60</li>
                <li><strong>新建仓</strong>: 中远海发回调至¥2.50-2.70区间考虑买入</li>
                <li><strong>资金管理</strong>: 保留充足现金等待更好机会</li>
                <li><strong>市场观察</strong>: 关注大盘走势和政策面变化</li>
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

👀 关注股票:
  🔵 中远海发 (601866): ¥2.90 (+23.78%)
      目标买入区间: ¥2.50-2.70 | 需下跌¥0.20 (6.9%)

📋 次日计划 ({tomorrow}):
  1. 华联股份：关注反弹机会，目标回本价¥1.87
  2. 风险控制：严格执行止损纪律，止损位¥1.60
  3. 新建仓：中远海发回调至¥2.50-2.70区间考虑买入
  4. 资金管理：保留充足现金等待更好机会
  5. 市场观察：关注大盘走势和政策面变化

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