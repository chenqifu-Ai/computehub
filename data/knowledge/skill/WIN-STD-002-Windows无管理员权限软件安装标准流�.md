# Knowledge: WIN-STD-002: Windows无管理员权限软件安装标准流程
> Type: skill
> Source: 小智
> Confidence: 0.9
> TTL: 30 days
> Tags: Windows, 无权限安装, WIN-STD-002, portable, 标准流程
> Timestamp: 2026-07-02T12:12:49+08:00

## Content

## 适用场景
Windows节点没有管理员权限，只能用 portable 版本安装

## 核心方法
- 使用 portable/绿色版软件
- 安装到用户目录（%USERPROFILE%）
- 手动加 PATH（setx PATH）
- 不依赖系统注册表

## 实战案例
wanlida-opc01（admin账户，无管理员权限）:
- Python 3.12.9 portable
- Node.js v18.20.8（nvm-windows）
- Git 2.54.0

完整标准: memory/topics/执行规则/WIN-STD-002_Windows无管理员权限软件安装标准流程.md
