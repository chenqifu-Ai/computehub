#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
早间投资汇报系统
每天早上 8:30 发送隔夜信息和今日计划
"""

from scripts.email_utils import send_email_safe
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "from_email": "19525456@qq.com",
    "to_email": "19525456@qq.com",
    "password": "xunlwhjokescbgdd"
}

def generate_morning_report():
    """生成早间汇报"""
    today = datetime.now().strftime('%Y-%m-%d')
    weekday = datetime.now().strftime('%A')
    
    subject = f"☀️ 早间投资汇报 - {today}"
    
    # 邮件内容
    html_content = f"""
<html>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        
        <!-- 标题 -->
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 24px;">☀️ 早间投资汇报</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">{today} {weekday}</p>
        </div>
        
        <!-- 隔夜信息 -->
        <div style="background: #e7f3ff; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #0984e3;">
            <h2 style="margin: 0 0 15px 0; color: #004085; font-size: 18px;">🌙 隔夜信息汇总</h2>
            <ul style="margin: 0; padding-left: 20px; color: #004085;">
                <li><strong>美股表现</strong>: 待更新（盘后查看）</li>
                <li><strong>中概股</strong>: 待更新（盘后查看）</li>
                <li><strong>A50 期货</strong>: 待更新（盘前查看）</li>
                <li><strong>汇率</strong>: 美元/人民币待更新</li>
                <li><strong>大宗商品</strong>: 原油、黄金待更新</li>
            </ul>
            <p style="margin: 15px 0 0 0; color: #004085; font-size: 14px;">
                💡 <strong>提示:</strong> 隔夜信息将在 8:30 前更新完毕
            </p>
        </div>
        
        <!-- 持仓状态 -->
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 15px 0; color: #2d3436; font-size: 18px;">📊 持仓状态</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #e9ecef;">
                    <th style="padding: 10px; text-align: left;">股票</th>
                    <th style="padding: 10px; text-align: right;">成本</th>
                    <th style="padding: 10px; text-align: right;">昨日收盘</th>
                    <th style="padding: 10px; text-align: right;">盈亏</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">
                        士兰微 (600460)<br>
                        <small style="color: #6c757d;">1,000 股</small>
                    </td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right;">¥29.364</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right;">¥29.50*</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right; color: #28a745;">
                        +¥136 (+0.46%)
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">
                        华联股份 (000882)<br>
                        <small style="color: #6c757d;">22,600 股</small>
                    </td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right;">¥1.779</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right;">¥1.58</td>
                    <td style="padding: 10px; border-bottom: 1px solid #dee2e6; text-align: right; color: #dc3545;">
                        -¥4,497 (-11.2%)
                    </td>
                </tr>
            </table>
            <p style="margin: 10px 0 0 0; font-size: 12px; color: #6c757d;">*注：士兰微价格为预估</p>
        </div>
        
        <!-- 今日计划 -->
        <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
            <h2 style="margin: 0 0 15px 0; color: #856404; font-size: 18px;">📋 今日交易计划</h2>
            <ol style="margin: 0; padding-left: 20px; color: #856404;">
                <li><strong>集合竞价 (9:15-9:25)</strong>: 观察持仓股开盘情况</li>
                <li><strong>开盘 (9:30)</strong>: 关注华联股份是否反弹</li>
                <li><strong>上午</strong>: 监控价格，等关键位通知</li>
                <li><strong>下午</strong>: 评估是否新建仓（比亚迪/茅台）</li>
                <li><strong>收盘 (15:00)</strong>: 记录收盘价，计算盈亏</li>
            </ol>
        </div>
        
        <!-- 重点关注 -->
        <div style="background: #d4edda; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #28a745;">
            <h2 style="margin: 0 0 15px 0; color: #155724; font-size: 18px;">🎯 今日重点关注</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #c3e6cb;"><strong>士兰微</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #c3e6cb;">关注¥32.00 止盈位</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #c3e6cb;"><strong>华联股份</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #c3e6cb;">关注¥1.78 回本位</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>新建仓</strong></td>
                    <td style="padding: 10px;">观察比亚迪、茅台企稳信号</td>
                </tr>
            </table>
        </div>
        
        <!-- 风控提醒 -->
        <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <p style="margin: 0; color: #721c24; font-size: 14px;">
                <strong>⚠️ 风控提醒:</strong>
                <br>- 士兰微止损：¥26.00
                <br>- 华联股份止损：¥1.40
                <br>- 严格执行止损纪律，不抱侥幸心理
            </p>
        </div>
        
        <!-- 底部 -->
        <div style="border-top: 2px solid #dee2e6; padding-top: 15px; margin-top: 20px; color: #6c757d; font-size: 12px; text-align: center;">
            <p style="margin: 0;">🤖 早间投资汇报系统自动生成</p>
            <p style="margin: 5px 0 0 0;">📧 每日 8:30 发送 · 晚间 20:00 发送</p>
        </div>
        
    </div>
</body>
</html>
"""
    
    # 纯文本内容
    text_content = f"""
☀️ 早间投资汇报 - {today} {weekday}
=====================================

🌙 隔夜信息汇总:
  - 美股表现：待更新
  - 中概股：待更新
  - A50 期货：待更新
  - 汇率：待更新
  - 大宗商品：待更新

📊 持仓状态:
  士兰微 (600460): ¥29.50* (+0.46%) 🟢
  华联股份 (000882): ¥1.58 (-11.2%) 🟡

📋 今日交易计划:
  1. 集合竞价 (9:15-9:25): 观察开盘
  2. 开盘 (9:30): 关注华联反弹
  3. 上午：监控价格
  4. 下午：评估新建仓
  5. 收盘 (15:00): 记录收盘价

🎯 今日重点关注:
  - 士兰微：关注¥32.00 止盈位
  - 华联股份：关注¥1.78 回本位
  - 新建仓：观察比亚迪、茅台

⚠️ 风控提醒:
  - 士兰微止损：¥26.00
  - 华联股份止损：¥1.40
  - 严格执行止损纪律

---
🤖 早间投资汇报系统自动生成
📧 每日 8:30 发送
"""
    
    return subject, text_content, html_content

def send_morning_email(subject, text_content, html_content):
    """发送邮件"""
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
        
        print(f"✅ 早间汇报已发送到 {EMAIL_CONFIG['to_email']}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
        return False

def main():
    """主函数"""
    print("=" * 70)
    print("☀️ 早间投资汇报系统")
    print("=" * 70)
    
    # 生成报告
    subject, text_content, html_content = generate_morning_report()
    
    # 发送邮件
    send_morning_email(subject, text_content, html_content)
    
    print("=" * 70)
    print("✅ 早间汇报发送完成！")
    print("=" * 70)

if __name__ == "__main__":
    main()


# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
