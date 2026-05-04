#!/usr/bin/env python3
"""
股票交易系统 - 真实行情版
接入腾讯财经 API 获取真实数据
"""

import json
import sqlite3
import hashlib
import random
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen, Request
from urllib.error import URLError
import os
import sys

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'stock_trading.db')

# 简单的 token 存储
TOKENS = {}

# 推荐的股票列表（替换原有 20 只）
RECOMMENDED_STOCKS = [
    # 持仓股
    {'code': '600460', 'name': '士兰微', 'market': 'SH', 'industry': '半导体'},
    {'code': '000882', 'name': '华联股份', 'market': 'SZ', 'industry': '零售'},
    
    # 关注股
    {'code': '002594', 'name': '比亚迪', 'market': 'SZ', 'industry': '新能源'},
    {'code': '600519', 'name': '贵州茅台', 'market': 'SH', 'industry': '白酒'},
    {'code': '601318', 'name': '中国平安', 'market': 'SH', 'industry': '保险'},
    
    # 蓝筹股
    {'code': '600036', 'name': '招商银行', 'market': 'SH', 'industry': '银行'},
    {'code': '601398', 'name': '工商银行', 'market': 'SH', 'industry': '银行'},
    {'code': '000001', 'name': '平安银行', 'market': 'SZ', 'industry': '银行'},
    
    # 科技股
    {'code': '000063', 'name': '中兴通讯', 'market': 'SZ', 'industry': '通信'},
    {'code': '000725', 'name': '京东方 A', 'market': 'SZ', 'industry': '电子'},
    {'code': '002475', 'name': '立讯精密', 'market': 'SZ', 'industry': '电子'},
    
    # 消费股
    {'code': '000858', 'name': '五粮液', 'market': 'SZ', 'industry': '白酒'},
    {'code': '600887', 'name': '伊利股份', 'market': 'SH', 'industry': '食品'},
    {'code': '000333', 'name': '美的集团', 'market': 'SZ', 'industry': '家电'},
    {'code': '000651', 'name': '格力电器', 'market': 'SZ', 'industry': '家电'},
    
    # 新能源
    {'code': '300750', 'name': '宁德时代', 'market': 'SZ', 'industry': '电池'},
    {'code': '601012', 'name': '隆基绿能', 'market': 'SH', 'industry': '光伏'},
    
    # 金融
    {'code': '300059', 'name': '东方财富', 'market': 'SZ', 'industry': '券商'},
    {'code': '601857', 'name': '中国石油', 'market': 'SH', 'industry': '石油'},
    {'code': '600900', 'name': '长江电力', 'market': 'SH', 'industry': '电力'},
    
    # 地产
    {'code': '000002', 'name': '万科 A', 'market': 'SZ', 'industry': '房地产'},
    {'code': '600000', 'name': '浦发银行', 'market': 'SH', 'industry': '银行'},
]

def get_real_quote(code):
    """从腾讯财经 API 获取真实行情"""
    try:
        # 腾讯财经 API
        market = "sh" if code.startswith("6") else "sz"
        url = f"http://qt.gtimg.cn/q={market}{code}"
        
        req = Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Referer', 'http://finance.qq.com/')
        
        response = urlopen(req, timeout=5)
        data = response.read().decode('gbk', errors='ignore')
        
        # 解析数据：v_sh600460="51~士兰微~600460~25.85~26.00~25.85~..."
        if '=' in data:
            parts = data.split('"')
            if len(parts) >= 2:
                quote_data = parts[1].split('~')
                if len(quote_data) >= 32:
                    return {
                        'code': code,
                        'name': quote_data[1],
                        'price': float(quote_data[3]),
                        'open': float(quote_data[5]),
                        'high': float(quote_data[33]) if len(quote_data) > 33 else 0,
                        'low': float(quote_data[34]) if len(quote_data) > 34 else 0,
                        'close': float(quote_data[4]),  # 昨收
                        'volume': int(quote_data[6]) if quote_data[6].isdigit() else 0,
                        'amount': float(quote_data[7]) if quote_data[7] else 0,
                        'change': float(quote_data[3]) - float(quote_data[4]),
                        'change_percent': ((float(quote_data[3]) - float(quote_data[4])) / float(quote_data[4]) * 100) if quote_data[4] else 0
                    }
    except Exception as e:
        print(f"获取行情失败 {code}: {e}")
    
    return None

def get_all_quotes():
    """批量获取所有股票行情"""
    quotes = []
    
    for stock in RECOMMENDED_STOCKS:
        code = stock['code']
        quote = get_real_quote(code)
        
        if quote:
            quotes.append({
                'code': quote['code'],
                'name': quote['name'],
                'market': stock['market'],
                'industry': stock['industry'],
                'price': quote['price'],
                'open': quote['open'],
                'high': quote.get('high', quote['price']),
                'low': quote.get('low', quote['price']),
                'close': quote['close'],
                'volume': quote['volume'],
                'amount': quote['amount'],
                'change': quote['change'],
                'change_percent': quote['change_percent']
            })
        else:
            # API 失败时用默认数据
            quotes.append({
                'code': code,
                'name': stock['name'],
                'market': stock['market'],
                'industry': stock['industry'],
                'price': 10.0,
                'open': 10.0,
                'high': 10.0,
                'low': 10.0,
                'close': 10.0,
                'volume': 0,
                'amount': 0,
                'change': 0,
                'change_percent': 0
            })
    
    return quotes

# 缓存
QUOTE_CACHE = {}
CACHE_TIME = 0
CACHE_INTERVAL = 10  # 10 秒刷新一次

def get_cached_quotes():
    """获取缓存的行情数据"""
    global QUOTE_CACHE, CACHE_TIME
    
    current_time = time.time()
    if current_time - CACHE_TIME > CACHE_INTERVAL or not QUOTE_CACHE:
        QUOTE_CACHE = get_all_quotes()
        CACHE_TIME = current_time
    
    return QUOTE_CACHE


class StockHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # ============ 行情 API ============
        
        # 股票列表
        if path == '/api/market/stocks':
            quotes = get_cached_quotes()
            self.send_json({'code': 200, 'data': {'list': quotes}})
            return
        
        # 个股行情
        if path == '/api/market/quote':
            code = params.get('code', [''])[0]
            quote = get_real_quote(code)
            if quote:
                self.send_json({'code': 200, 'data': quote})
            else:
                self.send_json({'code': 404, 'message': '股票未找到'}, 404)
            return
        
        # K 线数据
        if path == '/api/market/kline':
            code = params.get('code', [''])[0]
            kline_type = params.get('type', ['day'])[0]
            count = int(params.get('count', ['30'])[0])
            
            # 生成模拟 K 线（真实 K 线需要付费 API）
            quote = get_real_quote(code)
            if quote:
                kline = []
                base_price = quote['price']
                for i in range(count):
                    change = random.uniform(-0.05, 0.05)
                    price = base_price * (1 + change)
                    kline.append({
                        'date': f'2026-03-{23-i:02d}',
                        'open': price * 0.99,
                        'high': price * 1.02,
                        'low': price * 0.98,
                        'close': price,
                        'volume': random.randint(10000, 1000000)
                    })
                self.send_json({'code': 200, 'data': {'kline': kline}})
            else:
                self.send_json({'code': 404, 'message': '股票未找到'}, 404)
            return
        
        # 分时数据
        if path == '/api/market/min':
            code = params.get('code', [''])[0]
            quote = get_real_quote(code)
            if quote:
                min_data = []
                base_price = quote['price']
                for i in range(240):
                    change = random.uniform(-0.02, 0.02)
                    min_data.append({
                        'time': f'{9+i//60:02d}:{i%60:02d}',
                        'price': base_price * (1 + change),
                        'volume': random.randint(100, 10000)
                    })
                self.send_json({'code': 200, 'data': {'min': min_data}})
            else:
                self.send_json({'code': 404, 'message': '股票未找到'}, 404)
            return
        
        # 技术指标
        if path == '/api/market/indicator':
            code = params.get('code', [''])[0]
            indicator_type = params.get('type', ['ma'])[0]
            
            quote = get_real_quote(code)
            if quote:
                # 生成模拟指标
                self.send_json({'code': 200, 'data': {
                    'type': indicator_type,
                    'value': random.uniform(-10, 10),
                    'signal': 'hold'
                }})
            else:
                self.send_json({'code': 404, 'message': '股票未找到'}, 404)
            return
        
        self.send_json({'code': 404, 'message': 'Not Found'}, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 策略信号
        if path == '/api/strategy/signal':
            code = data.get('stock_code', '')
            quote = get_real_quote(code)
            if quote:
                # 简单信号判断
                change = quote.get('change_percent', 0)
                signal = 'buy' if change < -3 else 'sell' if change > 3 else 'hold'
                self.send_json({'code': 200, 'data': {
                    'ma_cross': signal,
                    'rsi': signal,
                    'macd': signal
                }})
            else:
                self.send_json({'code': 404, 'message': '股票未找到'}, 404)
            return
        
        self.send_json({'code': 404, 'message': 'Not Found'}, 404)


def run_server(port=8000):
    """启动服务器"""
    print("="*70)
    print("📊 股票交易 API 服务（真实行情版）")
    print("="*70)
    print(f"🌐 服务地址：http://localhost:{port}")
    print(f"📈 数据源：腾讯财经 API")
    print(f"📋 股票数量：{len(RECOMMENDED_STOCKS)} 只")
    print("")
    print("持仓股:")
    print("  - 600460 士兰微")
    print("  - 000882 华联股份")
    print("")
    print("关注股:")
    print("  - 002594 比亚迪")
    print("  - 600519 贵州茅台")
    print("  - 601318 中国平安")
    print("")
    print("="*70)
    print("")
    
    server = HTTPServer(('0.0.0.0', port), StockHandler)
    print(f"✅ 服务已启动，监听端口 {port}")
    print("按 Ctrl+C 停止服务")
    print("")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        server.shutdown()


if __name__ == '__main__':
    run_server()
