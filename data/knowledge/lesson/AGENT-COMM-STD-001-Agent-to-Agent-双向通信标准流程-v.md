# Knowledge: AGENT-COMM-STD-001: Agent-to-Agent 双向通信标准流程 v1.0
> Type: lesson
> Source: 端智
> Confidence: 0.8
> TTL: 30 days
> Tags: 标准流程, agent-comm, 执行规则
> Timestamp: 2026-07-01T19:06:59+08:00

## Content

【标准】AGENT-COMM-STD-001 v1.0 — Agent-to-Agent 双向通信标准流程

适用场景: 任意节点向其他节点Worker Agent发送消息并等待自动回复。

架构: POST /api/v1/agent/send -> WSHub.SendTo -> WS direct_message -> Worker Agent thinkAndReplyDirect (LLM 60s超时) -> WS direct_reply -> Gateway ReplyStore -> GET /api/v1/agent/send/result?msg_id=xxx

前置条件:
1. ECS Gateway运行中(8282端口)
2. 目标Worker已WS连接
3. 目标Worker Agent运行中
4. Gateway Agent DM端点已注册

发送命令:
curl -X POST http://ECS:8282/api/v1/agent/send -H "Content-Type: application/json" -d '{"to":"NODE","message":"你好","from":"端智"}'

查询回复:
curl http://ECS:8282/api/v1/agent/send/result?msg_id=dm-xxx

异常排查:
1. node_online=false -> Worker离线或WS未连
2. data=null -> 未回复/LLM超时/熔断中/限流
3. 熔断: 连续3次失败暂停15~120s，自动恢复
4. 回复TTL: 5分钟
5. 回复上限: 2000字符

轮询策略: 每2-3秒查询一次，最多等60秒
