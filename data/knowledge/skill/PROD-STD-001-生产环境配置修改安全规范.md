# Knowledge: PROD-STD-001: 生产环境配置修改安全规范
> Type: skill
> Source: 小智
> Confidence: 0.9
> TTL: 30 days
> Tags: 生产环境, 配置修改, PROD-STD-001, 安全规范, 回滚
> Timestamp: 2026-07-02T12:12:49+08:00

## Content

## 3条铁律
1. 一次只改一件事 — 禁止同时执行多个破坏性改动
2. 先扫描再动刀 — 删除任何provider/配置前必须全量扫描
3. 改完必验证 — 修改后必须验证，失败立即回滚

## 验证脚本
scripts/scan-deps.sh <目标值> — 扫描所有引用
scripts/verify-config.sh — 配置链路验证 + Gateway检查

## 回滚
git checkout HEAD~1 -- openclaw.json && systemctl restart openclaw-gateway

完整标准: memory/topics/执行规则/PROD-STD-001_生产环境配置修改安全规范.md
