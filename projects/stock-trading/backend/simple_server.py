#!/usr/bin/env python3
"""
股票交易系统 - 简化版后端
使用Python标准库，无需安装任何依赖
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

# 添加brokers模块路径
sys.path.insert(0, os.path.dirname(__file__))
from brokers.sync_broker import broker as broker_instance

# 数据库路径 - 使用绝对路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'stock_trading.db')

# 简单的token存储
TOKENS = {}

# 缓存股票数据
STOCK_CACHE = {}
CACHE_TIME = 0

# 股票列表
STOCKS = [
    {'code': '000001', 'name': '平安银行', 'market': 'SZ', 'industry': '银行'},
    {'code': '000002', 'name': '万科A', 'market': 'SZ', 'industry': '房地产'},
    {'code': '000063', 'name': '中兴通讯', 'market': 'SZ', 'industry': '通信'},
    {'code': '000333', 'name': '美的集团', 'market': 'SZ', 'industry': '家电'},
    {'code': '000651', 'name': '格力电器', 'market': 'SZ', 'industry': '家电'},
    {'code': '000858', 'name': '五粮液', 'market': 'SZ', 'industry': '白酒'},
    {'code': '600000', 'name': '浦发银行', 'market': 'SH', 'industry': '银行'},
    {'code': '600036', 'name': '招商银行', 'market': 'SH', 'industry': '银行'},
    {'code': '600519', 'name': '贵州茅台', 'market': 'SH', 'industry': '白酒'},
    {'code': '600887', 'name': '伊利股份', 'market': 'SH', 'industry': '食品'},
    {'code': '002594', 'name': '比亚迪', 'market': 'SZ', 'industry': '汽车'},
    {'code': '300059', 'name': '东方财富', 'market': 'SZ', 'industry': '金融'},
    {'code': '300750', 'name': '宁德时代', 'market': 'SZ', 'industry': '新能源'},
    {'code': '601318', 'name': '中国平安', 'market': 'SH', 'industry': '保险'},
    {'code': '601398', 'name': '工商银行', 'market': 'SH', 'industry': '银行'},
    {'code': '601857', 'name': '中国石油', 'market': 'SH', 'industry': '能源'},
    {'code': '600900', 'name': '长江电力', 'market': 'SH', 'industry': '电力'},
    {'code': '000725', 'name': '京东方A', 'market': 'SZ', 'industry': '电子'},
    {'code': '002475', 'name': '立讯精密', 'market': 'SZ', 'industry': '电子'},
    {'code': '601012', 'name': '隆基绿能', 'market': 'SH', 'industry': '新能源'},
]


def get_real_quote(stock_code):
    """从腾讯API获取实时行情"""
    global STOCK_CACHE, CACHE_TIME
    
    # 使用缓存（30秒有效期）
    if time.time() - CACHE_TIME < 30 and stock_code in STOCK_CACHE:
        return STOCK_CACHE[stock_code]
    
    # 确定市场前缀
    if stock_code.startswith('6'):
        market_code = f'sh{stock_code}'
    else:
        market_code = f'sz{stock_code}'
    
    try:
        url = f'http://qt.gtimg.cn/q={market_code}'
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://qt.gtimg.cn/'
        })
        response = urlopen(req, timeout=5)
        data = response.read().decode('gbk')
        
        # 解析数据
        if '~' in data:
            parts = data.split('~')
            price = float(parts[3])
            change = float(parts[31])
            change_percent = float(parts[32])
            volume = int(parts[6])
            amount = float(parts[37])
            
            result = {
                'code': stock_code,
                'price': price,
                'change': change,
                'change_percent': change_percent,
                'volume': volume,
                'amount': amount
            }
            STOCK_CACHE[stock_code] = result
            CACHE_TIME = time.time()
            return result
    except Exception as e:
        print(f'获取行情失败: {e}')
    
    # 失败时返回模拟数据
    base_prices = {
        '000001': 10.0, '000002': 15.0, '000063': 25.0, '000333': 55.0,
        '000651': 40.0, '000858': 160.0, '600000': 8.0, '600036': 35.0,
        '600519': 1688.0, '600887': 28.0, '002594': 268.0, '300059': 18.0,
        '300750': 180.0, '601318': 48.0, '601398': 5.0, '601857': 8.0,
        '600900': 25.0, '000725': 4.0, '002475': 30.0, '601012': 35.0,
    }
    base = base_prices.get(stock_code, 10.0)
    change_percent = random.uniform(-5, 5)
    price = base * (1 + change_percent / 100)
    return {
        'code': stock_code,
        'price': round(price, 2),
        'change': round(base * change_percent / 100, 2),
        'change_percent': round(change_percent, 2),
        'volume': random.randint(100000, 10000000),
        'amount': round(base * random.randint(100000, 10000000), 2)
    }


def get_kline_data(stock_code, kline_type='day', count=100):
    """获取K线数据"""
    # 直接返回模拟数据（腾讯API不稳定）
    base_prices = {'600519': 1688, '000858': 160, '000333': 55, '002594': 268, '000001': 10.77, '601318': 59.74}
    base = base_prices.get(stock_code, get_real_quote(stock_code)['price'] if stock_code in [s['code'] for s in STOCKS] else 50)
    
    result = []
    price = base
    from datetime import datetime, timedelta
    for i in range(count):
        date = (datetime.now() - timedelta(days=count-i)).strftime('%Y-%m-%d')
        change = random.uniform(-0.03, 0.03)
        open_p = price
        close_p = price * (1 + change)
        high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.02))
        low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.02))
        result.append({'date': date, 'open': round(open_p, 2), 'close': round(close_p, 2),
                      'high': round(high_p, 2), 'low': round(low_p, 2), 'volume': random.randint(100000, 1000000)})
        price = close_p
    return result


def get_min_data(stock_code):
    """获取分时数据"""
    base_prices = {'600519': 1688, '000858': 160, '000333': 55, '002594': 268}
    base = base_prices.get(stock_code, 50)
    result = []
    price = base
    for i in range(240):
        hour = 9 + i // 60
        minute = i % 60
        if hour >= 11 and hour < 13: continue
        time_str = f'{hour:02d}:{minute:02d}'
        change = random.uniform(-0.002, 0.002)
        price = price * (1 + change)
        result.append({'time': time_str, 'price': round(price, 2), 'volume': random.randint(1000, 10000)})
    return result


def calculate_indicators(kline_data, indicator_type='ma'):
    """计算技术指标"""
    if not kline_data: return {}
    closes = [k['close'] for k in kline_data]
    
    if indicator_type == 'ma':
        ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else None
        ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else None
        ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        return {'ma5': round(ma5, 2) if ma5 else None, 'ma10': round(ma10, 2) if ma10 else None,
                'ma20': round(ma20, 2) if ma20 else None, 'trend': 'up' if closes[-1] > ma5 else 'down'}
    
    if indicator_type == 'macd':
        if len(closes) < 26: return {'macd': None}
        ema12, ema26 = sum(closes[-12:]) / 12, sum(closes[-26:]) / 26
        dif = ema12 - ema26
        return {'macd': round((dif - dif) * 2, 2), 'dif': round(dif, 2), 'signal': 'buy' if dif > 0 else 'sell'}
    
    if indicator_type == 'kdj':
        if len(kline_data) < 9: return {'k': None}
        highs = [k['high'] for k in kline_data[-9:]]
        lows = [k['low'] for k in kline_data[-9:]]
        hn, ln = max(highs), min(lows)
        rsv = (closes[-1] - ln) / (hn - ln) * 100 if hn != ln else 50
        return {'k': round(rsv, 2), 'd': round(rsv, 2), 'j': round(rsv, 2), 'signal': 'buy' if rsv < 20 else 'sell' if rsv > 80 else 'hold'}
    
    if indicator_type == 'rsi':
        if len(closes) < 14: return {'rsi': None}
        gains, losses = [], []
        for i in range(1, 15):
            change = closes[-i] - closes[-i-1]
            (gains if change > 0 else losses).append(abs(change))
        avg_gain = sum(gains) / 14 if gains else 0
        avg_loss = sum(losses) / 14 if losses else 0.001
        rsi = 100 - (100 / (1 + avg_gain / avg_loss))
        return {'rsi': round(rsi, 2), 'signal': 'buy' if rsi < 30 else 'sell' if rsi > 70 else 'hold'}
    
    return {}


def get_all_quotes():
    """获取所有股票实时行情"""
    global STOCK_CACHE, CACHE_TIME
    
    # 使用缓存（30秒有效期）
    if time.time() - CACHE_TIME < 30 and len(STOCK_CACHE) >= len(STOCKS):
        return STOCK_CACHE
    
    # 批量获取
    codes = []
    for s in STOCKS:
        if s['code'].startswith('6'):
            codes.append(f"sh{s['code']}")
        else:
            codes.append(f"sz{s['code']}")
    
    try:
        url = f"http://qt.gtimg.cn/q={','.join(codes)}"
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://qt.gtimg.cn/'
        })
        response = urlopen(req, timeout=10)
        data = response.read().decode('gbk')
        
        # 解析每只股票
        for line in data.split(';'):
            if '~' in line:
                try:
                    parts = line.split('~')
                    code = parts[2]
                    result = {
                        'code': code,
                        'price': float(parts[3]),
                        'change': float(parts[31]),
                        'change_percent': float(parts[32]),
                        'volume': int(parts[6]),
                        'amount': float(parts[37])
                    }
                    STOCK_CACHE[code] = result
                except:
                    pass
        
        CACHE_TIME = time.time()
    except Exception as e:
        print(f'批量获取行情失败: {e}')
    
    return STOCK_CACHE


class Database:
    """数据库操作类"""
    
    def __init__(self):
        self._ensure_db()
    
    def _ensure_db(self):
        """确保数据库存在"""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 1000000.0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                volume INTEGER NOT NULL,
                cost_price REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                order_type TEXT NOT NULL,
                order_price REAL NOT NULL,
                order_volume INTEGER NOT NULL,
                status TEXT DEFAULT 'filled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 插入默认用户
        cursor.execute('''
            INSERT OR IGNORE INTO users (id, username, password) VALUES (1, 'admin', 'admin123')
        ''')
        cursor.execute('''
            INSERT OR IGNORE INTO accounts (user_id, balance) VALUES (1, 1000000.0)
        ''')
        
        # 插入默认策略
        strategies = [
            (1, '双均线策略', '5日均线上穿20日均线买入', 'ma5_cross_ma20'),
            (1, 'MACD策略', 'MACD金叉买入，死叉卖出', 'macd_cross'),
            (1, 'RSI策略', 'RSI低于30买入，高于70卖出', 'rsi_strategy'),
            (1, '布林带策略', '价格触及下轨买入，上轨卖出', 'bollinger_strategy'),
        ]
        for s in strategies:
            cursor.execute('''
                INSERT OR IGNORE INTO strategies (user_id, name, description, code) VALUES (?, ?, ?, ?)
            ''', s)
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        return sqlite3.connect(DB_PATH)
    
    def verify_user(self, username, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            return {'id': user[0], 'username': user[1]}
        return None
    
    def get_account(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM accounts WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 1000000.0
    
    def update_balance(self, user_id, balance):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE accounts SET balance = ? WHERE user_id = ?', (balance, user_id))
        conn.commit()
        conn.close()
    
    def get_positions(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT stock_code, stock_name, volume, cost_price FROM positions WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{'stock_code': r[0], 'stock_name': r[1], 'volume': r[2], 'cost_price': r[3]} for r in rows]
    
    def add_position(self, user_id, stock_code, stock_name, volume, cost_price):
        """添加或更新持仓"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, volume, cost_price FROM positions WHERE user_id = ? AND stock_code = ?', (user_id, stock_code))
        existing = cursor.fetchone()
        
        if existing:
            new_volume = existing[1] + volume
            new_cost = (existing[2] * existing[1] + cost_price * volume) / new_volume
            cursor.execute('UPDATE positions SET volume = ?, cost_price = ? WHERE id = ?', (new_volume, new_cost, existing[0]))
        else:
            cursor.execute('INSERT INTO positions (user_id, stock_code, stock_name, volume, cost_price) VALUES (?, ?, ?, ?, ?)',
                          (user_id, stock_code, stock_name, volume, cost_price))
        
        conn.commit()
        conn.close()
    
    def reduce_position(self, user_id, stock_code, volume):
        """减少持仓"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, volume, cost_price FROM positions WHERE user_id = ? AND stock_code = ?', (user_id, stock_code))
        existing = cursor.fetchone()
        
        if existing:
            new_volume = existing[1] - volume
            if new_volume <= 0:
                cursor.execute('DELETE FROM positions WHERE id = ?', (existing[0],))
            else:
                cursor.execute('UPDATE positions SET volume = ? WHERE id = ?', (new_volume, existing[0]))
        
        conn.commit()
        conn.close()
    
    def create_order(self, user_id, stock_code, stock_name, order_type, order_price, order_volume):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (user_id, stock_code, stock_name, order_type, order_price, order_volume)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, stock_code, stock_name, order_type, order_price, order_volume))
        conn.commit()
        conn.close()
    
    def get_orders(self, user_id, limit=50):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, stock_code, stock_name, order_type, order_price, order_volume, status, created_at
            FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{'id': r[0], 'stock_code': r[1], 'stock_name': r[2], 'order_type': r[3],
                 'order_price': r[4], 'order_volume': r[5], 'status': r[6], 'created_at': r[7]} for r in rows]
    
    def get_strategies(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, description, code FROM strategies WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{'id': r[0], 'name': r[1], 'description': r[2], 'code': r[3]} for r in rows]


# 全局数据库实例
db = Database()


def get_quote(stock_code):
    """获取股票行情（模拟）"""
    base_prices = {
        '000001': 10.0, '000002': 15.0, '000063': 25.0, '000333': 55.0,
        '000651': 40.0, '000858': 160.0, '600000': 8.0, '600036': 35.0,
        '600519': 1688.0, '600887': 28.0, '002594': 268.0, '300059': 18.0,
        '300750': 180.0, '601318': 48.0, '601398': 5.0, '601857': 8.0,
        '600900': 25.0, '000725': 4.0, '002475': 30.0, '601012': 35.0,
    }
    base = base_prices.get(stock_code, 10.0)
    change_percent = random.uniform(-5, 5)
    price = base * (1 + change_percent / 100)
    return {
        'code': stock_code,
        'price': round(price, 2),
        'change': round(base * change_percent / 100, 2),
        'change_percent': round(change_percent, 2),
        'volume': random.randint(100000, 10000000),
        'amount': round(base * random.randint(100000, 10000000), 2)
    }


class StockHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def log_message(self, format, *args):
        """不打印日志"""
        pass
    
    def send_json(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 静态文件
        if path == '/' or path == '/index.html':
            self.serve_index()
            return
        
        # API路由
        if path.startswith('/api/'):
            self.handle_api_get(path)
        else:
            self.send_json({'code': 404, 'message': 'Not Found'}, 404)
    
    def do_POST(self):
        """处理POST请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith('/api/'):
            self.handle_api_post(path)
        else:
            self.send_json({'code': 404, 'message': 'Not Found'}, 404)
    
    def serve_index(self):
        """服务首页"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        html = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>股票交易API</title></head>
<body><h1>📈 股票交易API服务运行中</h1>
<p>API文档: <a href="/api/docs">/api/docs</a></p>
<p>股票列表: <a href="/api/market/stocks">/api/market/stocks</a></p>
<p>登录接口: POST /api/auth/login (username=admin, password=admin123)</p>
</body></html>'''
        self.wfile.write(html.encode('utf-8'))
    
    def get_token_user(self):
        """从请求头获取用户"""
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth[7:]
            return TOKENS.get(token)
        return None
    
    def handle_api_get(self, path):
        """处理GET API"""
        # 股票列表 - 使用真实数据
        if path == '/api/market/stocks':
            stocks = []
            quotes = get_all_quotes()
            for s in STOCKS:
                q = quotes.get(s['code'], get_real_quote(s['code']))
                stocks.append({**s, **q})
            self.send_json({'code': 200, 'data': {'list': stocks}})
            return
        
        # 市场概况
        if path == '/api/market/summary':
            self.send_json({
                'code': 200,
                'data': {
                    'sh_index': {'price': round(3000 + random.uniform(-50, 50), 2), 'change': round(random.uniform(-1, 1), 2)},
                    'sz_index': {'price': round(10000 + random.uniform(-100, 100), 2), 'change': round(random.uniform(-1, 1), 2)},
                    'cy_index': {'price': round(2000 + random.uniform(-20, 20), 2), 'change': round(random.uniform(-1, 1), 2)}
                }
            })
            return
        
        # 热门股票
        if path == '/api/market/hot':
            hot = random.sample(STOCKS, min(8, len(STOCKS)))
            result = []
            for s in hot:
                quote = get_real_quote(s['code'])
                result.append({**s, **quote})
            self.send_json({'code': 200, 'data': {'list': result}})
            return
        
        # 股票搜索
        if path.startswith('/api/market/search'):
            query = parse_qs(urlparse(self.path).query)
            keyword = query.get('keyword', [''])[0].upper()
            stocks = []
            for s in STOCKS:
                if keyword in s['code'] or keyword in s['name']:
                    quote = get_real_quote(s['code'])
                    stocks.append({**s, **quote})
            self.send_json({'code': 200, 'data': {'list': stocks}})
            return
        
        # 行情
        if path.startswith('/api/market/quote/'):
            code = path.split('/')[-1]
            for s in STOCKS:
                if s['code'] == code:
                    quote = get_real_quote(code)
                    self.send_json({'code': 200, 'data': {**s, **quote}})
                    return
            self.send_json({'code': 404, 'message': '股票不存在'}, 404)
            return
        
        # K线数据
        if path.startswith('/api/market/kline/'):
            parts = path.split('/')
            code = parts[-1] if len(parts) > 0 else ''
            query = parse_qs(urlparse(self.path).query)
            kline_type = query.get('type', ['day'])[0]
            count = int(query.get('count', ['100'])[0])
            
            # 获取K线数据
            kline_data = get_kline_data(code, kline_type, count)
            self.send_json({'code': 200, 'data': {'list': kline_data}})
            return
        
        # 分时数据
        if path.startswith('/api/market/min/'):
            code = path.split('/')[-1]
            min_data = get_min_data(code)
            self.send_json({'code': 200, 'data': {'list': min_data}})
            return
        
        # 技术指标
        if path.startswith('/api/market/indicator/'):
            code = path.split('/')[-1]
            query = parse_qs(urlparse(self.path).query)
            indicator_type = query.get('type', ['ma'])[0]
            
            # 获取K线数据计算指标
            kline_data = get_kline_data(code, 'day', 100)
            indicators = calculate_indicators(kline_data, indicator_type)
            self.send_json({'code': 200, 'data': indicators})
            return
        
        # ============ 公开的券商接口 ============
        
        # 列出所有券商（公开）
        if path == '/api/broker/list':
            brokers = broker_instance.list_brokers()
            self.send_json({'code': 200, 'data': {'brokers': brokers}})
            return
        
        # 获取当前券商（公开）
        if path == '/api/broker/current':
            current = broker_instance.get_current_broker()
            self.send_json({'code': 200, 'data': current})
            return
        
        # 获取券商行情（公开）
        if path.startswith('/api/broker/quote/'):
            code = path.split('/')[-1]
            quote = broker_instance.get_quote(code)
            if quote:
                self.send_json({'code': 200, 'data': quote})
            else:
                self.send_json({'code': 404, 'message': f'无法获取股票行情: {code}'}, 404)
            return
        
        # 需要认证的接口
        user = self.get_token_user()
        if not user:
            self.send_json({'code': 401, 'message': '未登录'}, 401)
            return
        
        # 账户信息
        if path == '/api/account/info':
            balance = db.get_account(user['id'])
            positions = db.get_positions(user['id'])
            market_value = sum(get_real_quote(p['stock_code'])['price'] * p['volume'] for p in positions)
            total_asset = balance + market_value
            profit = total_asset - 1000000.0
            self.send_json({
                'code': 200,
                'data': {
                    'account': {
                        'balance': round(balance, 2),
                        'market_value': round(market_value, 2),
                        'total_asset': round(total_asset, 2),
                        'total_profit': round(profit, 2),
                        'total_profit_percent': round(profit / 1000000 * 100, 2)
                    },
                    'positions': positions
                }
            })
            return
        
        # 持仓
        if path == '/api/trading/positions':
            positions = db.get_positions(user['id'])
            result = []
            for p in positions:
                quote = get_real_quote(p['stock_code'])
                result.append({
                    **p,
                    'current_price': quote['price'],
                    'market_value': round(quote['price'] * p['volume'], 2),
                    'profit': round((quote['price'] - p['cost_price']) * p['volume'], 2)
                })
            self.send_json({'code': 200, 'data': {'list': result}})
            return
        
        # 订单
        if path == '/api/trading/orders':
            orders = db.get_orders(user['id'])
            self.send_json({'code': 200, 'data': {'list': orders}})
            return
        
        # 策略列表
        if path == '/api/strategy/list':
            strategies = db.get_strategies(user['id'])
            self.send_json({'code': 200, 'data': {'list': strategies}})
            return
        
        # ============ 券商接口（需要认证）============
        
        # 获取券商账户
        if path == '/api/broker/account':
            account = broker_instance.get_account()
            self.send_json({'code': 200, 'data': account})
            return
        
        # 获取券商持仓
        if path == '/api/broker/positions':
            positions = broker_instance.get_positions()
            self.send_json({'code': 200, 'data': {'list': positions}})
            return
        
        # 获取券商订单
        if path == '/api/broker/orders':
            orders = broker_instance.get_orders()
            self.send_json({'code': 200, 'data': {'list': orders}})
            return
        
        self.send_json({'code': 404, 'message': 'Not Found'}, 404)
    
    def handle_api_post(self, path):
        """处理POST API"""
        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
        try:
            data = json.loads(body)
        except Exception as e:
            print(f"[ERROR] JSON parse error: {e}", flush=True)
            data = {}
        
        # 登录
        if path == '/api/auth/login':
            username = data.get('username', '')
            password = data.get('password', '')
            user = db.verify_user(username, password)
            if user:
                token = hashlib.md5(f"{username}{time.time()}".encode()).hexdigest()
                TOKENS[token] = user
                self.send_json({'code': 200, 'data': {'token': token, 'user': user}})
            else:
                self.send_json({'code': 401, 'message': '用户名或密码错误'}, 401)
            return
        
        # 注册
        if path == '/api/auth/register':
            username = data.get('username', '')
            password = data.get('password', '')
            if not username or not password:
                self.send_json({'code': 400, 'message': '用户名和密码不能为空'}, 400)
                return
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
                user_id = cursor.lastrowid
                cursor.execute('INSERT INTO accounts (user_id, balance) VALUES (?, 1000000)', (user_id,))
                conn.commit()
                conn.close()
                self.send_json({'code': 200, 'message': '注册成功'})
            except sqlite3.IntegrityError:
                self.send_json({'code': 400, 'message': '用户名已存在'}, 400)
            return
        
        # 需要认证的接口
        user = self.get_token_user()
        if not user:
            self.send_json({'code': 401, 'message': '未登录'}, 401)
            return
        
        # 买入
        if path == '/api/trading/buy':
            stock_code = data.get('stock_code', '')
            volume = int(data.get('volume', 0))
            price = float(data.get('price', 0))
            
            if not stock_code or volume <= 0:
                self.send_json({'code': 400, 'message': '参数错误'}, 400)
                return
            
            stock_name = stock_code
            for s in STOCKS:
                if s['code'] == stock_code:
                    stock_name = s['name']
                    break
            
            if price <= 0:
                price = get_real_quote(stock_code)['price']
            
            amount = price * volume
            balance = db.get_account(user['id'])
            
            if amount > balance:
                self.send_json({'code': 400, 'message': '余额不足'}, 400)
                return
            
            db.update_balance(user['id'], balance - amount)
            db.add_position(user['id'], stock_code, stock_name, volume, price)
            db.create_order(user['id'], stock_code, stock_name, 'buy', price, volume)
            
            self.send_json({'code': 200, 'message': '买入成功', 'data': {
                'stock_code': stock_code, 'stock_name': stock_name,
                'volume': volume, 'price': price, 'amount': round(amount, 2)
            }})
            return
        
        # 卖出
        if path == '/api/trading/sell':
            stock_code = data.get('stock_code', '')
            volume = int(data.get('volume', 0))
            price = float(data.get('price', 0))
            
            positions = db.get_positions(user['id'])
            pos = None
            for p in positions:
                if p['stock_code'] == stock_code:
                    pos = p
                    break
            
            if not pos:
                self.send_json({'code': 400, 'message': '没有该股票持仓'}, 400)
                return
            
            if volume > pos['volume']:
                self.send_json({'code': 400, 'message': '卖出数量超过持仓'}, 400)
                return
            
            if price <= 0:
                price = get_real_quote(stock_code)['price']
            
            amount = price * volume
            balance = db.get_account(user['id'])
            
            db.update_balance(user['id'], balance + amount)
            db.reduce_position(user['id'], stock_code, volume)
            db.create_order(user['id'], stock_code, pos['stock_name'], 'sell', price, volume)
            
            self.send_json({'code': 200, 'message': '卖出成功', 'data': {
                'stock_code': stock_code, 'stock_name': pos['stock_name'],
                'volume': volume, 'price': price, 'amount': round(amount, 2)
            }})
            return
        
        # ============ 券商接口 ============
        
        # 切换券商
        if path == '/api/broker/switch':
            broker_id = data.get('broker_id', '')
            result = broker_instance.switch_broker(broker_id)
            if result['success']:
                self.send_json({'code': 200, 'message': result['message']})
            else:
                self.send_json({'code': 400, 'message': result['message']}, 400)
            return
        
        # 券商下单
        if path == '/api/broker/order':
            stock_code = data.get('stock_code', '')
            direction = data.get('direction', 'buy')
            volume = int(data.get('volume', 0))
            price = data.get('price')
            
            result = broker_instance.place_order(stock_code, direction, volume, price)
            if result['success']:
                self.send_json({'code': 200, 'data': result})
            else:
                self.send_json({'code': 400, 'message': result['message']}, 400)
            return
        
        # 券商撤单
        if path.startswith('/api/broker/order/') and path.endswith('/cancel'):
            order_id = path.split('/')[-2]
            result = broker_instance.cancel_order(order_id)
            if result['success']:
                self.send_json({'code': 200, 'message': result['message']})
            else:
                self.send_json({'code': 400, 'message': result['message']}, 400)
            return
        
        # 券商状态保存
        if path == '/api/broker/state/save':
            state = broker_instance.save_state()
            state_file = os.path.join(os.path.dirname(__file__), 'data', 'broker_state.json')
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            self.send_json({'code': 200, 'message': '状态保存成功'})
            return
        
        # ============ 风控 API ============
        
        # 获取风控配置
        if path == '/api/risk/config' and method == 'GET':
            from services.risk_control import risk_control
            config = {
                "stop_loss_percent": risk_control.stop_loss_percent,
                "stop_profit_percent": risk_control.stop_profit_percent,
                "max_position_percent": risk_control.max_position_percent,
                "max_total_position": risk_control.max_total_position
            }
            self.send_json({'code': 200, 'data': config})
            return
        
        # 更新风控配置
        if path == '/api/risk/config' and method == 'POST':
            from services.risk_control import risk_control
            config = data.get('config', {})
            if 'stop_loss_percent' in config:
                risk_control.stop_loss_percent = config['stop_loss_percent']
            if 'stop_profit_percent' in config:
                risk_control.stop_profit_percent = config['stop_profit_percent']
            if 'max_position_percent' in config:
                risk_control.max_position_percent = config['max_position_percent']
            self.send_json({'code': 200, 'message': '风控配置已更新'})
            return
        
        # 设置止损
        if path == '/api/risk/stop_loss' and method == 'POST':
            from services.risk_control import risk_control
            stock_code = data.get('stock_code')
            percent = data.get('percent', 0.05)
            risk_control.set_stop_loss(stock_code, percent)
            self.send_json({'code': 200, 'message': f'已设置 {stock_code} 止损 {percent*100}%'})
            return
        
        # 风控报告
        if path == '/api/risk/report' and method == 'GET':
            from services.risk_control import risk_control
            positions = db.get_positions(user_id)
            current_prices = {}
            for pos in positions:
                try:
                    quote = get_quote(pos['stock_code'])
                    if quote and 'data' in quote:
                        current_prices[pos['stock_code']] = quote['data'].get('price', pos['cost_price'])
                except:
                    pass
            report = risk_control.get_risk_report(positions, current_prices)
            self.send_json({'code': 200, 'data': report})
            return
        
        # ============ 策略 API ============
        
        # 策略信号
        if path == '/api/strategy/signal' and method == 'POST':
            from services.strategy_executor import SignalGenerator
            stock_code = data.get('stock_code', '000001')
            try:
                kline = get_kline_data(stock_code, 'day', 30)
                prices = [d['close'] for d in kline.get('data', [])] if kline and 'data' in kline else []
                if prices:
                    signals = {
                        'ma_cross': SignalGenerator.ma_cross(prices),
                        'rsi': SignalGenerator.rsi_signal(prices),
                        'macd': SignalGenerator.macd_signal(prices)
                    }
                    self.send_json({'code': 200, 'data': signals})
                else:
                    self.send_json({'code': 400, 'message': '无法获取价格数据'})
            except Exception as e:
                self.send_json({'code': 500, 'message': str(e)})
            return
        
        # 券商状态加载
        if path == '/api/broker/state/load':
            state_file = os.path.join(os.path.dirname(__file__), 'data', 'broker_state.json')
            if os.path.exists(state_file):
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                broker_instance.load_state(state)
                self.send_json({'code': 200, 'message': '状态加载成功'})
            else:
                self.send_json({'code': 404, 'message': '状态文件不存在'}, 404)
            return
        
        self.send_json({'code': 404, 'message': 'Not Found'}, 404)


def run_server(port=8000):
    """启动服务器"""
    print("="*50)
    print("📊 股票交易API服务")
    print("="*50)
    print(f"🌐 服务地址: http://localhost:{port}")
    print(f"📖 API文档: http://localhost:{port}/api/docs")
    print(f"📊 股票列表: http://localhost:{port}/api/market/stocks")
    print("")
    print("默认账号: admin / admin123")
    print("初始资金: 1,000,000元")
    print("")
    print("📈 券商接口:")
    print(f"  券商列表: /api/broker/list")
    print(f"  当前券商: /api/broker/current")
    print(f"  券商账户: /api/broker/account")
    print(f"  券商持仓: /api/broker/positions")
    print(f"  券商下单: POST /api/broker/order")
    print("="*50)
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