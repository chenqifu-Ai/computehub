#!/usr/bin/env python3
"""
查询华联股份实时行情
"""

import requests
import json
from datetime import datetime

def get_stock_data(stock_code):
    """获取股票实时数据"""
    
    # 腾讯财经API
    if stock_code.startswith('6'):
        url = f"http://qt.gtimg.cn/q=sh{stock_code}"
    else:
        url = f"http://qt.gtimg.cn/q=sz{stock_code}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.text
            # 解析数据格式: v_sh600460="1~华联股份~000882~1.65~1.64~1.66~22600~123456~..."
            parts = data.split('~')
            
            if len(parts) > 5:
                stock_info = {
                    'name': parts[1],
                    'code': parts[2],
                    'current_price': float(parts[3]),
                    'open_price': float(parts[4]),
                    'close_price': float(parts[5]),
                    'volume': int(parts[6]),
                    'turnover': float(parts[7]),
                    'high': float(parts[8]),
                    'low': float(parts[9]),
                    'timestamp': datetime.now().isoformat()
                }
                return stock_info
        
    except Exception as e:
        print(f"查询失败: {e}")
    
    return None

def analyze_position(stock_info, position):
    """分析持仓情况"""
    
    if not stock_info:
        return None
    
    current_price = stock_info['current_price']
    cost_price = position['cost_price']
    quantity = position['quantity']
    
    # 计算盈亏
    profit_loss = (current_price - cost_price) * quantity
    profit_loss_rate = (current_price - cost_price) / cost_price * 100
    
    # 计算市值
    market_value = current_price * quantity
    
    # 止损分析
    stop_loss_price = position.get('stop_loss', cost_price * 0.9)
    stop_loss_distance = (current_price - stop_loss_price) / current_price * 100
    
    # 目标分析
    target_price = position.get('target_price', cost_price * 1.1)
    target_distance = (target_price - current_price) / current_price * 100
    
    analysis = {
        'current_price': current_price,
        'cost_price': cost_price,
        'quantity': quantity,
        'market_value': market_value,
        'profit_loss': profit_loss,
        'profit_loss_rate': profit_loss_rate,
        'stop_loss_price': stop_loss_price,
        'stop_loss_distance': stop_loss_distance,
        'target_price': target_price,
        'target_distance': target_distance,
        'recommendation': ''
    }
    
    # 给出建议
    if profit_loss_rate > 5:
        analysis['recommendation'] = '考虑减仓锁定利润'
    elif profit_loss_rate < -5:
        analysis['recommendation'] = '密切关注，接近止损位'
    else:
        analysis['recommendation'] = '持有观察'
    
    return analysis

def main():
    """主函数"""
    
    print("🔍 查询华联股份实时行情...")
    
    # 华联股份持仓信息
    position = {
        'code': '000882',
        'name': '华联股份',
        'quantity': 22600,
        'cost_price': 1.779,
        'stop_loss': 1.60,
        'target_price': 2.00
    }
    
    # 获取实时数据
    stock_info = get_stock_data(position['code'])
    
    if stock_info:
        print(f"✅ 查询成功: {stock_info['name']} ({stock_info['code']})")
        print(f"📊 当前价格: ¥{stock_info['current_price']}")
        print(f"📈 今日涨跌: {stock_info['current_price'] - stock_info['close_price']:.2f}")
        
        # 分析持仓
        analysis = analyze_position(stock_info, position)
        
        if analysis:
            print(f"\n📊 持仓分析:")
            print(f"   持仓数量: {analysis['quantity']:,}股")
            print(f"   成本价格: ¥{analysis['cost_price']}")
            print(f"   当前市值: ¥{analysis['market_value']:,.2f}")
            print(f"   浮动盈亏: ¥{analysis['profit_loss']:,.2f} ({analysis['profit_loss_rate']:.2f}%)")
            print(f"   止损价位: ¥{analysis['stop_loss_price']} (距离: {analysis['stop_loss_distance']:.1f}%)")
            print(f"   目标价位: ¥{analysis['target_price']} (距离: {analysis['target_distance']:.1f}%)")
            print(f"   操作建议: {analysis['recommendation']}")
        
        # 保存结果
        result = {
            'stock_info': stock_info,
            'position_analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        with open('/root/.openclaw/workspace/hualian_analysis_20260325.json', 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 分析结果已保存")
        
    else:
        print("❌ 查询失败，请检查网络连接")

if __name__ == "__main__":
    main()