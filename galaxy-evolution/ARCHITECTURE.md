# 银河进化计划 — 架构设计文档

## 概述

银河进化计划的核心目标：**不升级，学原理**。通过深入分析 OpenClaw 2026.6.8 的源码设计，用我们现有的能力实现等效功能，应用到集群中。

## 四大模块

### Phase 1: 承诺管理系统 (commitments)

**原理来源**: OpenClaw 2026.6.8 `commitments` 模块
**实现语言**: Python (端智) + Go (小智)
**存储**: `~/.galaxy-evolution/commitments/commitments.json`

#### 状态机
```
                  ┌─────────┐
                  │ pending │ ← 新建
                  └────┬────┘
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
        ┌──────┐  ┌────────┐  ┌────────┐
        │ sent │  │snoozed │  │dismissed│
        └──────┘  └───┬────┘  └────────┘
                       │ (到期)
                       ▼
                   ┌────────┐
                   │ expired│
                   └────────┘
```

#### 核心设计
- **去重**: `dedupeKey + scopeKey` (agent+session+channel)
- **过期**: 到期后 72h 自动 expired
- **限流**: 每天每 session 最多 3 条
- **置信度**: 0.72 (普通) / 0.86 (关怀)
- **心跳驱动**: 心跳时检查到期承诺，自动推送

### Phase 2: 安全审计系统 (security audit)

**原理来源**: OpenClaw 2026.6.8 `security` 模块

#### 检查项格式
```json
{
  "checkId": "gateway.bind_no_auth",
  "severity": "critical",
  "title": "Gateway binds beyond loopback without auth",
  "detail": "...",
  "remediation": "Set gateway.auth..."
}
```

#### 检查覆盖
- Gateway 绑定和认证
- 明文密钥存储
- 沙箱配置
- Webhook 安全
- mDNS 泄漏
- 插件安全

### Phase 3: 密钥管理 (secrets)

**原理来源**: OpenClaw 2026.6.8 `secrets` 模块

#### 工作流
```
audit → configure → apply --dry-run → apply → reload
```

#### 核心设计
- 运行时快照 + 原子替换
- 失败保留上次快照
- 明文残留扫描 + 自动清理

### Phase 4: 修复助手 (crestodian)

**原理来源**: OpenClaw 2026.6.8 `crestodian` 模块

#### 架构
```
overview(诊断) → dialogue(解析) → operations(执行)
```

#### 模式
- 交互式 TUI
- 单次命令
- JSON 输出

## 集群部署

### 文件同步
- Gallery (ECS:8282) 作为中心存储
- 各节点通过 Gallery API 上传/下载
- git 同步作为备份

### 节点分工
| 节点 | 角色 | 语言 |
|------|------|------|
| 端智 (本地) | JSON 存储 + 心跳驱动 | Python |
| 小智 (ECS) | 状态机引擎 + 过期检测 | Go |
| Windows | 测试验证 | - |
| xiaomi-table | 备用 | - |

## 核心原则
- **不升级，学原理**
- **承诺管理先做**
- **安全 > 功能 > 效率**
