# 🚀 ComputeHub - 一日冲刺快速启动指南

**目标**: 1 天完成 MVP 开发  
**当前状态**: ✅ 基础架构完成

---

## 📋 已完成功能

- ✅ FastAPI 框架搭建
- ✅ PostgreSQL + Redis 配置
- ✅ 节点注册/心跳 API
- ✅ 任务创建/查询 API
- ✅ Celery Worker 配置
- ✅ Node Agent (节点代理)
- ✅ Docker Compose 编排
- ✅ 单元测试框架

---

## 🔧 快速启动 (5 分钟)

### Step 1: 安装依赖

```bash
cd /root/GitHub/computehub

# 运行安装脚本
./scripts/setup.sh
```

### Step 2: 启动数据库和缓存

```bash
docker-compose up -d postgres redis

# 验证服务
docker-compose ps
```

### Step 3: 启动 API 服务

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动 FastAPI
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 注册节点
curl -X POST http://localhost:8000/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-node-1",
    "gpu_model": "RTX 4090",
    "gpu_count": 1,
    "cpu_cores": 8,
    "memory_gb": 32
  }'

# 访问 API 文档
open http://localhost:8000/docs
```

---

## 🧪 运行测试

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行单元测试
pytest tests/unit/test_nodes.py -v
```

---

## 📡 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/nodes/register` | POST | 注册节点 |
| `/api/v1/nodes/` | GET | 列出节点 |
| `/api/v1/nodes/{id}` | GET | 获取节点 |
| `/api/v1/nodes/{id}/heartbeat` | POST | 心跳上报 |
| `/api/v1/tasks/` | POST | 创建任务 |
| `/api/v1/tasks/` | GET | 列出任务 |

---

## 🎯 今日待办

- [ ] 启动 PostgreSQL + Redis
- [ ] 启动 API 服务
- [ ] 运行测试验证
- [ ] 启动 Node Agent 测试心跳
- [ ] 提交到 Git

---

## 🐛 故障排除

### 端口被占用

```bash
# 查看占用端口的进程
lsof -i :8000
lsof -i :5432
lsof -i :6379

# 杀死进程
kill -9 <PID>
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 查看日志
docker-compose logs postgres
```

### 依赖安装失败

```bash
# 升级 pip
pip install --upgrade pip

# 重新安装
pip install -r requirements.txt --force-reinstall
```

---

**下一步**: 启动服务并测试！🚀
