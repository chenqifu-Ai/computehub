#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送投资指导意见报告到邮箱
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# 配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "from_email": "19525456@qq.com",
    "to_email": "19525456@qq.com",
    "password": "xunlwhjokescbgdd"
}

today = date.today().isoformat()

# 邮件内容
subject = f"🔴 紧急投资指导意见 - {today}（市场暴跌）"

html_content = f"""
<html>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        
        <!-- 标题 -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 24px;">🔴 紧急投资指导意见</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">{today} 市场暴跌特别报告</p>
        </div>
        
        <!-- 风险等级 -->
        <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #721c24; font-size: 18px;">⚠️ 风险等级：高风险</h2>
            <p style="margin: 0; color: #721c24;">市场情绪极度恐慌，90% 股票下跌，建议采取防御策略</p>
        </div>
        
        <!-- 核心建议 -->
        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #856404; font-size: 18px;">🎯 核心建议（立即执行）</h2>
            <ol style="margin: 0; padding-left: 20px; color: #856404;">
                <li><strong>减仓</strong> - 地产、银行股减至 10% 以下</li>
                <li><strong>止损</strong> - 设置 -3% 到 -5% 止损线</li>
                <li><strong>持币</strong> - 现金比例提升至 70%</li>
                <li><strong>观望</strong> - 不要抄底，等企稳信号</li>
            </ol>
        </div>
        
        <!-- 市场数据 -->
        <div style="background: #f8f9fa; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #2d3436; font-size: 18px;">📊 市场数据</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>上涨/下跌</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #dc3545;">2 / 18 (10% 上涨)</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>建议仓位</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">20-30% 股票 / 70-80% 现金</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>止损线</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #dc3545;">-3% ~ -5%</td>
                </tr>
            </table>
        </div>
        
        <!-- 领跌股票 -->
        <div style="background: #f8d7da; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #721c24; font-size: 18px;">🔴 领跌股票</h2>
            <ul style="margin: 0; padding-left: 20px; color: #721c24;">
                <li>万科 A: -6.45%</li>
                <li>中兴通讯：-5.54%</li>
                <li>京东方 A: -4.66%</li>
                <li>浦发银行：-4.09%</li>
                <li>贵州茅台：-3.00%</li>
            </ul>
        </div>
        
        <!-- 可以持有 -->
        <div style="background: #d4edda; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #155724; font-size: 18px;">🟢 可以持有</h2>
            <ul style="margin: 0; padding-left: 20px; color: #155724;">
                <li><strong>比亚迪</strong> (+5.34%) - 新能源龙头</li>
                <li><strong>中国石油</strong> (+0.98%) - 防御性板块</li>
                <li><strong>消费龙头</strong> - 茅台、五粮液（等企稳）</li>
            </ul>
        </div>
        
        <!-- 坚决回避 -->
        <div style="background: #f8d7da; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #721c24; font-size: 18px;">❌ 坚决回避</h2>
            <ul style="margin: 0; padding-left: 20px; color: #721c24;">
                <li><strong>地产股</strong> - 万科 A 等（政策风险）</li>
                <li><strong>银行股</strong> - 浦发、工行等（坏账风险）</li>
                <li><strong>高位科技股</strong> - 估值过高</li>
            </ul>
        </div>
        
        <!-- 行动清单 -->
        <div style="background: #e7f3ff; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #004085; font-size: 18px;">📋 今日行动清单</h2>
            <ul style="margin: 0; padding-left: 20px; color: #004085;">
                <li>☐ 检查所有持仓亏损情况</li>
                <li>☐ 设置止损价位（-3% ~ -5%）</li>
                <li>☐ 减仓地产、银行股至 10% 以下</li>
                <li>☐ 现金比例提升至 70%</li>
            </ul>
        </div>
        
        <!-- 抄底时机 -->
        <div style="background: #fff3cd; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #856404; font-size: 18px;">⏰ 抄底时机（尚未出现）</h2>
            <p style="margin: 0 0 10px 0; color: #856404;">需同时满足以下条件：</p>
            <ul style="margin: 0; padding-left: 20px; color: #856404;">
                <li>❌ 成交量萎缩（恐慌盘出清）</li>
                <li>❌ 出现领涨板块（至少 3 只涨停）</li>
                <li>❌ 政策面利好（救市政策）</li>
                <li>❌ 技术指标超卖（RSI<20）</li>
            </ul>
            <p style="margin: 10px 0 0 0; font-weight: bold; color: #856404;">结论：继续观望，不要急于入场！</p>
        </div>
        
        <!-- 时间规划 -->
        <div style="background: #f8f9fa; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #2d3436; font-size: 18px;">📅 时间规划</h2>
            <ul style="margin: 0; padding-left: 20px; color: #636e72;">
                <li><strong>今日</strong>: 减仓、止损、持币</li>
                <li><strong>明日</strong>: 观察、执行止损</li>
                <li><strong>本周</strong>: 等待企稳信号</li>
                <li><strong>下周</strong>: 根据信号决定</li>
            </ul>
        </div>
        
        <!-- 风险提示 -->
        <div style="background: #f8d7da; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <h2 style="margin: 0 0 10px 0; color: #721c24; font-size: 18px;">⚠️ 风险警示</h2>
            <ul style="margin: 0; padding-left: 20px; color: #721c24;">
                <li>市场风险：短期可能继续下跌 5-10%</li>
                <li>不要借钱炒股</li>
                <li>不要满仓操作</li>
                <li>不要盲目抄底</li>
            </ul>
        </div>
        
        <!-- 底部 -->
        <div style="border-top: 2px solid #dee2e6; padding-top: 15px; margin-top: 20px; color: #636e72; font-size: 12px;">
            <p style="margin: 0;">📊 报告发布：金融智能体分析中心</p>
            <p style="margin: 5px 0 0 0;">📧 联系方式：19525456@qq.com</p>
            <p style="margin: 5px 0 0 0; font-style: italic;">⚠️ 本报告仅供参考，不构成投资建议。投资有风险，决策需谨慎。</p>
        </div>
        
    </div>
</body>
</html>
"""

text_content = f"""
🔴 紧急投资指导意见 - {today}
=====================================

⚠️ 风险等级：高风险

市场情绪极度恐慌，90% 股票下跌，建议采取防御策略

🎯 核心建议（立即执行）:
1. 减仓 - 地产、银行股减至 10% 以下
2. 止损 - 设置 -3% 到 -5% 止损线
3. 持币 - 现金比例提升至 70%
4. 观望 - 不要抄底，等企稳信号

📊 市场数据:
- 上涨/下跌：2 / 18 (10% 上涨)
- 建议仓位：20-30% 股票 / 70-80% 现金
- 止损线：-3% ~ -5%

🔴 领跌股票:
- 万科 A: -6.45%
- 中兴通讯：-5.54%
- 京东方 A: -4.66%
- 浦发银行：-4.09%
- 贵州茅台：-3.00%

🟢 可以持有:
- 比亚迪 (+5.34%) - 新能源龙头
- 中国石油 (+0.98%) - 防御性板块
- 消费龙头 - 茅台、五粮液（等企稳）

❌ 坚决回避:
- 地产股 - 万科 A 等（政策风险）
- 银行股 - 浦发、工行等（坏账风险）
- 高位科技股 - 估值过高

📋 今日行动清单:
☐ 检查所有持仓亏损情况
☐ 设置止损价位（-3% ~ -5%）
☐ 减仓地产、银行股至 10% 以下
☐ 现金比例提升至 70%

⏰ 抄底时机（尚未出现）:
需同时满足：成交量萎缩 + 领涨板块 + 政策利好 + 技术超卖
结论：继续观望，不要急于入场！

📅 时间规划:
- 今日：减仓、止损、持币
- 明日：观察、执行止损
- 本周：等待企稳信号
- 下周：根据信号决定

⚠️ 风险警示:
- 市场风险：短期可能继续下跌 5-10%
- 不要借钱炒股
- 不要满仓操作
- 不要盲目抄底

---
📊 报告发布：金融智能体分析中心
📧 联系方式：19525456@qq.com
⚠️ 本报告仅供参考，不构成投资建议。投资有风险，决策需谨慎。
"""

try:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_CONFIG["from_email"]
    msg["To"] = EMAIL_CONFIG["to_email"]
    
    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    
    server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
    server.login(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["password"])
    server.sendmail(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["to_email"], msg.as_string())
    server.quit()
    
    print(f"✅ 投资指导意见已发送到 {EMAIL_CONFIG['to_email']}")
    print(f"   主题：{subject}")
    print(f"   风险等级：高风险")
    print(f"   发送时间：{today} 14:45")
    
except Exception as e:
    print(f"❌ 邮件发送失败：{e}")
    import traceback
    traceback.print_exc()
