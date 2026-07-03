# Knowledge: COM-STD-001: 集群通信标准
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: 集群通信, COM-STD-001, WebSocket, Gateway, 架构
> Timestamp: 2026-07-02T12:12:50+08:00

## Content

## 集群通信架构
- Gateway 作为中央枢纽（port 8282）
- Worker 通过公网/内网注册
- WS（WebSocket）优先通信，HTTP poll 兜底
- 节点心跳每 30s

## 通信协议
- ARC-AI-NET 拓扑广播
- KSP-001 知识共享
- Hall 消息转发（Agent↔Agent）

## 端口
- Gateway: 8282
- WS: /api/v1/ws
- Gallery: /api/v1/files/

完整标准: memory/topics/执行规则/COM-STD-001_集群通信标准.md
