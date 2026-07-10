# Knowledge: windows-home-01 Gateway /ai 路由缺失 — 三管齐下规避方案
> Type: lesson
> Source: ecs-p2ph
> Confidence: 0.8
> TTL: 30 days
> Tags: 
> Timestamp: 2026-07-10T22:36:48+08:00

## Content

三管齐下：1) routes.go /ai 无条件注册 2) gatewaycmd/cmd.go 加 --config 参数 + 环境变量兜底 + 醒目警告 3) scripts/win-deploy-gateway.py 一键部署脚本
