# 股票交易软件 - 完整项目规划

## 一、项目概述

### 项目名称
**股票交易软件**（stock-trading）

### 项目定位
面向个人投资者的量化交易平台，支持策略开发、回测、自动交易。

### 核心价值
- **简单易用**：无需编程基础，可视化策略编辑
- **量化交易**：支持多种技术指标和策略
- **风险控制**：完善的止损止盈机制
- **模拟盘优先**：先验证再实盘

### 目标用户
- 个人投资者
- 量化交易爱好者
- 小型私募基金

---

## 二、功能规划

### MVP版本（第一阶段）

#### 2.1 核心功能

| 模块 | 功能 | 优先级 |
|------|------|--------|
| 用户系统 | 注册、登录、权限 | P0 |
| 行情数据 | 股票列表、实时行情、历史K线 | P0 |
| 策略管理 | 创建、编辑、删除策略 | P0 |
| 策略回测 | 历史数据回测、收益分析 | P0 |
| 模拟交易 | 下单、撤单、持仓管理 | P0 |
| 账户管理 | 资金、持仓、收益统计 | P0 |

#### 2.2 功能详情

##### 行情模块
```
- 股票搜索（代码/名称）
- 实时行情（价格、涨跌、成交量）
- 历史K线（日线、周线、月线）
- 技术指标（MA、MACD、RSI、KDJ）
```

##### 策略模块
```
- 策略编辑器（Python代码）
- 预设策略模板
  - 双均线策略
  - MACD策略
  - RSI策略
  - 布林带策略
- 回测引擎
- 收益报告
```

##### 交易模块
```
- 模拟交易
- 订单管理（买入、卖出、撤单）
- 持仓管理
- 资金管理
- 交易记录
```

### 第二阶段功能

| 模块 | 功能 | 优先级 |
|------|------|--------|
| 实盘对接 | 券商API对接 | P1 |
| 实时监控 | 实时策略运行、告警 | P1 |
| 数据分析 | 收益分析、风险评估 | P1 |
| 社区功能 | 策略分享、跟单 | P2 |
| 高级图表 | 更多技术指标、画线工具 | P2 |

### 第三阶段功能

| 模块 | 功能 | 优先级 |
|------|------|--------|
| AI策略 | 机器学习策略推荐 | P2 |
| 多市场 | 港股、美股支持 | P2 |
| 移动端 | APP开发 | P2 |
| API开放 | 开放API供第三方调用 | P3 |

---

## 三、技术架构

### 3.1 技术选型

#### 后端
| 组件 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.11 | 生态丰富、适合量化 |
| 框架 | FastAPI | 高性能异步框架 |
| 数据库 | PostgreSQL | 生产级关系数据库 |
| 缓存 | Redis | 行情缓存、会话管理 |
| 任务队列 | Celery | 异步任务、策略运行 |
| 消息队列 | RabbitMQ | 实时数据推送 |

#### 前端
| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3 | 响应式框架 |
| UI库 | Element Plus | 企业级组件库 |
| 图表 | ECharts | 金融图表 |
| 状态管理 | Pinia | Vue官方状态管理 |
| 构建 | Vite | 快速构建工具 |

#### 数据源
| 数据 | 来源 | 说明 |
|------|------|------|
| 行情 | Tushare / AKShare | 免费行情数据 |
| 财务 | Tushare | 财务数据 |
| 新闻 | 新浪财经 | 新闻资讯 |

#### 部署
| 组件 | 技术 | 说明 |
|------|------|------|
| 容器 | Docker | 容器化部署 |
| 编排 | Docker Compose | 简化部署 |
| 反向代理 | Nginx | 负载均衡、HTTPS |
| 监控 | Prometheus + Grafana | 性能监控 |

### 3.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   登录页    │  │   主界面    │  │   策略编辑   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                    Vue 3 + Element Plus                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        API层                                 │
│                      FastAPI + JWT                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 认证API  │ │ 行情API  │ │ 策略API  │ │ 交易API  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        服务层                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 用户服务 │ │ 行情服务 │ │ 策略服务 │ │ 交易服务 │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ 回测引擎 │ │ 风控服务 │ │ 消息推送 │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
│                      Celery + RabbitMQ                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        数据层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PostgreSQL   │  │    Redis     │  │  数据源API   │     │
│  │  用户/策略   │  │ 行情/缓存   │  │ Tushare/AK  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、数据库设计

### 4.1 核心表

```sql
-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 股票表
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    market VARCHAR(20),
    industry VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 策略表
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    code TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 回测记录表
CREATE TABLE backtests (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategies(id),
    start_date DATE,
    end_date DATE,
    initial_capital DECIMAL(18,2),
    final_capital DECIMAL(18,2),
    total_return DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 订单表
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    strategy_id INTEGER REFERENCES strategies(id),
    stock_id INTEGER REFERENCES stocks(id),
    order_type VARCHAR(10) NOT NULL,
    price DECIMAL(10,2),
    volume INTEGER NOT NULL,
    filled_volume INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 持仓表
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    stock_id INTEGER REFERENCES stocks(id),
    volume INTEGER NOT NULL,
    available_volume INTEGER NOT NULL,
    cost_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 账户表
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id),
    balance DECIMAL(18,2) DEFAULT 0,
    frozen DECIMAL(18,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 交易记录表
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    order_id INTEGER REFERENCES orders(id),
    stock_id INTEGER REFERENCES stocks(id),
    trans_type VARCHAR(20) NOT NULL,
    amount DECIMAL(18,2),
    volume INTEGER,
    price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- K线数据表
CREATE TABLE klines (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    trade_date DATE NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    amount DECIMAL(18,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, trade_date)
);
```

---

## 五、开发计划

### 5.1 阶段划分

#### 第一阶段：基础框架（Day 1-3）
- [ ] 项目结构搭建
- [ ] 数据库设计与初始化
- [ ] 后端API框架
- [ ] 前端框架搭建
- [ ] 用户认证模块

#### 第二阶段：核心功能（Day 4-7）
- [ ] 行情数据接口
- [ ] 策略管理模块
- [ ] 回测引擎开发
- [ ] 模拟交易模块
- [ ] 账户管理模块

#### 第三阶段：完善优化（Day 8-10）
- [ ] 前端界面完善
- [ ] 技术指标图表
- [ ] 风控系统
- [ ] 性能优化
- [ ] 测试与修复

#### 第四阶段：部署上线（Day 11-14）
- [ ] Docker容器化
- [ ] 部署配置
- [ ] 数据源对接
- [ ] 安全加固
- [ ] 上线测试

### 5.2 时间表

| 阶段 | 内容 | 时间 |
|------|------|------|
| Day 1-3 | 基础框架 | 3天 |
| Day 4-7 | 核心功能 | 4天 |
| Day 8-10 | 完善优化 | 3天 |
| Day 11-14 | 部署上线 | 4天 |
| **总计** | | **14天** |

---

## 六、资源需求

### 6.1 技术资源

| 资源 | 用途 | 成本 |
|------|------|------|
| 云服务器 | 部署后端 | ¥100-300/月 |
| 数据库 | PostgreSQL | ¥0（自建） |
| 行情数据 | Tushare/AKShare | ¥0（免费） |
| 域名 | 访问入口 | ¥50-100/年 |

### 6.2 人力需求

| 角色 | 工作 | 时间 |
|------|------|------|
| 全栈开发 | 后端+前端 | 全程 |
| 测试 | 功能测试 | Day 8-14 |

---

## 七、风险评估

### 7.1 技术风险

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 数据源不稳定 | 中 | 高 | 多数据源备份 |
| 性能瓶颈 | 中 | 中 | 缓存优化、异步处理 |
| 安全漏洞 | 低 | 高 | 安全审计、加密 |

### 7.2 业务风险

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 用户需求变化 | 高 | 中 | 敏捷开发、快速迭代 |
| 竞品压力 | 中 | 中 | 差异化定位 |
| 监管政策 | 低 | 高 | 模拟盘优先、合规设计 |

---

## 八、下一步行动

### 立即执行
1. ✅ 项目结构已创建
2. ⏳ 完善数据库设计
3. ⏳ 实现用户认证
4. ⏳ 对接行情数据源

### 本周目标
- 完成基础框架
- 实现行情模块
- 完成策略管理基础功能

### 下周目标
- 完成回测引擎
- 实现模拟交易
- 前端界面完善

---

*创建时间：2026-03-21*
*预计完成：2026-04-04*