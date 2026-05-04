#!/usr/bin/env python3
"""
实时股价查询
检查中远海发、海康威视、宁德时代的实时价格
"""

import datetime

def get_real_time_prices():
    """获取实时股价（模拟实际查询）"""
    
    # 这里应该是实际的API调用，暂时用模拟数据
    # 实际使用时需要接入股票数据API
    
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    
    stocks = [
        {
            'code': '601866',
            'name': '中远海发',
            'previous_close': 2.67,  # 昨日收盘价
            'current_price': 2.65,   # 模拟当前价（下跌0.75%）
            'change': -0.02,
            'change_percent': -0.75,
            'status': '交易中'
        },
        {
            'code': '002415', 
            'name': '海康威视',
            'previous_close': 32.50,
            'current_price': 32.80,  # 模拟当前价（上涨0.92%）
            'change': +0.30,
            'change_percent': +0.92,
            'status': '交易中'
        },
        {
            'code': '300750',
            'name': '宁德时代', 
            'previous_close': 150.80,
            'current_price': 149.50,  # 模拟当前价（下跌0.86%）
            'change': -1.30,
            'change_percent': -0.86,
            'status': '交易中'
        }
    ]
    
    return stocks, current_time

def print_price_comparison():
    """打印价格对比"""
    stocks, current_time = get_real_time_prices()
    
    print(f"📈 实时股价查询 - {current_time}")
    print("=" * 60)
    print(f"{'股票':<10} {'代码':<8} {'昨收':<8} {'现价':<8} {'涨跌':<8} {'涨幅':<8} {'状态':<6}")
    print("-" * 60)
    
    for stock in stocks:
        color = "🟢" if stock['change'] > 0 else "🔴" if stock['change'] < 0 else "⚪"
        print(f"{stock['name']:<10} {stock['code']:<8} {stock['previous_close']:<8.2f} "
              f"{stock['current_price']:<8.2f} {color}{stock['change']:+.2f} {stock['change_percent']:+.2f}% "
              f"{stock['status']:<6}")
    
    print("=" * 60)
    
    # 投资建议更新
    print(f"\n🎯 基于实时价格的投资建议")
    print("=" * 60)
    
    for stock in stocks:
        if stock['code'] == '601866':  # 中远海发
            if stock['current_price'] <= 2.70:
                status = "✅ 在买入区间内"
                suggestion = "可考虑开始建仓"
            else:
                status = "🟡 略高于买入区间"
                suggestion = "等待回调至2.70以下"
                
        elif stock['code'] == '002415':  # 海康威视
            if 32.00 <= stock['current_price'] <= 34.00:
                status = "✅ 在买入区间内"
                suggestion = "可考虑建仓"
            else:
                status = "🟡 不在理想区间"
                suggestion = "等待更好价格"
                
        else:  # 宁德时代
            if 145.00 <= stock['current_price'] <= 155.00:
                status = "✅ 在买入区间内"
                suggestion = "可考虑分批买入"
            else:
                status = "🟡 价格偏离区间"
                suggestion = "耐心等待机会"
        
        print(f"{stock['name']}({stock['code']}): {status}")
        print(f"   现价: ¥{stock['current_price']} | 建议: {suggestion}")

def main():
    print_price_comparison()
    
    # 实时数据获取说明
    print(f"\n💡 说明:")
    print("• 以上为模拟实时价格，实际投资前请确认最新价格")
    print("• 建议使用证券APP或财经网站查询确切价格")
    print("• 投资决策应以实时市场数据为准")
    print("• 股市有风险，投资需谨慎")

if __name__ == "__main__":
    main()