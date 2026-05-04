#!/usr/bin/env python3
"""
赚钱核心分析脚本 - 专注于股票投资赚钱
"""

import requests
import json
from datetime import datetime
import time

def get_stock_real_time_data(stock_code):
    """获取股票实时数据"""
    try:
        # 东方财富接口
        secid = f"{1 if stock_code.startswith('6') else 0}.{stock_code}"
        url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f44,f45,f46,f60,f169,f170"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('rc') == 0 and 'data' in data:
                stock_data = data['data']
                return {
                    'current_price': stock_data.get('f43', 0) / 100,  # 现价
                    'high_price': stock_data.get('f44', 0) / 100,     # 最高
                    'low_price': stock_data.get('f45', 0) / 100,      # 最低
                    'open_price': stock_data.get('f46', 0) / 100,     # 开盘
                    'volume': stock_data.get('f60', 0),               # 成交量
                    'amount': stock_data.get('f169', 0),              # 成交额
                    'amplitude': stock_data.get('f170', 0) / 100      # 振幅
                }
    except Exception as e:
        print(f"获取{stock_code}数据失败: {e}")
    return None

def analyze_hualian(stock_data, quantity=22600, cost_price=1.779):
    """分析华联股份持仓"""
    current_price = stock_data['current_price']
    market_value = quantity * current_price
    cost_value = quantity * cost_price
    profit = market_value - cost_value
    profit_percent = (profit / cost_value) * 100
    
    # 止损分析
    stop_loss = 1.60
    distance_to_stop = ((current_price - stop_loss) / stop_loss) * 100
    
    return {
        'current_price': current_price,
        'market_value': market_value,
        'profit': profit,
        'profit_percent': profit_percent,
        'distance_to_stop': distance_to_stop,
        'stop_loss_triggered': current_price <= stop_loss
    }

def analyze_zhongyuan(stock_data, target_buy=[2.50, 2.70]):
    """分析中远海发买入机会"""
    current_price = stock_data['current_price']
    in_buy_zone = target_buy[0] <= current_price <= target_buy[1]
    
    return {
        'current_price': current_price,
        'in_buy_zone': in_buy_zone,
        'distance_to_buy': ((current_price - target_buy[0]) / target_buy[0]) * 100 if current_price > target_buy[0] else 0
    }

def generate_trading_strategy(hualian_data, zhongyuan_data):
    """生成交易策略"""
    strategies = []
    
    # 华联股份策略
    if hualian_data['stop_loss_triggered']:
        strategies.append("🚨 华联股份触发止损！立即卖出！")
    elif hualian_data['profit_percent'] < -5:
        strategies.append("⚠️ 华联股份亏损超过5%，考虑减仓")
    elif hualian_data['profit_percent'] > 0:
        strategies.append("✅ 华联股份盈利中，持有观察")
    else:
        strategies.append("📊 华联股份小幅亏损，继续持有")
    
    # 中远海发策略
    if zhongyuan_data['in_buy_zone']:
        strategies.append("🎯 中远海发进入买入区间，可建仓")
    else:
        strategies.append(f"⏳ 中远海发等待回调，目标¥{zhongyuan_data['current_price']:.2f}")
    
    return strategies

def main():
    print("🚀 赚钱核心分析报告")
    print("=" * 50)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 获取实时数据
    print("📈 获取实时股票数据...")
    hualian_data = get_stock_real_time_data('000882')
    zhongyuan_data = get_stock_real_time_data('601866')
    
    if not hualian_data or not zhongyuan_data:
        print("❌ 数据获取失败，请检查网络连接")
        return
    
    # 分析持仓
    print("🔍 分析持仓情况...")
    hualian_analysis = analyze_hualian(hualian_data)
    zhongyuan_analysis = analyze_zhongyuan(zhongyuan_data)
    
    # 显示结果
    print("\n💼 华联股份(000882)持仓分析:")
    print(f"   当前价格: ¥{hualian_analysis['current_price']:.3f}")
    print(f"   持仓市值: ¥{hualian_analysis['market_value']:,.2f}")
    print(f"   浮动盈亏: ¥{hualian_analysis['profit']:,.2f} ({hualian_analysis['profit_percent']:+.2f}%)")
    print(f"   距离止损: {hualian_analysis['distance_to_stop']:.1f}% 安全空间")
    
    print("\n🎯 中远海发(601866)监控分析:")
    print(f"   当前价格: ¥{zhongyuan_analysis['current_price']:.2f}")
    print(f"   买入区间: ¥2.50-2.70")
    print(f"   是否可买: {'✅ 是' if zhongyuan_analysis['in_buy_zone'] else '❌ 否'}")
    
    # 生成策略
    print("\n💡 交易策略建议:")
    strategies = generate_trading_strategy(hualian_analysis, zhongyuan_analysis)
    for i, strategy in enumerate(strategies, 1):
        print(f"   {i}. {strategy}")
    
    # 赚钱效率分析
    print("\n⚡ 赚钱效率优化:")
    print("   1. 实时监控: 已实现自动化数据获取")
    print("   2. 止损机制: 华联股份止损位¥1.60")
    print("   3. 买入策略: 中远海发目标区间监控")
    print("   4. 流程优化: 减少人工干预，提高响应速度")
    
    print("\n🎯 下一步行动:")
    print("   1. 设置价格预警通知")
    print("   2. 优化数据接口稳定性")
    print("   3. 扩展更多赚钱标的")

if __name__ == "__main__":
    main()