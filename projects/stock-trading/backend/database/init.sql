-- 股票交易系统数据库初始化

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 账户表
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    balance REAL DEFAULT 1000000.0,
    market_value REAL DEFAULT 0.0,
    total_asset REAL DEFAULT 1000000.0,
    total_profit REAL DEFAULT 0.0,
    total_profit_percent REAL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 持仓表
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    volume INTEGER NOT NULL,
    cost_price REAL NOT NULL,
    current_price REAL,
    market_value REAL,
    profit REAL,
    profit_percent REAL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    order_type TEXT NOT NULL,
    order_volume INTEGER NOT NULL,
    order_price REAL NOT NULL,
    status TEXT DEFAULT 'filled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 策略表
CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    strategy_type TEXT,
    params TEXT,
    code TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 回测结果表
CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    start_date TEXT,
    end_date TEXT,
    initial_capital REAL,
    final_capital REAL,
    total_return REAL,
    annual_return REAL,
    max_drawdown REAL,
    sharpe_ratio REAL,
    win_rate REAL,
    total_trades INTEGER,
    profit_trades INTEGER,
    loss_trades INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_strategies_user ON strategies(user_id);

-- 插入默认用户
INSERT OR IGNORE INTO users (id, username, password, email) 
VALUES (1, 'admin', 'admin123', 'admin@example.com');

-- 插入默认账户
INSERT OR IGNORE INTO accounts (user_id, balance) 
VALUES (1, 1000000.0);