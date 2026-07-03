# Knowledge: qwen3.6-35b API适配经验（已迁移至NewAPI）
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: qwen3.6, API适配, NewAPI, reasoning, content null
> Timestamp: 2026-07-02T12:22:18+08:00

## Content

## 历史问题（已解决）
旧版qwen3.6-35b API（58.23.129.98:8000）所有输出在 reasoning 字段，content 始终为 null

## 解决方案
1. 适配层 ai_agent/config/qwen36_adapter.py：从 reasoning 字段读取
2. 最终迁移到 NewAPI（ai.zhangtuokeji.top:9090），content 正常

## 当前状态
已迁移至 NewAPI，不再需要适配层
content 正常输出，不再有 null 问题

## 关键配置
- API地址: https://ai.zhangtuokeji.top:9090/v1
- 模型: qwen3.6-35b-common
- API Key: sk-EJ5OJkr9pHDbvnDkVFoZWD0OGqaYhQ1W8Ap0idpZKBdIU9qX
- max_tokens ≥ 1024（推荐2048）

完整文档: memory/topics/技术经验/qwen36-35b-api-format-fix.md
