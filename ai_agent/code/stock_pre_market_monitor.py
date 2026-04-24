#!/usr/bin/env python3
"""
股票监控系统 - 盘前任务
执行时间: 开盘前 (8:00-9:00)
"""

import requests
import sys
import json
from datetime import datetime
import os

def get_stock_price(stock_code):
    """获取股票价格"""
    try:
        # 使用新浪股票API
        if stock_code.startswith('6'):
            prefix = 'sh'
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            prefix = 'sz'
        else:
            prefix = 'sh'
        
        url = f"https://hq.sinajs.cn/list={prefix}{stock_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gb2312'
        
        data = response.text
        if 'var hq_str_' in data and '=' in data:
            stock_data = data.split('="')[1].split('"')[0]
            parts = stock_data.split(',')
            
            if len(parts) > 3:
                return {
                    'name': parts[0],
                    'price': float(parts[3]),
                    'open': float(parts[1]) if parts[1] else 0,
                    'prev_close': float(parts[2]) if parts[2] else 0,
                    'high': float(parts[4]) if parts[4] else 0,
                    'low': float(parts[5]) if parts[5] else 0,
                    'volume': int(parts[8]) if parts[8] else 0,
                    'amount': float(parts[9]) if parts[9] else 0,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        
        return None
    except Exception as e:
        print(f"获取股价失败: {e}")
        return None

def check_hualian_stock():
    """检查华联股份持仓状态"""
    stock_code = "000882"
    stock_data = get_stock_price(stock_code)
    
    if not stock_data:
        return {
            'status': 'error',
            'message': '无法获取华联股份数据'
        }
    
    # 持仓信息
    holdings = 13500
    cost_price = 1.873
    stop_loss = 1.60
    
    current_price = stock_data['price']
    current_value = holdings * current_price
    total_cost = holdings * cost_price
    profit_loss = current_value - total_cost
    profit_loss_pct = (profit_loss / total_cost) * 100
    stop_loss_distance = ((current_price - stop_loss) / current_price) * 100
    
    return {
        'status': 'success',
        'stock_code': stock_code,
        'name': stock_data['name'],
        'current_price': current_price,
        'holdings': holdings,
        'cost_price': cost_price,
        'stop_loss': stop_loss,
        'current_value': current_value,
        'profit_loss': profit_loss,
        'profit_loss_pct': profit_loss_pct,
        'stop_loss_distance': stop_loss_distance,
        'risk_level': 'high' if stop_loss_distance < 5 else 'medium' if stop_loss_distance < 10 else 'low'
    }

def check_coscoshipping():
    """检查中远海发买入机会"""
    stock_code = "601866"
    stock_data = get_stock_price(stock_code)
    
    if not stock_data:
        return {
            'status': 'error',
            'message': '无法获取中远海发数据'
        }
    
    target_min = 2.50
    target_max = 2.70
    current_price = stock_data['price']
    
    in_range = target_min <= current_price <= target_max
    
    return {
        'status': 'success',
        'stock_code': stock_code,
        'name': stock_data['name'],
        'current_price': current_price,
        'target_range': [target_min, target_max],
        'in_range': in_range,
        'opportunity': 'buy' if in_range else 'wait'
    }

def generate_report(hualian_result, cosco_result):
    """生成盘前报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report = f"""# 📊 股票监控系统 - 盘前报告
## 🔍 报告时间: {now}

"""
    
    # 华联股份部分
    if hualian_result['status'] == 'success':
        report += f"""## 📈 华联股份 ({hualian_result['stock_code']})
- **当前价格**: ¥{hualian_result['current_price']:.2f}
- **持仓数量**: {hualian_result['holdings']:,}股
- **成本价格**: ¥{hualian_result['cost_price']:.3f}
- **当前市值**: ¥{hualian_result['current_value']:,.2f}
- **浮动盈亏**: ¥{hualian_result['profit_loss']:,.2f} ({hualian_result['profit_loss_pct']:+.2f}%)
- **止损价位**: ¥{hualian_result['stop_loss']:.2f}
- **安全空间**: {hualian_result['stop_loss_distance']:.1f}%
- **风险等级**: {hualian_result['risk_level'].upper()}

### 🎯 操作建议
"""
        if hualian_result['profit_loss_pct'] < -10:
            report += "- ❗ **亏损超10%**，建议减仓70%降低风险\n"
            report += f"- 减仓数量: {int(hualian_result['holdings'] * 0.7):,}股\n"
            report += f"- 预计回收资金: ¥{(hualian_result['current_price'] * hualian_result['holdings'] * 0.7):,.2f}\n"
        elif hualian_result['stop_loss_distance'] < 5:
            report += "- ⚠️ **接近止损位**，建议密切关注\n"
            report += "- 如跌破¥1.60立即全部止损\n"
        else:
            report += "- ✅ 当前风险可控，继续持有观察\n"
    else:
        report += f"## 📈 华联股份\n- ❌ {hualian_result['message']}\n"
    
    report += "\n"
    
    # 中远海发部分
    if cosco_result['status'] == 'success':
        report += f"""## 📊 中远海发 ({cosco_result['stock_code']})
- **当前价格**: ¥{cosco_result['current_price']:.2f}
- **目标区间**: ¥{cosco_result['target_range'][0]:.2f} - ¥{cosco_result['target_range'][1]:.2f}
- **状态**: {'✅ 在买入区间' if cosco_result['in_range'] else '⏳ 等待回调'}

### 💡 机会分析
"""
        if cosco_result['in_range']:
            report += "- 🎯 **买入机会出现**！建议考虑建仓\n"
            report += "- 可用资金来自华联股份减仓回收\n"
        else:
            report += "- 继续等待价格回调至目标区间\n"
            if cosco_result['current_price'] > cosco_result['target_range'][1]:
                diff = cosco_result['current_price'] - cosco_result['target_range'][1]
                diff_pct = (diff / cosco_result['current_price']) * 100
                report += f"- 需要下跌¥{diff:.2f} ({diff_pct:.1f}%) 才进入买入区间\n"
    else:
        report += f"## 📊 中远海发\n- ❌ {cosco_result['message']}\n"
    
    report += f"""\n
## 🔔 后续监控计划
- 每30分钟检查一次华联股份价格
- 中远海发价格进入¥2.50-2.70区间时立即提醒
- 跌破止损位¥1.60时自动发送紧急提醒

---
*股票监控系统 v2.1 | 执行时间: {now}*
"""
    
    return report

def main():
    print("🔍 执行股票监控系统 - 盘前任务...")
    print(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查华联股份
    print("\n📊 检查华联股份 (000882)...")
    hualian_result = check_hualian_stock()
    
    # 检查中远海发
    print("📊 检查中远海发 (601866)...")
    cosco_result = check_coscoshipping()
    
    # 生成报告
    report = generate_report(hualian_result, cosco_result)
    
    # 保存报告
    report_file = f"/root/.openclaw/workspace/memory/{datetime.now().strftime('%Y-%m-%d')}-stock-pre-market-report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 盘前报告已生成: {report_file}")
    print("\n📋 报告摘要:")
    
    if hualian_result['status'] == 'success':
        print(f"   华联股份: ¥{hualian_result['current_price']:.2f} ({hualian_result['profit_loss_pct']:+.2f}%)")
        print(f"   风险等级: {hualian_result['risk_level'].upper()}")
    
    if cosco_result['status'] == 'success':
        status = "✅ 买入机会" if cosco_result['in_range'] else "⏳ 等待"
        print(f"   中远海发: ¥{cosco_result['current_price']:.2f} ({status})")
    
    # 输出完整报告到stdout
    print("\n" + "="*60)
    print(report)
    print("="*60)

if __name__ == "__main__":
    main()