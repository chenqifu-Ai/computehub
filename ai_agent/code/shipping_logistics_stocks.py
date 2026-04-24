#!/usr/bin/env python3
"""
航运物流行业股票推荐
专注于航运、物流、港口相关股票
"""

import datetime

def get_shipping_stocks():
    """获取航运物流行业股票"""
    
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 航运物流行业主要股票
    stocks = [
        {
            'code': '601866',
            'name': '中远海发',
            'subindustry': '集装箱航运',
            'current_price': 2.65,
            'change_percent': -0.75,
            'market_cap': '中型',
            'investment_logic': [
                '全球贸易复苏直接受益',
                '一带一路政策核心标的',
                '估值处于历史低位',
                '分红收益率较高(约3-4%)',
                '船队规模行业领先'
            ],
            'risk_factors': [
                '受全球经济周期影响较大',
                '油价波动影响运营成本',
                '汇率波动风险',
                '行业竞争激烈'
            ],
            'buy_range': [2.50, 2.70],
            'target_price': 3.20,
            'stop_loss': 2.40,
            'rating': '⭐⭐⭐⭐⭐'
        },
        {
            'code': '601919',
            'name': '中远海控',
            'subindustry': '集装箱航运',
            'current_price': 8.95,
            'change_percent': -1.10,
            'market_cap': '大型',
            'investment_logic': [
                '全球集装箱航运龙头',
                '规模效应明显',
                '现金流充裕',
                '行业整合受益者',
                '国际化程度高'
            ],
            'risk_factors': [
                '运价波动风险',
                '全球经济不确定性',
                '环保政策压力',
                '资本开支较大'
            ],
            'buy_range': [8.50, 9.20],
            'target_price': 10.50,
            'stop_loss': 8.00,
            'rating': '⭐⭐⭐⭐'
        },
        {
            'code': '600026',
            'name': '中远海能',
            'subindustry': '油轮运输',
            'current_price': 15.80,
            'change_percent': +0.64,
            'market_cap': '中型',
            'investment_logic': [
                '油轮运输细分龙头',
                '能源运输需求稳定',
                '地缘政治因素利好',
                '运价弹性较大',
                '估值相对合理'
            ],
            'risk_factors': [
                '油价波动影响显著',
                '地缘政治风险',
                '环保法规趋严',
                '需求波动性大'
            ],
            'buy_range': [15.00, 16.50],
            'target_price': 18.50,
            'stop_loss': 14.50,
            'rating': '⭐⭐⭐⭐'
        },
        {
            'code': '002352',
            'name': '顺丰控股',
            'subindustry': '快递物流',
            'current_price': 42.30,
            'change_percent': +0.95,
            'market_cap': '大型',
            'investment_logic': [
                '国内快递行业龙头',
                '数字化转型领先',
                '冷链物流布局完善',
                '品牌价值突出',
                '业绩稳定增长'
            ],
            'risk_factors': [
                '行业价格竞争激烈',
                '人力成本上升',
                '新业务投入较大',
                '经济周期影响'
            ],
            'buy_range': [40.00, 44.00],
            'target_price': 48.00,
            'stop_loss': 38.00,
            'rating': '⭐⭐⭐⭐⭐'
        },
        {
            'code': '600017',
            'name': '日照港',
            'subindustry': '港口运营',
            'current_price': 3.15,
            'change_percent': -0.63,
            'market_cap': '中型',
            'investment_logic': [
                '一带一路重要节点',
                '区位优势明显',
                '估值低廉',
                '分红稳定',
                '受益贸易复苏'
            ],
            'risk_factors': [
                '吞吐量增长有限',
                '区域竞争激烈',
                '固定资产投资大',
                '经济周期敏感'
            ],
            'buy_range': [3.00, 3.30],
            'target_price': 3.80,
            'stop_loss': 2.80,
            'rating': '⭐⭐⭐'
        }
    ]
    
    return stocks, current_time

def print_recommendation():
    """打印推荐结果"""
    stocks, current_time = get_shipping_stocks()
    available_cash = 8364.00
    
    print(f"🚢 航运物流行业股票推荐 - {current_time}")
    print("=" * 80)
    print(f"💰 可用资金: ¥{available_cash:,.2f}")
    print("=" * 80)
    
    # 推荐前三名
    recommended_stocks = stocks[:3]  # 取前三只
    
    for i, stock in enumerate(recommended_stocks, 1):
        print(f"{i}. {stock['name']}({stock['code']}) - {stock['subindustry']} {stock['rating']}")
        print(f"   📊 现价: ¥{stock['current_price']} ({'🟢' if stock['change_percent'] >= 0 else '🔴'}{stock['change_percent']:+.2f}%)")
        print(f"   🎯 目标价: ¥{stock['target_price']} (+{(stock['target_price']/stock['current_price']-1)*100:.1f}%)")
        print(f"   🛡️  止损位: ¥{stock['stop_loss']} (-{(1-stock['stop_loss']/stock['current_price'])*100:.1f}%)")
        print(f"   📈 买入区间: ¥{stock['buy_range'][0]}-{stock['buy_range'][1]}")
        
        # 检查是否在买入区间
        if stock['buy_range'][0] <= stock['current_price'] <= stock['buy_range'][1]:
            status = "✅ 在买入区间内"
        else:
            status = "🟡 等待更好价格"
        print(f"   📍 当前状态: {status}")
        print()

def print_detailed_analysis():
    """打印详细分析"""
    stocks, current_time = get_shipping_stocks()
    
    print(f"📊 航运物流行业深度分析")
    print("=" * 80)
    
    for stock in stocks[:3]:  # 分析前三只
        print(f"\n🔍 {stock['name']}({stock['code']}) - {stock['subindustry']}")
        print("-" * 50)
        
        print(f"📈 投资逻辑:")
        for logic in stock['investment_logic']:
            print(f"   ✅ {logic}")
            
        print(f"\n⚠️  风险因素:")
        for risk in stock['risk_factors']:
            print(f"   🔸 {risk}")
            
        print(f"\n🎯 操作建议:")
        if stock['buy_range'][0] <= stock['current_price'] <= stock['buy_range'][1]:
            print(f"   立即考虑买入，现价¥{stock['current_price']}在理想区间")
        else:
            print(f"   等待价格进入¥{stock['buy_range'][0]}-{stock['buy_range'][1]}区间")
        print(f"   止损位: ¥{stock['stop_loss']}")
        print(f"   目标价: ¥{stock['target_price']}")

def main():
    print_recommendation()
    print_detailed_analysis()
    
    # 投资建议
    print(f"\n💡 行业投资要点")
    print("=" * 80)
    print("1. 🌍 全球贸易复苏是主要催化剂")
    print("2. 🚢 一带一路政策持续利好")
    print("3. 📦 电商发展推动物流需求")
    print("4. ⚓ 关注估值合理的龙头企业")
    print("5. ⚠️  注意经济周期和油价波动风险")
    print("\n📞 风险提示: 行业周期性较强，投资需谨慎")

if __name__ == "__main__":
    main()