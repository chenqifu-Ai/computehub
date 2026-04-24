# 更新日志

## v1.0.0 (2026-03-21)

### 新增功能

#### 后端API
- 用户认证系统（JWT Token）
- 股票行情数据（AKShare/Tushare/新浪）
- 历史K线查询
- 策略管理系统（创建/编辑/删除）
- 策略回测引擎
- 模拟交易系统
- 账户管理（资金/持仓/交易记录）

#### 策略模板
- 双均线策略（double_ma.py）
- MACD策略（macd_strategy.py）
- RSI策略（rsi_strategy.py）
- 布林带策略（bollinger_strategy.py）

#### 前端界面
- 登录页面
- 主界面（仪表盘/策略/交易/行情）

#### 部署支持
- Linux/Mac启动脚本
- Windows启动脚本
- Docker配置
- Docker Compose配置

### 技术栈
- 后端：FastAPI + SQLite
- 前端：Vue3 + Element Plus + ECharts
- 数据源：AKShare / Tushare / 新浪财经

### 数据库表
- users（用户）
- stocks（股票）
- strategies（策略）
- backtests（回测记录）
- orders（订单）
- positions（持仓）
- accounts（账户）
- transactions（交易记录）
- klines（K线数据）

---

## 开发计划

### v1.1.0（计划中）
- [ ] 实盘交易接口
- [ ] 实时行情推送（WebSocket）
- [ ] 更多技术指标（KDJ/CCI/WR）
- [ ] 策略编辑器（在线编写）
- [ ] 用户设置（风险偏好/通知）

### v1.2.0（计划中）
- [ ] AI策略推荐
- [ ] 风险评估系统
- [ ] 多账户管理
- [ ] 社区分享功能

---

*最后更新：2026-03-21*