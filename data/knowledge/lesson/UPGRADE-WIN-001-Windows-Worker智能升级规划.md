# Knowledge: UPGRADE-WIN-001: Windows Worker智能升级规划
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Windows升级, UPGRADE-WIN-001, Worker, 回滚
> Timestamp: 2026-07-02T12:12:50+08:00

## Content

## 升级策略
- 自动升级循环（间隔5-30min）
- schtasks 独立调度
- 下载新版本到带版本号文件名
- taskkill 后启动新版本

## 回滚
1. scp 旧版本到节点
2. taskkill /f /im computehub.exe
3. start 旧版本

完整标准: memory/topics/执行规则/UPGRADE-WIN-001_WindowsWorker智能升级规划.md
