#!/usr/bin/env python3
"""
三支股票推荐分析
基于当前市场环境和投资机会
"""

import datetime

def get_market_overview():
    """市场概览"""
    return {
        'date': '2026-04-07',
        'market_status': '结构性行情',
        'major_indices': {
            '上证指数': '+0.88%',
            '深证成指': '-0.56%', 
            '创业板指': '-0.70%',
            '沪深300': '+0.35%'
        },
        'sector_performance': {
            '强势板块': ['新能源', '芯片', '医药'],
            '弱势板块': ['房地产', '零售', '传统制造']
        },
        'investment_strategy': '精选个股，控制仓位'
    }

def recommend_stocks():
    """推荐三支股票"""
    
    stocks = [
        {
            'code': '601866',
            'name': '中远海发',
            'industry': '航运物流',
            'current_price': 2.67,
            'target_range': [2.50, 2.70],
            'investment_logic': [
                '全球贸易复苏受益股',
                '估值处于历史低位',
                '分红收益率较高',
                '一带一路政策受益'
            ],
            'risk_factors': [
                '受全球经济周期影响',
                '油价波动影响成本'
            ],
            'suggested_allocation': '30-40%',
            'buy_strategy': '分批建仓，2.50-2.70区间',
            'stop_loss': 2.40,
            'target_price': 3.20
        },
        {
            'code': '002415',
            'name': '海康威视',
            'industry': '安防监控',
            'current_price': 32.50,
            'target_range': [32.00, 34.00],
            'investment_logic': [
                'AI+安防龙头地位稳固',
                '海外业务恢复增长',
                '现金流充裕，估值合理',
                '智慧城市概念受益'
            ],
            'risk_factors': [
                '地缘政治风险',
                '行业竞争加剧'
            ],
            'suggested_allocation': '25-35%', 
            'buy_strategy': '现价附近分批买入',
            'stop_loss': 30.00,
            'target_price': 38.00
        },
        {
            'code': '300750',
            'name': '宁德时代',
            'industry': '新能源电池',
            'current_price': 150.80,
            'target_range': [145.00, 155.00],
            'investment_logic': [
                '全球动力电池龙头',
                '新能源汽车长期趋势',
                '技术领先，客户优质',
                '估值回调至合理区间'
            ],
            'risk_factors': [
                '行业竞争激烈',
                '原材料价格波动'
            ],
            'suggested_allocation': '20-30%',
            'buy_strategy': '145-155区间分批建仓',
            'stop_loss': 140.00,
            'target_price': 180.00
        }
    ]
    
    return stocks

def calculate_position(available_cash):
    """计算建议仓位"""
    stocks = recommend_stocks()
    
    print(f"💰 可用资金: ¥{available_cash:,.2f}")
    print("=" * 60)
    
    for i, stock in enumerate(stocks, 1):
        allocation_percent = 0.30  # 平均30%仓位
        allocation_cash = available_cash * allocation_percent
        shares = allocation_cash // stock['current_price']
        
        print(f"{i}. {stock['name']}({stock['code']}) - {stock['industry']}")
        print(f"   📊 现价: ¥{stock['current_price']}")
        print(f"   🎯 目标区间: ¥{stock['target_range'][0]}-{stock['target_range'][1]}")
        print(f"   📈 建议仓位: {stock['suggested_allocation']}")
        print(f"   💰 建议投入: ¥{allocation_cash:,.2f} » {shares:.0f}股")
        print(f"   🛡️  止损位: ¥{stock['stop_loss']}")
        print(f"   🚀 目标价: ¥{stock['target_price']} (+{(stock['target_price']/stock['current_price']-1)*100:.1f}%)")
        print()

def print_detailed_analysis():
    """打印详细分析"""
    market = get_market_overview()
    stocks = recommend_stocks()
    
    print("🌍 市场环境分析")
    print("=" * 60)
    print(f"📅 日期: {market['date']}")
    print(f"📈 市场状态: {market['market_status']}")
    print(f"📊 主要指数: {market['major_indices']}")
    print(f"🎯 投资策略: {market['investment_strategy']}")
    print()
    
    print("🏆 三支推荐股票")
    print("=" * 60)
    
    for i, stock in enumerate(stocks, 1):
        print(f"{i}. {stock['name']}({stock['code']}) - {stock['industry']}")
        print(f"   💰 当前价格: ¥{stock['current_price']}")
        print(f"   🎯 买入区间: ¥{stock['target_range'][0]}-{stock['target_range'][1]}")
        
        print(f"   📈 投资逻辑:")
        for logic in stock['investment_logic']:
            print(f"      ✅ {logic}")
            
        print(f"   ⚠️  风险因素:")
        for risk in stock['risk_factors']:
            print(f"      🔸 {risk}")
            
        print(f"   🎯 操作策略: {stock['buy_strategy']}")
        print(f"   🛡️  止损位: ¥{stock['stop_loss']} (-{(1-stock['stop_loss']/stock['current_price'])*100:.1f}%)")
        print(f"   🚀 目标价: ¥{stock['target_price']} (+{(stock['target_price']/stock['current_price']-1)*100:.1f}%)")
        print()

def main():
    available_cash = 8364.00  # 华联减仓回收资金
    
    print("🎯 三支股票推荐 - 2026年4月7日")
    print("=" * 60)
    
    # 详细分析
    print_detailed_analysis()
    
    # 仓位计算
    calculate_position(available_cash)
    
    print("💡 投资建议总结")
    print("=" * 60)
    print("1. 优先考虑中远海发 - 估值低位，安全边际高")
    print("2. 海康威视 - AI龙头，稳健成长")
    print("3. 宁德时代 - 新能源龙头，长期趋势")
    print("4. 建议分批建仓，控制单支股票仓位")
    print("5. 严格止损纪律，保护本金安全")
    print()
    print("📞 风险提示: 股市有风险，投资需谨慎")

if __name__ == "__main__":
    main()