#!/usr/bin/env python3
"""
集合竞价分析脚本

功能：
- 分析集合竞价阶段的股票表现
- 识别强势/弱势股
- 提供开盘建议

作者：小智
日期：2026-03-25
"""

import json
import os
from datetime import datetime

def analyze_call_auction(stock_data):
    """
    分析集合竞价数据
    
    Args:
        stock_data: 股票实时数据字典
    
    Returns:
        分析结果字典
    """
    analysis_results = {}
    
    for code, data in stock_data.items():
        price = data.get('price', 0)
        change_pct = data.get('change_pct', 0)
        
        # 获取持仓信息
        holding_info = None
        if code == '000882':  # 华联股份
            holding_info = {
                'cost_price': 1.779,
                'stop_loss': 1.60,
                'take_profit': 2.00,
                'quantity': 22600
            }
        
        analysis = {
            'stock_code': code,
            'stock_name': data.get('name', '未知'),
            'current_price': price,
            'change_pct': change_pct,
            'timestamp': data.get('timestamp'),
            'recommendations': []
        }
        
        # 分析逻辑
        if change_pct > 3:
            analysis['recommendations'].append("🟢 强势上涨，可考虑持有或加仓")
        elif change_pct < -3:
            analysis['recommendations'].append("🔴 弱势下跌，需谨慎")
        else:
            analysis['recommendations'].append("🟡 震荡整理，观望为主")
        
        # 持仓股特殊分析
        if holding_info:
            cost_price = holding_info['cost_price']
            stop_loss = holding_info['stop_loss']
            take_profit = holding_info['take_profit']
            
            if price <= stop_loss:
                analysis['recommendations'].append(f"⚠️ 触及止损位 {stop_loss}，建议考虑止损")
            elif price >= take_profit:
                analysis['recommendations'].append(f"🎯 触及止盈位 {take_profit}，建议考虑止盈")
            elif price < cost_price * 0.9:
                analysis['recommendations'].append("📉 浮亏较大，密切关注")
            elif price > cost_price * 1.1:
                analysis['recommendations'].append("📈 盈利良好，可考虑部分止盈")
        
        # 关注股分析
        if code == '601866':  # 中远海发
            buy_min, buy_max = 2.50, 2.70
            if buy_min <= price <= buy_max:
                analysis['recommendations'].append(f"💡 进入目标买入区间 [{buy_min}, {buy_max}]，可考虑建仓")
            elif price < buy_min:
                analysis['recommendations'].append(f"🔍 低于目标区间，继续观察")
            elif price > buy_max:
                analysis['recommendations'].append(f"🚀 突破目标区间，可能已错过最佳买点")
        
        analysis_results[code] = analysis
    
    return analysis_results

def generate_call_auction_report(analysis_results):
    """
    生成集合竞价分析报告
    """
    report_lines = []
    report_lines.append("📊 集合竞价分析报告")
    report_lines.append("=" * 50)
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    for code, analysis in analysis_results.items():
        report_lines.append(f"股票: {analysis['stock_name']} ({code})")
        report_lines.append(f"当前价格: ¥{analysis['current_price']:.3f}")
        report_lines.append(f"涨跌幅: {analysis['change_pct']:+.2f}%")
        report_lines.append("操作建议:")
        for rec in analysis['recommendations']:
            report_lines.append(f"  • {rec}")
        report_lines.append("-" * 30)
    
    return "\n".join(report_lines)

def main():
    """主函数"""
    print("🔍 执行集合竞价分析...")
    
    # 读取最新的实时数据
    data_dir = "/root/.openclaw/workspace/ai_agent/results"
    latest_data_file = None
    
    try:
        # 查找最新的实时数据文件
        import glob
        data_files = glob.glob(os.path.join(data_dir, "realtime_data_*.json"))
        if data_files:
            latest_data_file = max(data_files, key=os.path.getctime)
            with open(latest_data_file, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
            print(f"✅ 使用最新实时数据: {os.path.basename(latest_data_file)}")
        else:
            # 使用默认数据
            stock_data = {
                '000882': {'name': '华联股份', 'price': 1.65, 'change_pct': -7.25},
                '601866': {'name': '中远海发', 'price': 2.71, 'change_pct': 4.63}
            }
            print("⚠️ 未找到实时数据文件，使用默认数据")
    except Exception as e:
        print(f"❌ 读取实时数据失败: {e}")
        stock_data = {
            '000882': {'name': '华联股份', 'price': 1.65, 'change_pct': -7.25},
            '601866': {'name': '中远海发', 'price': 2.71, 'change_pct': 4.63}
        }
    
    # 执行分析
    analysis_results = analyze_call_auction(stock_data)
    
    # 生成报告
    report = generate_call_auction_report(analysis_results)
    print("\n" + report)
    
    # 保存分析结果
    result_file = f"/root/.openclaw/workspace/ai_agent/results/call_auction_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 分析报告已保存到: {result_file}")
    print("✅ 集合竞价分析完成")

if __name__ == "__main__":
    main()