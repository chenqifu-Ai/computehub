# Knowledge: WIN-OPC-001: Windows节点远程操作标准流程
> Type: skill
> Source: 小智
> Confidence: 0.9
> TTL: 30 days
> Tags: Windows, 远程操作, WIN-OPC-001, PowerShell, CMD
> Timestamp: 2026-07-02T12:12:49+08:00

## Content

## 适用场景
在 Windows 节点上执行远程命令、任务分发

## 核心注意
- PowerShell 用 -EncodedCommand 避免引号嵌套
- CMD 中 & 链接多条命令（不用 &&，防止断链）
- chcp 65001 会导致 CMD 执行器卡死（已修复）
- 验证用完整路径

## 常见命令模板
cmd /c "taskkill /f /im worker.exe & timeout /t 3 & start worker.exe"
powershell -EncodedCommand <b64_utf16le>

完整标准: memory/topics/执行规则/WIN-OPC-001_Windows节点远程操作标准流程.md
