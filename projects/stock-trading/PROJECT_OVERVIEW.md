# 股票交易系统 - 项目概述

## 项目信息
- **项目名称**: 电话 - 量化交易系统
- **技术栈**: FastAPI + Vue3 + SQLite
- **开发状态**: 核心功能已完成，实盘接口已实现
- **更新时间**: 2026-03-22 05:17

## 完成状态

### ✅ 已完成
1. **后端框架** - FastAPI + SQLite
2. **用户认证** - JWT登录注册
3. **数据库设计** - 用户、策略、订单、持仓表
4. **行情服务** - 股票列表、实时行情、K线数据（支持akshare扩展）
5. **策略管理** - 创建、编辑、删除、启动/停止策略
6. **回测引擎** - 完整回测逻辑，计算收益率、夏普比率等
7. **交易管理** - 下单、订单列表、持仓查询
8. **账户管理** - 账户信息、充值、提现、交易统计
9. **前端界面** - 仪表盘、策略、交易、行情页面
10. **实盘接口** - 模拟券商 + 实盘券商框架

### 🔜 待开发
1. **实盘对接** - 对接券商API（需账号配置）
2. **风控系统** - 止损止盈、风险预警
3. **策略编辑器** - 可视化策略编辑
4. **WebSocket推送** - 实时行情推送
5. **多用户权限** - 用户管理、权限控制

## 券商接口

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/broker/list` | GET | 列出所有可用券商 |
| `/api/broker/current` | GET | 获取当前券商 |
| `/api/broker/account` | GET | 获取账户信息 |
| `/api/broker/positions` | GET | 获取持仓列表 |
| `/api/broker/orders` | GET | 获取订单列表 |
| `/api/broker/order` | POST | 下单 |
| `/api/broker/quote/{code}` | GET | 获取实时行情 |
| `/api/broker/state/save` | POST | 保存账户状态 |
| `/api/broker/state/load` | POST | 加载账户状态 |

### 支持的券商

| 券商 | 类型 | 状态 |
|------|------|------|
| 模拟交易 (simulator) | 模拟 | ✅ 已实现 |
| 东方财富 (eastmoney) | 实盘 | 📝 模板已创建 |
| 华泰证券 (htsc) | 实盘 | 📝 模板已创建 |
| 讯投QMT (xtquant) | 实盘 | 📝 模板已创建 |

### 下单示例

```bash
# 登录获取Token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# 查询账户
curl http://localhost:8000/api/broker/account -H "Authorization: Bearer $TOKEN"

# 买入股票
curl -X POST http://localhost:8000/api/broker/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"000001","direction":"buy","volume":100,"price":10.5}'

# 卖出股票
curl -X POST http://localhost:8000/api/broker/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"000001","direction":"sell","volume":100}'
```

## 快速启动

```bash
cd /root/.openclaw/workspace/projects/stock-trading
./start.sh
```

访问: http://localhost:8000/docs

## 默认账户
- 用户名: admin
- 密码: admin123

## 目录结构

```
backend/
├── brokers/              # 券商接口
│   ├── __init__.py
│   ├── base.py          # 基础接口定义
│   ├── simulator.py     # 模拟券商
│   ├── sync_broker.py   # 同步包装器
│   ├── registry.py      # 券商注册中心
│   ├── eastmoney.py     # 东方财富接口
│   └── htsc.py          # 华泰证券接口
├── config/
│   └── brokers/         # 券商配置
├── routes/              # API路由
├── services/            # 业务服务
├── data/                # 数据存储
└── simple_server.py     # 主服务

frontend/
└── index.html           # 前端界面
```