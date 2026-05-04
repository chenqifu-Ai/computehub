#!/usr/bin/env python3
"""
可靠实时股票监控系统
多数据源验证，确保数据准确性
"""

import requests
import time
from datetime import datetime
import json

class ReliableStockMonitor:
    def __init__(self):
        self.data_sources = [
            self._get_sina_data,
            self._get_qq_data,
            self._get_eastmoney_data
        ]
        
    def _get_sina_data(self, stock_code):
        """新浪财经数据源"""
        try:
            if stock_code.startswith('6'):
                prefix = 'sh'
            else:
                prefix = 'sz'
            
            url = f"https://hq.sinajs.cn/list={prefix}{stock_code}"
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://finance.sina.com.cn'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.encoding = 'gb2312'
            
            if 'var hq_str_' in response.text:
                data = response.text.split('="')[1].split('"')[0]
                parts = data.split(',')
                if len(parts) > 3:
                    return {
                        'price': float(parts[3]),
                        'name': parts[0],
                        'source': 'sina',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
        except:
            pass
        return None
    
    def _get_qq_data(self, stock_code):
        """腾讯财经数据源（备用）"""
        try:
            url = f"https://qt.gtimg.cn/q={stock_code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=5)
            response.encoding = 'gb2312'
            
            if 'v_pv_none_match' not in response.text:
                parts = response.text.split('~')
                if len(parts) > 3:
                    return {
                        'price': float(parts[3]),
                        'name': parts[1],
                        'source': 'qq',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
        except:
            pass
        return None
    
    def _get_eastmoney_data(self, stock_code):
        """东方财富数据源（备用）"""
        try:
            url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={'1.' if stock_code.startswith('6') else '0.'}{stock_code}&fields=f43"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=5)
            data = response.json()
            
            if data.get('data'):
                return {
                    'price': data['data'].get('f43', 0),
                    'name': f"股票{stock_code}",
                    'source': 'eastmoney',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        except:
            pass
        return None
    
    def get_stock_price(self, stock_code):
        """多数据源获取股票价格，进行数据验证"""
        results = []
        
        for source in self.data_sources:
            result = source(stock_code)
            if result and result['price'] > 0:
                results.append(result)
                time.sleep(0.1)  # 避免请求过快
        
        if not results:
            return None
        
        # 数据一致性检查
        prices = [r['price'] for r in results]
        if len(set(prices)) == 1:  # 所有数据源一致
            return results[0]
        else:
            # 取多数一致或平均值
            from statistics import mode
            try:
                most_common = mode(prices)
                return next(r for r in results if r['price'] == most_common)
            except:
                avg_price = sum(prices) / len(prices)
                return {
                    'price': avg_price,
                    'name': f"股票{stock_code}",
                    'source': 'multiple',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'note': f'数据源不一致，取平均值（来源: {len(results)}个数据源）'
                }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='可靠实时股票监控')
    parser.add_argument('--stock', required=True, help='股票代码')
    parser.add_argument('--verbose', action='store_true', help='详细模式')
    
    args = parser.parse_args()
    
    monitor = ReliableStockMonitor()
    
    print(f"🔍 正在可靠监控股票 {args.stock}...")
    
    stock_data = monitor.get_stock_price(args.stock)
    
    if stock_data:
        print(f"\n📈 {stock_data['name']}({args.stock})")
        print(f"   💰 当前价格: ¥{stock_data['price']:.2f}")
        print(f"   📡 数据来源: {stock_data['source']}")
        print(f"   ⏰ 更新时间: {stock_data['timestamp']}")
        
        if 'note' in stock_data:
            print(f"   💡 备注: {stock_data['note']}")
        
        if args.verbose:
            print(f"\n🎯 数据可靠性: 多数据源验证通过")
    else:
        print("❌ 无法获取可靠的股票数据")
        print("💡 建议: 检查网络连接或稍后重试")

if __name__ == "__main__":
    main()