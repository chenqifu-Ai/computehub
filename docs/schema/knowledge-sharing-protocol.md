# 知识共享协议 v1.0 (KSP-001)

**版本**: 1.0
**日期**: 2026-07-01
**状态**: ✅ 定稿
**制定人**: 小智（总调度）

---

## 1. 目标

让三智（小智/端智/软智/米智/丁智）能互相共享知识，不重复，可追溯。

---

## 2. 统一知识格式

所有知识必须遵循此 JSON Schema：

```json
{
  "id": "uuid-v4",
  "source": "node_id",
  "type": "skill | pattern | lesson | insight",
  "title": "知识标题",
  "content": "知识内容（Markdown）",
  "tags": ["tag1", "tag2"],
  "confidence": 0.0-1.0,
  "ttl_days": 30,
  "timestamp": "ISO-8601",
  "trace_id": "uuid-v4"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | ✅ | UUID v4，全局唯一 |
| source | string | ✅ | 产生知识的节点 ID |
| type | string | ✅ | 分类：skill(技能)/pattern(模式)/lesson(教训)/insight(洞察) |
| title | string | ✅ | 知识标题，≤100字 |
| content | string | ✅ | Markdown 正文 |
| tags | string[] | ❌ | 标签，用于检索 |
| confidence | float | ❌ | 置信度 0-1，默认 0.8 |
| ttl_days | int | ❌ | 有效天数，默认 30 |
| timestamp | string | ✅ | ISO-8601 时间戳 |
| trace_id | string | ❌ | 链路追踪 ID |

---

## 3. 存储架构

```
shared/
├── knowledge/          # 通用经验库（结构化，可检索）
│   ├── skill/          # 技能类知识
│   ├── pattern/        # 模式类知识
│   ├── lesson/         # 教训类知识
│   └── insight/        # 洞察类知识
├── patterns/           # 发现的模式（失败案例、最佳实践）
├── insights/           # 提炼的洞察（跨 Agent 的规律）
└── timeline/           # 事件时间线（发生了什么）
```

### 文件命名规则

```
shared/knowledge/{type}/{slug}.md
```

其中 `slug` = 标题的 URL 友好版本，≤60 字符。

---

## 4. API 接口

### 4.1 写入知识

```
POST /api/v1/knowledge/put
Content-Type: application/json

{
  "source": "ecs-p2ph",
  "type": "lesson",
  "title": "Windows 远程执行语法差异",
  "content": "Windows cmd 和 PowerShell 的引号处理不同...",
  "tags": ["windows", "remote-exec", "cmd", "powershell"],
  "confidence": 0.9,
  "ttl_days": 90
}
```

响应：
```json
{
  "success": true,
  "data": {
    "id": "uuid-v4",
    "path": "shared/knowledge/lesson/windows-远程执行语法差异.md"
  }
}
```

### 4.2 查询知识

```
GET /api/v1/knowledge/query?q=windows&type=lesson&tags=remote-exec&limit=10
```

响应：
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "uuid-v4",
        "title": "Windows 远程执行语法差异",
        "type": "lesson",
        "source": "ecs-p2ph",
        "tags": ["windows", "remote-exec"],
        "confidence": 0.9,
        "timestamp": "2026-07-01T08:00:00+08:00"
      }
    ],
    "total": 1
  }
}
```

### 4.3 同步知识

```
POST /api/v1/knowledge/sync
Content-Type: application/json

{
  "source": "local-arm",
  "since": "2026-06-30T00:00:00+08:00"
}
```

响应：
```json
{
  "success": true,
  "data": {
    "new": 5,
    "updated": 2,
    "deleted": 0
  }
}
```

---

## 5. 冲突解决

| 场景 | 策略 |
|------|------|
| 同 ID 不同内容 | 时间戳优先（LWW），旧版本归档 |
| 同标题不同内容 | 置信度优先，低置信度标记为"待确认" |
| 同内容不同标题 | 保留两个，加关联标签 |
| 同 ID 同内容 | 跳过（幂等） |

---

## 6. 生命周期

```
新知识 → 活跃(7天) → 温(30天) → 归档(90天) → 淘汰(180天)
```

- 活跃期：全量索引，可搜索
- 温期：仅标签索引
- 归档期：仅 ID 可查
- 淘汰期：自动清理

---

## 7. 三智集成

### 小智（总调度）
- 负责协议维护和冲突仲裁
- 定期检查知识库健康度

### 端智（MemoryFuser）
- 负责知识融合和去重
- 自动从 memory/ 提取知识

### 软智（TriggerEngine）
- 基于知识库做触发决策
- 写入触发相关的 pattern

### 米智（KnowledgeBase）
- 负责知识 CRUD API
- 标签体系维护

---

## 8. 验收标准

1. ✅ 三智能通过 API 写入和查询知识
2. ✅ 重复内容自动去重（hash 相同跳过）
3. ✅ 跨节点同步：节点 A 写入，节点 B 能查到
4. ✅ 标签搜索：按标签能搜到相关条目
5. ✅ 冲突解决：同 ID 不同内容，时间戳优先
