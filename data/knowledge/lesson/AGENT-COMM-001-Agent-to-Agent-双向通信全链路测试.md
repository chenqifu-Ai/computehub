# Knowledge: AGENT-COMM-001: Agent-to-Agent 双向通信全链路测试
> Type: lesson
> Source: 端智
> Confidence: 0.8
> TTL: 30 days
> Tags: agent-comm, 测试验证, 银河计划, 通信架构
> Timestamp: 2026-07-01T19:01:03+08:00

## Content

端智(Android) -> ECS:8282 Gateway -> wanlida-work01(Windows,10xRTX4060) 双向通信已全线打通。
架构: HTTP POST /api/v1/agent/send -> WSHub.SendTo -> WS direct_message -> Worker Agent thinkAndReplyDirect -> LLM生成回复 -> WS direct_reply -> Gateway Store -> GET /api/v1/agent/send/result
关键参数: LLM超时60s, 熔断3次失败暂停15~120s, 回复TTL 5分钟, 回复上限2000字符, WS自动重连2~30s指数退避
