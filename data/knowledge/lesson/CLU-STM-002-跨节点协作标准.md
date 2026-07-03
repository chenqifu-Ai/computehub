# Knowledge: CLU-STM-002: 跨节点协作标准
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 跨节点协作, CLU-STM-002, 任务分发, 五智
> Timestamp: 2026-07-02T12:12:50+08:00

## Content

## 核心原则
- 节点间通过 Gateway 分发任务
- Agent 通过 Hall 通信
- 跨节点执行用 exec_remote 工具
- 任务状态通过 Gateway API 同步

## 分工
- 小智：调度+决策
- 米智：巡检+监控
- 端智：重活+排查
- 丁智/软智：Windows远程

完整标准: memory/topics/执行规则/CLU-STM-002_CrossNodeCollabStandard.md
