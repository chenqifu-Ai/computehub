#!/usr/bin/env python3
"""
华联股份 (000882) 实时监控脚本
获取股票价格、分析趋势、生成预警
"""

import requests
import json
import time
from datetime import datetime

def get_stock_price(stock_code="000882"):
    """获取股票实时价格"""
    try:
        # 使用模拟数据（实际使用时替换为真实API）
        # 这里使用随机波动模拟真实价格变化
        import random
        
        base_price = 1.70  # 基准价格
        fluctuation = random.uniform(-0.05, 0.05)  # ±5%波动
        current_price = round(base_price + fluctuation, 2)
        
        return {
            "code": stock_code,
            "name": "华联股份",
            "price": current_price,
            "change": round(fluctuation, 4),
            "change_percent": round(fluctuation / base_price * 100, 2),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {
            "code": stock_code,
            "name": "华联股份",
            "price": 0,
            "change": 0,
            "change_percent": 0,
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def analyze_trend(price_data):
    """分析股票趋势"""
    change = price_data["change_percent"]
    
    if change > 2:
        trend = "强势上涨"
        signal = "买入"
    elif change > 0.5:
        trend = "小幅上涨"
        signal = "持有"
    elif change > -0.5:
        trend = "平稳"
        signal = "观望"
    elif change > -2:
        trend = "小幅下跌"
        signal = "观察"
    else:
        trend = "大幅下跌"
        signal = "警惕"
    
    return {
        "trend": trend,
        "signal": signal,
        "risk_level": "低" if abs(change) < 1 else "中" if abs(change) < 3 else "高"
    }

def check_stop_loss(price_data, stop_loss_price=1.60):
    """检查止损条件"""
    current_price = price_data["price"]
    
    if current_price <= stop_loss_price:
        return {
            "stop_loss_triggered": True,
            "current_price": current_price,
            "stop_loss_price": stop_loss_price,
            "loss_percent": round((stop_loss_price - current_price) / stop_loss_price * 100, 2),
            "recommendation": "立即止损"
        }
    else:
        distance = current_price - stop_loss_price
        distance_percent = distance / stop_loss_price * 100
        
        return {
            "stop_loss_triggered": False,
            "current_price": current_price,
            "stop_loss_price": stop_loss_price,
            "safe_distance": round(distance, 2),
            "safe_percent": round(distance_percent, 2),
            "recommendation": "继续持有" if distance_percent > 5 else "密切关注"
        }

def generate_report():
    """生成监控报告"""
    # 获取价格数据
    price_data = get_stock_price()
    
    # 分析趋势
    trend_analysis = analyze_trend(price_data)
    
    # 检查止损
    stop_loss_check = check_stop_loss(price_data)
    
    # 生成综合报告
    report = {
        "stock_info": price_data,
        "trend_analysis": trend_analysis,
        "risk_management": stop_loss_check,
        "monitor_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return report

def main():
    """主函数"""
    print("📈 华联股份监控开始...")
    
    report = generate_report()
    
    # 输出报告
    print(f"\n股票代码: {report['stock_info']['code']}")
    print(f"股票名称: {report['stock_info']['name']}")
    print(f"当前价格: ¥{report['stock_info']['price']}")
    print(f"涨跌幅: {report['stock_info']['change_percent']}%")
    print(f"趋势分析: {report['trend_analysis']['trend']}")
    print(f"操作信号: {report['trend_analysis']['signal']}")
    print(f"风险等级: {report['trend_analysis']['risk_level']}")
    print(f"止损状态: {'已触发' if report['risk_management']['stop_loss_triggered'] else '未触发'}")
    print(f"建议: {report['risk_management']['recommendation']}")
    
    # 保存报告
    report_file = "/root/.openclaw/workspace/ai_agent/results/hualian_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 报告已保存至: {report_file}")
    
    return report

if __name__ == "__main__":
    main()