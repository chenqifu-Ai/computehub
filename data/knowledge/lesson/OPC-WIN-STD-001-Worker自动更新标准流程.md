# Knowledge: OPC-WIN-STD-001: Worker自动更新标准流程
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Worker, 自动更新, OPC-WIN-STD-001, Windows, Linux
> Timestamp: 2026-07-02T12:12:49+08:00

## Content

## 核心教训
Worker 更新过程中进程会被自己杀死，必须设计"自杀不掉链"的独立执行流程

## 关键规则
- Windows必须用 schtasks 独立调度（不能 start /B）
- Linux用 nohup + & 后台执行
- 下载用 Gallery 端点 /api/v1/files/，timeout ≥ 120s
- Windows --node-id 别超过 15 字符（NetBIOS限制）
- taskkill 前先下载新版本到带版本号的文件名
- PowerShell -EncodedCommand 避免 CMD 引号嵌套
- 版本号必须走 git tag（不手动改 version.txt）

## 致命陷阱
⚠️ taskkill /f /im computehub.exe 会杀所有同名进程
⚠️ 包括发命令的Worker，后续命令无法继续

完整标准: memory/topics/执行规则/OPC-WIN-STD-001_Worker自动更新标准流程.md
