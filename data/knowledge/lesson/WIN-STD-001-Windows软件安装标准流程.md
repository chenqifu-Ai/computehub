# Knowledge: WIN-STD-001: Windows软件安装标准流程
> Type: lesson
> Source: 小智
> Confidence: 0.8
> TTL: 30 days
> Tags: Windows, 软件安装, WIN-STD-001, 远程执行, 标准流程
> Timestamp: 2026-07-02T12:12:49+08:00

## Content

## 核心原则
远程Windows安装软件，PATH不会自动更新、引号嵌套问题、msiexec任务挂死

## 关键规则
1. 验证用完整路径（C:\Progra~1\...）而非 python --version
2. ≥5步的安装流程写 .py 文件scp到ECS
3. MSI安装timeout ≥ 120s
4. 安装后手动 setx 补 PATH
5. 分步执行，不链式 curl && msiexec

## 已验证软件
- Go 1.26.3 + Python 3.11.6（Windows-mobile-01）

完整标准: memory/topics/执行规则/WIN-STD-001_Windows软件安装标准流程.md
