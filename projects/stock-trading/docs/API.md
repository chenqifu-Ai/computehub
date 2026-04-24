# "电话"量化交易软件 - API接口文档

## 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Token
- **数据格式**: JSON

---

## 一、认证接口

### 1. 用户注册
```
POST /auth/register
```

**请求体**:
```json
{
    "username": "test",
    "password": "123456",
    "email": "test@example.com"
}
```

**响应**:
```json
{
    "code": 200,
    "message": "注册成功",
    "data": {
        "user_id": 1,
        "username": "test"
    }
}
```

### 2. 用户登录
```
POST /auth/login
```

**请求体**:
```json
{
    "username": "test",
    "password": "123456"
}
```

**响应**:
```json
{
    "code": 200,
    "message": "登录成功",
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user": {
            "id": 1,
            "username": "test"
        }
    }
}
```

---

## 二、行情接口

### 1. 获取股票列表
```
GET /market/stocks
```

**参数**:
- `market`: 市场（SH/SZ/HK/US），可选
- `keyword`: 关键词搜索，可选

**响应**:
```json
{
    "code": 200,
    "data": {
        "list": [
            {
                "code": "000001",
                "name": "平安银行",
                "market": "SZ"
            }
        ],
        "total": 4000
    }
}
```

### 2. 获取实时行情
```
GET /market/quote/{code}
```

**响应**:
```json
{
    "code": 200,
    "data": {
        "code": "000001",
        "name": "平安银行",
        "price": 12.35,
        "change": 0.25,
        "change_percent": 2.06,
        "open": 12.10,
        "high": 12.50,
        "low": 12.05,
        "volume": 12345678,
        "amount": 152345678.90
    }
}
```

### 3. 获取历史K线
```
GET /market/kline/{code}
```

**参数**:
- `start`: 开始日期 (YYYY-MM-DD)
- `end`: 结束日期 (YYYY-MM-DD)
- `type`: K线类型 (day/week/month)

**响应**:
```json
{
    "code": 200,
    "data": {
        "list": [
            {
                "date": "2026-03-20",
                "open": 12.10,
                "high": 12.50,
                "low": 12.05,
                "close": 12.35,
                "volume": 12345678
            }
        ]
    }
}
```

---

## 三、策略接口

### 1. 获取策略列表
```
GET /strategies
```

**响应**:
```json
{
    "code": 200,
    "data": {
        "list": [
            {
                "id": 1,
                "name": "双均线策略",
                "status": "running",
                "created_at": "2026-03-21 10:00:00"
            }
        ]
    }
}
```

### 2. 创建策略
```
POST /strategies
```

**请求体**:
```json
{
    "name": "双均线策略",
    "description": "5日均线上穿20日均线买入",
    "code": "# 策略代码\n..."
}
```

### 3. 回测策略
```
POST /strategies/{id}/backtest
```

**请求体**:
```json
{
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "initial_capital": 1000000,
    "stocks": ["000001", "000002"]
}
```

**响应**:
```json
{
    "code": 200,
    "data": {
        "total_return": 0.35,
        "annual_return": 0.35,
        "max_drawdown": -0.15,
        "sharpe_ratio": 1.5,
        "trades": 50
    }
}
```

### 4. 运行策略
```
POST /strategies/{id}/run
```

### 5. 停止策略
```
POST /strategies/{id}/stop
```

---

## 四、交易接口

### 1. 获取持仓
```
GET /trading/positions
```

**响应**:
```json
{
    "code": 200,
    "data": {
        "list": [
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "volume": 1000,
                "available": 1000,
                "cost_price": 12.00,
                "current_price": 12.35,
                "profit": 350.00,
                "profit_percent": 2.92
            }
        ]
    }
}
```

### 2. 下单
```
POST /trading/order
```

**请求体**:
```json
{
    "stock_code": "000001",
    "order_type": "buy",
    "price": 12.00,
    "volume": 1000
}
```

### 3. 撤单
```
DELETE /trading/order/{order_id}
```

### 4. 获取订单
```
GET /trading/orders
```

**参数**:
- `status`: 订单状态 (pending/filled/cancelled)
- `start_date`: 开始日期
- `end_date`: 结束日期

---

## 五、账户接口

### 1. 获取账户信息
```
GET /account/info
```

**响应**:
```json
{
    "code": 200,
    "data": {
        "balance": 988000.00,
        "frozen": 12000.00,
        "total_asset": 1000000.00,
        "profit": 1000.00,
        "profit_percent": 0.10
    }
}
```

### 2. 获取资金流水
```
GET /account/transactions
```

---

## 六、风控接口

### 1. 获取风控设置
```
GET /risk/settings
```

**响应**:
```json
{
    "code": 200,
    "data": {
        "max_position": 0.8,
        "stop_loss": 0.1,
        "stop_profit": 0.3,
        "max_single_trade": 0.2
    }
}
```

### 2. 更新风控设置
```
PUT /risk/settings
```

**请求体**:
```json
{
    "max_position": 0.8,
    "stop_loss": 0.1,
    "stop_profit": 0.3
}
```

---

*创建时间：2026-03-21*