# ARC-AI-NET 集群广播机制设计 v1.0

## 📋 设计概述

**通道**：ComputeHub Worker → Gateway API → 所有 Worker

**架构**：
```
┌──────────┐     ┌─────────────────┐     ┌──────────┐
│  Worker A │────▶│  Gateway        │────▶│  Worker B│
└──────────┘     │  (转发中枢)      │────▶│  Worker C│
                 │                 │────▶│  Worker D│
┌──────────┐     └─────────────────┘     └──────────┘
│  Worker B │
└──────────┘
```

**设计原则**：
- Gateway 是转发中枢，不做消息队列持久化
- Worker 通过 `/api/v1/worker/think` 接收广播
- 每条广播包含 `arc_net` 信封，接收方直接提取处理，不走 LLM 推理管道

---

## 📡 端到端流程

```
1. Worker A 想广播 → POST → Gateway: /api/v1/cluster/broadcast
   Body: { type, arc_net, role, content }

2. Gateway 收到广播 → 查 nodes/list → 获取所有在线节点

3. Gateway 遍历所有节点 → 各自 POST → Worker /api/v1/worker/think
   Body: { type: "arc_net_broadcast", arc_net, role: "system", content }

4. Worker 收到广播 → 提取 arc_net 字段 → 按事件类型处理
   → 不走 LLM 推理管道
```

---

## 📦 消息结构

### 广播信封

```json
{
  "type": "arc_net_broadcast",
  "arc_net": {
    "version": "1.0",
    "event": "node_join|node_leave|topology_update|heartbeat|sync_request",
    "seq": 42,
    "timestamp": 1749181440,
    "sender": {
      "node_id": "ecs-p2ph",
      "label": "ECS主节点",
      "host": "36.250.122.43",
      "platform": "linux/amd64",
      "model": "deepseek-v4-flash",
      "version": "1.3.16"
    },
    "payload": { ... }
  },
  "role": "system",
  "content": "[ARC-NET] 系统消息"
}
```

### 事件类型

| 事件 | payload | 触发条件 |
|------|---------|----------|
| `node_join` | 节点加入信息 | 新节点上线/重连 |
| `node_leave` | 节点离开原因 | 优雅下线/心跳超时 |
| `topology_update` | 变更内容 | 能力/IP变化 |
| `heartbeat` | 轻量心跳 | 每 30s |
| `sync_request` | 序列号 | 启动/seq gap |

---

## 🔒 可靠性

- **seq 去重**：接收方记录 last_seq，跳过旧消息
- **离线检测**：30s 心跳超时 → suspect，90s 未收到 → offline
- **并发限制**：Gateway 转发时限制并发数（默认 4）
- **本地缓存**：每节点存 topology.json 作为兜底

---

## 🗺️ 代码实现

### Gateway 端
- `src/gateway/gateway_broadcast.go` — 广播处理
- `POST /api/v1/cluster/broadcast` — 广播入口
- 自动遍历 nodes/list → 转发到所有 Worker

### Worker 端
- `src/workercmd/worker_agent.go` — 扩展 think handler
- 收到 `type=arc_net_broadcast` 时不走 LLM 管道
- 直接提取 arc_net 字段 → 按事件分发

---

## 📊 里程碑

| 阶段 | 内容 | 周期 |
|------|------|------|
| **P0** | Gateway 端广播 + Worker 端解析 | 1 天 |
| **P1** | 离线检测 + 全量同步 | 2 天 |
| **P2** | 节点自广播（无需 Gateway） | 3 天 |

---

## ⚠️ 注意事项

1. **不走 LLM 管道**：arc_net 消息接收后直接提取处理，丢弃不走推理
2. **Worker IP/Port 必须可访问**：Gateway 需要知道每个 Worker 的 IP 和端口才能转发
3. **Gateway 是单点**：Gateway 挂了广播通道就断了，需 HA 方案
4. **seq 机制**：ComputeHub 不保证 FIFO，接收方做去重+排序
