# 股票交易系统 - 快速启动指南

## 一键启动

```bash
cd /root/.openclaw/workspace/projects/stock-trading
./start.sh
```

访问：http://localhost:8000

---

## API 测试

```bash
# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 获取行情
curl http://localhost:8000/api/market/stocks

# 风控配置
curl http://localhost:8000/api/risk/config

# 策略信号
curl -X POST http://localhost:8000/api/strategy/signal \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"000001"}'
```

---

## 功能模块

| 模块 | 端点 | 状态 |
|------|------|------|
| 用户认证 | /api/auth/* | ✅ |
| 行情服务 | /api/market/* | ✅ |
| 交易管理 | /api/trading/* | ✅ |
| 券商接口 | /api/broker/* | ✅ |
| 风控系统 | /api/risk/* | ✅ |
| 策略系统 | /api/strategy/* | ✅ |

---

## 新增功能

### 风控系统
- 止损止盈设置
- 仓位限制检查
- 风险报告生成
- 自动警告提示

### 策略系统
- 策略执行器
- 信号生成器（MA/RSI/MACD）
- 策略管理 API
- 自动监控持仓

### WebSocket（开发中）
- 实时行情推送
- 订单状态推送
- 持仓变化推送

---

## 前端页面

- 仪表盘：/frontend/index.html
- 风控管理：/frontend/risk_control.html

---

## 测试脚本

```bash
python3 test_real_trading.py
```

---

**更新时间**: 2026-03-23 13:30