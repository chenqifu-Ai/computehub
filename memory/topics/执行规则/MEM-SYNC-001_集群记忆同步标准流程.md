# 🧠 MEM-SYNC-001: 集群记忆同步标准流程

**版本**: v1.0  
**创建时间**: 2026-06-27 06:52  
**适用范围**: 所有接入 ComputeHub 集群的 Agent

---

## 📖 什么是集群记忆

ComputeHub Gateway 内置共享记忆系统（SPEC-DMEM-001），所有 Worker 节点的经验（episodes）和知识（knowledge）通过 Gateway 集中存储和检索。

- **经验（Episodes）**: 执行某次任务的过程和结果，适合记录"怎么做的"
- **知识（Knowledge）**: 已验证的结构化知识，适合记录"是什么"和"怎么做"
- **持久化**: 写入 `~/ComputeHub/data/cluster_memory.json`
- **检索**: 倒排索引，支持中文 2-gram 分词

---

## 🔧 保存集群记忆（核心 API）

### 端点
```
POST /api/v1/memory/sync
```

### 请求格式

```json
{
  "node_id": "当前节点的 ID",
  "episodes": [
    {
      "task": "任务描述",
      "result": "执行结果",
      "success": true,
      "learned": "学到的经验",
      "strength": 1.0,
      "timestamp": "2026-06-27T06:52:00+08:00"
    }
  ],
  "knowledge": [
    {
      "topic": "主题标题",
      "content": "详细内容（支持 Markdown）",
      "author": "端智",
      "verified": "verified",
      "tags": ["标签1", "标签2", "标签3"],
      "timestamp": "2026-06-27T06:52:00+08:00"
    }
  ]
}
```

### 关键字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `node_id` | string | ✅ | 节点 ID，如 `local-arm`、`ecs-p2ph` |
| `episodes[].task` | string | ✅ | 任务描述（用于去重） |
| `episodes[].result` | string | ✅ | 执行结果 |
| `episodes[].learned` | string | | 学到的经验（用于索引） |
| `episodes[].strength` | float64 | | 经验强度，默认 1.0 |
| `knowledge[].topic` | string | ✅ | 知识主题（用于去重） |
| `knowledge[].content` | string | ✅ | 详细内容（支持 Markdown） |
| `knowledge[].author` | string | | 作者，默认空 |
| `knowledge[].verified` | string | | 验证状态 |
| `knowledge[].tags` | []string | ✅ | 标签列表（用于索引） |
| `knowledge[].timestamp` | string | | ISO 时间戳，默认当前时间 |

---

## 📝 标准操作

### 操作一：保存一条知识条目

**适用场景**: 完成一项重要的标准流程/经验总结/操作指南

```bash
curl -s -X POST http://localhost:8282/api/v1/memory/sync \
  -H 'Content-Type: application/json' \
  -d '{
  "node_id": "local-arm",
  "knowledge": [
    {
      "topic": "经验标题（简洁明确）",
      "content": "# 标题\n\n## 概述\n内容...\n\n## 步骤\n1. ...\n2. ...\n\n## 注意事项\n- 注意1\n- 注意2",
      "author": "你的 Agent 名称",
      "verified": "verified",
      "tags": ["领域关键词1", "领域关键词2", "领域关键词3"]
    }
  ]
}' | python3 -m json.tool
```

**预期成功响应**:
```json
{
  "success": true,
  "data": {
    "episodes_synced": 0,
    "knowledge_synced": 1
  }
}
```

### 操作二：保存一条经验

**适用场景**: 记录一次任务执行的经验（含过程和结果）

```bash
curl -s -X POST http://localhost:8282/api/v1/memory/sync \
  -H 'Content-Type: application/json' \
  -d '{
  "node_id": "local-arm",
  "episodes": [
    {
      "task": "请搜索人工智能进化方向的最新文章",
      "result": "搜索到 9 条结果...",
      "success": true,
      "learned": "AI 进化方向包括多模态、AGI、安全伦理等",
      "strength": 1.0
    }
  ]
}'
```

### 操作三：同时保存多条

支持一次性提交多条 knowledge 或多条 episodes，也可以混用：

```bash
curl -s -X POST http://localhost:8282/api/v1/memory/sync \
  -H 'Content-Type: application/json' \
  -d '{
  "node_id": "local-arm",
  "episodes": [ {...}, {...} ],
  "knowledge": [ {...} ]
}'
```

---

## 🔍 验证与检索

### 检查统计
```bash
curl -s http://localhost:8282/api/v1/memory/stats | python3 -m json.tool
```
响应示例:
```json
{
  "data": {
    "episodes": 11,
    "knowledge": 6,
    "nodes": 3,
    "node_sync": {"local-arm": "06:52:06", "ecs-p2ph": "11:29:05"}
  }
}
```

### 分页列表
```bash
# 只看经验
curl -s 'http://localhost:8282/api/v1/memory/list?page=1&type=episode'

# 只看知识
curl -s 'http://localhost:8282/api/v1/memory/list?page=1&type=knowledge'

# 混合
curl -s 'http://localhost:8282/api/v1/memory/list?page=1'
```

### 搜索记忆
```bash
curl -s 'http://localhost:8282/api/v1/memory/search?q=关键词'

# 限定类型
curl -s 'http://localhost:8282/api/v1/memory/search?q=Windows&type=knowledge'
```

### 删除知识
```bash
# 需要先获取要删除的 key（从 list API 中获取）
curl -s -X DELETE 'http://localhost:8282/api/v1/memory/delete?key=topic:nodeId'
```

---

## ⚠️ 注意事项

1. **node_id 要准确**: 用节点实际 ID，可通过 `hostname` 或 `curl http://localhost:8282/api/v1/hall/topics` 获取
2. **topic 唯一性**: 同 topic + 同 node_id 会覆盖旧条目，确保 topic 不重复
3. **tags 是关键**: 检索靠 tags 和分词，标签要包含关键词（中英文都要）
4. **content 支持 Markdown**: 用 `\n` 换行，不要直接放文件内容，要结构化
5. **批量提交优于逐条**: 一次 POST 多条比多次 POST 效率高
6. **失败不重试**: 如果 sync 失败，检查 Gateway 是否在线（`curl http://localhost:8282/api/v1/hall/topics`）
7. **不敏感信息**: 不要在 memory 中存储 API Key、密码等敏感信息
8. **跨节点同步**: Gateway 会自动同步到所有在线节点，无需手动广播

---

## 📋 快速参考卡片

```
保存知识: POST /api/v1/memory/sync {node_id, knowledge[{topic, content, tags}]}
保存经验: POST /api/v1/memory/sync {node_id, episodes[{task, result, learned}]}
检查统计: GET  /api/v1/memory/stats
搜索记忆: GET  /api/v1/memory/search?q=关键词
分页列表: GET  /api/v1/memory/list?page=N&type=knowledge
删除条目: DEL  /api/v1/memory/delete?key=topic:nodeId
```

---

*标准文档 MEM-SYNC-001 v1.0 — 任何需要保存集群记忆的操作都遵循此流程*
