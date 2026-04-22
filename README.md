# ⚡ ComputeHub v2.0

> **Start local. Scale globally.** 分布式算力出海平台

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/chenqifu-Ai/computehub)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/chenqifu-Ai/computehub.git
cd computehub

# 运行安装脚本
./scripts/setup.sh
```

### 2. 启动依赖服务

```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis
```

### 3. 启动后端服务

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动 API 服务
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动 Celery Worker

```bash
# 在另一个终端
celery -A backend.workers.tasks worker --loglevel=info
```

### 5. 访问 API 文档

打开浏览器访问：http://localhost:8000/docs

---

## 📁 项目结构

```
computehub/
├── backend/                 # 后端服务
│   ├── api/v1/             # API 路由和 Schema
│   ├── core/               # 核心配置
│   ├── models/             # 数据库模型
│   ├── services/           # 业务逻辑
│   ├── workers/            # Celery 任务
│   └── main.py             # 应用入口
├── node/                    # 节点代理
│   └── agent.py            # 节点代理程序
├── tests/                   # 测试
├── scripts/                 # 工具脚本
├── deployments/             # 部署配置
├── docker-compose.yml       # Docker 编排
├── requirements.txt         # Python 依赖
└── README.md               # 项目说明
```

---

## 🛠️ 技术栈

| 功能 | 技术 |
|------|------|
| **Web 框架** | FastAPI 0.109+ |
| **数据库** | PostgreSQL 15 + SQLAlchemy 2.0 |
| **缓存/队列** | Redis 7 + Celery 5.3 |
| **节点通信** | HTTP/REST (gRPC 后续迭代) |
| **监控** | Prometheus + Structlog |
| **GPU 监控** | pynvml + psutil |

---

## 📡 API 接口

### 节点管理

```bash
# 注册节点
curl -X POST http://localhost:8000/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-gpu-node",
    "gpu_model": "RTX 4090",
    "gpu_count": 1,
    "cpu_cores": 8,
    "memory_gb": 32
  }'

# 列出所有节点
curl http://localhost:8000/api/v1/nodes/

# 发送心跳
curl -X POST http://localhost:8000/api/v1/nodes/{node_id}/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "gpu_utilization": 45.5,
    "memory_utilization": 62.3,
    "network_latency_ms": 25.7
  }'
```

### 任务管理

```bash
# 创建任务
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "framework": "pytorch",
    "gpu_required": 1,
    "duration_hours": 24
  }'

# 列出任务
curl http://localhost:8000/api/v1/tasks/
```

---

## 🧪 运行测试

```bash
# 运行单元测试
pytest tests/unit/ -v

# 运行测试并生成覆盖率报告
pytest tests/ --cov=backend --cov-report=html
```

---

## 📊 监控

### 健康检查

```bash
curl http://localhost:8000/health
```

### 查看日志

```bash
# API 日志
docker-compose logs -f backend

# Worker 日志
docker-compose logs -f worker
```

---

## 🔧 开发

### 代码质量

```bash
# 格式化代码
black backend/ node/

# Lint 检查
ruff check backend/ node/

# 类型检查
mypy backend/
```

### 数据库迁移

```bash
# 生成迁移
alembic revision --autogenerate -m "Initial migration"

# 应用迁移
alembic upgrade head
```

---

## 📝 开发路线图

- [x] **v2.0.0** - 基础架构 (FastAPI + PostgreSQL + Redis)
- [ ] **v2.1.0** - 节点调度 (Celery + 智能路由)
- [ ] **v2.2.0** - gRPC 节点通信
- [ ] **v2.3.0** - 区块链结算
- [ ] **v2.4.0** - Web Dashboard

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License

---

**Made with ❤️ by the ComputeHub Team**
