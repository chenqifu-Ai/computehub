# 数据库设计

## 一、表结构

### 1. 用户表 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. 策略表 (strategies)
```sql
CREATE TABLE strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    code TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'draft', -- draft, testing, running, stopped
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 3. 股票表 (stocks)
```sql
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    market VARCHAR(20), -- SH, SZ, HK, US
    industry VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. 行情数据表 (market_data)
```sql
CREATE TABLE market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(10, 2),
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    close DECIMAL(10, 2),
    volume BIGINT,
    amount DECIMAL(18, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    UNIQUE(stock_id, trade_date)
);
```

### 5. 订单表 (orders)
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    strategy_id INTEGER,
    stock_id INTEGER NOT NULL,
    order_type VARCHAR(10) NOT NULL, -- buy, sell
    order_price DECIMAL(10, 2),
    order_volume INTEGER NOT NULL,
    filled_volume INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- pending, filled, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
```

### 6. 持仓表 (positions)
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL,
    volume INTEGER NOT NULL,
    available_volume INTEGER NOT NULL,
    cost_price DECIMAL(10, 2),
    current_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
```

### 7. 资金表 (accounts)
```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    balance DECIMAL(18, 2) DEFAULT 0,
    frozen DECIMAL(18, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 8. 交易记录表 (transactions)
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_id INTEGER,
    stock_id INTEGER NOT NULL,
    trans_type VARCHAR(20) NOT NULL, -- buy, sell, deposit, withdraw
    amount DECIMAL(18, 2),
    volume INTEGER,
    price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
```

---

## 二、索引设计

```sql
-- 行情数据索引
CREATE INDEX idx_market_data_stock_date ON market_data(stock_id, trade_date);

-- 订单索引
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- 持仓索引
CREATE INDEX idx_positions_user_stock ON positions(user_id, stock_id);
```

---

## 三、初始化数据

```sql
-- 插入测试用户
INSERT INTO users (username, password, email) VALUES ('admin', 'admin123', 'admin@dianhua.com');

-- 插入测试股票
INSERT INTO stocks (code, name, market, industry) VALUES 
('000001', '平安银行', 'SZ', '银行'),
('000002', '万科A', 'SZ', '房地产'),
('600000', '浦发银行', 'SH', '银行'),
('600036', '招商银行', 'SH', '银行'),
('600519', '贵州茅台', 'SH', '白酒');

-- 插入测试资金
INSERT INTO accounts (user_id, balance) VALUES (1, 1000000.00);
```

---

*创建时间：2026-03-21*