# 🚀 ComputeHub v2.0 重启开发计划

> 基于 OpenPC System 成熟架构模式重构 | 2026-04-23

---

## 📋 执行摘要

| 维度 | 现状 | 目标 |
|------|------|------|
| **状态** | 骨架项目，源码丢失（仅 pycache） | 从零重建，可编译可运行 |
| **技术栈** | Python + FastAPI + SQLite（已有） | Python + FastAPI + SQLite → PostgreSQL 演进 |
| **参考架构** | ❌ 无 | ✅ OpenPC System（已验证的模块化架构） |
| **数据库** | SQLite，含 3 表 11 条测试数据 | 保留 schema，迁移至生产级存储 |
| **部署** | ❌ 无 | ✅ systemd + k8s（借鉴 opcsystem 管理脚本） |

---

## 🏗️ 架构设计：借鉴 OpenPC System

### 核心映射关系

OpenPC System 的模式可以完美映射到 ComputeHub：

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ComputeHub v2.0 架构（融合 OpenPC System 模式）                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Client (Web/CLI/SDK)                                                    │
│       │                                                                   │
│  ┌────▼────┐                                                              │
│  │ Gateway │  ← API 网关（借鉴 opc-gateway）                                │
│  │ 网关层   │  - REST API + WebSocket                                       │
│  └────┬────┘  - 认证授权                                                     │
│       │                                                                   │
│  ┌────▼────┐                                                              │
│  │Pipeline │  ← 任务净化管道（借鉴 pure/pipeline）                           │
│  │任务净化  │  - 语法校验 → 权限校验 → 资源校验 → 安全隔离                     │
│  └────┬────┘                                                              │
│       │                                                                   │
│  ┌────▼────┐                                                              │
│  │ Kernel  │  ← 任务调度内核（借鉴 kernel/kernel）                           │
│  │调度内核  │  - 确定性任务队列                                               │
│  │         │  - 优先级 + 负载均衡                                            │
│  │         │  - 状态镜像（支持回滚）                                          │
│  └────┬────┘                                                              │
│       │                                                                   │
│  ┌────▼────┐                                                              │
│  │Executor │  ← 任务执行器（借鉴 executor/executor）                         │
│  │执行器   │  - 容器化执行环境                                               │
│  │         │  - 结果验证 + 学习反馈                                          │
│  └────┬────┘                                                              │
│       │                                                                   │
│  ┌────▼────┐                                                              │
│  │ Gene    │  ← 智能学习存储（借鉴 gene/store）                              │
│  │ Store   │  - 执行模式学习                                                │
│  │         │  - 优化策略演化                                                │
│  └─────────┘                                                              │
│                                                                          │
│  数据层: SQLite (dev) → PostgreSQL (prod)                                 │
│  配置:   JSON/YAML 配置文件驱动                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构（v2.0 重构）

```
computehub/
├── config/                    # 配置系统（借鉴 opcsystem config.json）
│   ├── config.yaml            # 主配置文件
│   └── config.json            # JSON 配置（兼容）
│
├── src/                       # 源代码（借鉴 opcsystem/src/ 结构）
│   ├── gateway/               # API 网关
│   │   ├── __init__.py
│   │   ├── api.py             # REST API 路由
│   │   ├── websocket.py       # WebSocket 实时推送
│   │   └── auth.py            # 认证授权
│   │
│   ├── kernel/                # 调度内核
│   │   ├── __init__.py
│   │   ├── scheduler.py       # 确定性任务队列调度器
│   │   ├── load_balancer.py   # 负载均衡器
│   │   └── state_mirror.py    # 状态镜像（支持回滚）
│   │
│   ├── pipeline/              # 任务净化管道（借鉴 pure/pipeline）
│   │   ├── __init__.py
│   │   ├── syntax_check.py    # Stage 1: 语法/格式校验
│   │   ├── security_check.py  # Stage 2: 安全校验
│   │   ├── resource_check.py  # Stage 3: 资源可行性校验
│   │   └── context_filter.py  # Stage 4: 上下文注入
│   │
│   ├── executor/              # 任务执行器（借鉴 executor/executor）
│   │   ├── __init__.py
│   │   ├── container_mgr.py   # 容器管理（Docker/podman）
│   │   ├── validator.py       # 执行结果验证器
│   │   └── sandbox.py         # 沙箱隔离
│   │
│   ├── learning/              # 智能学习存储（借鉴 gene/store）
│   │   ├── __init__.py
│   │   ├── store.py           # 持久化存储
│   │   ├── evolve.py          # 模式演化
│   │   └── recall.py          # 模式召回
│   │
│   ├── models/                # 数据模型（现有，保留）
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── node.py
│   │   └── task.py
│   │
│   └── workers/               # 后台工作进程（借鉴 celery）
│       ├── __init__.py
│       └── task_worker.py
│
├── main.py                    # 启动入口（借鉴 main_gateway.go）
├── alembic/                   # 数据库迁移（现有）
│   └── versions/              # 迁移脚本
│
├── tests/                     # 测试（从零构建）
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── scripts/                   # 管理脚本（借鉴 opcsystem 启动脚本）
│   ├── start-gateway.sh       # 启动网关
│   ├── stop-gateway.sh        # 停止网关
│   ├── start-worker.sh        # 启动工作进程
│   ├── health-check.sh        # 健康检查
│   └── logs.sh               # 日志查看
│
├── deploy/                    # 部署
│   └── k8s/                   # Kubernetes 配置
│       ├── gateway-deploy.yaml
│       ├── worker-deploy.yaml
│       └── ingress.yaml
│
├── requirements.txt           # 依赖
├── pyproject.toml             # 项目配置
└── README.md                  # 项目文档
```

---

## 📅 开发路线图

### Phase 0: 基础设施搭建（Day 1-2）

**目标**: 从零搭建可编译运行骨架

| # | 任务 | 交付物 | 耗时 |
|---|------|--------|------|
| 0.1 | 反编译 pycache 获取现有代码 | `decompiled/` 目录 | 2h |
| 0.2 | 清理项目结构，创建 `src/` 模块化目录 | 模块化目录树 | 1h |
| 0.3 | 创建配置系统 (`config.yaml` + `config.json`) | 配置文件 | 1h |
| 0.4 | 创建时间戳日志工具类 | `src/core/logging.py` | 1h |
| 0.5 | 创建启动入口 `main.py` | 可运行入口 | 2h |
| 0.6 | 恢复 `alembic` 迁移（基于现有 schema） | 迁移脚本 | 2h |
| 0.7 | 运行数据库迁移 | 验证数据库可用 | 1h |
| **合计** | | | **~10h** |

### Phase 1: 核心网关（Day 3-5）

**目标**: 实现 REST API 网关，完全可运行

| # | 任务 | 交付物 | 耗时 |
|---|------|--------|------|
| 1.1 | 实现 Gateway 类（借鉴 `gateway.go` 模式） | `src/gateway/api.py` | 4h |
| 1.2 | 实现健康检查 `/api/health` | 健康接口 | 1h |
| 1.3 | 实现状态接口 `/api/status` | 状态接口 | 2h |
| 1.4 | 实现用户管理 API（CRUD） | `/api/v1/users/*` | 4h |
| 1.5 | 实现节点管理 API（CRUD） | `/api/v1/nodes/*` | 4h |
| 1.6 | 实现任务提交流程 `/api/v1/tasks/submit` | 任务提交接口 | 4h |
| 1.7 | 实现认证/授权中间件 | JWT 认证 | 4h |
| **合计** | | | **~23h** |

### Phase 2: 任务调度内核（Day 6-8）

**目标**: 实现确定性调度内核

| # | 任务 | 交付物 | 耗时 |
|---|------|--------|------|
| 2.1 | 实现确定性任务队列调度器 | `kernel/scheduler.py` | 6h |
| 2.2 | 实现状态镜像（快照 + 回滚） | `kernel/state_mirror.py` | 4h |
| 2.3 | 实现负载均衡器 | `kernel/load_balancer.py` | 4h |
| 2.4 | 实现节点发现与注册 | 节点管理增强 | 3h |
| **合计** | | | **~17h** |

### Phase 3: 任务净化管道（Day 9-10）

**目标**: 实现四级安全过滤管道

| # | 任务 | 交付物 | 耗时 |
|---|------|--------|------|
| 3.1 | Stage 1: 语法/格式校验 | `pipeline/syntax_check.py` | 2h |
| 3.2 | Stage 2: 安全/权限校验 | `pipeline/security_check.py` | 3h |
| 3.3 | Stage 3: 资源可行性校验 | `pipeline/resource_check.py` | 2h |
| 3.4 | Stage 4: 上下文注入 | `pipeline/context_filter.py` | 2h |
| 3.5 | Pipeline 编排器 | `pipeline/__init__.py` | 2h |
| **合计** | | | **~11h** |

### Phase 4: 任务执行器（Day 11-13）

**目标**: 实现容器化执行 + 验证

| # | 任务 | 交付物 | 耗时 |
|---|------|--------|------|
| 4.1 | 容器管理器（Docker/podman） | `executor/container_mgr.py` | 6h |
| 4.2 | 沙箱隔离环境 | `executor/sandbox.py` | 4h |
| 4.3 | 执行结果验证器 | `executor/validator.py` | 3h |
| 4.4 | Execute → Verify → Learn 闭环 | 集成测试 | 3h |
| **合计** | | | **~16h** |

### Phase 5: 智能学习（Day 14-15）

**目标**: 实现模式学习 + 优化

| # | 任务 | 交付物 | 耗时 |
|---|------|--------|------|
| 5.1 | 学习存储层（借鉴 gene/store） | `learning/store.py` | 3h |
| 5.2 | 模式演化机制 | `learning/evolve.py` | 3h |
| 5.3 | 模式召回 + 优化建议 | `learning/recall.py` | 2h |
| **合计** | | | **~8h** |

### Phase 6: 测试 + 部署（Day 16-18）

**目标**: 完整测试 + 生产部署能力

| # | 任务 | 交付物 | 耗时 |
|---|------|--------|------|
| 6.1 | 单元测试（覆盖率 ≥ 80%） | `tests/unit/` | 6h |
| 6.2 | 集成测试 | `tests/integration/` | 4h |
| 6.3 | 管理脚本（借鉴 opcsystem） | `scripts/` | 2h |
| 6.4 | systemd 服务文件 | `.service` 文件 | 2h |
| 6.5 | Kubernetes 部署配置 | `deploy/k8s/` | 4h |
| 6.6 | CI/CD 流水线（GitHub Actions） | `.github/workflows/` | 2h |
| **合计** | | | **~20h** |

---

## 📊 总计划

| Phase | 描述 | 耗时 | 累计 |
|-------|------|------|------|
| 0 | 基础设施 | ~10h | 10h |
| 1 | 核心网关 | ~23h | 33h |
| 2 | 调度内核 | ~17h | 50h |
| 3 | 净化管道 | ~11h | 61h |
| 4 | 执行器 | ~16h | 77h |
| 5 | 智能学习 | ~8h | 85h |
| 6 | 测试+部署 | ~20h | **105h ≈ 13 个工作日** |

---

## 🔑 关键设计原则（从 opcsystem 继承）

### 1. 时间戳日志
```python
# 所有操作都有精确时间戳
def log_with_timestamp(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")
```

### 2. 配置驱动
```yaml
# config.yaml - 一切可配置
gateway:
  port: 8000
  workers: 4
  max_connections: 100
kernel:
  queue_size: 1000
  max_states: 10000
executor:
  sandbox_path: /tmp/computehub-sandbox
  default_framework: pytorch
learning:
  store_path: ./genes.json
  recall_threshold: 0.8
```

### 3. 确定性调度
```
任务进入 → 净化管道 → 状态快照 → 线性队列 → 执行 → 验证 → 学习
         ↓           ↓           ↓          ↓        ↓        ↓
       语法检查     状态镜像     优先级     容器化   结果验证  模式记录
```

### 4. 模块独立可测试
每个模块都是独立包，可单独测试：
- `gateway/` → 可独立测试 API 端点
- `kernel/` → 可独立测试调度逻辑
- `pipeline/` → 可独立测试过滤规则
- `executor/` → 可独立测试执行逻辑

---

## ⚡ 快速启动命令

```bash
# 启动网关
./scripts/start-gateway.sh start

# 启动工作进程
./scripts/start-worker.sh start

# 健康检查
./scripts/health-check.sh

# 查看日志
./scripts/logs.sh

# 停止服务
./scripts/stop-gateway.sh
```

---

## 📈 里程碑

| 里程碑 | 时间 | 状态 |
|--------|------|------|
| M0: 骨架可编译 | Day 2 | ⏳ 待启动 |
| M1: API 可调用 | Day 5 | ⏳ |
| M2: 调度可运行 | Day 8 | ⏳ |
| M3: 端到端可执行 | Day 13 | ⏳ |
| M4: 生产就绪 | Day 18 | ⏳ |

---

*计划制定: 2026-04-23 | 基于 OpenPC System 架构模式*
