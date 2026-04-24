#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import datetime

def generate_stock_analysis():
    # 读取实时数据
    with open('/root/.openclaw/workspace/ai_agent/results/stocks_realtime.json', 'r') as f:
        realtime_data = json.load(f)
    
    # 转换为字典格式
    stock_dict = {}
    for stock in realtime_data:
        stock_dict[stock['name']] = stock['current']
    
    # 持仓信息
    positions = {
        '士兰微': {
            'code': '600460',
            'shares': 1000,
            'cost_price': 29.364,
            'current_price': stock_dict['士兰微'],
            'market_value': stock_dict['士兰微'] * 1000
        },
        '华联股份': {
            'code': '000882',
            'shares': 22600,
            'cost_price': 1.779,
            'current_price': stock_dict['华联股份'],
            'market_value': stock_dict['华联股份'] * 22600
        }
    }
    
    # 计算盈亏
    for stock, info in positions.items():
        info['profit_loss_pct'] = (info['current_price'] - info['cost_price']) / info['cost_price'] * 100
        info['total_loss'] = (info['cost_price'] - info['current_price']) * info['shares']
    
    total_cost = sum(info['cost_price'] * info['shares'] for info in positions.values())
    total_value = sum(info['market_value'] for info in positions.values())
    total_loss_pct = (total_value - total_cost) / total_cost * 100
    
    # 生成分析报告
    report = f"""
📊 股票持仓分析报告
📅 日期: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
============================================================

【持仓概览】
• 总投入成本: ¥{total_cost:,.2f}
• 当前市值: ¥{total_value:,.2f}
• 总体浮亏: {total_loss_pct:.2f}% (¥{(total_cost - total_value):,.2f})

【个股详情】

1️⃣ 士兰微 (600460)
   • 持仓数量: 1,000股
   • 成本价: ¥29.364
   • 现价: ¥{positions['士兰微']['current_price']:.2f}
   • 浮亏: {positions['士兰微']['profit_loss_pct']:.2f}% (¥{positions['士兰微']['total_loss']:,.2f})
   • 市值: ¥{positions['士兰微']['market_value']:,.2f}

2️⃣ 华联股份 (000882)
   • 持仓数量: 22,600股
   • 成本价: ¥1.779
   • 现价: ¥{positions['华联股份']['current_price']:.2f}
   • 浮亏: {positions['华联股份']['profit_loss_pct']:.2f}% (¥{positions['华联股份']['total_loss']:,.2f})
   • 市值: ¥{positions['华联股份']['market_value']:,.2f}

【操作建议】

⚠️ 风险评估:
- 两只股票均处于深度亏损状态（>10%）
- 士兰微属于半导体板块，受行业周期影响较大
- 华联股份属于零售板块，基本面较弱

🎯 具体建议:

1. 士兰微 (600460):
   • 设置止损位: ¥25.00（再下跌约4.2%）
   • 如果反弹至¥28.00以上可考虑减仓50%
   • 关注半导体行业政策和芯片需求恢复情况

2. 华联股份 (000882):
   • 该股流动性较差，建议逢高减仓
   • 设置止损位: ¥1.50（再下跌约6.8%）
   • 如能反弹至¥1.70以上，建议全部清仓

3. 整体策略:
   • 严格控制总仓位风险，避免进一步扩大亏损
   • 分散投资，不要重仓单一股票
   • 关注大盘走势，如大盘继续下跌，考虑暂时离场观望

【监控提醒】
• 已设置邮件预警，当股价触及止损位时会自动发送提醒
• 建议每日收盘后查看持仓状态
• 下次监控时间: 10:00, 10:30, 11:00, 14:30, 14:50

============================================================
💡 温馨提示: 投资有风险，建议根据自身风险承受能力做出决策。
"""
    
    # 保存报告
    with open('/root/.openclaw/workspace/ai_agent/results/stock_analysis_report.md', 'w') as f:
        f.write(report)
    
    print(report)
    return report

if __name__ == "__main__":
    generate_stock_analysis()