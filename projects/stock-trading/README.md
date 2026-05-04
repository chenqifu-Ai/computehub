# 股票交易系统 - 快速启动指南

## 🚀 快速启动

### 1. 启动后端

```bash
cd /root/.openclaw/workspace/projects/stock-trading
chmod +x start.sh
./start.sh
```

或直接运行：
```bash
cd backend
pip3 install fastapi uvicorn pydantic python-jose passlib python-multipart
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. 访问系统

- **前端首页**: 打开 `frontend/index.html`
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 3. 默认账户

- 用户名: `admin`
- 密码: `admin123`

---

## 📊 功能模块

### 1. 仪表盘
- 账户总资产
- 持仓明细
- 收益曲线

### 2. 策略管理
- 创建策略
- 策略回测
- 启动/停止策略

### 3. 交易管理
- 手动下单
- 订单记录
- 持仓查询

### 4. 行情中心
- 股票搜索
- K线图
- 实时行情

### 5. 账户管理
- 账户信息
- 充值/提现
- 交易统计

---

## 🔧 API接口

### 认证
- `POST /api/v1/auth/login` - 登录
- `POST /api/v1/auth/register` - 注册
- `GET /api/v1/auth/me` - 获取当前用户

### 行情
- `GET /api/v1/market/stocks` - 股票列表
- `GET /api/v1/market/quote/{code}` - 实时行情
- `GET /api/v1/market/kline/{code}` - K线数据
- `GET /api/v1/market/search` - 搜索股票

### 策略
- `GET /api/v1/strategies/list` - 策略列表
- `POST /api/v1/strategies/create` - 创建策略
- `POST /api/v1/strategies/{id}/backtest` - 运行回测
- `POST /api/v1/strategies/{id}/start` - 启动策略

### 交易
- `POST /api/v1/trading/order` - 下单
- `GET /api/v1/trading/orders` - 订单列表
- `GET /api/v1/trading/positions` - 持仓

### 账户
- `GET /api/v1/account/info` - 账户信息
- `POST /api/v1/account/deposit` - 充值
- `POST /api/v1/account/withdraw` - 提现

---

## 📁 项目结构

```
stock-trading/
├── backend/
│   ├── main.py          # 入口文件
│   ├── config.py        # 配置
│   ├── database/
│   │   └── db.py        # 数据库
│   ├── routes/
│   │   ├── auth.py      # 认证
│   │   ├── market.py    # 行情
│   │   ├── strategy.py  # 策略
│   │   ├── trading.py   # 交易
│   │   └── account.py   # 账户
│   ├── services/
│   │   ├── backtest_engine.py  # 回测引擎
│   │   └── market_service.py   # 行情服务
│   └── core/
│       └── dependencies.py     # 依赖
├── frontend/
│   ├── index.html       # 主页面
│   └── login.html       # 登录页
├── data/                # 数据目录
├── start.sh             # 启动脚本
└── README.md            # 说明文档
```

---

## ⚠️ 注意事项

1. 这是模拟交易系统，不涉及真实资金
2. 行情数据为模拟数据（akshare可选）
3. 策略代码有安全限制，禁止危险操作
4. 数据存储在SQLite数据库中

---

## 🔜 后续开发

- [ ] WebSocket实时推送
- [ ] 策略编辑器（可视化）
- [ ] 更多技术指标
- [ ] 实盘接口对接
- [ ] 风控系统完善
- [ ] 多用户管理