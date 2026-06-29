# 🌌 银河进化计划

**不升级，学原理。** 把 OpenClaw 2026.6.8 的设计理念用现有能力实现等效功能。

## 路线图

| Phase | 模块 | 状态 | 负责人 |
|-------|------|------|--------|
| **Phase 1** | 承诺管理系统 (commitments) | 🚧 进行中 | 端智(Python) + 小智(Go) |
| **Phase 2** | 安全审计系统 (security audit) | 📋 待启动 | 小智 + 端智 |
| **Phase 3** | 密钥管理 (secrets) | 📋 待启动 | 小智 + 端智 |
| **Phase 4** | 修复助手 (crestodian) | 📋 待启动 | 小智 + 端智 |

## 核心设计原理

### 承诺管理 (commitments)
- **存储**: 纯 JSON 文件 + 文件锁，零外部依赖
- **状态机**: `pending → sent → dismissed → snoozed → expired`
- **去重**: `dedupeKey + scopeKey` (agent+session+channel)
- **过期**: 到期后 72h 自动 expired
- **限流**: 每天每 session 最多 3 条
- **心跳驱动**: 心跳时检查到期承诺，自动推送

### 安全审计 (security audit)
- **每个检查项**: `checkId + severity + title + detail + remediation`
- **模式**: 冷路径 vs `--deep` (含运行时探测)
- **抑制**: 可标记已知问题

### 密钥管理 (secrets)
- **工作流**: `audit → configure → apply --dry-run → apply → reload`
- **核心**: 运行时快照 + 原子替换

### 修复助手 (crestodian)
- **架构**: `overview → dialogue → operations`
- **模式**: 交互式 TUI / 单次命令 / JSON 输出

## 代码仓库

- **路径**: ECS `~/galaxy-evolution/` (独立仓库)
- **同步**: git 同步
- **语言**: Go (小智) + Python (端智)

## 核心原则

- **不升级，学原理** — 用现有能力实现等效功能
- **承诺管理先做** — 最轻量，价值最高
- **安全 > 功能 > 效率** — 老大铁律
