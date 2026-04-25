# ComputeHub v2.0 MVP 简化重写方案
## 基于 deepseek-v4-flash 分支

---

## 一、背景

当前工程代码仅以 `.pyc` 编译字节码存在，源码 `.py` 文件未提交到 Git。
反编译分析已完成，完整代码逻辑已逆向理解。

**问题**: 
- 无法直接编辑 `.pyc`
- 架构设计好但工程半成品
- 配置/依赖/部署文件缺失
- 安全漏洞（`hashlib` 而非 `bcrypt`）
- 不适合生产的存储选型（SQLite + JSON）

---

## 二、目标

在 `deepseek-v4-flash` 分支上，按以下原则重构出一个**最小可用版本**：

- ✅ **代码可编辑、可运行**
- ✅ **配置可管理（环境变量 + YAML）**
- ✅ **一键部署（Docker Compose）**
- ✅ **安全合规（bcrypt + JWT）**
- ✅ **核心流程完整（提交→调度→执行→结果）**
- ✅ **AI 就绪架构（预留 DeepSeek 接入点）**
- ✅ **Git 版本控制**

---

## 三、架构（简化版）

```
┌─────────────────────────────────────┐
│         FastAPI Gateway             │
│   (JWT认证 + RESTful API)          │
├─────────────────────────────────────┤
│         Celery Worker               │
│   (Redis Broker)                    │
├────────────┬────────────┬───────────┤
│  Scheduler │  Pipeline  │ Executor  │
│  (2策略)   │  (简化为2)  │ (子进程)  │
├────────────┴────────────┴───────────┤
│         PostgreSQL                  │
│   (users, nodes, tasks, history)   │
└─────────────────────────────────────┘
```

**砍掉的部分**:
- ❌ `learning/` 整个模块（genes.json 高并发问题，后续用数据库重建）
- ❌ `kernel/` 的 DeterministicKernel 快照机制（单节点无意义）
- ❌ Pipeline 4 Stage → 只保留 SyntaxFilter + SecurityFilter
- ❌ 调度策略 4种 → 只保留 `least_connections` + `round_robin`
- ❌ `node/` 节点代理（初期手动部署 Worker）
- ❌ K8s 部署（K8s 目录仍为空，暂不处理）

---

## 四、文件结构（最终目标）

```
computehub/
├── src/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 入口
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # 配置管理（YAML + 环境变量）
│   │   ├── database.py          # SQLAlchemy + PostgreSQL
│   │   └── logging.py           # 日志
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py              # ORM Base
│   │   ├── user.py              # User (bcrypt)
│   │   ├── node.py              # Node
│   │   └── task.py              # Task
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py              # JWT 认证依赖
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       ├── routes/
│   │       │   ├── __init__.py
│   │       │   ├── auth.py
│   │       │   ├── users.py
│   │       │   ├── nodes.py
│   │       │   └── tasks.py
│   │       └── schemas/
│   │           ├── __init__.py
│   │           ├── user.py
│   │           ├── node.py
│   │           └── task.py
│   ├── kernel/
│   │   ├── __init__.py
│   │   ├── scheduler.py         # 简化调度器
│   │   └── load_balancer.py     # 2策略 Load Balancer
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── pipeline.py          # 2 Stage Pipeline
│   ├── executor/
│   │   ├── __init__.py
│   │   └── executor.py          # 子进程执行器
│   └── workers/
│       ├── __init__.py
│       └── task_worker.py       # Celery Worker
├── config.yaml                  # 配置文件
├── requirements.txt             # 依赖
├── Dockerfile                   # 构建文件
├── docker-compose.yml           # 一键部署
├── .env.example                 # 环境变量模板
├── tests/
│   ├── __init__.py
│   ├── test_scheduler.py
│   └── test_executor.py
├── scripts/
│   ├── deploy.py
│   └── seed.py                  # 初始数据
├── README.md
└── CONTRIBUTING.md
```

---

## 五、实施计划（5个阶段）

### Phase 1 — 基础设施 (2h)

**目标**: 项目骨架可运行

| # | 任务 | 产出 |
|---|------|------|
| 1.1 | 初始化 `deepseek-v4-flash` 分支，清理 untracked 文件 | 干净的分支 |
| 1.2 | 创建 `src/main.py`（FastAPI 入口，uvicorn） | 可启动的 API |
| 1.3 | 创建 `config.yaml` + `src/core/config.py` | 配置管理 |
| 1.4 | 创建 `requirements.txt` | 依赖清单 |
| 1.5 | 创建 `Dockerfile` + `docker-compose.yml`（PostgreSQL + Redis + App） | 一键启动 |
| 1.6 | 提交所有文件到 git | git commit |

**关键决策**: 配置用 YAML + 环境变量覆盖（12-Factor App）

### Phase 2 — 数据层 (2h)

**目标**: 数据库模型 + 认证可用

| # | 任务 | 产出 |
|---|------|------|
| 2.1 | `src/core/database.py` — PostgreSQL 连接 | 可用的 engine/session |
| 2.2 | `src/models/base.py` + user/node/task | ORM 模型 |
| 2.3 | `src/api/auth.py` — JWT 依赖注入 | token 验证装饰器 |
| 2.4 | `src/api/v1/schemas/*` — Pydantic 模型 | 请求/响应校验 |
| 2.5 | `src/api/v1/routes/auth.py` — 注册/登录（bcrypt） | 认证流程可用 |
| 2.6 | `scripts/seed.py` — 初始数据脚本 | 启动时自动建表 |

**关键决策**: 密码用 `passlib[bcrypt]` 替代 `hashlib`

### Phase 3 — 核心逻辑 (3h)

**目标**: 任务提交→调度→执行→结果入库 闭环

| # | 任务 | 产出 |
|---|------|------|
| 3.1 | `src/kernel/load_balancer.py` — 2策略（least_connections, round_robin） | 节点选择 |
| 3.2 | `src/kernel/scheduler.py` — 简化调度器（调用 LB + 写入 DB） | 任务调度 |
| 3.3 | `src/pipeline/pipeline.py` — 2 Stage（Syntax + Security） | 任务净化 |
| 3.4 | `src/executor/executor.py` — subprocess 执行 + timeout | 任务执行 |
| 3.5 | `src/workers/task_worker.py` — Celery 异步调度 | 异步执行 |
| 3.6 | `src/api/v1/routes/tasks.py` — 提交/查询/取消任务 | 用户 API |
| 3.7 | `src/api/v1/routes/nodes.py` — 注册/心跳/列表 | 节点管理 API |

### Phase 4 — 测试 & 完善 (1h)

**目标**: 核心逻辑有测试保障

| # | 任务 | 产出 |
|---|------|------|
| 4.1 | `tests/test_scheduler.py` — round_robin + least_connections | 调度器测试 |
| 4.2 | `tests/test_executor.py` — 正常执行 + 超时 | 执行器测试 |
| 4.3 | `tests/test_api_auth.py` — 注册/登录/鉴权 | 认证测试 |
| 4.4 | 编写 `README.md` | 项目文档 |

### Phase 5 — AI 接入 (预留, 后续)

**目标**: DeepSeek 增强调度

| # | 任务 | 产出 |
|---|------|------|
| 5.1 | 建 `task_execution_history` 表 | 数据基础 |
| 5.2 | 实现 `AISchedulerAdvisor` — 查询历史 + 调用 DeepSeek | 智能调度建议 |
| 5.3 | 实现降级策略 — DeepSeek 不可用时 fallback 到 round_robin | 系统鲁棒性 |

---

## 六、关键设计决策

### 配置管理

```yaml
# config.yaml
database:
  url: "postgresql+asyncpg://user:pass@localhost:5432/computehub"
gateway:
  host: "0.0.0.0"
  port: 8000
auth:
  secret_key: "change-me-in-production"
  algorithm: "HS256"
  access_token_expire_minutes: 1440
executor:
  timeout_seconds: 300
  sandbox_path: "/tmp/computehub-sandbox"
```

环境变量覆盖: `COMPUTEHUB_DATABASE_URL`, `COMPUTEHUB_SECRET_KEY`, `COMPUTEHUB_PORT` 等。

### 任务生命周期

```
PENDING → VALIDATING → QUEUED → DISPATCHED → RUNNING → COMPLETED
                                       |           |
                                       ↓           ↓
                                     FAILED      TIMEOUT
```

### API 端点

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | /api/v1/auth/register | ❌ | 注册 |
| POST | /api/v1/auth/login | ❌ | 登录 → JWT |
| GET | /api/v1/users/me | ✅ | 当前用户 |
| POST | /api/v1/nodes/register | ✅ | 节点注册 |
| GET | /api/v1/nodes | ✅ | 节点列表 |
| POST | /api/v1/tasks | ✅ | 提交任务 |
| GET | /api/v1/tasks | ✅ | 任务列表 |
| GET | /api/v1/tasks/{id} | ✅ | 任务详情 |

---

## 七、技术栈

| 组件 | 选型 | 理由 |
|------|------|------|
| 框架 | **FastAPI** | 高性能，自动文档 |
| 数据库 | **PostgreSQL** | 生产级，支持并发 |
| ORM | **SQLAlchemy** | 成熟稳定 |
| 异步 | **Celery + Redis** | 任务队列标准方案 |
| 认证 | **python-jose + passlib[bcrypt]** | 安全合规 |
| 配置 | **PyYAML + os.getenv** | 12-Factor App |
| 容器 | **Docker + Docker Compose** | 一键部署 |
| AI | **ollama-cloud/deepseek-v4-flash** | 后续集成 |

---

## 八、时间预估

| Phase | 内容 | 预估时间 |
|-------|------|---------|
| 1 | 基础设施 | ~2h |
| 2 | 数据层 + 认证 | ~2h |
| 3 | 核心逻辑 | ~3h |
| 4 | 测试完善 | ~1h |
| **总计** | | **~8h** |

---

## 九、风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| 反编译逻辑不完整 | 中 | 高 | 边写边验证，对照 bytecode |
| SQLite→PostgreSQL 适配 | 低 | 中 | 用 SQLAlchemy ORM，切换简单 |
| Celery 配置复杂 | 中 | 低 | 先跑单进程，再切 Celery |
| DeepSeek API 调用失败 | 高 | 低 | 调度降级到 round_robin |
| 节点实际不可用 | 中 | 中 | 心跳超时自动标记 OFFLINE |

---

*方案版本: v1.0 | 2026-04-25 | 基于 DeepSeek-V4-Flash 分析*
