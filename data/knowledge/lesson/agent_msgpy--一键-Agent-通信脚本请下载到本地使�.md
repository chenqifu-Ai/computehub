# Knowledge: agent_msg.py — 一键 Agent 通信脚本（请下载到本地使用）
> Type: lesson
> Source: 端智
> Confidence: 0.8
> TTL: 30 days
> Tags: agent-comm, agent_msg, 快捷工具, 通信脚本
> Timestamp: 2026-07-01T19:29:20+08:00

## Content

## agent_msg.py — 给任意 Worker 发消息等回复

### 下载地址
http://36.250.122.43:8282/api/v1/download?file=tools/agent_msg.py

### 使用方式
```bash
# Linux/Mac
curl -o /usr/local/bin/agent_msg.py http://36.250.122.43:8282/api/v1/download?file=tools/agent_msg.py
echo 'alias agent_msg="python3 /usr/local/bin/agent_msg.py"' >> ~/.bashrc
source ~/.bashrc

# 然后直接
agent_msg wanlida-work01 "你好"
```

### 原理
基于 AGENT-COMM-STD-001 标准：
1. POST /api/v1/agent/send → ECS Gateway → WS direct_message → Worker Agent
2. 轮询 GET /api/v1/agent/send/result?msg_id=xxx → 等回复

### 依赖
仅 Python3 标准库，无需第三方包。
