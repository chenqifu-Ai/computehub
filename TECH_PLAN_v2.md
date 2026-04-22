# 🚀 ComputeHub 技术规划书 v2.0

**版本**: v2.0 (技术统一版)  
**制定时间**: 2026-04-22  
**核心原则**: 成熟优先 · 避免重复 · 技术统一

---

## 📋 技术选型原则

### 1. 成熟度优先 (Maturity First)
- 选择经过生产验证的框架，不追新
- 社区活跃、文档完善、长期支持 (LTS)
- 避免重复造轮子，优先集成现有方案

### 2. 技术统一 (Tech Unity)
- 全栈 Python 优先（减少语言切换成本）
- 统一数据模型和接口规范
- 避免同一功能多种实现

### 3. 先进性保障 (Advanced but Stable)
- 在成熟基础上选择最优解
- 性能指标可量化、可测试
- 支持水平扩展和云原生部署

---

## 🏛️ 系统架构 (精简版)

```
┌─────────────────────────────────────────────────────────┐
│                    用户界面层                              │
│         Web Dashboard (React) │ CLI │ SDK                │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    API 网关层 (FastAPI)                   │
│         认证 (JWT) │ 限流 (Redis) │ 路由 │ 日志          │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    调度层 (Celery + Redis)                │
│         任务队列 │ 智能调度 │ 负载均衡 │ 重试机制        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    节点层 (gRPC)                          │
│    GPU 节点 │ CPU 节点 │ 存储节点 (全球分布式部署)         │
└─────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    区块链层 (可选)                         │
│         智能合约 (Solidity) │ 自动结算 │ Token 管理       │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈明细

### 后端核心

| 功能 | 技术选型 | 理由 | 替代方案 |
|------|----------|------|----------|
| **Web 框架** | FastAPI 0.100+ | 高性能、异步、自动生成 OpenAPI 文档 | Flask (慢), Django (重) |
| **任务队列** | Celery 5.3+ + Redis | 成熟稳定、支持定时任务、重试机制 | RQ (简单), Dramatiq (新) |
| **数据库** | PostgreSQL 15+ | ACID、JSONB 支持、成熟可靠 | MySQL (功能少), SQLite (单机) |
| **缓存** | Redis 7+ | 高性能、数据结构丰富、Pub/Sub | Memcached (功能单一) |
| **ORM** | SQLAlchemy 2.0+ | 成熟、灵活、支持异步 | Tortoise (新), Peewee (简单) |
| **数据迁移** | Alembic | SQLAlchemy 官方迁移工具 | 手动迁移 (易错) |

### 节点通信

| 功能 | 技术选型 | 理由 | 替代方案 |
|------|----------|------|----------|
| **RPC 框架** | gRPC 1.50+ | 高性能、双向流、多语言 | REST (慢), Thrift (复杂) |
| **协议缓冲** | Protocol Buffers 3.x | 紧凑、高效、版本兼容 | JSON (慢), MessagePack (新) |
| **服务发现** | Consul / etcd | 成熟、支持健康检查 | 硬编码 (不可扩展) |

### 监控与可观测性

| 功能 | 技术选型 | 理由 | 替代方案 |
|------|----------|------|----------|
| **指标收集** | Prometheus | 云原生标准、Pull 模型 | InfluxDB (Push), StatsD (简单) |
| **可视化** | Grafana | 成熟、插件丰富、免费 | Kibana (重), Datadog (贵) |
| **日志** | Structlog + ELK | 结构化日志、可搜索 | 纯文本 (难分析) |
| **链路追踪** | Jaeger / Zipkin | OpenTelemetry 兼容 | 自研 (重复造轮子) |

### 部署与运维

| 功能 | 技术选型 | 理由 | 替代方案 |
|------|----------|------|----------|
| **容器化** | Docker 24+ | 行业标准、生态完善 | Podman (新), LXC (复杂) |
| **编排** | Kubernetes 1.27+ | 云原生标准、自动扩缩容 | Docker Swarm (简单), Nomad (新) |
| **CI/CD** | GitHub Actions | 集成在 GitHub、免费额度 | GitLab CI, Jenkins (重) |
| **配置管理** | Pydantic Settings | 类型安全、自动验证 | 环境变量 (易错), YAML (无验证) |

### 区块链 (可选模块)

| 功能 | 技术选型 | 理由 | 替代方案 |
|------|----------|------|----------|
| **智能合约** | Solidity 0.8+ | 行业标准、工具链完善 | Vyper (新), Rust (复杂) |
| **Web3 交互** | Web3.py 6+ | Python 原生、成熟 | Brownie (重), Ape (新) |
| **测试网** | Sepolia / Goerli | 免费、稳定 | 主网 (贵), 本地链 (不真实) |

### 前端 (Dashboard)

| 功能 | 技术选型 | 理由 | 替代方案 |
|------|----------|------|----------|
| **框架** | React 18+ | 生态最大、人才多 | Vue (简单), Svelte (新) |
| **UI 库** | Ant Design / MUI | 组件丰富、企业级 | Tailwind (手写), Bootstrap (旧) |
| **图表** | Recharts / Chart.js | 简单好用、文档好 | D3 (复杂), ECharts (重) |
| **地图** | Leaflet + OpenStreetMap | 免费、轻量 | Google Maps (贵), Mapbox (收费) |

### 开发工具链

| 功能 | 技术选型 | 理由 | 替代方案 |
|------|----------|------|----------|
| **代码格式化** | Black + isort | 官方推荐、无配置 | Prettier (JS), autopep8 (旧) |
| **类型检查** | mypy 1.0+ | 成熟、严格 | Pyright (新), Pyre (Meta) |
| **Lint** | Ruff | 超快 (Rust 编写)、兼容 Flake8 | Flake8 (慢), Pylint (慢) |
| **测试框架** | pytest 7+ + pytest-asyncio | 插件丰富、异步支持 | unittest (内置), nose (旧) |
| **覆盖率** | pytest-cov | 集成 pytest、报告清晰 | coverage.py (手动) |
| **文档生成** | MkDocs + Material | 美观、Markdown 友好 | Sphinx (复杂), Docusaurus (JS) |

---

## 📦 项目结构 (标准化)

```
computehub/
├── backend/                    # 后端服务
│   ├── api/                   # FastAPI 路由
│   │   ├── v1/               # API 版本
│   │   │   ├── routes/       # 路由定义
│   │   │   ├── schemas/      # Pydantic 模型
│   │   │   └── deps/         # 依赖注入
│   │   └── __init__.py
│   ├── core/                  # 核心配置
│   │   ├── config.py         # Pydantic Settings
│   │   ├── security.py       # JWT/认证
│   │   └── exceptions.py     # 自定义异常
│   ├── models/                # SQLAlchemy 模型
│   │   ├── node.py           # 节点模型
│   │   ├── task.py           # 任务模型
│   │   └── user.py           # 用户模型
│   ├── services/              # 业务逻辑
│   │   ├── scheduler.py      # 调度服务
│   │   ├── monitor.py        # 监控服务
│   │   └── billing.py        # 计费服务
│   ├── workers/               # Celery 任务
│   │   ├── tasks.py          # 异步任务
│   │   └── schedulers.py     # 定时任务
│   └── main.py               # 应用入口
│
├── node/                      # 节点代理 (Python)
│   ├── agent.py              # 节点代理主程序
│   ├── monitor.py            # 资源监控 (GPU/CPU/网络)
│   ├── executor.py           # 任务执行器
│   └── config.py             # 节点配置
│
├── proto/                     # gRPC 协议定义
│   ├── node.proto            # 节点通信协议
│   └── task.proto            # 任务协议
│
├── blockchain/                # 区块链模块 (可选)
│   ├── contracts/            # Solidity 合约
│   │   ├── ComputeToken.sol
│   │   └── Settlement.sol
│   └── web3_client.py        # Web3.py 封装
│
├── web/                       # 前端 Dashboard
│   ├── src/                  # React 源码
│   ├── public/               # 静态资源
│   └── package.json
│
├── deployments/               # 部署配置
│   ├── docker/               # Dockerfile
│   ├── k8s/                  # Kubernetes YAML
│   └── docker-compose.yml    # 本地开发
│
├── tests/                     # 测试
│   ├── unit/                 # 单元测试
│   ├── integration/          # 集成测试
│   └── e2e/                  # 端到端测试
│
├── docs/                      # 文档
│   ├── api/                  # API 文档
│   ├── guides/               # 使用指南
│   └── architecture/         # 架构文档
│
├── scripts/                   # 工具脚本
│   ├── setup.sh              # 环境初始化
│   ├── migrate.py            # 数据库迁移
│   └── seed.py               # 测试数据
│
├── requirements.txt           # Python 依赖
├── requirements-dev.txt       # 开发依赖
├── pyproject.toml             # 项目配置 (Black/Ruff/mypy)
├── alembic.ini                # 数据库迁移配置
└── README.md                  # 项目说明
```

---

## 🎯 核心功能实现策略

### 1. API 网关层 (FastAPI)

**不重复造轮子**:
- ✅ 使用 FastAPI 内置依赖注入
- ✅ 使用 `fastapi-limiter` 实现限流
- ✅ 使用 `python-jose` 处理 JWT
- ✅ 使用 `passlib` 处理密码哈希

**关键文件**:
```python
# backend/api/v1/routes/nodes.py
from fastapi import APIRouter, Depends, HTTPException
from backend.api.v1.deps import get_current_user
from backend.services.scheduler import NodeService

router = APIRouter()

@router.get("/nodes", response_model=List[NodeSchema])
async def list_nodes(current_user = Depends(get_current_user)):
    """列出所有可用节点"""
    return await NodeService.list_active()

@router.post("/nodes/register")
async def register_node(node_data: NodeRegisterSchema):
    """节点注册"""
    return await NodeService.register(node_data)
```

---

### 2. 调度系统 (Celery + Redis)

**不重复造轮子**:
- ✅ 使用 Celery 内置任务队列
- ✅ 使用 `celery-beat` 实现定时调度
- ✅ 使用 Redis Stream 实现任务分发
- ✅ 使用 `tenacity` 实现重试逻辑

**关键文件**:
```python
# backend/workers/tasks.py
from celery import Celery
from tenacity import retry, stop_after_attempt, wait_exponential

celery_app = Celery('computehub', broker='redis://localhost:6379/0')

@celery_app.task(bind=True, max_retries=3)
@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def execute_task(self, task_id: str, node_id: str):
    """在指定节点执行任务"""
    try:
        # 调用 gRPC 节点执行
        result = grpc_client.execute(node_id, task_id)
        return {"status": "completed", "result": result}
    except Exception as exc:
        raise self.retry(exc=exc)
```

---

### 3. 节点监控 (物理心跳)

**不重复造轮子**:
- ✅ 使用 `pynvml` 监控 NVIDIA GPU
- ✅ 使用 `psutil` 监控系统资源
- ✅ 使用 `ping3` 测量网络延迟
- ✅ 使用 `uuid` 生成硬件指纹

**关键文件**:
```python
# node/monitor.py
import pynvml
import psutil
from ping3 import ping

class NodeMonitor:
    def get_gpu_status(self) -> dict:
        """获取 GPU 物理状态"""
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        return {
            "gpu_temp": pynvml.nvmlDeviceGetTemperature(handle, 0),
            "gpu_util": pynvml.nvmlDeviceGetUtilizationRates(handle).gpu,
            "mem_used": pynvml.nvmlDeviceGetMemoryInfo(handle).used,
            "mem_total": pynvml.nvmlDeviceGetMemoryInfo(handle).total,
        }
    
    def get_heartbeat(self) -> dict:
        """物理心跳报告"""
        return {
            "timestamp": time.time(),
            "node_id": self.node_id,
            "gpu": self.get_gpu_status(),
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent,
            "network_latency": ping("gateway.computehub.io") * 1000,  # ms
            "hardware_fingerprint": self.get_fingerprint(),
        }
```

---

### 4. 数据库设计 (PostgreSQL + SQLAlchemy)

**核心表结构**:
```sql
-- 节点表
CREATE TABLE nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'offline',  -- online/offline/maintenance
    gpu_model VARCHAR(255),
    gpu_count INTEGER,
    location GEOGRAPHY(POINT),  -- PostGIS 地理坐标
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 任务表
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'pending',  -- pending/running/completed/failed
    node_id UUID REFERENCES nodes(id),
    framework VARCHAR(50),  -- pytorch/tensorflow/jax
    gpu_required INTEGER DEFAULT 1,
    duration_hours INTEGER,
    result_path TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 计费记录表
CREATE TABLE billings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    node_id UUID REFERENCES nodes(id),
    gpu_hours DECIMAL(10, 2),
    unit_price DECIMAL(10, 4),
    total_amount DECIMAL(10, 2),
    status VARCHAR(50) DEFAULT 'pending',  -- pending/paid/refunded
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 5. 防御性机制

**区域熔断** (使用 `circuitbreaker` 库):
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def dispatch_to_region(region: str, task: Task):
    """带熔断的区域调度"""
    nodes = get_nodes_in_region(region)
    if not nodes:
        raise CircuitOpenError(f"Region {region} unavailable")
    return select_best_node(nodes, task)
```

**任务状态机** (使用 `transitions` 库):
```python
from transitions import Machine

class TaskStateMachine(Machine):
    states = ['pending', 'scheduled', 'executing', 'verifying', 'completed', 'failed']
    
    transitions = [
        {'trigger': 'schedule', 'source': 'pending', 'dest': 'scheduled'},
        {'trigger': 'start', 'source': 'scheduled', 'dest': 'executing'},
        {'trigger': 'verify', 'source': 'executing', 'dest': 'verifying'},
        {'trigger': 'complete', 'source': 'verifying', 'dest': 'completed'},
        {'trigger': 'fail', 'source': '*', 'dest': 'failed'},
    ]
```

---

## 📅 实施路线图 (精简版)

### 阶段一：基础架构 (2 周)
| 周次 | 任务 | 交付物 |
|------|------|--------|
| W1 | FastAPI 框架 + PostgreSQL + Redis | `backend/main.py` 可运行 |
| W1 | Celery 任务队列配置 | 异步任务可执行 |
| W2 | 节点注册/发现 API | `/api/v1/nodes` 可用 |
| W2 | 基础监控 (心跳上报) | 节点状态可视化 |

### 阶段二：核心功能 (3 周)
| 周次 | 任务 | 交付物 |
|------|------|--------|
| W3 | 任务调度器 (Celery Beat) | 任务自动分发 |
| W3 | gRPC 节点通信 | 节点可接收任务 |
| W4 | 物理监控 (GPU/CPU/网络) | 真实指标上报 |
| W4 | 任务状态机 | 状态流转可追踪 |
| W5 | 防御性机制 (熔断/重试) | 系统鲁棒性提升 |

### 阶段三：区块链 + 验证 (2 周)
| 周次 | 任务 | 交付物 |
|------|------|--------|
| W6 | 智能合约开发 (测试网) | ComputeToken 部署 |
| W6 | Web3.py 集成 | 链上交互可用 |
| W7 | 双节点验证机制 | 关键任务冗余执行 |
| W7 | 物理交付凭证 | 执行快照生成 |

### 阶段四：可视化 + SDK (2 周)
| 周次 | 任务 | 交付物 |
|------|------|--------|
| W8 | React Dashboard (基础) | 监控仪表盘 |
| W8 | 全球算力地图 | Leaflet 可视化 |
| W9 | Python SDK | `pip install computehub-sdk` |
| W9 | 文档完善 | MkDocs 站点上线 |

### 阶段五：性能优化 + 部署 (1 周)
| 周次 | 任务 | 交付物 |
|------|------|--------|
| W10 | gRPC 优化 + 缓存策略 | P99 < 100ms |
| W10 | Kubernetes 部署 | 一键部署脚本 |
| W10 | 压力测试 + 基准报告 | 性能测试报告 |

---

## 📊 技术 KPI 目标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| API 响应时间 (P99) | < 100ms | Prometheus + Grafana |
| 任务调度延迟 | < 500ms | 任务日志时间戳 |
| 节点心跳间隔 | 30s | Redis 最后活跃时间 |
| 系统可用性 | > 99.9% | Uptime 监控 |
| 任务成功率 | > 99% | 任务状态统计 |
| 部署时间 | < 5 分钟 | CI/CD 流水线时长 |

---

## 🔧 开发环境快速启动

```bash
# 1. 克隆项目
git clone https://github.com/chenqifu-Ai/computehub.git
cd computehub

# 2. 初始化环境
./scripts/setup.sh

# 3. 启动依赖 (Docker Compose)
docker-compose up -d postgres redis

# 4. 运行后端
cd backend && uvicorn main:app --reload

# 5. 运行 Celery Worker
celery -A workers.tasks worker --loglevel=info

# 6. 运行节点代理
cd node && python agent.py --register

# 7. 访问 API 文档
open http://localhost:8000/docs
```

---

## 🎯 技术决策记录 (ADR)

### ADR-001: 为什么选择 FastAPI 而非 Flask/Django?
- **决策**: FastAPI
- **理由**: 
  - 原生异步支持 (async/await)
  - 自动生成 OpenAPI 文档
  - Pydantic 类型验证
  - 性能优于 Flask (Starlette 基底)

### ADR-002: 为什么选择 Celery 而非 RQ/Dramatiq?
- **决策**: Celery
- **理由**:
  - 生产验证 (Uber/Instagram 使用)
  - 支持定时任务 (Celery Beat)
  - 成熟的重试/错误处理机制
  - 支持多种 Broker (Redis/RabbitMQ)

### ADR-003: 为什么选择 gRPC 而非 REST 用于节点通信?
- **决策**: gRPC
- **理由**:
  - 性能高 (Protobuf 二进制)
  - 双向流式通信
  - 强类型契约 (.proto 文件)
  - 多语言支持 (未来 Go/Rust 节点)

### ADR-004: 区块链模块是否必须?
- **决策**: 可选模块，V2 阶段实现
- **理由**:
  - V1 优先验证核心调度功能
  - 区块链增加复杂度
  - 可先用 PostgreSQL 记账，后期迁移

---

## 📝 下一步行动

1. **创建 requirements.txt** - 定义所有 Python 依赖
2. **初始化项目结构** - 创建标准目录
3. **实现 FastAPI 骨架** - 可运行的最小应用
4. **配置 Docker Compose** - 本地开发环境

---

**制定者**: 小智  
**审核状态**: 待老大确认  
**下次更新**: 启动开发后每周评审
