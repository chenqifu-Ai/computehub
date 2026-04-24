#!/usr/bin/env python3
"""
金融专家 - 持续信息收集系统
监控持仓股票、市场动态、学习金融知识
"""

import requests
import json
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from email.header import Header

# 配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
EMAIL_USER = "19525456@qq.com"
EMAIL_PASS = "xunlwhjokescbgdd"

# 持仓股票
HOLDINGS = [
    {"name": "士兰微", "code": "600460", "shares": 1000, "cost": 29.364, "stop_loss": 26.00},
    {"name": "华联股份", "code": "000882", "shares": 17600, "cost": 1.779, "stop_loss": 1.50},
]

# 关注股票（潜在标的）
WATCH_LIST = ["000001", "600519", "002594", "300750", "601318"]

def get_stock_data(code):
    """获取股票实时数据"""
    prefix = "sh" if code.startswith('6') else "sz"
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        resp = requests.get(url, timeout=5)
        parts = resp.text.split('~')
        if len(parts) > 40:
            return {
                "code": code,
                "name": parts[1],
                "price": float(parts[3]),
                "change_pct": parts[31],
                "volume": parts[36],
                "high": parts[33],
                "low": parts[34],
                "open": parts[32],
                "last_close": parts[4],
            }
    except Exception as e:
        print(f"获取{code}数据失败: {e}")
    return None

def analyze_holding(holding, current_data):
    """分析持仓股票"""
    if not current_data:
        return None
    
    price = current_data['price']
    cost = holding['cost']
    stop_loss = holding['stop_loss']
    shares = holding['shares']
    
    profit_pct = (price - cost) / cost * 100
    profit_amt = (price - cost) * shares
    
    # 判断信号
    signals = []
    if price <= stop_loss:
        signals.append("🔴 止损信号：跌破止损位！")
    elif price <= stop_loss * 1.02:
        signals.append("⚠️ 接近止损：距止损位不足2%")
    
    if profit_pct >= 10:
        signals.append("📈 止盈信号：盈利超过10%")
    elif profit_pct >= 5:
        signals.append("📊 减仓信号：盈利超过5%")
    
    return {
        "name": holding['name'],
        "code": holding['code'],
        "shares": shares,
        "cost": cost,
        "current_price": price,
        "change_pct": current_data['change_pct'],
        "profit_pct": round(profit_pct, 2),
        "profit_amt": round(profit_amt, 2),
        "signals": signals,
        "high": current_data['high'],
        "low": current_data['low'],
    }

def collect_market_news():
    """收集市场新闻（简化版，实际可接入新闻API）"""
    # 这里可以接入新浪财经、东方财富等新闻API
    news_items = [
        {"title": "A股市场早盘分析", "source": "internal"},
        {"title": "半导体板块动态", "source": "internal"},
        {"title": "零售商业板块动态", "source": "internal"},
    ]
    return news_items

def generate_report(holdings_analysis, watch_data):
    """生成分析报告"""
    report = f"""# 金融市场日报
**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 📊 持仓分析

"""
    total_profit = 0
    for h in holdings_analysis:
        if h:
            signal_str = "\n".join([f"  - {s}" for s in h['signals']]) if h['signals'] else "  - 无特殊信号"
            report += f"""### {h['name']} ({h['code']})
- 持仓: {h['shares']}股
- 成本价: ¥{h['cost']}
- 现价: ¥{h['current_price']}
- 涨跌幅: {h['change_pct']}%
- 浮盈亏: {h['profit_pct']}% (¥{h['profit_amt']})
- 今日最高: ¥{h['high']}
- 今日最低: ¥{h['low']}
- 信号:
{signal_str}

"""
            total_profit += h['profit_amt']
    
    report += f"""## 📈 关注股票

"""
    for w in watch_data:
        if w:
            report += f"- {w['name']} ({w['code']}): ¥{w['price']} ({w['change_pct']}%)\n"
    
    report += f"""
## 💰 总体盈亏

- 总浮动盈亏: ¥{total_profit:,.2f}

## 📚 今日金融知识要点

1. **止损纪律**: 严格执行止损是风险管理的核心
2. **仓位管理**: 单只股票不超过总资金的30%
3. **趋势判断**: 关注量价关系和技术指标

## ⚠️ 风险提示

- 市场有风险，投资需谨慎
- 本报告仅供参考，不构成投资建议

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*金融专家智能体*
"""
    return report

def send_email(subject, content):
    """发送邮件"""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg['Subject'] = Header(subject, 'utf-8')
    msg.attach(MIMEText(content, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        server.quit()
        print(f"邮件发送成功: {subject}")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

def main():
    print("=== 金融专家信息收集系统 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 收集持仓数据
    print("\n[1/4] 收集持仓数据...")
    holdings_analysis = []
    for h in HOLDINGS:
        data = get_stock_data(h['code'])
        analysis = analyze_holding(h, data)
        holdings_analysis.append(analysis)
        if analysis:
            print(f"  {analysis['name']}: ¥{analysis['current_price']} ({analysis['profit_pct']}%)")
    
    # 2. 收集关注股票数据
    print("\n[2/4] 收集关注股票数据...")
    watch_data = []
    for code in WATCH_LIST:
        data = get_stock_data(code)
        if data:
            watch_data.append(data)
            print(f"  {data['name']}: ¥{data['price']}")
    
    # 3. 生成报告
    print("\n[3/4] 生成分析报告...")
    report = generate_report(holdings_analysis, watch_data)
    
    # 保存报告
    report_path = f"/root/.openclaw/workspace/reports/finance_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  报告已保存: {report_path}")
    
    # 4. 发送邮件
    print("\n[4/4] 发送邮件报告...")
    send_email(f"【金融专家】市场日报 {datetime.now().strftime('%Y-%m-%d %H:%M')}", report)
    
    # 检查止损信号
    print("\n=== 信号检测 ===")
    for h in holdings_analysis:
        if h and h['signals']:
            print(f"🔴 {h['name']}: {', '.join(h['signals'])}")
    
    print("\n=== 完成 ===")

if __name__ == "__main__":
    main()