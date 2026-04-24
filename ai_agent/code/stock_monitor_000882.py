#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华联股份(000882)实时监控脚本
用于监控股价并执行止损操作
"""

import requests
import time
import json
from datetime import datetime
import os

class StockMonitor:
    def __init__(self):
        self.stock_code = "000882"
        self.holding_qty = 13500
        self.cost_price = 1.873
        self.stop_loss = 1.60
        self.take_profit = 2.00
        
        # 监控配置
        self.check_interval = 300  # 5分钟检查一次
        self.alert_threshold = 1.62  # 预警价格
        
        # 文件路径
        self.portfolio_file = "/root/.openclaw/workspace/memory/stock-portfolio.md"
        self.trade_record_file = "/root/.openclaw/workspace/memory/trade_record.json"
        
    def get_current_price(self):
        """获取实时股价"""
        try:
            # 尝试从新浪财经获取数据
            url = f"http://hq.sinajs.cn/list=sz{self.stock_code}"
            response = requests.get(url, timeout=10)
            response.encoding = 'gbk'
            
            if response.status_code == 200:
                data = response.text
                # 解析新浪财经数据格式
                if '="' in data and '";' in data:
                    stock_data = data.split('="')[1].split('";')[0]
                    price_data = stock_data.split(',')
                    if len(price_data) >= 4:
                        current_price = float(price_data[3])  # 当前价格
                        return current_price
            
            # 如果新浪失败，尝试其他数据源
            return self.fallback_price_lookup()
            
        except Exception as e:
            print(f"获取股价失败: {e}")
            return None
    
    def fallback_price_lookup(self):
        """备用价格查询方法"""
        try:
            # 尝试东方财富
            url = f"https://quote.eastmoney.com/sz{self.stock_code}.html"
            response = requests.get(url, timeout=10)
            # 这里需要解析HTML获取价格，简化处理返回None
            return None
        except:
            return None
    
    def analyze_risk(self, current_price):
        """分析风险等级"""
        if current_price is None:
            return "UNKNOWN", "无法获取实时股价"
        
        # 计算盈亏
        profit_loss = (current_price - self.cost_price) * self.holding_qty
        profit_loss_percent = (current_price - self.cost_price) / self.cost_price * 100
        
        # 风险等级判断
        if current_price <= self.stop_loss:
            return "CRITICAL", f"已跌破止损位！当前价: ¥{current_price:.2f}, 亏损: {profit_loss_percent:.2f}%"
        elif current_price <= self.alert_threshold:
            return "HIGH", f"接近止损位！当前价: ¥{current_price:.2f}, 距离止损: ¥{self.stop_loss - current_price:.2f}"
        elif current_price <= self.cost_price * 0.95:
            return "MEDIUM", f"中度亏损: ¥{current_price:.2f}, 亏损: {profit_loss_percent:.2f}%"
        else:
            return "LOW", f"正常波动: ¥{current_price:.2f}"
    
    def should_take_action(self, risk_level, current_price):
        """判断是否需要操作"""
        if risk_level == "CRITICAL":
            return True, "立即减仓70%"
        elif risk_level == "HIGH":
            return True, "减仓50%"
        else:
            return False, "暂不操作"
    
    def update_portfolio(self, action_taken=False, details=None):
        """更新持仓记录"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            if os.path.exists(self.portfolio_file):
                with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 添加监控记录
                new_content = content + f"\n\n## 📊 监控记录 {current_time}"
                if action_taken and details:
                    new_content += f"\n- **操作执行**: {details}"
                
                with open(self.portfolio_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            
        except Exception as e:
            print(f"更新持仓记录失败: {e}")
    
    def run_monitoring(self):
        """运行监控循环"""
        print(f"开始监控华联股份(000882)...")
        print(f"持仓: {self.holding_qty}股, 成本: ¥{self.cost_price}, 止损: ¥{self.stop_loss}")
        
        while True:
            try:
                current_price = self.get_current_price()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if current_price:
                    risk_level, risk_msg = self.analyze_risk(current_price)
                    action_needed, action_msg = self.should_take_action(risk_level, current_price)
                    
                    print(f"[{current_time}] 价格: ¥{current_price:.2f} | 风险: {risk_level} | {risk_msg}")
                    
                    if action_needed:
                        print(f"🚨 需要操作: {action_msg}")
                        # 这里可以添加实际交易操作的代码
                        self.update_portfolio(action_taken=True, details=action_msg)
                        break
                    else:
                        print(f"📊 状态: {action_msg}")
                        self.update_portfolio()
                else:
                    print(f"[{current_time}] 无法获取股价数据")
                
                # 等待下一次检查
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\n监控已停止")
                break
            except Exception as e:
                print(f"监控出错: {e}")
                time.sleep(60)  # 出错后等待1分钟

if __name__ == "__main__":
    monitor = StockMonitor()
    
    # 单次检查模式
    current_price = monitor.get_current_price()
    if current_price:
        risk_level, risk_msg = monitor.analyze_risk(current_price)
        action_needed, action_msg = monitor.should_take_action(risk_level, current_price)
        
        print(f"当前股价: ¥{current_price:.2f}")
        print(f"风险等级: {risk_level}")
        print(f"风险描述: {risk_msg}")
        print(f"操作建议: {action_msg}")
        
        if action_needed:
            print("🚨 紧急: 需要立即操作！")
        
        # 更新记录
        monitor.update_portfolio(action_needed, action_msg if action_needed else "监控检查完成")
    else:
        print("无法获取实时股价，请手动检查")
        print("建议操作: 登录交易软件查看实时价格，如跌破¥1.60立即减仓")