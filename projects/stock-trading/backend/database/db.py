"""
数据库连接和操作
"""
import os
import sqlite3
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


class Database:
    """SQLite数据库操作类"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认数据库路径
            db_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 'data', 'stock_trading.db'
            )
        self.db_path = db_path
        self._ensure_db_dir()
        self.init_db()
    
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def init_db(self):
        """初始化数据库"""
        # SQL脚本路径
        sql_path = os.path.join(
            os.path.dirname(__file__), 
            'init_sqlite.sql'
        )
        
        # 如果SQL文件存在，执行初始化
        if os.path.exists(sql_path):
            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            with self.get_connection() as conn:
                conn.executescript(sql_script)
        else:
            # 如果没有SQL文件，创建基本表结构
            self._create_tables()
    
    def _create_tables(self):
        """创建基本表结构"""
        with self.get_connection() as conn:
            # 用户表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    email VARCHAR(100),
                    phone VARCHAR(20),
                    role VARCHAR(20) DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 股票表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code VARCHAR(20) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    market VARCHAR(20),
                    industry VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 策略表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    code TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 回测记录表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS backtests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER NOT NULL,
                    stock_code VARCHAR(20),
                    start_date DATE,
                    end_date DATE,
                    initial_capital DECIMAL(18,2),
                    final_capital DECIMAL(18,2),
                    total_return DECIMAL(10,4),
                    max_drawdown DECIMAL(10,4),
                    sharpe_ratio DECIMAL(10,4),
                    win_rate DECIMAL(10,4),
                    total_trades INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
                )
            ''')
            
            # 订单表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    strategy_id INTEGER,
                    stock_code VARCHAR(20) NOT NULL,
                    order_type VARCHAR(10) NOT NULL,
                    order_price DECIMAL(10,2),
                    order_volume INTEGER NOT NULL,
                    filled_volume INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 持仓表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    stock_code VARCHAR(20) NOT NULL,
                    volume INTEGER NOT NULL,
                    available_volume INTEGER NOT NULL,
                    cost_price DECIMAL(10,2),
                    current_price DECIMAL(10,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 账户表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    balance DECIMAL(18,2) DEFAULT 0,
                    frozen DECIMAL(18,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 交易记录表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    order_id INTEGER,
                    stock_code VARCHAR(20) NOT NULL,
                    trans_type VARCHAR(20) NOT NULL,
                    amount DECIMAL(18,2),
                    volume INTEGER,
                    price DECIMAL(10,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 插入默认用户
            conn.execute('''
                INSERT OR IGNORE INTO users (username, password, email) 
                VALUES ('admin', 'admin123', 'admin@stock.com')
            ''')
            
            # 插入默认账户
            conn.execute('''
                INSERT OR IGNORE INTO accounts (user_id, balance) 
                VALUES (1, 1000000.00)
            ''')
            
            # 插入默认股票
            stocks_data = [
                ('000001', '平安银行', 'SZ', '银行'),
                ('000002', '万科A', 'SZ', '房地产'),
                ('000063', '中兴通讯', 'SZ', '通信'),
                ('000333', '美的集团', 'SZ', '家电'),
                ('000651', '格力电器', 'SZ', '家电'),
                ('000858', '五粮液', 'SZ', '白酒'),
                ('600000', '浦发银行', 'SH', '银行'),
                ('600036', '招商银行', 'SH', '银行'),
                ('600519', '贵州茅台', 'SH', '白酒'),
                ('600887', '伊利股份', 'SH', '食品'),
            ]
            for stock in stocks_data:
                conn.execute('''
                    INSERT OR IGNORE INTO stocks (code, name, market, industry) 
                    VALUES (?, ?, ?, ?)
                ''', stock)
            
            # 插入默认策略
            conn.execute('''
                INSERT OR IGNORE INTO strategies (user_id, name, description, code, status) 
                VALUES (1, '双均线策略', '5日均线上穿20日均线买入，下穿卖出', 
                'def strategy(df):
    df["short_ma"] = df["close"].rolling(5).mean()
    df["long_ma"] = df["close"].rolling(20).mean()
    df["signal"] = 0
    df.loc[df["short_ma"] > df["long_ma"], "signal"] = 1
    df.loc[df["short_ma"] < df["long_ma"], "signal"] = -1
    return df["signal"]', 
                'active')
            ''')
            
            conn.execute('''
                INSERT OR IGNORE INTO strategies (user_id, name, description, code, status) 
                VALUES (1, 'MACD策略', 'MACD金叉买入，死叉卖出', 
                'def strategy(df):
    df["ema12"] = df["close"].ewm(span=12).mean()
    df["ema26"] = df["close"].ewm(span=26).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["signal_line"] = df["macd"].ewm(span=9).mean()
    df["signal"] = 0
    df.loc[df["macd"] > df["signal_line"], "signal"] = 1
    df.loc[df["macd"] < df["signal_line"], "signal"] = -1
    return df["signal"]', 
                'active')
            ''')
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def execute(self, sql: str, params: tuple = ()) -> int:
        """执行SQL语句"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount
    
    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        """查询单条"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict]:
        """查询多条"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # 用户相关
    def create_user(self, username: str, password: str, email: str = None) -> int:
        """创建用户"""
        sql = "INSERT INTO users (username, password, email) VALUES (?, ?, ?)"
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (username, password, email))
            return cursor.lastrowid
    
    def get_user(self, username: str) -> Optional[Dict]:
        """获取用户"""
        return self.fetchone("SELECT * FROM users WHERE username = ?", (username,))
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """验证用户登录"""
        user = self.fetchone(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        return user if user else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """根据ID获取用户"""
        return self.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
    
    # 股票相关
    def get_stock(self, code: str) -> Optional[Dict]:
        """获取股票"""
        return self.fetchone("SELECT * FROM stocks WHERE code = ?", (code,))
    
    def get_stocks(self, market: str = None, keyword: str = None) -> List[Dict]:
        """获取股票列表"""
        sql = "SELECT * FROM stocks WHERE 1=1"
        params = []
        if market:
            sql += " AND market = ?"
            params.append(market)
        if keyword:
            sql += " AND (code LIKE ? OR name LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        return self.fetchall(sql, tuple(params))
    
    # 策略相关
    def create_strategy(self, user_id: int, name: str, code: str, 
                        description: str = None) -> int:
        """创建策略"""
        sql = """INSERT INTO strategies (user_id, name, code, description) 
                 VALUES (?, ?, ?, ?)"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (user_id, name, code, description))
            return cursor.lastrowid
    
    def get_strategies(self, user_id: int) -> List[Dict]:
        """获取用户的策略列表"""
        return self.fetchall(
            "SELECT * FROM strategies WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
    
    def get_strategy(self, strategy_id: int) -> Optional[Dict]:
        """获取策略"""
        return self.fetchone("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
    
    def update_strategy(self, strategy_id: int, **kwargs) -> int:
        """更新策略"""
        fields = []
        params = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            params.append(value)
        params.append(strategy_id)
        sql = f"UPDATE strategies SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        return self.execute(sql, tuple(params))
    
    def delete_strategy(self, strategy_id: int) -> int:
        """删除策略"""
        return self.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))
    
    # 回测相关
    def save_backtest(self, strategy_id: int, stock_code: str,
                      start_date: str, end_date: str,
                      initial_capital: float, final_capital: float,
                      total_return: float, max_drawdown: float,
                      sharpe_ratio: float, win_rate: float,
                      total_trades: int) -> int:
        """保存回测结果"""
        sql = """INSERT INTO backtests 
                 (strategy_id, stock_code, start_date, end_date, 
                  initial_capital, final_capital, total_return, 
                  max_drawdown, sharpe_ratio, win_rate, total_trades)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (strategy_id, stock_code, start_date, end_date,
                  initial_capital, final_capital, total_return,
                  max_drawdown, sharpe_ratio, win_rate, total_trades)
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid
    
    def get_backtests(self, strategy_id: int = None, limit: int = 20) -> List[Dict]:
        """获取回测记录"""
        if strategy_id:
            return self.fetchall(
                "SELECT * FROM backtests WHERE strategy_id = ? ORDER BY created_at DESC LIMIT ?",
                (strategy_id, limit)
            )
        return self.fetchall(
            "SELECT * FROM backtests ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
    
    # 账户相关
    def get_account(self, user_id: int) -> Optional[Dict]:
        """获取账户"""
        return self.fetchone("SELECT * FROM accounts WHERE user_id = ?", (user_id,))
    
    def update_balance(self, user_id: int, balance: float) -> int:
        """更新余额"""
        return self.execute(
            "UPDATE accounts SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (balance, user_id)
        )
    
    # 持仓相关
    def get_positions(self, user_id: int) -> List[Dict]:
        """获取持仓"""
        return self.fetchall(
            "SELECT * FROM positions WHERE user_id = ? AND volume > 0",
            (user_id,)
        )
    
    def update_position(self, user_id: int, stock_code: str, 
                        volume: int, cost_price: float) -> int:
        """更新持仓"""
        existing = self.fetchone(
            "SELECT * FROM positions WHERE user_id = ? AND stock_code = ?",
            (user_id, stock_code)
        )
        if existing:
            return self.execute(
                """UPDATE positions SET volume = ?, cost_price = ?, 
                   updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND stock_code = ?""",
                (volume, cost_price, user_id, stock_code)
            )
        else:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO positions (user_id, stock_code, volume, available_volume, cost_price)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, stock_code, volume, volume, cost_price)
                )
                return cursor.lastrowid
    
    # 订单相关
    def create_order(self, user_id: int, stock_code: str, order_type: str,
                     order_price: float, order_volume: int,
                     strategy_id: int = None) -> int:
        """创建订单"""
        sql = """INSERT INTO orders 
                 (user_id, strategy_id, stock_code, order_type, order_price, order_volume)
                 VALUES (?, ?, ?, ?, ?, ?)"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (user_id, strategy_id, stock_code, 
                                        order_type, order_price, order_volume))
            return cursor.lastrowid
    
    def get_orders(self, user_id: int, status: str = None, limit: int = 50) -> List[Dict]:
        """获取订单"""
        if status:
            return self.fetchall(
                "SELECT * FROM orders WHERE user_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, status, limit)
            )
        return self.fetchall(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
    
    def update_order_status(self, order_id: int, status: str, filled_volume: int = None) -> int:
        """更新订单状态"""
        if filled_volume is not None:
            return self.execute(
                "UPDATE orders SET status = ?, filled_volume = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, filled_volume, order_id)
            )
        return self.execute(
            "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, order_id)
        )


# 全局数据库实例
db = Database()