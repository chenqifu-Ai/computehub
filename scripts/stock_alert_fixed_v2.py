#!/usr/bin/env python3
"""修复版股票预警系统"""

from scripts.email_utils import send_email_safe
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class FixedStockAlert:
    def __init__(self):
        self.portfolio = {
            '000882': {
                'name': '华联股份',
                'quantity': 13500,
                'cost_price': 1.873,
                'stop_loss': 1.60,
                'target_price': 2.00
            }
        }
        
        self.email_config = {
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 465,
            'email': '19525456@qq.com',
            'auth_code': 'xunlwhjokescbgdd'
        }
    
    def get_stock_price_stable(self, stock_code):
        """稳定的股票价格获取"""
        # 尝试多个数据源
        sources = [
            # 腾讯财经
            f'http://qt.gtimg.cn/q={stock_code}',
            # 新浪财经
            f'http://hq.sinajs.cn/list={stock_code}',
        ]
        
        for url in sources:
            try:
                print(f"尝试数据源: {url[:50]}...")
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    content = response.text
                    
                    # 解析腾讯财经格式
                    if 'qt.gtimg.cn' in url and '~' in content:
                        parts = content.split('=')[1].strip().strip('\"').split('~')
                        if len(parts) > 3:
                            return float(parts[3])
                    
                    # 解析新浪财经格式
                    elif 'sinajs.cn' in url and ',' in content:
                        parts = content.split('=')[1].strip().strip('\"').split(',')
                        if len(parts) > 3:
                            return float(parts[3])
                            
            except Exception as e:
                print(f"数据源失败: {e}")
                continue
        
        return None
    
    def send_alert_email(self, subject, content):
        """发送预警邮件"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['email']
            msg['To'] = self.email_config['email']
            msg['Subject'] = subject
            
            html_content = f"""
            <html>
            <body>
            <h2 style=\"color: #ff6b6b;\">{subject}</h2>
            <div style=\"background: #f8f9fa; padding: 20px; border-radius: 10px;\">
            {content.replace('\\n', '<br>')}
            </div>
            <p style=\"color: #666;\">发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            server = smtplib.SMTP_SSL(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.login(self.email_config['email'], self.email_config['auth_code'])
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
    
    def check_and_alert(self):
        """检查并发送预警"""
        print("🔍 开始检查股票状态...")
        
        # 获取华联股份价格
        price = self.get_stock_price_stable('000882')
        
        if price is None:
            print("❌ 无法获取股票价格")
            return False
        
        print(f"📊 华联股份当前价格: ¥{price:.3f}")
        
        # 计算盈亏
        info = self.portfolio['000882']
        quantity = info['quantity']
        cost_price = info['cost_price']
        
        profit = (price - cost_price) * quantity
        profit_percent = (price - cost_price) / cost_price * 100
        
        print(f"💰 盈亏: ¥{profit:,.2f} ({profit_percent:+.2f}%)")
        
        # 检查预警条件
        need_alert = False
        alert_type = ""
        
        if profit_percent < -10:
            need_alert = True
            alert_type = "严重亏损"
        elif price <= info['stop_loss']:
            need_alert = True
            alert_type = "触发止损"
        elif abs(profit_percent) > 3:
            need_alert = True
            alert_type = "价格变动"
        
        if need_alert:
            print(f"🚨 需要发送{alert_type}预警")
            
            # 生成邮件内容
            subject = f"🚨 股票{alert_type}预警: {info['name']}"
            
            content = f"""
📊 **持仓详情:**
- 股票: {info['name']} (000882)
- 持仓: {quantity:,}股
- 成本价: ¥{cost_price:.3f}
- 当前价: ¥{price:.3f}
- 浮动盈亏: ¥{profit:,.2f} ({profit_percent:+.2f}%)

💡 **深度分析解决方案:**

1. **立即减仓70%**
   - 操作: 卖出{int(quantity*0.7):,}股，保留{int(quantity*0.3):,}股
   - 优点: 快速降低风险
   - 缺点: 可能错过反弹

2. **分批减仓策略**
   - 操作: 今日减仓30%，观察2天
   - 优点: 平衡风险与机会
   - 缺点: 风险暴露延长

3. **等待反弹策略**
   - 操作: 设置严格止损¥{info['stop_loss']:.2f}
   - 优点: 可能减少亏损
   - 缺点: 风险较大

🎯 **推荐方案:** 立即减仓70%

⚠️ **风险提示:** 投资有风险，决策需谨慎。
            """
            
            # 发送邮件
            if self.send_alert_email(subject, content):
                print("✅ 预警邮件发送成功")
                return True
            else:
                print("❌ 预警邮件发送失败")
                return False
        else:
            print("✅ 当前无需预警")
            return False

def main():
    alert = FixedStockAlert()
    result = alert.check_and_alert()
    
    if result:
        print("\n🎉 预警系统运行成功")
    else:
        print("\n📊 系统检查完成")

if __name__ == "__main__":
    main()

# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
