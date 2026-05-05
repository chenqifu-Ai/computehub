# ComputeHub API 文档

**版本**: v1.1
**基础 URL**: `http://localhost:8282`

---

## 目录

1. [健康检查](#1-健康检查)
2. [系统状态](#2-系统状态)
3. [节点管理](#3-节点管理)
4. [任务管理](#4-任务管理)
5. [大模型编排](#5-大模型编排)
6. [Prometheus 指标](#6-prometheus-指标)
7. [错误码](#7-错误码)
8. [通用响应格式](#8-通用响应格式)

---

## 通用响应格式

```json
{
  "success": true,
  "data": {},
  "error": "",
  "duration": "0.023s"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 请求是否成功 |
| `data` | object | 响应数据 |
| `error` | string | 错误信息（失败时） |
| `duration` | string | 处理耗时 |

---

## 1. 健康检查

### `GET /api/health`

检查 Gateway 是否存活。

**示例:**
```bash
curl http://localhost:8282/api/health
```

**响应:**
```json
{
  "success": true,
  "data": "ComputeHub System Healthy",
  "duration": "0.001s"
}
```

---

## 2. 系统状态

### `GET /api/status`

获取系统各组件状态。

**示例:**
```bash
curl http://localhost:8282/api/status
```

**响应:**
```json
{
  "success": true,
  "data": {
    "kernel": {
      "status": "running",
      "schedule_latency": "12ms",
      "queue_depth": 5
    },
    "pipeline": {
      "status": "active",
      "interceptions": 0,
      "pure_latency": "3ms"
    },
    "executor": {
      "status": "running",
      "verification_rate": 100.0,
      "sandbox_path": "/tmp/computehub-sandbox"
    },
    "nodeManager": {
      "total_nodes": 3,
      "online_nodes": 2,
      "total_tasks": 10,
      "active_tasks": 4,
      "nodes": [
        {
          "node_id": "gpu-node-01",
          "region": "us-east-1",
          "gpu_type": "A100-80GB",
          "status": "online",
          "active_tasks": 2,
          "cpu_utilization": 45.2,
          "gpu_metrics": [
            {"id": 0, "utilization": 78.5, "memory_used_mb": 40960, "temp_c": 65}
          ]
        }
      ]
    },
    "geneStore": {
      "size": 42,
      "recall_rate": 0.85
    },
    "uptime": "2d 14h 32m"
  }
}
```

---

## 3. 节点管理

### 3.1 注册节点

**`POST /api/v1/nodes/register`**

注册一个新的算力节点到集群。

**请求体:**
```json
{
  "node_id": "gpu-node-01",
  "region": "us-east-1",
  "gpu_type": "A100-80GB",
  "gpu_count": 4,
  "cpu_cores": 32,
  "memory_mb": 131072,
  "max_tasks": 10
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "node_id": "gpu-node-01",
    "registered_at": "2026-05-05T08:30:00Z",
    "status": "registered"
  }
}
```

---

### 3.2 注销节点

**`POST /api/v1/nodes/unregister`**

从集群中移除节点。

**请求体:**
```json
{
  "node_id": "gpu-node-01"
}
```

---

### 3.3 心跳

**`POST /api/v1/nodes/heartbeat`**

节点定期发送心跳。

**请求体:**
```json
{
  "node_id": "gpu-node-01",
  "cpu_util": 45.2,
  "gpu_metrics": [
    {"gpu_id": 0, "utilization": 78.5, "memory_mb": 40960, "temperature": 65}
  ],
  "active_tasks": 2
}
```

---

### 3.4 节点列表

**`GET /api/v1/nodes/list`**

**响应:**
```json
{
  "success": true,
  "data": {
    "total": 3,
    "online": 2,
    "nodes": [...]
  }
}
```

---

### 3.5 节点指标

**`GET /api/v1/nodes/metrics`**

获取所有节点的实时 GPU/CPU 指标。

---

## 4. 任务管理

### 4.1 提交任务

**`POST /api/v1/tasks/submit`**

提交计算任务到调度器。

**请求体:**
```json
{
  "task_id": "task-001",
  "priority": 5,
  "task_type": "inference",
  "gpu_requirement": {
    "min_gpu": 1,
    "preferred_type": "A100-80GB"
  },
  "payload": {
    "model": "qwen3.6-35b",
    "input": "Hello, world!"
  },
  "timeout_seconds": 300
}
```

**优先级说明:**
| 优先级 | 说明 | 典型场景 |
|--------|------|----------|
| 1-3 | 低 | 批处理、离线任务 |
| 4-6 | 中 | 普通推理请求 |
| 7-8 | 高 | 实时交互 |
| 9-10 | 紧急 | 抢占式任务 |

---

### 4.2 任务编排（Composer）

**`POST /api/v1/tasks/compose`**

大模型任务自动拆解、并行分发、结果汇总。

**请求体:**
```json
{
  "task_id": "compose-001",
  "prompt": "分析以下数据并生成报告：[data]",
  "model": "qwen3.6-35b-common",
  "sub_tasks": [
    {"type": "data_extract", "priority": 5},
    {"type": "data_analyze", "priority": 7},
    {"type": "report_generate", "priority": 8, "depends_on": ["data_analyze"]}
  ]
}
```

---

### 4.3 任务结果

**`GET /api/v1/tasks/result?task_id=xxx`**

获取任务执行结果。

---

### 4.4 任务列表

**`GET /api/v1/tasks/list?status=pending|running|completed|failed`**

---

### 4.5 任务详情

**`GET /api/v1/tasks/detail?task_id=xxx`**

---

## 5. 大模型编排

### `POST /api/v1/tasks/compose`

**功能**: 将复杂任务自动拆解为子任务，并行分发执行，最后汇总结果。

**流程:**
```
用户请求 → Composer 拆解 → 并行分发子任务 → 收集结果 → 汇总返回
```

**使用示例:**
```bash
curl -X POST http://localhost:8282/api/v1/tasks/compose \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "分析近7天服务器性能数据并给出优化建议",
    "model": "qwen3.6-35b-common"
  }'
```

---

## 6. Prometheus 指标

### `GET /metrics`

暴露 Prometheus 格式的监控指标。

**指标列表:**
| 指标名 | 类型 | 说明 |
|--------|------|------|
| `computehub_node_total` | gauge | 节点总数 |
| `computehub_node_online` | gauge | 在线节点数 |
| `computehub_task_total` | gauge | 任务总数 |
| `computehub_task_active` | gauge | 活跃任务数 |
| `computehub_gpu_utilization` | gauge | GPU 利用率 (%) |
| `computehub_gpu_temperature` | gauge | GPU 温度 (°C) |
| `computehub_gpu_memory_used` | gauge | GPU 已用显存 (MB) |
| `computehub_network_latency_ms` | gauge | 网络延迟 (ms) |
| `computehub_heartbeat_last` | gauge | 上次心跳时间戳 |

**查询示例:**
```bash
curl http://localhost:8282/metrics
```

---

## 7. 错误码

| HTTP 状态码 | 说明 | 常见原因 |
|-------------|------|----------|
| 200 | 成功 | — |
| 400 | 请求错误 | JSON 解析失败、参数缺失 |
| 405 | 方法不允许 | 使用非 POST 调用 POST 端点 |
| 404 | 未找到 | 路径不存在 |
| 500 | 服务器错误 | 内核异常、调度失败 |

**错误响应格式:**
```json
{
  "success": false,
  "error": "JSON parse error: invalid character 'x' in literal",
  "duration": "0.001s"
}
```

---

## 8. 最佳实践

### 节点接入流程
```
1. POST /api/v1/nodes/register    → 注册节点
2. POST /api/v1/nodes/heartbeat   → 每 15s 发送心跳
3. GET  /api/v1/tasks/list        → 拉取可用任务
4. POST /api/v1/tasks/result      → 提交任务结果
```

### 任务提交流程
```
1. POST /api/v1/tasks/submit      → 提交任务
2. GET  /api/v1/tasks/result?task_id=xxx  → 轮询结果
3. 或: POST /api/v1/tasks/result  → 主动提交结果
```

### 压测建议
| 场景 | 并发数 | 预期 TPS |
|------|--------|----------|
| 小规模 | 50 | 100+ |
| 中规模 | 200 | 200+ |
| 大规模 | 400 | 250+ |
| 峰值 | 500 | 249+ (99.8% 成功率) |

---

*文档版本: v1.1 | 更新: 2026-05-05*
