# Knowledge: WS连接不稳定排查 — 网络抖动/Gateway重启/回声循环
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: WebSocket, WS不稳定, Hall回声, 网络诊断, Gateway
> Timestamp: 2026-07-02T12:23:16+08:00

## Content

## 现象
节点频繁WS重连，每隔~30s出现"已加入大厅(WS)"
Hall消息回声循环（节点间反复发"收到"自我介绍）

## 常见根因
1. Gateway重启 → 节点自动重连，WS session重新建立
2. 网络抖动 → 移动宽带到阿里云不稳定
3. 自动升级 → Worker重启重建WS连接
4. Hall回声循环 → Agent cron循环回复导致消息爆炸

## 诊断命令
查看gateway日志: tail -100 /home/computehub/gateway.log | grep -E "ws|WS|WebSocket"
查看节点注册时间: curl -s localhost:8282/api/v1/nodes
可跳过Hall回声: 设置since_seq跳过已读消息
排查Gateway重启: systemctl status computehub-gateway

## 预防
- 设置Hall消息节流（同一节点30秒内不发重复消息）
- Gateway优雅关闭前通知所有节点
- 检测回声循环并自动抑制
