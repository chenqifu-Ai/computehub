# 股票交易系统 - 快速启动指南

## 一键启动

```bash
# 方式1: 使用启动脚本
./start.sh

# 方式2: 直接运行
cd backend
python3 simple_server.py
```

**无需安装任何依赖！使用Python标准库。**

## 访问地址

- **API服务**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **前端页面**: 打开 `frontend/index.html`

## 默认账号

- 用户名: `admin`
- 密码: `admin123`
- 初始资金: `1,000,000元`

## 功能列表

| 功能 | 状态 | 说明 |
|------|------|------|
| 用户登录 | ✅ | JWT认证 |
| 行情数据 | ✅ | 模拟数据 + akshare接口 |
| 股票搜索 | ✅ | 按代码/名称搜索 |
| 买入卖出 | ✅ | 模拟交易 |
| 持仓管理 | ✅ | 实时更新 |
| 策略管理 | ✅ | 创建/编辑/删除 |
| 策略回测 | ✅ | 历史数据回测 |
| 账户管理 | ✅ | 余额/持仓/订单 |

## API端点

### 认证
- `POST /api/auth/login` - 登录
- `POST /api/auth/register` - 注册

### 行情
- `GET /api/market/stocks` - 股票列表
- `GET /api/market/quote/{code}` - 实时行情
- `GET /api/market/kline/{code}` - K线数据

### 交易
- `POST /api/trading/buy` - 买入
- `POST /api/trading/sell` - 卖出
- `GET /api/trading/positions` - 持仓查询
- `GET /api/trading/orders` - 订单查询

### 策略
- `GET /api/strategy/list` - 策略列表
- `POST /api/strategy/create` - 创建策略
- `POST /api/strategy/backtest` - 运行回测

### 账户
- `GET /api/account/info` - 账户信息
- `GET /api/account/positions` - 持仓明细
- `GET /api/account/orders` - 订单记录

## 数据库

使用SQLite数据库，自动创建在 `backend/data/stock_trading.db`

## 注意事项

1. **模拟数据**: 默认使用模拟数据，无需真实数据源
2. **akshare可选**: 如需真实行情，安装 `pip install akshare`
3. **pandas可选**: 回测引擎可在无pandas时运行

## 故障排除

### 端口被占用
```bash
# 查找占用8000端口的进程
lsof -i :8000

# 杀掉进程
kill -9 <PID>
```

### 依赖安装失败
```bash
# Termux环境
pkg install python build-essential
pip install fastapi uvicorn pydantic PyJWT requests
```

### 数据库错误
```bash
# 删除重建
rm backend/data/stock_trading.db
python3 backend/main.py
```