# Knowledge: STD-002: Gateway任务调度node字段兼容
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 任务调度, Gateway, STD-002, node字段
> Timestamp: 2026-07-02T12:12:48+08:00

## Content

## 问题
Gateway API 任务调度支持两种 node 字段写法

## 写法
- curl -d '{"command":"task","node":"Windows-mobile-01"}'  （最简推荐）
- curl -d '{"command":"task","node_id":"Windows-mobile-01"}'（Go原生）

## 注意
两种写法都兼容，推荐用短的 node

完整标准: memory/topics/执行规则/STD-002_Gateway任务调度node字段兼容.md
