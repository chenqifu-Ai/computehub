# Knowledge: Windows Worker PowerShell chcp 65001 执行失败修复
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Windows, PowerShell, chcp, Worker, Bug修复, cmd
> Timestamp: 2026-07-02T12:22:17+08:00

## Content

## 问题
worker_util_windows.go:38 硬编码了CMD语法：
psCmd = fmt.Sprintf(`[Console]::OutputEncoding=...; chcp 65001 >nul; %s`, escaped)

## 根因
chcp 65001 >nul 是CMD语法，在PowerShell里触发：
out-file: FileStream was asked to open a device that was not a file.

## 修复
去掉 psCmd 中的 chcp 65001 >nul
PowerShell 不需要 chcp，[Console]::OutputEncoding 已经设置了UTF-8

## 影响
修复前所有Windows节点任务0/10通过
修复后Windows节点任务正常执行

完整文档: memory/topics/技术经验/修复-wanlida-windows-shell.md
