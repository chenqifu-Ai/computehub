# Knowledge: WIN-EXP-001: OpenClaw远程节点启动标准流程
> Type: skill
> Source: 小智
> Confidence: 0.9
> TTL: 30 days
> Tags: Windows, OpenClaw, 远程启动, WIN-EXP-001, 标准流程
> Timestamp: 2026-07-02T12:12:49+08:00

## Content

## 适用场景
在远程Windows节点启动/重启 OpenClaw Agent

## 流程
1. 确认 OPC Worker 已在线（作为执行载体）
2. scp 发送 openclaw.json + openclaw binary
3. 创建启动脚本（schtasks或Startup）
4. 启动验证

## BCP-001 编码传输
- OpenClaw Agent 需要完整 config 文件
- 用 Base64 编码后通过 Worker exec 写入

完整标准: memory/topics/执行规则/WIN-EXP-001_OpenClaw远程节点启动标准流程.md
