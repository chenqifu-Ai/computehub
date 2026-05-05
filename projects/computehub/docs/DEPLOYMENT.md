# ComputeHub 生产部署手册

**版本**: v0.7.0
**更新日期**: 2026-05-05

---

## 目录

1. [前置要求](#1-前置要求)
2. [快速部署](#2-快速部署)
3. [生产环境配置](#3-生产环境配置)
4. [配置文件说明](#4-配置文件说明)
5. [监控配置](#5-监控配置)
6. [故障排查](#6-故障排查)
7. [节点接入](#7-节点接入)

---

## 1. 前置要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Docker | ≥ 24.0 | 容器运行时 |
| Docker Compose | ≥ v2 | 编排工具 |
| 系统内存 | ≥ 4GB | Gateway 运行 |
| 系统磁盘 | ≥ 10GB 可用 | 二进制 + 数据 |
| 网络 | 端口 8282 开放 | API 访问 |

---

## 2. 快速部署

### 2.1 克隆代码

```bash
cd /path/to/projects
git clone <repo-url>
cd computehub
```

### 2.2 配置文件准备

```bash
# 复制默认配置（按需修改）
cp config.json.example config.json 2>/dev/null || true
cp genes.json.example genes.json 2>/dev/null || true
cp .env.example .env
```

### 2.3 启动服务

```bash
# 标准模式
docker compose up -d

# 或指定配置文件
docker compose -f docker-compose.prod.yml up -d
```

### 2.4 验证部署

```bash
# 检查容器状态
docker compose ps

# 检查健康状态
curl http://localhost:8282/api/health

# 查看系统状态
curl http://localhost:8282/api/status | python3 -m json.tool
```

预期响应:
```json
{
  "success": true,
  "data": "ComputeHub System Healthy"
}
```

---

## 3. 生产环境配置

### 3.1 资源限制

编辑 `.env` 文件调整资源配额：

```bash
# Gateway 资源限制
COMPUTEHUB_CPU_LIMIT=4.0           # 最大 CPU 核心数
COMPUTEHUB_CPU_RESERVATION=0.5     # 预留 CPU
COMPUTEHUB_MEM_LIMIT=4G            # 最大内存
COMPUTEHUB_MEM_RESERVATION=512M    # 预留内存

# 端口配置
GATEWAY_PORT=8282                  # Gateway 端口
```

### 3.2 日志轮转

生产环境日志自动轮转配置：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"     # 单文件最大 10MB
    max-file: "3"       # 保留 3 个文件
    compress: "true"    # 压缩旧日志
```

### 3.3 多环境启动

```bash
# 开发环境 (最小资源)
COMPUTEHUB_ENV=development docker compose up -d

# 生产环境 (标准配置)
COMPUTEHUB_ENV=production docker compose up -d

# 监控模式 (含 Prometheus + Grafana)
docker compose --profile monitoring -f docker-compose.prod.yml up -d
```

---

## 4. 配置文件说明

### config.json

Gateway 核心配置，包含：
- 监听端口 (默认 8282)
- Dashboard 目录路径
- 日志级别
- 各模块参数

### genes.json

基因存储配置，包含：
- 学习进化规则
- 错误修复模式
- 知识持久化设置

---

## 5. 监控配置

### 5.1 Prometheus 集成

启用监控 profile:

```bash
docker compose --profile monitoring -f docker-compose.prod.yml up -d
```

访问:
- **Grafana Dashboard**: http://localhost:3000 (默认 admin/admin)
- **Prometheus**: http://localhost:9090
- **Gateway Metrics**: http://localhost:8282/metrics

### 5.2 关键指标

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| GPU 利用率 | >90% 持续 5min | GPU 过载 |
| GPU 温度 | >85°C | 过热风险 |
| 活跃任务数 | >节点容量 80% | 队列积压 |
| 心跳延迟 | >5s | 网络异常 |
| 任务失败率 | >5% | 系统异常 |

### 5.3 自定义 Dashboard

导入 `config/grafana/dashboards/` 中的 JSON 文件到 Grafana。

---

## 6. 故障排查

### 6.1 常见问题

**Q: Gateway 启动失败**
```bash
# 查看日志
docker logs computehub-gateway

# 检查端口占用
ss -tlnp | grep 8282

# 验证配置
cat config.json | python3 -m json.tool
```

**Q: 节点无法注册**
```bash
# 检查网络连通
docker exec computehub-gateway wget -qO- http://localhost:8282/api/health

# 检查 Docker 网络
docker network inspect computehub_computehub-net
```

**Q: 任务提交超时**
```bash
# 查看当前任务
curl http://localhost:8282/api/v1/tasks/list

# 查看系统状态
curl http://localhost:8282/api/status
```

**Q: 磁盘空间不足**
```bash
# 清理日志
docker volume prune -f
docker system prune -f

# 查看体积占用
docker system df
```

### 6.2 健康检查诊断

```bash
# 手动执行健康检查
docker exec computehub-gateway wget -qO- http://localhost:8282/api/health

# 查看健康检查历史
docker inspect --format='{{json .State.Health}}' computehub-gateway | python3 -m json.tool
```

---

## 7. 节点接入

### 7.1 接入流程

```bash
# 1. 注册节点
curl -X POST http://localhost:8282/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "gpu-node-01",
    "region": "us-east-1",
    "gpu_type": "A100-80GB",
    "gpu_count": 4,
    "cpu_cores": 32,
    "memory_mb": 131072,
    "max_tasks": 10
  }'

# 2. 定期心跳 (每 15s)
while true; do
  curl -X POST http://localhost:8282/api/v1/nodes/heartbeat \
    -H "Content-Type: application/json" \
    -d '{
      "node_id": "gpu-node-01",
      "cpu_util": 45.2,
      "gpu_metrics": [{"gpu_id": 0, "utilization": 78.5, "memory_mb": 40960, "temperature": 65}],
      "active_tasks": 2
    }'
  sleep 15
done
```

### 7.2 Worker Agent

部署 Worker Agent 到 GPU 节点:

```bash
# 编译 Worker
cd projects/computehub
go build -o compute-worker ./cmd/worker/

# 运行
./compute-worker \
  --gateway http://localhost:8282 \
  --node-id gpu-node-01 \
  --region us-east-1
```

---

## 8. 安全建议

1. **防火墙**: 仅开放必要端口 (8282)
2. **TLS**: 生产环境建议加反向代理 (Nginx) 配置 HTTPS
3. **认证**: 后续版本增加 API Token 认证
4. **备份**: 定期备份 `genes.json` 和 `config.json`

---

*部署手册版本: v0.7.0 | 更新: 2026-05-05*
