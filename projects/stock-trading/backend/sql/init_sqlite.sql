# 股票交易软件 - 数据库初始化

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 股票表
CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    market VARCHAR(20),
    industry VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 策略表
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
);

-- 回测记录表
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
);

-- 订单表
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
);

-- 持仓表
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
);

-- 账户表
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    balance DECIMAL(18,2) DEFAULT 0,
    frozen DECIMAL(18,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 交易记录表
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
);

-- K线数据表
CREATE TABLE IF NOT EXISTS klines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    amount DECIMAL(18,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_klines_stock_date ON klines(stock_code, trade_date);
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);
CREATE INDEX IF NOT EXISTS idx_positions_user_stock ON positions(user_id, stock_code);
CREATE INDEX IF NOT EXISTS idx_strategies_user ON strategies(user_id);
CREATE INDEX IF NOT EXISTS idx_backtests_strategy ON backtests(strategy_id);

-- 插入测试用户
INSERT OR IGNORE INTO users (username, password, email) VALUES ('admin', 'admin123', 'admin@stock.com');

-- 插入测试股票
INSERT OR IGNORE INTO stocks (code, name, market, industry) VALUES 
('000001', '平安银行', 'SZ', '银行'),
('000002', '万科A', 'SZ', '房地产'),
('000063', '中兴通讯', 'SZ', '通信'),
('000333', '美的集团', 'SZ', '家电'),
('000651', '格力电器', 'SZ', '家电'),
('000858', '五粮液', 'SZ', '白酒'),
('600000', '浦发银行', 'SH', '银行'),
('600036', '招商银行', 'SH', '银行'),
('600519', '贵州茅台', 'SH', '白酒'),
('600887', '伊利股份', 'SH', '食品');

-- 插入测试资金
INSERT OR IGNORE INTO accounts (user_id, balance) VALUES (1, 1000000.00);

-- 插入测试策略
INSERT OR IGNORE INTO strategies (user_id, name, description, code, status) VALUES 
(1, '双均线策略', '5日均线上穿20日均线买入，下穿卖出', 'def strategy(df):\n    df[\"short_ma\"] = df[\"close\"].rolling(5).mean()\n    df[\"long_ma\"] = df[\"close\"].rolling(20).mean()\n    df[\"signal\"] = 0\n    df.loc[df[\"short_ma\"] > df[\"long_ma\"], \"signal\"] = 1\n    df.loc[df[\"short_ma\"] < df[\"long_ma\"], \"signal\"] = -1\n    return df[\"signal\"]', 'active'),
(1, 'MACD策略', 'MACD金叉买入，死叉卖出', 'def strategy(df):\n    df[\"ema12\"] = df[\"close\"].ewm(span=12).mean()\n    df[\"ema26\"] = df[\"close\"].ewm(span=26).mean()\n    df[\"macd\"] = df[\"ema12\"] - df[\"ema26\"]\n    df[\"signal_line\"] = df[\"macd\"].ewm(span=9).mean()\n    df[\"signal\"] = 0\n    df.loc[df[\"macd\"] > df[\"signal_line\"], \"signal\"] = 1\n    df.loc[df[\"macd\"] < df[\"signal_line\"], \"signal\"] = -1\n    return df[\"signal\"]', 'active');