# Knowledge: agent_msg.py — 一句话给任意 Worker Agent 发消息
> Type: lesson
> Source: 端智
> Confidence: 0.8
> TTL: 30 days
> Tags: agent-comm, 快捷工具, agent_msg
> Timestamp: 2026-07-01T19:11:53+08:00

## Content

一键通信脚本: python3 agent_msg.py <节点> <消息>

示例:
  python3 agent_msg.py wanlida-work01 '你好'
  python3 agent_msg.py wanlida-work01 '测试超时' 30

路径: ai_agent/code/agent_msg.py (端智本地)
发送后自动等回复(最长60s)，回复到了自动打印

依赖: 仅 Python3 标准库 (urllib, json, sys, time)
Gateway: http://36.250.122.43:8282

底层调用:
  1. POST /api/v1/agent/send -> 投递消息
  2. 轮询 GET /api/v1/agent/send/result?msg_id=xxx -> 拉回复
