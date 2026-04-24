import requests
import json
import re

def get_stock_price(symbol):
    """获取股票价格"""
    try:
        # 尝试使用腾讯财经API
        url = f"http://qt.gtimg.cn/q={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.text
            # 解析腾讯财经返回的数据格式: v_sh601866="..."; 
            match = re.search(r'v_{}="([^"]*)"'.format(symbol), data)
            if match:
                values = match.group(1).split('~')
                if len(values) > 3:
                    price = float(values[3])  # 当前价格在第4个位置(索引3)
                    return price
    except Exception as e:
        print(f"腾讯财经API失败: {e}")
    
    try:
        # 尝试使用东方财富API
        url = f"http://push2.eastmoney.com/api/qt/stock/get?secid=0.{symbol[2:]}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and data['data'] and 'f43' in data['data']:
                price = data['data']['f43']  # 当前价格字段
                return float(price)
    except Exception as e:
        print(f"东方财富API失败: {e}")
    
    return None

# 获取华联股份(000882)的股价
stock_symbol = "sz000882"
current_price = get_stock_price(stock_symbol)

# 持仓信息
quantity = 13500
cost_price = 1.873
stop_loss = 1.60

if current_price is not None:
    print(f"华联股份(000882)当前股价: ¥{current_price:.3f}")
    
    # 计算盈亏
    current_value = current_price * quantity
    cost_value = cost_price * quantity
    profit_loss = current_value - cost_value
    profit_loss_percent = (profit_loss / cost_value) * 100
    
    print(f"持仓数量: {quantity:,}股")
    print(f"成本价格: ¥{cost_price:.3f}")
    print(f"当前市值: ¥{current_value:,.2f}")
    print(f"成本市值: ¥{cost_value:,.2f}")
    print(f"浮动盈亏: ¥{profit_loss:,.2f} ({profit_loss_percent:.2f}%)")
    print(f"止损价位: ¥{stop_loss:.2f}")
    
    # 风险分析
    distance_to_stop_loss = current_price - stop_loss
    stop_loss_percent = (distance_to_stop_loss / current_price) * 100
    
    print(f"距离止损位: ¥{distance_to_stop_loss:.3f} ({stop_loss_percent:.2f}%)")
    
    # 操作建议
    if current_price <= stop_loss:
        print("\n🚨 紧急警报: 股价已跌破止损位！建议立即止损！")
        print("建议操作: 减仓70%以上降低风险")
    elif profit_loss_percent <= -10:
        print("\n⚠️ 风险警报: 亏损超过10%，接近止损位！")
        print("建议操作: 考虑减仓50%降低风险")
    elif profit_loss_percent <= -5:
        print("\n🟡 提醒: 亏损超过5%，需要密切关注")
        print("建议操作: 持续监控，准备减仓")
    else:
        print("\n🟢 状态正常: 亏损在可控范围内")
        print("建议操作: 继续持有，密切关注")
        
else:
    print("无法获取华联股份(000882)的股价信息")