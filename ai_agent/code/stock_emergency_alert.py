#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华联股份紧急警报脚本
检测股价是否跌破止损位并发送警报
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append('/root/.openclaw/workspace')

# 股票配置
STOCK_CONFIG = {
    'code': '000882',
    'name': '华联股份',
    'position': 8400,  # 持仓数量
    'cost_price': 1.873,  # 成本价
    'stop_loss': 1.60,  # 止损位
    'target_price': 2.00,  # 止盈位
}

def get_current_price():
    """
    获取当前股价（模拟函数，实际应接入实时数据接口）
    返回: 当前股价
    """
    # 这里使用从HEARTBEAT.md中获取的最新价格
    return 1.59  # 从心跳文件获取的当前价格

def calculate_profit_loss(current_price):
    """计算盈亏情况"""
    position = STOCK_CONFIG['position']
    cost_price = STOCK_CONFIG['cost_price']
    
    # 计算浮动盈亏
    floating_pl = (current_price - cost_price) * position
    floating_pl_percent = (current_price - cost_price) / cost_price * 100
    
    return floating_pl, floating_pl_percent

def check_stop_loss(current_price):
    """检查是否跌破止损位"""
    stop_loss = STOCK_CONFIG['stop_loss']
    return current_price < stop_loss

def generate_alert_message(current_price):
    """生成警报消息"""
    floating_pl, floating_pl_percent = calculate_profit_loss(current_price)
    
    message = f"🚨 紧急股票警报 - {STOCK_CONFIG['name']}({STOCK_CONFIG['code']})\n"
    message += f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += f"📊 当前价格: ¥{current_price:.2f}\n"
    message += f"⛔ 止损价位: ¥{STOCK_CONFIG['stop_loss']:.2f}\n"
    message += f"📉 浮动盈亏: {floating_pl_percent:.2f}% (¥{floating_pl:.2f})\n"
    message += f"📦 持仓数量: {STOCK_CONFIG['position']}股\n"
    
    if check_stop_loss(current_price):
        message += "\n🔴 紧急状况: 已跌破止损位！\n"
        message += "💡 建议操作: 立即执行止损纪律\n"
        message += f"💰 预估回收资金: ¥{current_price * STOCK_CONFIG['position']:.2f}\n"
    else:
        message += "\n🟡 预警状况: 接近止损位，密切监控\n"
    
    return message

def main():
    """主函数"""
    print("📈 开始华联股份紧急检查...")
    
    # 获取当前价格
    current_price = get_current_price()
    print(f"当前股价: ¥{current_price:.2f}")
    
    # 生成警报消息
    alert_message = generate_alert_message(current_price)
    print("\n" + "="*50)
    print(alert_message)
    print("="*50)
    
    # 检查是否需要紧急操作
    if check_stop_loss(current_price):
        print("\n🟥 执行紧急操作建议:")
        print("1. 立即登录交易平台")
        print("2. 卖出全部8,400股")
        print("3. 确认成交后更新持仓记录")
        print("4. 重新评估投资策略")
        
        # 这里可以添加自动发送邮件或消息的通知功能
        # send_alert_notification(alert_message)
        
        return 1  # 返回紧急状态码
    else:
        print("\n🟢 当前状况: 持仓安全，继续监控")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)