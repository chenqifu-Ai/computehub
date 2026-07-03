# Knowledge: TUI-STD-001: Windows Worker任务卡住问题诊断
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Windows, Worker卡死, TUI-STD-001, 任务诊断
> Timestamp: 2026-07-02T12:12:50+08:00

## Content

## 问题
Windows Worker 任务状态卡在 Running 不结束

## 排查步骤
1. 查看 Worker 日志（gateway.log）
2. 检查 CMD/PowerShell 进程是否僵死
3. 检查 chcp 65001 是否导致执行器卡死
4. 检查引号嵌套（单引号 vs 双引号）

## 修复
- 去掉 chcp 65001
- 用 Base64 编码传命令
- 超时 120s+

完整标准: memory/topics/执行规则/TUI-STD-001_Windows_Worker_任务卡住问题.md
