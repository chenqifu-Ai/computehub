#!/usr/bin/env python3
"""
智能股票预警系统 - 深度思考解决方案 + 邮件提醒
"""

import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json

class StockAlertSystem:
    def __init__(self):
        self.portfolio = {
            '000882': {
                'name': '华联股份',
                'quantity': 13500,
                'cost_price': 1.873,
                'stop_loss': 1.60,
                'target_price': 2.00
            },
            '601866': {
                'name': '中远海发', 
                'target_buy': [2.50, 2.70],
                'monitoring': True
            }
        }
        
        # 邮件配置
        self.email_config = {
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 465,
            'email': '19525456@qq.com',
            'auth_code': 'xunlwhjokescbgdd'
        }
    
    def get_stock_price(self, stock_code):
        """获取股票实时价格"""
        try:
            secid = f"{1 if stock_code.startswith('6') else 0}.{stock_code}"
            url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('rc') == 0 and 'data' in data:
                    return data['data'].get('f43', 0) / 100
        except:
            return None
        return None
    
    def deep_analysis_hualian(self, current_price):
        """深度分析华联股份解决方案"""
        info = self.portfolio['000882']
        quantity = info['quantity']
        cost_price = info['cost_price']
        
        market_value = quantity * current_price
        cost_value = quantity * cost_price
        profit = market_value - cost_value
        profit_percent = (profit / cost_value) * 100
        
        # 多种解决方案分析
        solutions = []
        
        # 方案1: 立即减仓
        if profit_percent < -10:
            solutions.append({
                'name': '立即减仓70%',
                'action': f'卖出{int(quantity*0.7):,}股，保留{int(quantity*0.3):,}股',
                'risk_reduction': '高风险→中风险',
                'pros': '快速降低风险，锁定部分亏损',
                'cons': '可能错过反弹机会'
            })
        
        # 方案2: 分批减仓
        solutions.append({
            'name': '分批减仓策略',
            'action': '今日减仓30%，观察2天后再决定',
            'risk_reduction': '逐步降低风险',
            'pros': '平衡风险与机会',
            'cons': '风险暴露时间延长'
        })
        
        # 方案3: 等待反弹
        solutions.append({
            'name': '等待反弹策略',
            'action': '设置严格止损¥1.60，等待技术反弹',
            'risk_reduction': '高风险但可能减少亏损',
            'pros': '跌破支撑后往往有反弹',
            'cons': '风险较大，需要严格纪律'
        })
        
        # 方案4: 转换标的
        solutions.append({
            'name': '转换标的策略',
            'action': '卖出华联，等待中远海发买入机会',
            'risk_reduction': '换到更有潜力标的',
            'pros': '可能获得更好收益',
            'cons': '需要精准时机判断'
        })
        
        return {
            'current_price': current_price,
            'market_value': market_value,
            'profit': profit,
            'profit_percent': profit_percent,
            'solutions': solutions,
            'recommendation': solutions[0] if profit_percent < -10 else solutions[1]
        }
    
    def send_email_alert(self, subject, content):
        """发送邮件提醒"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['email']
            msg['To'] = self.email_config['email']
            msg['Subject'] = subject
            
            # HTML格式内容
            html_content = f"""
            <html>
            <body>
            <h2 style=\"color: #ff6b6b;\">{subject}</h2>
            <div style=\"background: #f8f9fa; padding: 20px; border-radius: 10px;\">
            {content.replace('\\n', '<br>')}
            </div>
            <p style=\"color: #666; font-size: 12px;\">
            发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
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
        """检查并发送提醒"""
        print("🔍 检查股票状态...")
        
        # 检查华联股份
        hualian_price = self.get_stock_price('000882')
        if hualian_price:
            analysis = self.deep_analysis_hualian(hualian_price)
            
            # 判断是否需要发送提醒
            need_alert = False
            alert_reason = ""
            
            if analysis['profit_percent'] < -10:
                need_alert = True
                alert_reason = "亏损超过10%，需要紧急处理"
            elif hualian_price <= self.portfolio['000882']['stop_loss']:
                need_alert = True
                alert_reason = "触发止损位，立即行动"
            elif abs(analysis['profit_percent']) > 3:
                need_alert = True
                alert_reason = "价格变动超过3%"
            
            if need_alert:
                # 生成邮件内容
                subject = f"🚨 股票预警: {self.portfolio['000882']['name']} {alert_reason}"
                
                content = f"""
📊 **持仓详情:**
- 股票: {self.portfolio['000882']['name']} (000882)
- 持仓: {self.portfolio['000882']['quantity']:,}股
- 成本价: ¥{self.portfolio['000882']['cost_price']:.3f}
- 当前价: ¥{analysis['current_price']:.3f}
- 浮动盈亏: ¥{analysis['profit']:,.2f} ({analysis['profit_percent']:+.2f}%)

💡 **深度分析解决方案:**

"""
                
                for i, solution in enumerate(analysis['solutions'], 1):
                    content += f"""
{i}. **{solution['name']}**
   - 操作: {solution['action']}
   - 风险: {solution['risk_reduction']}
   - 优点: {solution['pros']}
   - 缺点: {solution['cons']}

"""
                
                content += f"""
🎯 **推荐方案:** {analysis['recommendation']['name']}

⚠️ **风险提示:** 投资有风险，决策需谨慎。
                """
                
                # 发送邮件
                if self.send_email_alert(subject, content):
                    print("✅ 邮件提醒发送成功")
                else:
                    print("❌ 邮件发送失败")
                
                return analysis
        
        return None

def main():
    system = StockAlertSystem()
    result = system.check_and_alert()
    
    if result:
        print(f"\n📈 分析完成:")
        print(f"   当前价格: ¥{result['current_price']:.3f}")
        print(f"   盈亏: {result['profit_percent']:+.2f}%")
        print(f"   推荐方案: {result['recommendation']['name']}")
    else:
        print("✅ 当前无需提醒")

if __name__ == "__main__":
    main()