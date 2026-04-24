#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据抓取与分析脚本
数据源：东方财富、新浪财经

抓取内容：
1. A50期指 - 判断A股开盘方向
2. 北向资金流向 - 外资动向
3. 龙虎榜数据 - 主力动向
4. 士兰微(600460)和华联股份(000882)的实时数据

时间：2026-03-24
"""

import requests
import json
import re
from datetime import datetime
from pathlib import Path

# 结果保存目录
RESULTS_DIR = Path("/root/.openclaw/workspace/ai_agent/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'http://data.eastmoney.com/',
}

def fetch_a50():
    """
    抓取A50期指数据 - 富时中国A50指数期货
    用于判断A股开盘方向
    """
    print("\n" + "="*60)
    print("📊 1. A50期指数据")
    print("="*60)
    
    result = {
        'success': False,
        'data': {},
        'source': '',
        'error': None
    }
    
    try:
        # 东方财富A50期指接口
        # 富时中国A50指数期货代码: CN0Y (主力合约)
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'fid': 'f3',
            'poist': 'f1',
            'fs': 'b:CN0Y',
            'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18',
            'ut': 'b2884a393a59ad64002292a3e90d46a5'
        }
        
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        
        if data.get('data') and data['data'].get('diff'):
            item = data['data']['diff'][0]
            result['data'] = {
                'code': item.get('f12', 'CN0Y'),  # 代码
                'name': item.get('f14', '富时中国A50'),  # 名称
                'price': item.get('f2', 0),  # 最新价
                'change': item.get('f3', 0),  # 涨跌幅
                'change_amount': item.get('f4', 0),  # 涨跌额
                'volume': item.get('f5', 0),  # 成交量
                'amount': item.get('f6', 0),  # 成交额
                'open': item.get('f17', 0),  # 开盘价
                'prev_close': item.get('f18', 0),  # 昨收
            }
            result['success'] = True
            result['source'] = '东方财富'
            
            print(f"✅ 获取成功")
            print(f"  代码：{result['data']['code']}")
            print(f"  名称：{result['data']['name']}")
            print(f"  最新价：{result['data']['price']}")
            print(f"  涨跌幅：{result['data']['change']}%")
            print(f"  涨跌额：{result['data']['change_amount']}")
        else:
            # 备用：新浪财经接口
            print("  东方财富数据为空，尝试新浪财经...")
            url2 = "http://hq.sinajs.cn/list=nf_CN0Y"
            resp2 = requests.get(url2, headers=HEADERS, timeout=10)
            resp2.encoding = 'gbk'
            
            # 解析数据
            match = re.search(r'"([^"]+)"', resp2.text)
            if match:
                parts = match.group(1).split(',')
                if len(parts) >= 6:
                    result['data'] = {
                        'code': 'CN0Y',
                        'name': '富时中国A50期指',
                        'price': float(parts[0]) if parts[0] else 0,
                        'change': float(parts[1]) if parts[1] else 0,
                        'volume': int(parts[5]) if parts[5] else 0,
                    }
                    result['success'] = True
                    result['source'] = '新浪财经'
                    print(f"✅ 新浪数据获取成功")
            
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ 获取失败：{e}")
    
    return result


def fetch_north_money():
    """
    抓取北向资金流向数据
    外资动向分析
    """
    print("\n" + "="*60)
    print("💰 2. 北向资金流向")
    print("="*60)
    
    result = {
        'success': False,
        'data': {},
        'source': '',
        'error': None
    }
    
    try:
        # 东方财富北向资金接口
        url = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        params = {
            'lmt': '0',
            'klt': '101',
            'secid': '1.000001',  # 上证指数
            'fields1': 'f1,f2,f3,f4,f5,f6,f7',
            'fields2': 'f51,f52,f53,f54,f55,f56',
            'ut': 'b2884a393a59ad64002292a3e90d46a5'
        }
        
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        
        if data.get('data') and data['data'].get('klines'):
            # 取最近的数据
            klines = data['data']['klines']
            if klines:
                latest = klines[-1].split(',') if isinstance(klines[-1], str) else klines[-1]
                
                # 北向资金净流入数据
                result['data'] = {
                    'date': latest[0] if len(latest) > 0 else '',
                    'north_net_inflow': float(latest[1]) if len(latest) > 1 else 0,  # 北向净流入
                    'south_net_inflow': float(latest[2]) if len(latest) > 2 else 0,  # 南向净流入
                }
                result['success'] = True
                result['source'] = '东方财富'
                
                print(f"✅ 获取成功")
                print(f"  日期：{result['data']['date']}")
                print(f"  北向净流入：{result['data']['north_net_inflow']:.2f}亿")
                print(f"  南向净流入：{result['data']['south_net_inflow']:.2f}亿")
        
        # 如果上面接口失败，尝试另一个接口
        if not result['success']:
            url2 = "http://data.eastmoney.com/hsgt/2.html"
            # 北向资金汇总数据
            url3 = "http://push2.eastmoney.com/api/qt/clist/get"
            params3 = {
                'fid': 'f3',
                'poist': 'f1',
                'fs': 'm:1,m:2',
                'fields': 'f1,f2,f3,f4,f5,f6',
                'ut': 'b2884a393a59ad64002292a3e90d46a5'
            }
            
            # 使用北向资金专用接口
            url4 = "http://push2.eastmoney.com/api/qt/stock/get"
            params4 = {
                'secid': '1.000001',
                'fields': 'f51,f52,f53,f54,f55,f56',
                'ut': 'b2884a393a59ad64002292a3e90d46a5'
            }
            
            resp4 = requests.get(url4, params=params4, headers=HEADERS, timeout=10)
            data4 = resp4.json()
            
            if data4.get('data'):
                d = data4['data']
                result['data'] = {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'north_net_inflow': d.get('f51', 0) / 100000000 if d.get('f51') else 0,  # 转换为亿
                }
                result['success'] = True
                result['source'] = '东方财富(备用)'
                print(f"✅ 备用接口获取成功")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ 获取失败：{e}")
    
    return result


def fetch_longhubang():
    """
    抓取龙虎榜数据
    主力动向分析
    """
    print("\n" + "="*60)
    print("📈 3. 龙虎榜数据")
    print("="*60)
    
    result = {
        'success': False,
        'data': [],
        'source': '',
        'error': None
    }
    
    try:
        # 东方财富龙虎榜接口
        today = datetime.now().strftime('%Y-%m-%d')
        url = "http://data.eastmoney.com/DataAPI_v3.ashx"
        params = {
            'sortColumns': 'f1',
            'sortTypes': '-1',
            'pageSize': '20',
            'pageNumber': '1',
            'reportName': 'R_BILLBOARD_DAILY',
            'columns': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15',
            'source': 'WEB',
            'client': 'WEB',
            'filter': f'(f1="{today}")'
        }
        
        # 备用接口 - 最近龙虎榜
        url2 = "http://push2.eastmoney.com/api/qt/clist/get"
        params2 = {
            'fid': 'f3',
            'poist': 'f1',
            'fs': 'b:MK0022',
            'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14',
            'ut': 'b2884a393a59ad64002292a3e90d46a5'
        }
        
        resp = requests.get(url2, params=params2, headers=HEADERS, timeout=10)
        data = resp.json()
        
        if data.get('data') and data['data'].get('diff'):
            items = data['data']['diff'][:10]  # 取前10个
            
            for item in items:
                stock_data = {
                    'code': item.get('f12', ''),
                    'name': item.get('f14', ''),
                    'price': item.get('f2', 0),
                    'change_pct': item.get('f3', 0),
                    'turnover_rate': item.get('f8', 0),
                    'net_buy': item.get('f5', 0),  # 净买入
                }
                result['data'].append(stock_data)
            
            result['success'] = True
            result['source'] = '东方财富'
            
            print(f"✅ 获取成功，共 {len(result['data'])} 条")
            for i, item in enumerate(result['data'][:5], 1):
                print(f"  {i}. {item['name']}({item['code']}): {item['change_pct']}%")
        else:
            print("  ⚠️ 今日暂无龙虎榜数据")
            
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ 获取失败：{e}")
    
    return result


def fetch_stock_realtime(code, name):
    """
    抓取单个股票的实时数据
    """
    print(f"\n  获取 {name}({code})...")
    
    result = {
        'code': code,
        'name': name,
        'success': False,
        'data': {},
        'error': None
    }
    
    try:
        # 新浪财经接口（免费、稳定）
        # 代码格式：sh600460（上海）或 sz000882（深圳）
        prefix = 'sh' if code.startswith('6') else 'sz'
        full_code = f"{prefix}{code}"
        
        url = f"http://hq.sinajs.cn/list={full_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn/'
        }
        
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        
        # 解析数据
        match = re.search(r'"([^"]+)"', resp.text)
        if match:
            data_str = match.group(1)
            parts = data_str.split(',')
            
            if len(parts) >= 32:
                result['data'] = {
                    'name': parts[0],
                    'open': float(parts[1]) if parts[1] else 0,
                    'prev_close': float(parts[2]) if parts[2] else 0,
                    'price': float(parts[3]) if parts[3] else 0,
                    'high': float(parts[4]) if parts[4] else 0,
                    'low': float(parts[5]) if parts[5] else 0,
                    'bid': float(parts[6]) if parts[6] else 0,  # 买一价
                    'ask': float(parts[7]) if parts[7] else 0,  # 卖一价
                    'volume': int(float(parts[8])) if parts[8] else 0,  # 成交量（股）
                    'amount': float(parts[9]) if parts[9] else 0,  # 成交额（元）
                    'date': parts[30],
                    'time': parts[31],
                }
                
                # 计算涨跌
                if result['data']['prev_close'] > 0:
                    change = result['data']['price'] - result['data']['prev_close']
                    change_pct = (change / result['data']['prev_close']) * 100
                    result['data']['change'] = round(change, 2)
                    result['data']['change_pct'] = round(change_pct, 2)
                else:
                    result['data']['change'] = 0
                    result['data']['change_pct'] = 0
                
                result['success'] = True
                
    except Exception as e:
        result['error'] = str(e)
    
    return result


def fetch_holdings():
    """
    抓取持仓股票实时数据
    - 士兰微(600460)
    - 华联股份(000882)
    """
    print("\n" + "="*60)
    print("📊 4. 持仓股票实时数据")
    print("="*60)
    
    holdings = [
        {'code': '600460', 'name': '士兰微'},
        {'code': '000882', 'name': '华联股份'},
    ]
    
    results = []
    
    for stock in holdings:
        data = fetch_stock_realtime(stock['code'], stock['name'])
        results.append(data)
        
        if data['success']:
            d = data['data']
            print(f"  ✅ {d['name']}({stock['code']})")
            print(f"     最新价：{d['price']}  涨跌：{d['change']} ({d['change_pct']}%)")
            print(f"     今开：{d['open']}  最高：{d['high']}  最低：{d['low']}")
            print(f"     成交量：{d['volume']/10000:.2f}万手  成交额：{d['amount']/100000000:.2f}亿")
        else:
            print(f"  ❌ {stock['name']}({stock['code']}) 获取失败：{data.get('error')}")
    
    return results


def analyze_impact(a50_data, north_data, lhb_data, holdings_data):
    """
    分析数据对持仓股票的影响
    """
    print("\n" + "="*60)
    print("📋 综合分析与建议")
    print("="*60)
    
    analysis = {
        'a50_signal': '',
        'north_signal': '',
        'lhb_signal': '',
        'holdings_impact': [],
        'suggestions': []
    }
    
    # A50期指分析
    if a50_data['success']:
        change = a50_data['data'].get('change', 0)
        if change > 0.5:
            analysis['a50_signal'] = f"🟢 A50涨{change}%，A股高开概率大"
        elif change < -0.5:
            analysis['a50_signal'] = f"🔴 A50跌{change}%，A股低开概率大"
        else:
            analysis['a50_signal'] = f"🟡 A50变动{change}%，A股平开可能"
        print(f"\n【A50信号】{analysis['a50_signal']}")
    else:
        analysis['a50_signal'] = "⚠️ A50数据获取失败"
        print(f"\n【A50信号】{analysis['a50_signal']}")
    
    # 北向资金分析
    if north_data['success']:
        inflow = north_data['data'].get('north_net_inflow', 0)
        if inflow > 50:
            analysis['north_signal'] = f"🟢 北向资金大幅流入{inflow:.2f}亿，外资看好A股"
        elif inflow > 0:
            analysis['north_signal'] = f"🟡 北向资金小幅流入{inflow:.2f}亿，外资态度谨慎偏多"
        elif inflow > -50:
            analysis['north_signal'] = f"🟠 北向资金流出{abs(inflow):.2f}亿，外资有所撤离"
        else:
            analysis['north_signal'] = f"🔴 北向资金大幅流出{abs(inflow):.2f}亿，外资看空A股"
        print(f"【北向资金】{analysis['north_signal']}")
    else:
        analysis['north_signal'] = "⚠️ 北向资金数据获取失败"
        print(f"【北向资金】{analysis['north_signal']}")
    
    # 龙虎榜分析
    if lhb_data['success'] and lhb_data['data']:
        analysis['lhb_signal'] = f"📊 今日龙虎榜{len(lhb_data['data'])}只个股上榜，关注主力动向"
        print(f"【龙虎榜】{analysis['lhb_signal']}")
        
        # 检查持仓股票是否上龙虎榜
        holdings_codes = ['600460', '000882']
        for item in lhb_data['data']:
            if item['code'] in holdings_codes:
                print(f"  ⚠️ 持仓股票 {item['name']}({item['code']}) 上榜！")
    else:
        analysis['lhb_signal'] = "⚠️ 龙虎榜数据获取失败或暂无数据"
        print(f"【龙虎榜】{analysis['lhb_signal']}")
    
    # 持仓股票分析
    print("\n【持仓分析】")
    for stock in holdings_data:
        if stock['success']:
            d = stock['data']
            change_pct = d.get('change_pct', 0)
            
            impact = {
                'code': stock['code'],
                'name': stock['name'],
                'price': d['price'],
                'change_pct': change_pct,
                'signal': ''
            }
            
            # 判断信号
            if change_pct > 5:
                impact['signal'] = f"🟢 {stock['name']}大涨{change_pct}%，注意止盈"
            elif change_pct > 2:
                impact['signal'] = f"🟢 {stock['name']}上涨{change_pct}%，走势良好"
            elif change_pct > 0:
                impact['signal'] = f"🟡 {stock['name']}微涨{change_pct}%，观望"
            elif change_pct > -2:
                impact['signal'] = f"🟡 {stock['name']}微跌{change_pct}%，正常波动"
            elif change_pct > -5:
                impact['signal'] = f"🟠 {stock['name']}下跌{change_pct}%，关注支撑"
            else:
                impact['signal'] = f"🔴 {stock['name']}大跌{change_pct}%，注意止损"
            
            analysis['holdings_impact'].append(impact)
            print(f"  {impact['signal']}")
    
    # 综合建议
    print("\n【盘前建议】")
    
    suggestions = []
    
    # 根据A50判断开盘
    if a50_data['success']:
        a50_change = a50_data['data'].get('change', 0)
        if a50_change > 1:
            suggestions.append("📈 A50大涨，开盘可考虑逢高减仓")
        elif a50_change < -1:
            suggestions.append("📉 A50大跌，开盘谨慎，避免恐慌杀跌")
    
    # 根据北向资金
    if north_data['success']:
        inflow = north_data['data'].get('north_net_inflow', 0)
        if inflow < -30:
            suggestions.append("⚠️ 北向资金大幅流出，控制仓位，关注蓝筹股")
        elif inflow > 30:
            suggestions.append("💪 北向资金大幅流入，可适当参与")
    
    # 个股建议
    for stock in holdings_data:
        if stock['success']:
            change = stock['data'].get('change_pct', 0)
            name = stock['name']
            code = stock['code']
            
            if code == '600460':  # 士兰微
                if change < -3:
                    suggestions.append(f"📉 士兰微跌幅较大，关注60日线支撑，跌破考虑止损")
                elif change > 3:
                    suggestions.append(f"📈 士兰微涨幅较好，可持有等待更高位置")
            
            if code == '000882':  # 华联股份
                if change < -3:
                    suggestions.append(f"📉 华联股份跌幅较大，关注量能变化，缩量下跌可持有")
                elif change > 3:
                    suggestions.append(f"📈 华联股份表现强势，注意上方压力位")
    
    if not suggestions:
        suggestions.append("📊 今日数据正常，按计划操作，注意风险控制")
    
    analysis['suggestions'] = suggestions
    
    for i, s in enumerate(suggestions, 1):
        print(f"  {i}. {s}")
    
    return analysis


def save_results(a50, north, lhb, holdings, analysis):
    """
    保存结果到文件
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_file = RESULTS_DIR / f"stock_analysis_{timestamp}.json"
    
    data = {
        'timestamp': datetime.now().isoformat(),
        'data': {
            'a50': a50,
            'north_money': north,
            'longhubang': lhb,
            'holdings': holdings,
            'analysis': analysis
        }
    }
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 结果已保存：{result_file}")
    
    return result_file


def main():
    """
    主函数
    """
    print("="*60)
    print("🚀 股票数据抓取与分析")
    print(f"   时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 1. A50期指
    a50_data = fetch_a50()
    
    # 2. 北向资金
    north_data = fetch_north_money()
    
    # 3. 龙虎榜
    lhb_data = fetch_longhubang()
    
    # 4. 持仓股票
    holdings_data = fetch_holdings()
    
    # 5. 综合分析
    analysis = analyze_impact(a50_data, north_data, lhb_data, holdings_data)
    
    # 6. 保存结果
    result_file = save_results(a50_data, north_data, lhb_data, holdings_data, analysis)
    
    print("\n" + "="*60)
    print("✅ 数据抓取完成")
    print("="*60)
    
    return {
        'a50': a50_data,
        'north': north_data,
        'lhb': lhb_data,
        'holdings': holdings_data,
        'analysis': analysis,
        'result_file': str(result_file)
    }


if __name__ == "__main__":
    result = main()