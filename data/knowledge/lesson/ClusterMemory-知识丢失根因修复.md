# Knowledge: ClusterMemory 知识丢失根因修复
> Type: lesson
> Source: ecs-p2ph
> Confidence: 0.9
> TTL: 30 days
> Tags: memory, knowledge, bugfix, cluster
> Timestamp: 2026-07-01T08:38:04+08:00

## Content

syncGitMemoryToCluster 只同步 episode 不同步 knowledge 导致知识丢失。修复：新增 ListRecentKnowledge + sync 阶段直接操作 map + 一次性持久化。
