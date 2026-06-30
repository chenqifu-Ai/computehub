# SPEC-DMEM-001: 集群共享记忆层

**版本**: v1.0  
**创建日期**: 2026-06-21  
**状态**: 规划中  
**维护者**: 端智  

---

## 1. 概述

### 1.1 要解决什么问题

目前每个 Worker Agent 有独立的本地记忆（Git 记忆系统），但：
- Agent A 学到的经验，Agent B 不知道
- 同一个问题在不同节点上重复踩坑
- 专家 Agent 之间没有知识共享

### 1.2 目标

构建一个**集群级共享记忆层**，让所有 Worker 和专家 Agent 能：
1. **上报**：执行经验、知识自动同步到 Gateway
2. **搜索**：跨节点搜索相关经验
3. **联想**：基于关键词联想检索
4. **统计**：查看集群记忆概况

### 1.3 非目标

- ❌ 不做实时同步（最终一致性即可）
- ❌ 不做分布式存储（Gateway 单点存储，Worker 只读/写）
- ❌ 不做向量数据库（中文 2-gram 倒排索引够用）

---

## 2. 架构

```
┌─────────────┐     POST /api/v1/memory/sync     ┌──────────────┐
│  Worker A   │ ──────────────────────────────→   │              │
│ (Agent)     │                                   │   Gateway    │
│             │     GET /api/v1/memory/search      │  (Cluster    │
│  Worker B   │ ←──────────────────────────────   │   Memory)   │
│ (Agent)     │                                   │              │
│             │     GET /api/v1/memory/stats       │ 倒排索引     │
│  Worker C   │ ←──────────────────────────────   │ 经验+知识    │
│ (Expert)    │                                   └──────────────┘
└─────────────┘
```

### 2.1 数据流

```
Worker 执行任务
  ↓
SaveEpisode() / SaveKnowledge()  →  本地 Git 记忆
  ↓
MemorySyncClient.SyncEpisode()  →  POST /api/v1/memory/sync  →  Gateway 倒排索引
  ↓
其他 Worker 搜索  →  GET /api/v1/memory/search  →  返回匹配结果
```

### 2.2 已实现

| 组件 | 文件 | 行数 | 状态 |
|------|------|:----:|:----:|
| Gateway 记忆端点 | `src/gateway/gateway_memory.go` | 480 | ✅ 已实现 |
| Worker 记忆客户端 | `src/workercmd/worker_memory_client.go` | 281 | ✅ 已实现 |
| Agent 工具注册 | `worker_memory_client.go` 中 `registerMemorySyncTools()` | - | ✅ 已实现 |
| 路由注册 | `gateway.go` 中 `/api/v1/memory/*` | - | ✅ 已实现 |

---

## 3. API 端点

### 3.1 POST /api/v1/memory/sync

Worker 上报新记忆。

**请求**:
```json
{
  "node_id": "ecs-p2ph",
  "episodes": [
    {
      "task": "部署 nginx 到 192.168.1.100",
      "result": "成功安装 nginx 1.24",
      "success": true,
      "learned": "Ubuntu 22.04 需要先 apt update",
      "strength": 1.0
    }
  ],
  "knowledge": [
    {
      "topic": "nginx 安装步骤",
      "content": "1. apt update\n2. apt install nginx\n3. systemctl start nginx",
      "author": "ecs-p2ph",
      "tags": ["nginx", "部署", "Ubuntu"]
    }
  ]
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "episodes_synced": 1,
    "knowledge_synced": 1
  }
}
```

### 3.2 GET /api/v1/memory/search

跨节点搜索记忆。

**参数**:
- `q` — 搜索关键词（必填）
- `limit` — 返回条数（默认 10）
- `type` — 类型：`episode` / `knowledge` / `all`（默认 all）

**响应**:
```json
{
  "success": true,
  "data": {
    "query": "nginx",
    "episodes": [...],
    "knowledge": [...],
    "ep_count": 1,
    "kn_count": 1
  }
}
```

### 3.3 POST /api/v1/memory/recall

联想检索（含关联扩展）。

**请求**:
```json
{
  "query": "nginx 部署",
  "tags": ["nginx", "Ubuntu"],
  "limit": 10
}
```

### 3.4 GET /api/v1/memory/stats

集群记忆统计。

**响应**:
```json
{
  "success": true,
  "data": {
    "nodes": 3,
    "episodes": 15,
    "knowledge": 8,
    "node_sync": {
      "ecs-p2ph": "14:32:01",
      "local-arm": "14:30:55",
      "windows-mobile01": "14:28:12"
    }
  }
}
```

---

## 4. Agent 工具

Worker Agent 通过以下工具与共享记忆层交互：

### 4.1 memory_sync_episode

同步经验到共享记忆层。

```json
{
  "name": "memory_sync_episode",
  "parameters": {
    "task": "任务描述",
    "result": "执行结果",
    "success": "true/false",
    "learned": "学到的经验教训"
  }
}
```

### 4.2 memory_search

搜索共享记忆。

```json
{
  "name": "memory_search",
  "parameters": {
    "query": "搜索关键词",
    "limit": 5
  }
}
```

### 4.3 memory_stats

查看集群记忆统计。

```json
{
  "name": "memory_stats",
  "parameters": {}
}
```

---

## 5. 分词策略

中文 2-gram 倒排索引：

```
输入: "nginx 部署失败"
分词: ["nginx", "部署", "失败", "部署失败"]
```

- 英文：按空格/标点分割，长度 > 1 的 token
- 中文：单字 + 2-gram
- 去重：同 token 只索引一次

---

## 6. 当前状态

### 6.1 已实现 ✅

- [x] Gateway 4 个记忆端点（sync/search/recall/stats）
- [x] Worker 记忆同步客户端（SyncEpisode/SyncKnowledge/SearchRemote/GetStats）
- [x] Agent 工具注册（memory_sync_episode/memory_search/memory_stats）
- [x] 中文 2-gram 分词索引
- [x] 路由注册到 Gateway

### 6.2 待实现 ⏳

- [ ] **Worker 自动同步**：Agent 每次 SaveEpisode/SaveKnowledge 后自动调用 SyncEpisode/SyncKnowledge
- [ ] **启动时拉取**：Worker 启动时从 Gateway 拉取共享记忆到本地
- [ ] **记忆衰减**：旧记忆 strength 随时间衰减，淘汰低价值记忆
- [ ] **专家 Agent 集成**：专家 Agent 在思考时自动搜索共享记忆
- [ ] **Web 管理页面**：在 `/ai` 页面增加记忆搜索和统计展示
- [ ] **持久化**：Gateway 重启后记忆不丢失（写入文件或 SQLite）

### 6.3 已知问题 🐛

- 当前 Worker 的 `SaveEpisode`/`SaveKnowledge` 只写本地 Git，没有自动触发同步
- 专家 Agent 的 `think` 函数没有集成 `memory_search` 工具
- 无持久化，Gateway 重启后记忆清空

---

## 7. 实施计划

### Phase 1: 基础层（✅ 已完成）
- Gateway 记忆端点
- Worker 记忆客户端
- Agent 工具注册

### Phase 2: 自动同步（当前）
- Worker 每次 SaveEpisode 后自动调用 SyncEpisode
- Worker 启动时拉取共享记忆
- 专家 Agent 集成 memory_search

### Phase 3: 增强
- 记忆衰减机制
- 持久化存储
- Web 管理页面

---

## 8. 测试

```bash
# 1. 查看当前记忆统计
curl http://36.250.122.43:8282/api/v1/memory/stats

# 2. 手动同步一条经验
curl -X POST http://36.250.122.43:8282/api/v1/memory/sync \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "test",
    "episodes": [{
      "task": "测试共享记忆",
      "result": "成功",
      "success": true,
      "learned": "共享记忆层工作正常"
    }]
  }'

# 3. 搜索
curl "http://36.250.122.43:8282/api/v1/memory/search?q=测试"

# 4. 验证统计
curl http://36.250.122.43:8282/api/v1/memory/stats
```

---

## 9. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-06-21 | 初始规划文档 |

---

*文档位置: `docs/SPEC-DMEM-001_集群共享记忆层.md`*
