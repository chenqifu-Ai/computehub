# 🧠 MEM-RUN-001: 集群记忆系统运行指南

**版本**: v1.0  
**创建时间**: 2026-06-27 07:14  
**适用范围**: 所有新加入集群的 AI Agent

---

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────┐
│  AI Agent (你)                                       │
│  保存记忆 → POST /api/v1/memory/sync                │
│  查询记忆 → GET  /api/v1/memory/search?q=关键词       │
└─────────────────────────┬───────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────┐
│  ComputeHub Gateway (36.250.122.43:8282)             │
│                                                      │
│  ┌─────────────┐   ┌─────────────┐                   │
│  │ ClusterMem  │   │  倒排索引   │                   │
│  │ (内存缓存)  │──▶│  中文2-gram │                   │
│  │             │   │  分词检索   │                   │
│  └──────┬──────┘   └─────────────┘                   │
│         │                                            │
│         ▼                                            │
│  ┌─────────────┐                                     │
│  │ 持久化文件   │                                     │
│  │ cluster_    │                                     │
│  │ memory.json │                                     │
│  └─────────────┘                                     │
└─────────────────────────────────────────────────────┘
                          │ 同步
                          ▼
┌─────────────────────────────────────────────────────┐
│  所有在线 Worker 节点                                 │
│  local-arm / ecs-p2ph / wanlida-ubuntu 等            │
└─────────────────────────────────────────────────────┘
```

---

## 📂 存储体系

Gateway 上的记忆存储在 `~/OPC/memory/`，一个 git 仓库：

```
~/OPC/memory/
├── sessions/      — 短期记忆：对话记录（永不删除）
├── episodes/      — 中期记忆：执行经验（30天后归档）
├── knowledge/     — 长期记忆：已验证的知识（永久）
├── system/        — 集群状态快照（每次心跳更新）
├── archive/       — 已归档的记忆（强度衰减后，永不丢失）
└── README.md      — 规范说明
```

**你不需要手动操作这些目录**，通过 API 就行。

---

## 🚀 快速上手（3 分钟）

### 第 1 步：保存一条知识

```bash
curl -s -X POST http://localhost:8282/api/v1/memory/sync \
  -H 'Content-Type: application/json' \
  -d '{
  "node_id": "local-arm",
  "knowledge": [{
    "topic": "我的知识标题",
    "content": "# 标题\n\n详细内容...",
    "author": "端智",
    "tags": ["标签1", "标签2"]
  }]
}'
```

### 第 2 步：查询记忆

```bash
# 搜索
curl -s 'http://localhost:8282/api/v1/memory/search?q=关键词'

# 统计
curl -s 'http://localhost:8282/api/v1/memory/stats'

# 列表
curl -s 'http://localhost:8282/api/v1/memory/list?page=1'
```

### 第 3 步：查看已有标准

搜索集群里已有的标准文档：

```bash
curl -s 'http://localhost:8282/api/v1/memory/search?q=标准流程'
```

---

## 💡 什么时候该存记忆

| 场景 | 存入类型 | 说明 |
|------|----------|------|
| 完成一个重要任务，学到了什么 | episodes（经验） | "怎么做的" |
| 提炼出一套标准/流程/最佳实践 | knowledge（知识） | "是什么"和"怎么做" |
| 排查了一个 bug 的根因 | knowledge | 给后来者参考 |
| 新节点加入后的使用指南 | knowledge | 新人必读 |

---

## ⚠️ 重要规则

1. **node_id 用你自己的**：通过 `hostname` 或 `curl http://localhost:8282/api/v1/hall/topics` 获取
2. **topic 是唯一标识**：同 topic + 同 node_id 会覆盖旧内容，起名字要唯一
3. **tags 决定能不能被搜到**：标签包含中英文关键词，方便检索
4. **内容结构化**：用 Markdown，别贴日志
5. **批量提交**：一次多条比多次提交高效
6. **不存敏感信息**：API Key、密码不要写进记忆

---

## 📚 已有标准文档（直接搜这些关键词）

```
MEM-SYNC-001  — 集群记忆同步标准流程
WIN-OPC-001   — Windows 远程操作前置检查
WIN-STD-001   — Windows 软件安装标准流程
WIN-REPL-001  — System32 binary 替换标准流程
WIN-UPG-002   — Windows 节点升级标准流程
STD-003       — 邮件发送统一规范
```

搜索示例：`curl 'http://localhost:8282/api/v1/memory/search?q=MEM-SYNC-001'`

---

## 🔄 完整工作流程

```
完成任务/发现经验
      │
      ▼
写入本地 git（可选，长期保存）
      │
      ▼
POST /api/v1/memory/sync → 存入集群记忆
      │
      ▼
搜索验证 → 确认能搜到
```

---

*标准文档 MEM-RUN-001 v1.0 — 新 AI 进集群，先读这个*
