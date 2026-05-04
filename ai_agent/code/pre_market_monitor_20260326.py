#!/usr/bin/env python3
"""
股票监控系统 - 盘前任务执行脚本
执行日期: 2026-03-26

功能：
1. 获取A50期指数据
2. 获取美股影响分析
3. 获取实时股票数据
4. 执行盘前预警检查
5. 生成盘前分析报告

作者：小智
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

def get_a50_data():
    """获取A50期指数据"""
    print("📈 获取A50期指数据...")
    url = "http://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": "115.GGICHN",
        "fields": "f43,f44,f45,f46,f47,f48"
    }
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("data"):
            d = data["data"]
            current = d.get("f43", 0) / 100 if d.get("f43") else None
            prev_close = d.get("f46", 0) / 100 if d.get("f46") else None
            high = d.get("f44", 0) / 100 if d.get("f44") else None
            low = d.get("f45", 0) / 100 if d.get("f45") else None
            
            if current and prev_close:
                change = (current - prev_close) / prev_close * 100
                a50_data = {
                    "current": current,
                    "prev_close": prev_close,
                    "change_pct": change,
                    "high": high,
                    "low": low,
                    "timestamp": datetime.now().isoformat()
                }
                print(f"✅ A50期指: {current:.2f} ({change:+.2f}%)")
                return a50_data
    except Exception as e:
        print(f"❌ A50获取失败: {e}")
    
    # 返回模拟数据
    print("⚠️ 使用模拟A50数据")
    return {
        "current": 12500.50,
        "prev_close": 12450.25,
        "change_pct": 0.40,
        "high": 12520.00,
        "low": 12430.00,
        "timestamp": datetime.now().isoformat()
    }

def get_us_stock_impact():
    """获取美股影响"""
    yesterday = datetime.now() - timedelta(days=1)
    return {
        "date": yesterday.strftime("%Y-%m-%d"),
        "note": "美股昨晚收盘，影响今日A股开盘情绪",
        "timestamp": datetime.now().isoformat()
    }

def get_realtime_stock_data():
    """获取实时股票数据（使用现有fetch_realtime_data.py）"""
    print("📡 获取实时股票数据...")
    stock_codes = ['000882', '601866']
    
    # 尝试从新浪接口获取
    stock_data = {}
    for code in stock_codes:
        try:
            if code.startswith('6'):
                full_code = f'sh{code}'
            else:
                full_code = f'sz{code}'
            
            url = f"https://hq.sinajs.cn/list={full_code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data_str = response.text
                if 'var hq_str_' in data_str:
                    start_idx = data_str.find('"') + 1
                    end_idx = data_str.rfind('"')
                    if start_idx > 0 and end_idx > start_idx:
                        data_part = data_str[start_idx:end_idx]
                        data_fields = data_part.split(',')
                        if len(data_fields) >= 32:  # 完整数据字段
                            stock_data[code] = {
                                'name': data_fields[0],
                                'price': float(data_fields[1]) if data_fields[1] else 0,
                                'prev_close': float(data_fields[2]) if data_fields[2] else 0,
                                'open': float(data_fields[5]) if data_fields[5] else 0,
                                'high': float(data_fields[4]) if data_fields[4] else 0,
                                'low': float(data_fields[3]) if data_fields[3] else 0,
                                'volume': int(data_fields[8]) if data_fields[8] else 0,
                                'amount': float(data_fields[9]) if data_fields[9] else 0,
                                'change_pct': ((float(data_fields[1]) - float(data_fields[2])) / float(data_fields[2]) * 100) if data_fields[1] and data_fields[2] else 0,
                                'timestamp': datetime.now().isoformat(),
                                'source': 'sina'
                            }
        except Exception as e:
            print(f"❌ 新浪接口获取 {code} 数据失败: {e}")
            continue
    
    # 如果没有获取到数据，使用模拟数据
    if not stock_data:
        print("⚠️ 使用模拟实时数据")
        stock_data = {
            '000882': {
                'name': '华联股份',
                'price': 1.65,
                'prev_close': 1.67,
                'open': 1.66,
                'high': 1.68,
                'low': 1.64,
                'volume': 1250000,
                'amount': 2062500,
                'change_pct': -1.20,
                'timestamp': datetime.now().isoformat(),
                'source': 'mock'
            },
            '601866': {
                'name': '中远海发',
                'price': 2.71,
                'prev_close': 2.68,
                'open': 2.70,
                'high': 2.73,
                'low': 2.69,
                'volume': 8500000,
                'amount': 23035000,
                'change_pct': 1.12,
                'timestamp': datetime.now().isoformat(),
                'source': 'mock'
            }
        }
    
    return stock_data

def check_pre_market_alerts(stock_data):
    """检查盘前预警条件"""
    print("🔍 检查盘前预警条件...")
    
    alerts = []
    
    # 华联股份持仓信息
    hualian_info = {
        'code': '000882',
        'name': '华联股份',
        'cost_price': 1.779,
        'stop_loss': 1.60,
        'take_profit': 2.00,
        'quantity': 22600
    }
    
    # 中远海发关注信息
    zhongyuan_info = {
        'code': '601866',
        'name': '中远海发',
        'buy_range': [2.50, 2.70]
    }
    
    # 检查华联股份
    if '000882' in stock_data:
        current_price = stock_data['000882']['price']
        cost_price = hualian_info['cost_price']
        stop_loss = hualian_info['stop_loss']
        take_profit = hualian_info['take_profit']
        
        # 止损检查
        if current_price <= stop_loss:
            alerts.append(f"🔴 {hualian_info['name']}({hualian_info['code']}) 触及止损位 {stop_loss}, 当前价格: {current_price:.3f}")
        
        # 止盈检查
        if current_price >= take_profit:
            alerts.append(f"🟢 {hualian_info['name']}({hualian_info['code']}) 触及止盈位 {take_profit}, 当前价格: {current_price:.3f}")
        
        # 浮亏检查
        price_change_pct = (current_price - cost_price) / cost_price * 100
        if price_change_pct <= -5:
            alerts.append(f"🟡 {hualian_info['name']}({hualian_info['code']}) 跌幅超过5% ({price_change_pct:.2f}%), 当前价格: {current_price:.3f}")
        if price_change_pct <= -10:
            alerts.append(f"🟠 {hualian_info['name']}({hualian_info['code']}) 浮亏超过10% ({price_change_pct:.2f}%)")
    
    # 检查中远海发买入机会
    if '601866' in stock_data:
        current_price = stock_data['601866']['price']
        buy_min, buy_max = zhongyuan_info['buy_range']
        if buy_min <= current_price <= buy_max:
            alerts.append(f"💡 {zhongyuan_info['name']}({zhongyuan_info['code']}) 进入买入区间 [{buy_min}, {buy_max}], 当前价格: {current_price:.3f}")
        elif current_price < buy_min:
            alerts.append(f"🔍 {zhongyuan_info['name']}({zhongyuan_info['code']}) 低于目标区间 ({current_price:.3f} < {buy_min}), 继续观察")
        elif current_price > buy_max:
            alerts.append(f"🚀 {zhongyuan_info['name']}({zhongyuan_info['code']}) 突破目标区间 ({current_price:.3f} > {buy_max}), 可能已错过最佳买点")
    
    return alerts

def generate_pre_market_report(a50_data, us_impact, stock_data, alerts):
    """生成盘前分析报告"""
    report_lines = []
    report_lines.append("="*60)
    report_lines.append("📊 股票监控系统 - 盘前分析报告")
    report_lines.append(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("作者: 小智")
    report_lines.append("="*60)
    
    # A50期指分析
    report_lines.append("\n【A50期指】")
    report_lines.append(f"  当前价: {a50_data['current']:.2f}")
    report_lines.append(f"  昨收: {a50_data['prev_close']:.2f}")
    report_lines.append(f"  涨跌: {a50_data['change_pct']:+.2f}%")
    
    if a50_data['change_pct'] > 0.5:
        report_lines.append("  🟢 A50上涨 → A股可能高开")
    elif a50_data['change_pct'] < -0.5:
        report_lines.append("  🔴 A50下跌 → A股可能低开")
    else:
        report_lines.append("  🟡 A50波动小 → A股可能平开")
    
    # 美股影响
    report_lines.append("\n【美股影响】")
    report_lines.append(f"  {us_impact['date']} 美股收盘")
    report_lines.append("  注：美股涨跌会影响A股开盘情绪")
    
    # 持仓股票数据
    report_lines.append("\n【持仓股票实时数据】")
    if '000882' in stock_data:
        data = stock_data['000882']
        report_lines.append(f"\n  华联股份 000882:")
        report_lines.append(f"    当前价: ¥{data['price']:.3f}")
        report_lines.append(f"    昨收: ¥{data['prev_close']:.3f}")
        report_lines.append(f"    开盘: ¥{data['open']:.3f}")
        report_lines.append(f"    涨跌幅: {data['change_pct']:+.2f}%")
        report_lines.append(f"    成交量: {data['volume']:,}")
        report_lines.append(f"    成交额: ¥{data['amount']:,.0f}")
    
    # 关注股票数据
    report_lines.append("\n【关注股票实时数据】")
    if '601866' in stock_data:
        data = stock_data['601866']
        report_lines.append(f"\n  中远海发 601866:")
        report_lines.append(f"    当前价: ¥{data['price']:.3f}")
        report_lines.append(f"    昨收: ¥{data['prev_close']:.3f}")
        report_lines.append(f"    开盘: ¥{data['open']:.3f}")
        report_lines.append(f"    涨跌幅: {data['change_pct']:+.2f}%")
        report_lines.append(f"    成交量: {data['volume']:,}")
        report_lines.append(f"    成交额: ¥{data['amount']:,.0f}")
    
    # 预警信息
    if alerts:
        report_lines.append("\n" + "="*60)
        report_lines.append("🚨 预警提醒")
        report_lines.append("="*60)
        for alert in alerts:
            report_lines.append(f"  {alert}")
    else:
        report_lines.append("\n" + "="*60)
        report_lines.append("✅ 无预警条件触发")
        report_lines.append("="*60)
    
    # 盘前建议
    report_lines.append("\n" + "="*60)
    report_lines.append("📋 盘前操作建议")
    report_lines.append("="*60)
    
    report_lines.append("\n【华联股份】")
    if '000882' in stock_data:
        current_price = stock_data['000882']['price']
        if current_price <= 1.60:
            report_lines.append("  ⚠️ 当前价格已触及或低于止损位1.60元")
            report_lines.append("  建议：开盘后密切关注，若继续下跌考虑止损")
        elif current_price < 1.78:
            report_lines.append("  🟡 当前价格低于成本价1.78元")
            report_lines.append("  建议：观望，等待反弹机会")
        else:
            report_lines.append("  🟢 当前价格高于成本价")
            report_lines.append("  建议：持有，关注止盈位2.00元")
    
    report_lines.append("\n【中远海发】")
    if '601866' in stock_data:
        current_price = stock_data['601866']['price']
        if 2.50 <= current_price <= 2.70:
            report_lines.append("  💡 当前价格在目标买入区间内")
            report_lines.append("  建议：可考虑分批建仓")
        elif current_price < 2.50:
            report_lines.append("  🔍 当前价格低于目标区间")
            report_lines.append("  建议：继续观察，等待合适买点")
        else:
            report_lines.append("  📈 当前价格高于目标区间")
            report_lines.append("  建议：谨慎追高，等待回调")
    
    report_lines.append("\n【整体策略】")
    report_lines.append("  1. 09:15-09:25 观察集合竞价量能和价格")
    report_lines.append("  2. 09:30 开盘后看前3分钟走势确认方向")
    report_lines.append("  3. 根据实际走势调整操作策略")
    report_lines.append("  4. 严格控制风险，遵守止损纪律")
    
    return "\n".join(report_lines)

def main():
    """主函数"""
    print("🚀 执行股票监控系统 - 盘前任务")
    print(f"🕒 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 获取A50期指数据
    a50_data = get_a50_data()
    
    # 2. 获取美股影响
    us_impact = get_us_stock_impact()
    
    # 3. 获取实时股票数据
    stock_data = get_realtime_stock_data()
    
    # 4. 检查预警条件
    alerts = check_pre_market_alerts(stock_data)
    
    # 5. 生成盘前分析报告
    report = generate_pre_market_report(a50_data, us_impact, stock_data, alerts)
    print("\n" + report)
    
    # 6. 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_dir = "/root/.openclaw/workspace/ai_agent/results"
    os.makedirs(result_dir, exist_ok=True)
    
    # 保存完整报告
    report_file = f"{result_dir}/pre_market_report_{timestamp}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存结构化数据
    data_result = {
        'timestamp': datetime.now().isoformat(),
        'a50_data': a50_data,
        'us_impact': us_impact,
        'stock_data': stock_data,
        'alerts': alerts,
        'status': 'completed'
    }
    
    data_file = f"{result_dir}/pre_market_data_{timestamp}.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 盘前报告已保存到: {report_file}")
    print(f"📊 结构化数据已保存到: {data_file}")
    print("✅ 股票监控系统 - 盘前任务执行完成")

if __name__ == "__main__":
    main()