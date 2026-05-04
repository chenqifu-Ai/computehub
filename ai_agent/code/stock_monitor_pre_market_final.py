#!/usr/bin/env python3
"""
股票监控系统 - 盘前任务
执行时间: 2026-04-10 晚上 (盘后检查，为明日盘前准备)
"""

import json
import requests
from datetime import datetime

def get_stock_price(stock_code):
    """获取股票价格 - 使用腾讯财经API"""
    try:
        if stock_code.startswith('6'):
            url = f"http://qt.gtimg.cn/q=sh{stock_code}"
        else:
            url = f"http://qt.gtimg.cn/q=sz{stock_code}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.text
            if '="' in data:
                parts = data.split('~')
                if len(parts) > 3:
                    return {
                        'name': parts[1],
                        'code': parts[2],
                        'current_price': float(parts[3]),
                        'open_price': float(parts[4]) if parts[4] != '0' else None,
                        'close_price': float(parts[5]) if parts[5] != '0' else None,
                        'high': float(parts[8]) if parts[8] != '0' else None,
                        'low': float(parts[9]) if parts[9] != '0' else None,
                        'volume': int(parts[6]) if parts[6] != '0' else 0,
                        'timestamp': datetime.now().isoformat()
                    }
        return None
    except Exception as e:
        print(f"获取股价失败 {stock_code}: {e}")
        return None

def load_holdings():
    """加载持仓信息"""
    try:
        with open('/root/.openclaw/workspace/ai_agent/results/stock_holdings.json', 'r') as f:
            holdings = json.load(f)
        return holdings
    except Exception as e:
        print(f"加载持仓失败: {e}")
        # 返回默认持仓
        return [{
            "股票": "华联股份",
            "代码": "000882", 
            "数量": 13500,
            "成本价": 1.873,
            "止损位": 1.6,
            "止盈位": 2.0
        }]

def load_watchlist():
    """加载关注列表"""
    try:
        with open('/root/.openclaw/workspace/stock_watchlist.json', 'r') as f:
            watchlist = json.load(f)
        return watchlist
    except Exception as e:
        print(f"加载关注列表失败: {e}")
        return []

def analyze_stock_risk(holding, current_price):
    """分析股票风险"""
    cost_price = holding["成本价"]
    stop_loss = holding["止损位"]
    quantity = holding["数量"]
    
    # 计算盈亏
    profit_loss = (current_price - cost_price) * quantity
    profit_loss_rate = (current_price - cost_price) / cost_price * 100
    
    # 计算距离止损的距离
    if current_price > 0:
        stop_loss_distance = (current_price - stop_loss) / current_price * 100
    else:
        stop_loss_distance = 0
    
    risk_level = "低风险"
    if profit_loss_rate < -10:
        risk_level = "高风险"
    elif profit_loss_rate < -5:
        risk_level = "中风险"
    
    return {
        'current_price': current_price,
        'profit_loss': profit_loss,
        'profit_loss_rate': profit_loss_rate,
        'stop_loss_distance': stop_loss_distance,
        'risk_level': risk_level,
        'market_value': current_price * quantity
    }

def main():
    print("📊 股票监控系统 - 盘前任务执行")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 加载持仓和关注列表
    holdings = load_holdings()
    watchlist = load_watchlist()
    
    results = {
        'holdings_analysis': [],
        'watchlist_analysis': [],
        'alerts': [],
        'timestamp': datetime.now().isoformat()
    }
    
    # 分析持仓股票
    print("\n🔍 持仓股票分析:")
    for holding in holdings:
        stock_code = holding["代码"]
        stock_data = get_stock_price(stock_code)
        
        if stock_data:
            analysis = analyze_stock_risk(holding, stock_data['current_price'])
            
            print(f"\n📈 {holding['股票']} ({stock_code})")
            print(f"   当前价格: ¥{stock_data['current_price']:.2f}")
            print(f"   成本价格: ¥{holding['成本价']:.3f}")
            print(f"   持仓数量: {holding['数量']:,}股")
            print(f"   市值: ¥{analysis['market_value']:,.2f}")
            print(f"   浮动盈亏: ¥{analysis['profit_loss']:,.2f} ({analysis['profit_loss_rate']:.2f}%)")
            print(f"   止损位: ¥{holding['止损位']:.2f} (距离: {analysis['stop_loss_distance']:.2f}%)")
            print(f"   风险等级: {analysis['risk_level']}")
            
            # 风险提醒
            if analysis['profit_loss_rate'] < -10:
                alert_msg = f"⚠️ {holding['股票']} 亏损超过10%，建议密切关注"
                results['alerts'].append(alert_msg)
                print(f"   ⚠️ 风险提醒: {alert_msg}")
            elif analysis['stop_loss_distance'] < 2:
                alert_msg = f"🚨 {holding['股票']} 距离止损位不足2%，需立即关注"
                results['alerts'].append(alert_msg)
                print(f"   🚨 紧急提醒: {alert_msg}")
            
            results['holdings_analysis'].append({
                'holding': holding,
                'stock_data': stock_data,
                'analysis': analysis
            })
        else:
            print(f"❌ 无法获取 {holding['股票']} ({stock_code}) 的数据")
    
    # 分析关注列表
    print("\n👀 关注股票分析:")
    for stock in watchlist:
        stock_symbol = stock['symbol']
        # 提取纯数字代码
        if '.' in stock_symbol:
            code = stock_symbol.split('.')[0]
        else:
            code = stock_symbol
        
        stock_data = get_stock_price(code)
        if stock_data:
            print(f"📊 {stock['name']} ({code}): ¥{stock_data['current_price']:.2f}")
            results['watchlist_analysis'].append({
                'stock': stock,
                'stock_data': stock_data
            })
        else:
            print(f"❌ 无法获取 {stock['name']} ({code}) 的数据")
    
    # 保存结果
    output_file = f"/root/.openclaw/workspace/ai_agent/results/stock_pre_market_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 分析结果已保存到: {output_file}")
    
    # 输出总结
    print("\n" + "=" * 50)
    print("📋 盘前监控总结:")
    if results['alerts']:
        print("🚨 需要关注的风险:")
        for alert in results['alerts']:
            print(f"   • {alert}")
    else:
        print("✅ 无紧急风险提醒")
    
    print(f"\n🎯 明日交易建议:")
    print("   • 开盘后立即检查华联股份实时价格")
    print("   • 如价格低于¥1.62，考虑减仓50-70%")
    print("   • 严格执行¥1.60止损纪律")
    print("   • 关注大盘整体走势对个股影响")

if __name__ == "__main__":
    main()