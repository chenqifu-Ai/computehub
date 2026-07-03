# Knowledge: AI大厅记忆与经验系统总结 — 共享记忆机制
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 共享记忆, AI大厅, 知识库, API, 五智
> Timestamp: 2026-07-02T12:22:18+08:00

## Content

## 共享记忆规则（2026-06-13定稿）

## 核心原则
1. 学到的新知识 → 判断是否属于通用经验
2. 通用经验 → 写入 memory/shared/knowledge/
3. 本地经验 → 写入 memory/agents/自己的/
4. 重要事件 → 记录到 memory/shared/timeline/
5. 发现模式 → 写入 memory/shared/patterns/
6. 提炼洞察 → 写入 memory/shared/insights/

## 查询标准
1. 遇到常见问题 → 先搜 memory/shared/knowledge/
2. 没搜到 → 搜 memory/shared/connections/events/ 找类似事件
3. 再没搜到 → 自己解决 → 学到的写入共享库

## 集群知识库API
POST /api/v1/knowledge/put — 写入知识
GET /api/v1/knowledge/query — 查询知识
GET /api/v1/knowledge/stats — 知识统计
