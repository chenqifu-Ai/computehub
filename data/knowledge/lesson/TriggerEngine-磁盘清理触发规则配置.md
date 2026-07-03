# Knowledge: TriggerEngine 磁盘清理触发规则配置
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: trigger, 磁盘, 监控, v1.3.51
> Timestamp: 2026-07-03T03:28:22+08:00

## Content

TriggerEngine 可以配置磁盘使用率告警规则，当磁盘超过85%时触发清理提醒。规则配置在 data/trigger_rules.json，支持系统指标采集（CPU/Mem/Disk/Load）和事件触发。采集间隔60秒，通过 gateway_trigger_linux.go 实现平台特定采集。
