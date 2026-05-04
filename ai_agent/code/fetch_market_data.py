#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充抓取：A50期指和北向资金
使用备用接口
"""

import requests
import json
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Referer': 'http://quote.eastmoney.com/',
}

def fetch_a50_simple():
    """A50期指 - 简化接口"""
    print("\n" + "="*60)
    print("📊 A50期指数据（备用接口）")
    print("="*60)
    
    result = {'success': False, 'data': {}, 'source': '', 'error': None}
    
    try:
        # 方法1：新浪全球期货接口
        # CN0Y 是富时A50期货代码
        urls = [
            ("新浪期货", f"http://hq.sinajs.cn/list=nf_CN0Y"),
            ("新浪期货2", f"http://stock.finance.sina.com.cn/futures/api/jsonp.php/IO.XSRV2.CallbackLists['xxx']/InnerFuturesNewService.getDailyKLine?symbol=CN0Y"),
            ("东方财富指数", "http://push2.eastmoney.com/api/qt/stock/get?secid=100.FTFA50&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14&ut=b2884a393a59ad64002292a3e90d46a5"),
        ]
        
        for name, url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=5)
                resp.encoding = 'gbk' if 'sina' in url else 'utf-8'
                text = resp.text
                
                if 'FTFA50' in url:
                    # 东方财富富时A50指数
                    data = resp.json()
                    if data.get('data'):
                        d = data['data']
                        result['data'] = {
                            'code': 'FTFA50',
                            'name': '富时中国A50指数',
                            'price': d.get('f2', 0) / 100 if d.get('f2') else 0,
                            'change': d.get('f3', 0) / 100 if d.get('f3') else 0,
                        }
                        result['success'] = True
                        result['source'] = name
                        print(f"✅ {name}获取成功")
                        print(f"   指数：{result['data']['price']:.2f}")
                        print(f"   涨跌：{result['data']['change']:.2f}%")
                        return result
                        
                elif 'hq.sinajs' in url:
                    # 新浪行情格式
                    match = re.search(r'"([^"]*)"', text)
                    if match:
                        data_str = match.group(1)
                        if data_str:
                            parts = data_str.split(',')
                            # 提取数值
                            result['data'] = {
                                'code': 'CN0Y',
                                'name': '富时中国A50期指',
                                'raw': data_str[:200]
                            }
                            result['success'] = True
                            result['source'] = name
                            print(f"✅ {name}获取成功")
                            print(f"   原始数据：{data_str[:100]}...")
                            return result
                            
            except Exception as e:
                print(f"  {name}失败：{e}")
                continue
        
        # 最后尝试：直接获取页面
        print("  所有接口失败，尝试网页抓取...")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ 获取失败：{e}")
    
    return result


def fetch_north_simple():
    """北向资金 - 简化接口"""
    print("\n" + "="*60)
    print("💰 北向资金流向（备用接口）")
    print("="*60)
    
    result = {'success': False, 'data': {}, 'source': '', 'error': None}
    
    try:
        # 方法1：东方财富数据中心接口
        url = "http://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            'reportName': 'RPT_MUTUAL_STOCK_NORTH_ACC',
            'columns': 'ALL',
            'filter': "(TRADE_DATE='2026-03-24')",
            'pageSize': '5',
            'pageNumber': '1',
            'sortColumns': 'TRADE_DATE',
            'sortTypes': '-1',
            'source': 'WEB',
            'client': 'WEB'
        }
        
        # 方法2：直接请求北向资金页面
        urls = [
            ("东方财富北向资金", "http://push2.eastmoney.com/api/qt/stock/fflow/day/kline/get?lmt=0&klt=101&secid=1.000001&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56&ut=b2884a393a59ad64002292a3e90d46a5"),
            ("北向汇总", "http://push2.eastmoney.com/api/qt/clist/get?fid=f62&fs=m:1+t:2,m:1+t:23&fields=f12,f14,f62,f184&pn=1&pz=10&ut=b2884a393a59ad64002292a3e90d46a5"),
        ]
        
        for name, url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=5)
                data = resp.json()
                
                if data.get('data'):
                    d = data['data']
                    
                    if 'klines' in d:
                        # kline格式
                        klines = d.get('klines', [])
                        if klines:
                            latest = klines[-1] if isinstance(klines[-1], str) else str(klines[-1])
                            print(f"  原始数据：{latest[:100]}...")
                            # 解析格式
                            parts = latest.split(',')
                            if len(parts) >= 2:
                                result['data'] = {
                                    'date': parts[0] if parts[0] else datetime.now().strftime('%Y-%m-%d'),
                                    'raw': latest
                                }
                                result['success'] = True
                                result['source'] = name
                                print(f"✅ {name}获取成功")
                                return result
                                
                    elif 'diff' in d:
                        # 列表格式
                        diff = d.get('diff', [])
                        if diff:
                            item = diff[0]
                            result['data'] = {
                                'code': item.get('f12', ''),
                                'name': item.get('f14', ''),
                                'value': item.get('f62', 0),  # 北向净买入
                            }
                            # 转换单位（可能是分，需要转元再转亿）
                            val = item.get('f62', 0)
                            if val:
                                result['data']['north_net_inflow'] = val / 100000000  # 分转亿
                            result['success'] = True
                            result['source'] = name
                            print(f"✅ {name}获取成功")
                            print(f"   名称：{result['data']['name']}")
                            print(f"   净流入：{result['data'].get('north_net_inflow', 0):.2f}亿")
                            return result
                            
            except Exception as e:
                print(f"  {name}失败：{e}")
                continue
        
        # 备用：爬取网页
        print("  所有JSON接口失败")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ 获取失败：{e}")
    
    return result


def main():
    """主函数"""
    print("="*60)
    print("🔄 补充抓取市场数据")
    print(f"   时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # A50
    a50 = fetch_a50_simple()
    
    # 北向资金
    north = fetch_north_simple()
    
    # 总结
    print("\n" + "="*60)
    print("📊 数据汇总")
    print("="*60)
    
    if a50['success']:
        print(f"✅ A50: {a50['data']}")
    else:
        print(f"❌ A50: 获取失败 - {a50.get('error', '未知错误')}")
    
    if north['success']:
        print(f"✅ 北向资金: {north['data']}")
    else:
        print(f"❌ 北向资金: 获取失败 - {north.get('error', '未知错误')}")
    
    return {'a50': a50, 'north': north}


if __name__ == "__main__":
    main()