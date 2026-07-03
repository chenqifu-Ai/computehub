# SPEC-MEMORY-001: Git 记忆系统设计规范

> **状态**: 设计阶段 | **版本**: v1.0 | **日期**: 2026-05-31
> **作者**: 小智
> **负责**: 从 OPC Memory 模块设计到 Agent 集成全流程

---

## 目录

1. [概述](#1-概述)
2. [存储结构规范](#2-存储结构规范)
3. [文件格式规范](#3-文件格式规范)
4. [命名规范](#4-命名规范)
5. [API 接口规范](#5-api-接口规范)
6. [Git 操作规范](#6-git-操作规范)
7. [数据生命周期规范](#7-数据生命周期规范)
8. [Agent 集成规范](#8-agent-集成规范)
9. [错误闭环规范](#9-错误闭环规范)
10. [安全规范](#10-安全规范)
11. [附录：参考实现](#11-附录参考实现)

---

## 1. 概述

### 1.1 核心理念：向人类记忆学习

人类记忆不是文件系统，不是数据库。它是**一张随时间生长的网**。

```
人类记忆的特征：
  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  时间轴     每一段记忆都有一个时间坐标，可以"往回翻"      │
  │                                                          │
  │  联想       一个记忆会"钩"起另一个——"说到磁盘，上次..."   │
  │                                                          │
  │  衰减       不用的记忆慢慢淡忘，常用的越来越清晰           │
  │                                                          │
  │  强化       "又遇到这情况了"→ 这条记忆权重变高            │
  │                                                          │
  │  网络化      记忆不是孤立的文件，是互相链接的节点          │
  │                                                          │
  │  场景驱动    "我记得那时候我在修Windows..." → 场景回忆     │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
```

**OPC 记忆系统就是模拟这个模型。** 它解决的核心问题：

```
没有记忆（当前）：
  Agent: "检查磁盘空间"
  Agent: 执行 df -h → "85%"
  Agent: "清理一下 /tmp"
  Agent: 执行 rm -rf /tmp/* → 完成
  Agent: "检查磁盘空间"（5分钟后）
  Agent: 又执行 df -h → "80%"  ← 不记得刚做过，每次都重查

有记忆（目标）：
  Agent: "检查磁盘空间"
  Agent: 执行 df -h → "85%" → 记录到时间轴
  Agent: "清理一下 /tmp"
  Agent: 执行 → 记录 → 关联到"磁盘"这个节点
  Agent: "检查磁盘空间"（5分钟后）
  Agent: 沿时间轴回溯 → "刚才清理了 /tmp，磁盘应该降了"
  Agent: 执行 df -h 验证 → "80%，跟预期一致"  ← 聪明了
  
  Agent: "说到磁盘..."（第二天）
  Agent: 联想网络跳转 → "磁盘"节点 → 清理记录 → Windows 磁盘
  Agent: "对了，上次 Windows 也说磁盘快满了，要不要一起看看？"
```

### 1.2 人类记忆的四个核心模型

#### 模型1：时间轴（Temporal Timeline）

```
每一段记忆都锚定在时间轴上，可以：
  - 回溯："上周这时候我在干什么？"
  - 浏览："让我看看 5 月发生了什么"
  - 上下文："就在 Windows 更新之前，我记得..."
  
实现方式：
  ├── 时间作为文件名的一部分（YYYY-MM-DD-...）
  ├── 每个段落都有时间戳
  └── git log 本身就是一条完整的时间轴
```

#### 模型2：联想网络（Associative Network）

```
记忆不是孤立的，而是互相链接的节点：

        日志分析
          │
          ├── 关联→ Linux: journalctl 用法
          ├── 关联→ Windows: Event Log 查询
          ├── 关联→ 那次 OOM killer 事件
          ├── 关联→ "磁盘快满了" → 触发清理
          │                    ├── /tmp 清理
          │                    └── docker prune
          └── 关联→ "内存不够" → 加交换分区

实现方式：
  ├── 每个 memory 文件内有 [[关联链接]]
  ├── INDEX.md 维护一个轻量标签网络
  └── 相似内容通过内容哈希自动链接
```

#### 模型3：衰减与强化（Decay & Reinforcement）

```
记忆强度随使用频率变化：

  强度 ▲
       │   ╔══╗           ╔══╗
       │   ║  ║           ║  ║
       │   ║  ║  ──────   ║  ║        ← 不用就衰减
       │ ╔═╝  ╚══╗      ╔═╝  ╚══╗
       │ ║       ║      ║       ║
       │ ║       ║  ─── ║       ║     ← 再次使用→强化
       └─╨───────╨───────────────╨──→ 时间
         第1次    衰减中    再次遇到

实现方式：
  ├── 每条记忆有 access_count 和 last_access
  ├── 每次命中 → 强化（count++）
  ├── 超过 N 天未访问 → 标记"衰减中"
  └── 衰减到阈值以下 → 摘要化（保留核心，丢弃细节）
```

#### 模型4：场景回忆（Contextual Recall）

```
人类回忆时不是"搜索关键词"，而是"回到那个场景"：

  "那天我在修 Windows Worker 升级的时候..."
  → 场景：Windows-mobile 节点、凌晨6点、schtasks、PowerShell
  → 关联：NetBIOS 截断、taskkill 自杀、版本号问题
  → 整个场景一次拉出来，不是一个点一个点找

实现方式：
  ├── 每条记忆关联场景标签（node, time, context）
  ├── 场景是"第一索引"，关键词是"第二索引"
  └── 回忆时先定位场景，再展开细节
```

### 1.3 设计原则

| 原则 | 说明 | 违规后果 |
|------|------|---------|
| **零外部依赖** | 只依赖 Go 标准库 + 系统 Git 命令 | 引入第三方包 → 否决 |
| **文件即数据** | 每个文件是可读的 Markdown，不用二进制序列化 | 不可读格式 → 否决 |
| **Git 原生** | 充分利用 git diff/grep/log，不做包装层 | 自建索引 → 否决 |
| **简单优先** | 用文件系统做数据库，不引入 SQLite/BoltDB | 加数据库 → 否决 |
| **网络化优先** | 每段记忆必须有关联链接，孤立记忆会被衰减 | 无关联的单点 → 否决 |
| **衰减机制** | 记忆必须能"淡忘"，不保留所有细节 | 无限膨胀 → 否决 |

### 1.4 适用范围

本规范覆盖：
- `src/agent/memory.go` — 记忆系统的 Go 实现（含关联网络 + 衰减引擎）
- `src/agent/memory_test.go` — 测试套件
- memory 仓库目录结构、文件格式、关联规则、衰减策略
- Agent 集成时对 memory 的调用方式

不覆盖：
- Agent 的业务逻辑（`agent.go`）
- Brain 心跳循环（`brain.go`）
- 远程同步机制（GitHub remote push/pull）

---

## 2. 存储结构规范

### 2.1 仓库根目录

```
<memory_root>/                           ← Git 仓库根目录
├── .git/                                ← Git 元数据
├── README.md                            ← 仓库说明
├── SPEC-MEMORY-001.md                   ← 本规范（可选复制）
│
├── sessions/                            ← 短期记忆：对话记录
│   ├── session-xxxxxxxx.md
│   └── ...
│
├── episodes/                            ← 中期记忆：执行经验
│   ├── YYYY-MM-DD-slug.md
│   └── ...
│
├── knowledge/                           ← 长期记忆：已验证知识
│   ├── topic-slug.md
│   └── ...
│
└── system/                              ← 系统状态快照
    ├── cluster-status.md
    └── ...
```

**默认路径**: `/home/computehub/opc-memory/`
**可覆盖**: 通过 `config.json` 的 `memory.path` 字段配置

### 2.2 目录职责

| 目录 | 存储器 | 生命周期 | 写入频率 | 容量上限 |
|------|--------|---------|---------|---------|
| `sessions/` | Agent 对话记录 | 持久，60天后自动归档 | 每次对话消息 | 每个 session 50条 |
| `episodes/` | 执行任务记录 | 持久，30天后自动归档 | 每次任务完成 | 1000条（超限只归档不删）|
| `knowledge/` | 验证过的知识 | 永久保留 | 偶尔 | 500条（超限只归档不删）|
| `system/` | 集群状态快照 | 只保留当前快照 | 每次心跳 | 1个文件 |

### 2.3 关联网络：记忆之间的链接

这是"人类记忆"的核心——记忆不是孤立的文件，而是互相链接的节点。

#### 2.3.1 链接方式

```
episodes/2026-05-31-disk-cleanup.md
    │
    ├── relates: episodes/2026-05-28-windows-disk-full.md
    │     ↑ "那次磁盘满的问题引出了这次清理"
    │
    ├── relates: knowledge/linux-tmp-cleanup.md
    │     ↑ "这次清理用到的知识"
    │
    └── relates: sessions/session-a1b2c3d4.md
          ↑ "这次操作的对话记录"
```

#### 2.3.2 链接类型

| 类型 | 语义 | 示例 |
|------|------|------|
| `relates` | 一般关联 | 同一话题的相关内容 |
| `causes` | 因果关系 | A 导致了 B |
| `solves` | 解决方案 | A 解决了 B 的问题 |
| `follows` | 时间先后 | A 之后发生了 B |
| `similar` | 相似场景 | A 和 B 类似 |
| `contradicts` | 矛盾 | A 和 B 的结论不同 |

#### 2.3.3 INDEX.md —— 全局标签索引

为了让 Agent 能快速"联想到"相关内容，维护一个轻量标签索引：

```markdown
# INDEX — Memory Association Index
> Updated: 2026-05-31 15:00:00

## Tags

### 磁盘
- episodes/2026-05-31-disk-cleanup.md (2026-05-31, ✅)
- episodes/2026-05-28-windows-disk-full.md (2026-05-28, ✅)
- knowledge/linux-tmp-cleanup.md (永久)

### Windows
- episodes/2026-05-28-windows-upgrade-fix.md (2026-05-28, ✅)
- knowledge/windows-gpu-detection.md (永久)
- knowledge/windows-log-search.md (永久)

### GPU
- knowledge/windows-gpu-detection.md (永久)
- episodes/2026-05-29-gpu-detection-test.md (2026-05-29, ❌)

## Recent Cross-Links
- 磁盘 → Windows: Windows 磁盘问题两次处理
- GPU → Windows: Windows GPU 检测 WMI 方法
- 日志 → Linux: journalctl 使用
- 日志 → Windows: Select-String 对比 findstr
```

INDEX.md 的维护：
- **写入时**：新 episode/knowledge 自动提取关键词，追加到 INDEX
- **每次 auto-commit**：重新生成 INDEX（轻量，不耗资源）
- **不是搜索引擎**：只是"目录"，搜索靠 git grep

### 2.3 .gitignore 规范

```gitignore
# OPC Agent Memory — .gitignore
*.swp
*.tmp
*.log
.DS_Store
```

---

## 3. 文件格式规范

### 3.1 通用规则

所有记忆文件使用 **UTF-8 编码的 Markdown**。

#### 3.1.1 元数据块

每个文件头部包含 YAML 风格的元数据块：

```markdown
# Title
> Key: Value
> Key2: Value2
```

允许的元数据键:

| 键 | 必填 | 说明 |
|----|:----:|------|
| `Created` | ✅ | 创建时间，格式 `2026-05-31 14:30:22` |
| `Updated` | ❌ | 最后更新时间 |
| `Type` | ✅ | `session` / `episode` / `knowledge` / `system` |
| `SessionID` | session必填 | 对话 ID |
| `Success` | episode必填 | `✅` 或 `❌` |
| `Strength` | ❌ | 记忆强度值，范围 0.0 ~ 1.0，不填默认为 1.0 |
| `Tags` | ❌ | 逗号分隔的标签，用于联想和索引，如 `windows, disk, error` |
| `AccessCount` | ❌ | 被检索次数 |
| `LastAccess` | ❌ | 最后被检索时间 |
| `Associations` | ❌ | 关联文件列表，半角逗号分隔 |
| `Summarized` | ❌ | 是否已摘要化，取值 `true` / `false` |

**强度与标签的自动维护**：`Strength`、`AccessCount`、`LastAccess` 由系统自动更新，不在 Markdown 正文中编辑。Agent 读取文件时通过 git note 或独立元数据文件维护，不污染正文。简化实现也可直接在文件头部更新。

#### 3.1.2 时间格式

所有时间使用 `Asia/Shanghai` 时区，格式：
- 完整时间: `2026-05-31 14:30:22`
- 仅时间: `14:30:22`
- 仅日期: `2026-05-31`

#### 3.1.3 代码块

Shell 命令和输出使用 Markdown 代码块：
```markdown
​```json
{
  "command": "df -h",
  "result": "Filesystem ..."
}
​```
```

```markdown
​```
stdout 输出内容
​```
```

### 3.2 session 文件格式

```markdown
# Session: session-a1b2c3d4
> Type: session
> SessionID: session-a1b2c3d4
> Created: 2026-05-31 14:30:22
> Updated: 2026-05-31 14:35:10
> Source: tui
> Summary: 分析了三台服务器的日志，发现15个异常

## 14:30:22 — User
帮我分析一下所有节点的日志

## 14:30:23 — Agent (thought)
需要先收集日志，再用 LLM 分析。

## 14:30:24 — Action: step_1 (ecs-p2ph)
​```shell
grep -i error /var/log/syslog | tail -10
​```
→ ✅ 完成 (0.3s)
​```
Output: ...
​```

## 14:31:00 — Agent (result)
分析完成。一共发现 15 个异常...
```

#### 3.2.1 角色标识

| role | 显示名 | 说明 |
|------|--------|------|
| `User` | 用户 | 老大/用户输入 |
| `Agent (thought)` | AI 的思考 | Agent 的内部推理 |
| `Agent (result)` | AI 的回答 | Agent 给用户的最终输出 |
| `Action: step_N (node_id)` | 执行步骤 | Agent 执行的具体操作 |

#### 3.2.2 执行步骤规范

每条 Action 记录必须包含：
```
→ [status] [duration]
[stdout/stderr 输出]
```

状态标识:
- `✅` — 成功
- `❌` — 失败
- `🔄` — 重试中

#### 3.2.3 压缩标记

当 session 超过 50 条消息被压缩后，在文件头部添加：
```
> Compacted: true
> CompactedAt: 2026-05-31 16:00:00
> OriginalCount: 67
> Summary: 对话涉及日志分析、磁盘清理建议、新节点注册等话题...
```

### 3.3 episode 文件格式

```markdown
# Episode: 分析服务器错误日志
> Type: episode
> Date: 2026-05-31
> Success: ✅
> Duration: 45s
> Trigger: user_request
> SessionID: session-a1b2c3d4

## Task
分析所有节点的 /var/log/syslog，找出异常模式

## Steps
1. ecs-p2ph: grep -i error /var/log/syslog (✅ 0.3s)
2. Windows-mobile: findstr /i "error" C:\var\log\*.log (✅ 0.8s)
3. Agent: LLM 汇总分析 (✅ 2.1s)

## Result
发现 15 个异常，其中 3 个关键：
1. ecs-p2ph: OOM killer 在 05:30 触发（内存不足）
2. Windows-mobile: 服务崩溃（应用日志）

## Learned
- Windows 的 findstr 和 Linux 的 grep 行为不同，不能直接用同一个正则
- OOM killer 触发的频率在增加，可能需要加内存

## Related
- knowledge/windows-log-search.md
- knowledge/oom-killer-troubleshooting.md
```

#### 3.3.1 Trigger 取值

| 值 | 说明 |
|----|------|
| `user_request` | 用户主动要求 |
| `auto_recovery` | Brain 自动触发恢复 |
| `auto_maintenance` | Brain 自动维护任务 |
| `system_event` | 系统事件触发（如节点上线） |

#### 3.3.2 Learned 规范

每一条 `Learned` 必须满足：
1. **可验证** — 写的是事实，不是猜测
2. **可复用** — 下次遇到类似情况能用上
3. **具体** — 不要"学到了更多经验"，要"findstr 不支持正向预查"

好的 Learned：
```
- findstr 不支持正则预查，要用 Select-String
- OOM killer 触发的前 30 分钟 dmesg 有警告
- Windows 路径大小写不敏感
```

差的 Learned：
```
- 学到了更多经验
- 日志很重要
- 需要更小心
```

### 3.4 knowledge 文件格式

```markdown
# Knowledge: Windows 日志搜索方法
> Type: knowledge
> Verified: 2026-05-30
> Author: Agent (auto-discovery)
> VerifiedBy: Agent (self-verified)
> RelatedFiles: src/workercmd/worker_util_windows.go

## Problem
在 Windows 节点上搜索包含 "error" 的日志，
但 findstr 功能和 grep 差异很大。

## Solution
推荐使用 PowerShell 的 Select-String：
```powershell
Select-String -Path "C:\var\log\*.log" -Pattern "error" | Select-Object -First 10
```

避免使用 findstr，因为：
1. 不支持正则预查/后查
2. 不支持多行匹配
3. 中文编码有问题

## Verification
```shell
# 在 Windows-mobile 上测试通过
Select-String -Path "C:\var\log\*.log" -Pattern "error" | Measure-Object | %{$_.Count}
# 返回 3 条，结果正确
```

## Edge Cases
- 日志文件被占用时：Select-String 会报 "访问被拒绝"，需要管理员权限
- 文件过大时：加 -Tail 参数限制行数

## Related
- episodes/2026-05-30-windows-log-search.md
- episodes/2026-05-29-compare-grep-findstr.md
```

#### 3.4.1 写入条件

只有满足以下**全部**条件才能写入 knowledge：
1. 经过至少 **2 次验证**（不同时间/场景）
2. 有具体的 **Solution** 描述
3. 有 **Edge Cases** 处理
4. 有可重现的 **Verification** 步骤

### 3.5 system 文件格式

```markdown
# System: Cluster Status
> Type: system
> Updated: 2026-05-31 14:30:00
> Agent: Agent-v1.2.1

## Nodes
| NodeID | Status | GPU | Tasks | Uptime |
|--------|--------|-----|-------|--------|
| ecs-p2ph | ✅ online | CPU | 0 | 11d |
| Windows-mobile-01 | ✅ online | CPU | 0 | 3d |
| Windows-mobile | ✅ online | CPU | 0 | 3d |

## Queue
- pending: 0
- running: 0
- completed (24h): 12

## System
- Memory: 12.5% (966M/7.76G)
- Load: 0.01
- Disk: 52% (22G/45G)
```

system 文件只保留**当前状态**，不保留历史。历史全在 git commit 里。

---

## 4. 命名规范

### 4.1 session 文件名

```
session-{8位短ID}.md
```

- 短 ID: 使用 `crypto/rand` 生成 8 字符 hex（base16），如 `a1b2c3d4`
- 全部小写
- 不可使用时间戳（避免冲突和猜测）

示例：`session-a1b2c3d4.md`

### 4.2 episode 文件名

```
{YYYY-MM-DD}-{slug}.md
```

- 日期部分：4位年 + 2位月 + 2位日
- slug 部分：从任务描述提取，长度 10-40 字符
- 全部小写，中划线分隔
- 去除特殊字符（只保留 `[a-z0-9-]`）

示例：
- `2026-05-31-analyze-server-logs.md`
- `2026-05-31-disk-cleanup.md`
- `2026-05-30-windows-gpu-detection.md`

### 4.3 knowledge 文件名

```
{topic}-{subtopic}.md
```

- 全部小写，中划线分隔
- topic 和 subtopic 都用英文（避免编码问题）
- 长度 10-60 字符

示例：
- `windows-gpu-detection.md`
- `windows-log-search.md`
- `linux-oom-killer.md`
- `agent-memory-commit-strategy.md`

### 4.4 system 文件名

固定名称，不改：
- `cluster-status.md`
- `agent-config.md`

---

## 5. API 接口规范

### 5.1 Memory 接口定义

```go
// Memory 是 Agent 记忆系统的接口。
// 所有实现必须满足此接口。
type Memory interface {
    // ──────── 仓库管理 ────────

    // Init 初始化记忆仓库。
    // 如果仓库不存在则创建并 git init。
    // 如果已存在则直接加载。
    // 返回 error 表示初始化失败。
    Init() error

    // Close 关闭记忆系统。
    // 执行最终 commit 并释放资源。
    Close() error


    // ──────── 短期记忆：对话 ────────

    // AppendSession 追加一条对话消息。
    // sessionID 必须非空，role 必须是规范定义的角色之一。
    // 自动处理文件创建和追加。
    AppendSession(sessionID string, role string, content string) error

    // GetSession 读取完整对话内容。
    // 返回整个 session 文件的原始 Markdown。
    GetSession(sessionID string) (string, error)

    // ListSessions 列出最近的 session。
    // 按更新时间倒序，limit <= 0 时返回全部。
    ListSessions(limit int) ([]SessionInfo, error)

    // SummarizeSession 压缩长对话。
    // 保留最近 20 条完整消息，其余压缩为摘要。
    // 调用者需提供 LLMClient 用于生成摘要。
    SummarizeSession(sessionID string, llm *composer.LLMClient) error


    // ──────── 中期记忆：经验 ────────

    // SaveEpisode 保存一条执行经验。
    // task — 任务描述（必填）
    // result — 执行结果（必填）
    // success — 是否成功
    // learned — 学到的经验（可选，但推荐）
    SaveEpisode(task string, result string, success bool, learned string) error

    // SearchEpisodes 按关键词搜索经验。
    // 使用 git grep 实现全文搜索。
    // 返回匹配的 episode 摘要列表。
    SearchEpisodes(query string, limit int) ([]EpisodeSummary, error)

    // ListRecentEpisodes 列出最近的 N 条经验。
    ListRecentEpisodes(limit int) ([]EpisodeSummary, error)

    // CleanOldEpisodes 清理 30 天前的 episode。
    // 清理前先检查是否有 "learned" 标记，
    // 有价值的经验应先转为 knowledge 再清理。
    CleanOldEpisodes() error


    // ──────── 长期记忆：知识 ────────

    // SaveKnowledge 保存一条验证过的知识。
    // 调用者有责任保证知识已经过充分验证。
    SaveKnowledge(topic string, content string) error

    // SearchKnowledge 搜索知识库。
    // 使用 git grep 实现全文搜索。
    SearchKnowledge(query string, limit int) ([]KnowledgeSummary, error)


    // ──────── 系统状态 ────────

    // UpdateSystemStatus 更新集群状态快照。
    // systemJSON — 包含节点、队列、资源信息的 JSON 字符串。
    UpdateSystemStatus(systemJSON string) error

    // GetSystemStatus 读取当前集群状态。
    GetSystemStatus() (string, error)


    // ──────── Git 操作 ────────

    // Commit 提交所有未提交的改动。
    // message — commit message
    // 如果无改动（!dirty），静默返回 nil。
    Commit(message string) error

    // AutoCommit 自动提交。
    // 供定时器调用，message 自动生成。
    AutoCommit() error

    // History 查看历史 commit 列表。
    History(limit int) ([]CommitInfo, error)

    // Diff 查看某次 commit 的改动。
    Diff(commitHash string) (string, error)


    // ──────── 查询统计 ────────

    // Stats 返回记忆仓库统计信息。
    Stats() (*MemoryStats, error)
}
```

### 5.2 数据结构

```go
// SessionInfo session 摘要信息
type SessionInfo struct {
    ID        string    `json:"id"`        // session-xxxxxxxx
    CreatedAt time.Time `json:"created_at"`
    UpdatedAt time.Time `json:"updated_at"`
    MessageCount int    `json:"message_count"`
    Source    string    `json:"source"`     // "tui" | "think" | "agent"
    Summary   string    `json:"summary,omitempty"`
}

// EpisodeSummary episode 摘要
type EpisodeSummary struct {
    File    string `json:"file"`
    Title   string `json:"title"`
    Date    string `json:"date"`
    Task    string `json:"task"`
    Success bool   `json:"success"`
    Learned string `json:"learned,omitempty"`
}

// KnowledgeSummary 知识条目摘要
type KnowledgeSummary struct {
    File     string `json:"file"`
    Topic    string `json:"topic"`
    Problem  string `json:"problem"`
    Verified string `json:"verified"`
}

// CommitInfo commit 信息
type CommitInfo struct {
    Hash    string    `json:"hash"`
    Author  string    `json:"author"`
    Date    time.Time `json:"date"`
    Message string    `json:"message"`
    Files   int       `json:"files"`
    Insertions int    `json:"insertions"`
    Deletions  int    `json:"deletions"`
}

// MemoryStats 统计
type MemoryStats struct {
    SessionCount  int    `json:"session_count"`
    EpisodeCount  int    `json:"episode_count"`
    KnowledgeCount int   `json:"knowledge_count"`
    TotalCommits  int    `json:"total_commits"`
    RepoSize      string `json:"repo_size"` // 友好显示
    LastCommit    string `json:"last_commit"`
}
```

### 5.3 错误处理

所有错误返回类型：

```go
var (
    ErrMemoryNotInit  = errors.New("memory not initialized")
    ErrSessionEmpty   = errors.New("session ID cannot be empty")
    ErrInvalidRole    = errors.New("invalid role")
    ErrTooLarge       = errors.New("content exceeds size limit")
)
```

错误处理规则：
1. 所有方法必须返回 `error`
2. Git 命令失败时，返回的 error 必须包含 git stderr 输出
3. 不 panic

---

## 6. Git 操作规范

### 6.1 提交频率

```
┌─────────────┐    每 30 秒               每 5 分钟           每天一次
│  Agent      │─────── 心跳决策 ──────→  AutoCommit ──────→  Cleanup
│  Think 循环  │                             │                  │
│             │    每次重要事件             git commit         git gc
│  对话        │─────── 立即 Commit ──────→  -a -m "auto:..."  清理旧记录
│  Action     │                                       
└─────────────┘
```

**立即 commit 的事件**：
- Episode 保存 ✅
- Knowledge 保存 ✅
- System 状态更新 ✅

**不立即 commit 的事件**：
- Session 追加（等 5min auto-commit）

### 6.2 commit message 规范

格式：
```
{type}: {简短描述}
```

| type | 使用场景 | 示例 |
|------|---------|------|
| `session` | 对话记录（auto-commit） | `session: 分析服务器日志 (4 messages)` |
| `episode` | 执行经验 | `episode: disk-cleanup (✅) freed 3.4GB` |
| `knowledge` | 知识保存 | `knowledge: windows-gpu-wmi-fallback` |
| `system` | 状态更新 | `system: cluster-status update — 3 nodes online` |
| `auto` | 自动提交 | `auto: memory update at 2026-05-31 15:00` |
| `init` | 初始化 | `init: OPC Agent Memory repository` |
| `compact` | 压缩整理 | `compact: clean 23 old episodes from May` |

message 长度：**不超过 72 字符**（Git 标准行宽）

### 6.3 git config

仓库级 git config 设置：

```bash
git config user.name "ComputeHub Agent"
git config user.email "agent@computehub.ai"
git config core.autocrlf input     # Linux 风格换行
git config commit.gpgsign false    # 不签名
```

### 6.4 禁止的 Git 操作

| 操作 | 原因 | 替代方案 |
|------|------|---------|
| `git push` | 非必需，以后按需增加 | 暂不实现 |
| `git pull` | 同上 | 暂不实现 |
| `git merge` | 单写者场景无需 merge | 不存在冲突 |
| `git rebase` | 改写历史 | 用 `git revert` |
| `git reset --hard` | 数据丢失风险 | `git revert` |
| `git gc --aggressive` | 太重 | `git gc --auto` |

### 6.5 git grep 搜索规则

```go
// 搜索实现使用以下命令：
// sessions 搜索: git grep -i -l "{query}" -- sessions/
// episodes 搜索: git grep -i -l "{query}" -- episodes/
// knowledge 搜索: git grep -i -l "{query}" -- knowledge/
// 全量搜索:  git grep -i -l "{query}" -- sessions/ episodes/ knowledge/
```

参数说明：
- `-i`: 大小写不敏感
- `-l`: 只返回文件名
- `--`: 分隔符，后面跟路径限制

---

## 7. 数据生命周期规范

### 7.1 核心模型：衰减曲线

每条记忆有一个"强度值"，随时间变化：

```
强度值范围: 0.0 (完全归档) ~ 1.0 (刚创建/刚强化)

新创建:               强度 = 1.0
每天的自然衰减:       强度 -= 0.02 * (1 + 无访问天数 * 0.1)
被 Agent 检索命中:    强度 = min(1.0, 强度 + 0.3)
相关记忆被检索:       强度 = min(1.0, 强度 + 0.1)  ← 联想强化
```

衰减曲线示例：
```
强度
1.0 ┤●
    │ \
0.8 ┤  \
    │   \
0.6 ┤    ●← 第3天又用了一次，强度回到0.8
    │     \
0.4 ┤      \
    │       \
0.2 ┤        ●← 第7天又用了一次，强度回到0.6
    │         \
0.0 ┤──────────●← 30天没用，强度≈0.0 → 自动摘要化
    └────────────────────────────→ 天数
    0   5   10  15  20  25  30
```

### 7.2 衰减策略参数

```go
type DecayConfig struct {
    // 每日基础衰减率（默认 0.02 = 50天从1.0降到0.0）
    DailyDecay float64 `json:"daily_decay"`
    
    // 无访问天数加速系数（默认 0.1）
    // 作用：越久没看，忘得越快
    NeglectAccel float64 `json:"neglect_accel"`
    
    // 直接命中强化值（默认 0.3）
    DirectHitReinforce float64 `json:"direct_hit_reinforce"`
    
    // 关联命中强化值（默认 0.1）
    // "说到磁盘的时候提了一下那次清理"→ 也涨一点
    AssocHitReinforce float64 `json:"assoc_hit_reinforce"`
    
    // 摘要化阈值（默认 0.15）
    // 低于此值 → 保留核心摘要，丢弃细节
    SummarizeThreshold float64 `json:"summarize_threshold"`
    
    // 彻底归档阈值（默认 0.05）
    // 低于此值且无关联链接 → 移入 archive/
    DeleteThreshold float64 `json:"archive_threshold"`
    
    // 每次清理检查的记忆数（默认 20）
    // 每次自动维护时只检查 N 条，避免性能问题
    BatchSize int `json:"batch_size"`
}
```

### 7.3 状态流转图

```
        创建
          │
          ▼
    ┌──────────┐    活跃期     ┌──────────┐
    │ 活跃记忆  │ ←────────→ │ 刚创建的  │
    │ 强度 ≥ 0.5│   强化/使用  │ 强度 1.0  │
    └─────┬────┘              └──────────┘
          │ 超过 N 天未访问
          ▼
    ┌──────────┐    衰减期
    │ 衰减记忆  │  ←──  强度持续下降
    │ 0.05~0.5 │
    └─────┬────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌──────────┐  ┌──────────────┐
│ 摘要化    │  │ 归档         │
│ 强度<0.15 │  │ 强度<0.05    │
│ 保留核心   │  │ 移入 archive/│
│ 丢弃细节   │  │ 索引中保留   │
│ 文件原地   │  │ git mv      │
└──────────┘  └──────────────┘
```

### 7.4 状态定义

```go
type MemoryState string

const (
    StateActive      MemoryState = "active"       // 活跃: 强度 ≥ 0.5
    StateDecaying    MemoryState = "decaying"     // 衰减: 0.05 ~ 0.5
    StateSummarized  MemoryState = "summarized"   // 摘要化: < 0.15, 已压缩
    StateArchived    MemoryState = "archived"     // 已归档: < 0.05, 移入 archive/
)
```

### 7.5 每种记忆的生命周期

#### 7.5.1 session —— 短期对话

```
创建（首次 AppendSession）
  │
  ├── 活跃期（当前对话中）
  │   ├── 上限 50 条消息
  │   ├── 超限 → 自动压缩（保留 20 条 + 摘要）
  │   └── 每次 Append 强化一次
  │
  ├── 静止 24h → 标记"已结束"
  │   └── 强度从 1.0 开始衰减
  │
  ├── 衰减 60 天
  │   ├── 如果期间被查询 → 强度回升（强化）
  │   └── 如果 60 天无人问津
  │       └── 摘要化：提取关键对话 → 转为 episode
  │       └── 原始 session 标记 "archived: true"
  │
  └── 强度 < 0.05 → 移入 archive/sessions/
```

#### 7.5.2 episode —— 中期经验

```
创建（任务完成时 SaveEpisode）
  │
  ├── 活跃期（前 7 天）
  │   ├── 强度 = 1.0
  │   └── Agent think 时可以检索
  │
  ├── 衰减期（7 ~ 30 天）
  │   ├── 每天 Decay()
  │   ├── 每次检索 → 强化
  │   └── 被关联命中 → 弱强化
  │
  ├── 摘要期（强度 < 0.15）
  │   ├── 保留 Learned 和 Task（核心）
  │   ├── 丢弃 Steps 和 Result（细节）
  │   └── 文件标注 "summarized: true"
  │
  └── 归档期（强度 < 0.05）
      ├── 移入 archive/episodes/
      └── 有 learned → 同步检查是否应提升为 knowledge
```

#### 7.5.3 knowledge —— 长期知识

```
写入
  │
  └── 永久保存
      ├── 不会衰减（强度锁定 1.0）
      ├── 不可自动删除
      ├── 发现更好方案时覆盖
      └── 旧版本在 git history 中可追溯
```

### 7.6 衰减执行的时机

Agent 不实时计算衰减（太耗），而是：

```go
// 1. 每次 Agent think 时
func (m *GitMemory) OnRecall(filepath string) {
    // 检索命中 → 强化
    m.reinforce(filepath, m.cfg.DirectHitReinforce)
    
    // 关联记忆 → 弱强化
    for _, assoc := range m.getAssociations(filepath) {
        m.reinforce(assoc, m.cfg.AssocHitReinforce)
    }
}

// 2. Brain 每天凌晨 3 点
func (m *GitMemory) DailyDecay() {
    // 对所有 episode 执行一次 Decay()
    // 不是实时衰减，是"批量快照"
    
    for _, ep := range m.ListEpisodes() {
        newStrength := ep.Strength - m.cfg.DailyDecay * (1 + daysSinceLastAccess * m.cfg.NeglectAccel)
        m.updateStrength(ep, max(0, newStrength))
        
        if newStrength < m.cfg.SummarizeThreshold {
            m.summarize(ep)
        }
        if newStrength < m.cfg.DeleteThreshold && len(ep.Associations) == 0 {
            m.delete(ep)
        }
    }
}

// 3. 手动也可以触发
```

### 7.7 Agent 回忆时的行为

```go
// Agent think 时从记忆库检索
func (m *GitMemory) Recall(query string, sceneTags []string) ([]MemoryItem, error) {
    // Step 1: 先用场景标签定位
    items := m.matchScene(sceneTags)
    
    // Step 2: 关键词搜索（过滤已衰减的）
    keywordHits := m.search(query)
    
    // Step 3: 联想扩展
    // 找到的每个结果 → 带上它的关联
    for _, item := range items {
        assocs := m.getAssociations(item.Path)
        items = append(items, assocs...)
    }
    
    // Step 4: 去重 + 按强度排序
    items = m.dedupe(items)
    sort.Slice(items, func(i, j int) bool {
        return items[i].Strength > items[j].Strength
    })
    
    // Step 5: 强化这些命中的记忆
    for _, item := range items {
        m.reinforce(item.Path, m.cfg.DirectHitReinforce)
        for _, assoc := range m.getAssociations(item.Path) {
            m.reinforce(assoc, m.cfg.AssocHitReinforce)
        }
    }
    
    // Step 6: 只返回强度 > 0.15 的（高于摘要阈值）
    var result []MemoryItem
    for _, item := range items {
        if item.Strength > 0.15 {
            result = append(result, item)
        }
    }
    
    return result, nil
}
```

### 7.8 联想：Agent 如何"触类旁通"

Agent think 时，除了回答问题，还可以**联想**：

```go
// Agent 回答完"检查 Windows 磁盘"后的联想
func (m *GitMemory) Associate(fromPath string) []MemoryItem {
    // 1. 找标签相同的
    tags := m.getTags(fromPath)
    sameTag := m.searchByTags(tags)
    
    // 2. 找时间相近的
    time := m.getTimestamp(fromPath)
    samePeriod := m.searchByTime(time.Add(-2*24*time.Hour), time.Add(2*24*time.Hour))
    
    // 3. 找 INDEX 中有交叉链接的
    crossLinks := m.getIndexCrossLinks(fromPath)
    
    return m.merge(sameTag, samePeriod, crossLinks)
}

// Agent 可以这样使用联想：
// "说到 Windows 磁盘..."
// → 联想到 Windows 上次出过什么问题
// → 联想到 GPU 检测也在 Windows 上
// → "对了，上次 GPU 检测 bug 还在，要不要一块修了？"
```

### 7.9 容量上限

| 指标 | 软上限 | 硬上限 | 超限处理 |
|------|:------:|:------:|---------|
| session 消息数 | 40条 | 50条 | 自动压缩 |
| session 文件数 | 100 | 200 | 压缩最旧的 |
| episode 文件数 | 500 | 1000 | 衰减 → 清理 |
| knowledge 文件数 | 200 | 500 | 合并相关主题 |
| 单文件大小 | 50KB | 100KB | 截断/压缩 |
| INDEX.md 大小 | — | 100KB | 自动清理低频标签 |
| 仓库总大小 | 50MB | 100MB | git gc + 衰减加速 |

### 7.1 状态图

```
                         永久保存
                         ┌──────────┐
                         │ knowledge │ ←── 手动/自动提升
                         └──────────┘
                              ↑
                              │ 有价值的经验
                              │
┌──────────┐  完成任务后   ┌──────────┐  30天后   ┌──────────────┐
│ 对话     │ ──────────→  │ episode  │ ──────→  │ 清理（或转为  │
│ session  │               │          │          │ knowledge）   │
└──────────┘              └──────────┘          └──────────────┘
     │                        ↑
     │ 对话压缩               │ 有价值的经验
     ▼                        │
┌──────────┐     session完成  │
│ 摘要保存  │ ────────────────┘
└──────────┘
```

### 7.2 session 生命周期

```
创建（首次 AppendSession）
  │
  ├── 活跃期（不断追加消息）
  │   ├── 上限 50 条消息
  │   └── 超限 → 自动压缩
  │         ├── 保留最近 20 条完整消息
  │         ├── 之前 30 条压缩为摘要
  │         └── 添加 Compacted 标记
  │
  ├── 静止期（24 小时无新消息）
  │   └── 标记为"已结束"
  │
  └── 归档
      └── 60 天后：压缩历史摘要
          保存为一条 episode
```

### 7.3 episode 生命周期

```
创建（任务完成时 SaveEpisode）
  │
  ├── 活跃期（30天内）
  │   └── Agent think 时可以检索
  │
  ├── 检查期（第30天）
  │   ├── 有 "learned" 且有价值 → 提升为 knowledge
  │   └── 无 "learned" 或 无价值 → 标记待清理
  │
  └── 清理（第31天）
      └── 从 episodes/ 目录删除
```

### 7.4 knowledge 生命周期

```
创建（多轮验证后 SaveKnowledge）
  │
  ├── 永久保存
  │   └── 不可自动删除
  │
  └── 更新
      └── 发现更好的方案时覆盖
          保留旧版本在 git history 中
```

### 7.5 容量限制

| 指标 | 软上限 | 硬上限 | 超限处理 |
|------|:------:|:------:|---------|
| session 消息数 | 40条 | 50条 | 自动压缩 |
| session 文件数 | 100 | 200 | 压缩最旧的 |
| episode 文件数 | 500 | 1000 | 清理最旧的 |
| knowledge 文件数 | 200 | 500 | 合并相关主题 |
| 单文件大小 | 50KB | 100KB | 截断/压缩 |
| 仓库总大小 | 50MB | 100MB | git gc + 清理 |
| 单个 content 字段 | 4KB | 8KB | 截断 |

---

## 8. Agent 集成规范

### 8.1 注入点

```go
// agent.go 中创建 Agent 时注入 memory
func NewAgent(llm *composer.LLMClient, tools *ToolRegistry, memory Memory) *Agent {
    return &Agent{
        llm:    llm,
        tools:  tools,
        memory: memory,   // ← 注入
    }
}
```

### 8.2 调用时序

```
Agent.Think():
  1. Load memory context into system prompt
     ├── ListRecentEpisodes(5) → 最近 5 条经验
     ├── GetSystemStatus() → 集群状态
     └── SearchKnowledge(task关键词) → 相关知识
     
  2. LLM 生成计划
     └── AppendSession(req.SessionID, "user", req.Task)
     └── AppendSession(req.SessionID, "agent (thought)", thought)
  
  3. 逐步执行计划
     └── 每一步执行: AppendSession(sessionID, "action", step_log)
  
  4. 汇总结果
     └── AppendSession(sessionID, "agent (result)", result)
     
  5. 记录经验
     └── SaveEpisode(task, result, success, learned)
     
  6. 立即 commit
     └── Commit("episode: analyze-logs (✅)")
```

### 8.3 系统提示注入格式

每次 think 时，在 system prompt 末尾追加：

```markdown
## 记忆上下文

### 最近经验
- ✅ 2026-05-31: 分析三台服务器日志（发现 15 个异常）
- ❌ 2026-05-30: Windows 日志搜索（findstr 不支持预查）
- ✅ 2026-05-30: 磁盘清理（释放 3.4GB）

### 当前集群状态
- Nodes: 3 online, 0 offline
- Queue: 0 pending, 0 running
- Memory: 12.5%

### 相关知识
- knowledge/windows-gpu-detection.md: Windows GPU 检测 WMI 方法
- knowledge/windows-log-search.md: 推荐用 Select-String
```

### 8.4 经验提升为知识的触发条件

Agent 在以下情况自动考虑提升：

```go
// Agent 检查是否应将 episode 提升为 knowledge
func shouldPromoteToKnowledge(ep EpisodeSummary) bool {
    // 条件1: 有 learned 内容
    if ep.Learned == "" {
        return false
    }
    
    // 条件2: learned 超过 20 字
    if len(ep.Learned) < 20 {
        return false
    }
    
    // 条件3: 该知识不在现有 knowledge 中
    // （通过 git grep 检查）
    
    return true
}
```

### 8.5 Brain 集成点

```go
// brain.go
func (b *Brain) heartbeatMemoryMaintenance() {
    // 每 5 分钟
    b.memory.AutoCommit()
    
    // 每天凌晨 3 点
    b.memory.CleanOldEpisodes()
    b.memory.runGC()
}
```

---

## 9. 错误闭环规范

### 9.1 核心理念

> **任何错误都不是终点，而是标准化的起点。**

错误闭环的完整链路：

```
┌──────────────────────────────────────────────────────────────────┐
│                   错误发生                                        │
│                       │                                          │
│                       ▼                                          │
│   ┌─────────────────────────────────────┐                       │
│   │ 1. 记录错误                         │  ← 自动写入 episode   │
│   │    - 什么错了（错误类型、堆栈）       │    文件               │
│   │    - 在哪错了（代码位置、触发场景）   │                       │
│   │    - 影响范围（功能/数据影响）        │                       │
│   └──────────────┬──────────────────────┘                       │
│                  │                                               │
│                  ▼                                               │
│   ┌─────────────────────────────────────┐                       │
│   │ 2. 分析根因                         │  ← Agent 自动分析     │
│   │    - 是代码 bug？还是环境问题？       │    或人工排查          │
│   │    - 是偶发还是必现？                 │                       │
│   │    - 根本原因是什么？                │                       │
│   └──────────────┬──────────────────────┘                       │
│                  │                                               │
│                  ▼                                               │
│   ┌─────────────────────────────────────┐                       │
│   │ 3. 修复问题                         │  ← 修复代码/配置       │
│   │    - 短期修复（止血）                 │                       │
│   │    - 长期修复（根治）                 │                       │
│   └──────────────┬──────────────────────┘                       │
│                  │                                               │
│                  ▼                                               │
│   ┌─────────────────────────────────────┐                       │
│   │ 4. 形成标准                         │  ← 写入 knowledge     │
│   │    - 更新规范文档                    │    或规范              │
│   │    - 添加自动化检测                  │                       │
│   │    - 防止同类问题再发生              │                       │
│   └──────────────┬──────────────────────┘                       │
│                  │                                               │
│                  ▼                                               │
│   ┌─────────────────────────────────────┐                       │
│   │ 5. 沉淀为知识                       │  ← 写入 knowledge      │
│   │    - 验证后的解决方案                │    经验永久保存         │
│   │    - 关联的 episode 引用             │                       │
│   │    - 可被未来 Agent 检索             │                       │
│   └─────────────────────────────────────┘                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
   下次遇到同类错误 → 直接查到 knowledge
   → 秒级修复，不再走全流程
```

### 9.2 错误分类与处理流程

| 等级 | 标签 | 定义 | 处理流程 | 响应时间 |
|:----:|:----:|------|---------|:--------:|
| 🔴 **致命** | `critical` | 记忆仓库损坏、数据丢失、Agent 无法启动 | 立即修复 → 1h 内形成标准 | 15分钟 |
| 🟡 **严重** | `error` | 单条数据写入失败、Git 命令异常、搜索不准 | 自动修复 → 1天内形成标准 | 2小时 |
| 🟢 **一般** | `warning` | 压缩失败、超时、格式异常 | 下次维护时修复 → 1周内形成标准 | 下次维护 |
| ⚪ **提示** | `info` | 尝试写入敏感内容（被白名单拦截）、文件已存在 | 记录即可，无需修复 | 不要求 |

### 9.3 错误记录规范（Error Episode）

每次错误闭环后，**必须**生成一条带 `error` 标签的 episode 文件：

```markdown
# Episode: [ERROR] 记忆仓库 Git 损坏修复
> Type: episode
> Tags: error, recovery, memory
> Date: 2026-05-31
> Error: 🔴 critical
> Success: ✅
> Duration: 12min

## Error
Git 仓库在 `Init()` 阶段发现 `.git/HEAD` 损坏。
原因：Agent 被 `kill -9` 中断，导致 git write 半完成。

## Impact
- Agent 启动失败
- 记忆系统不可用
- 所有未提交的对话丢失

## Root Cause
`kill -9` 不会触发 Go 的 defer cleanup，
导致文件写入时被中断，git ref 处于不一致状态。

## Fix
短期修复（1min）：`git checkout HEAD` 恢复 HEAD 引用
长期修复（1天）：memory 增加启动完整性检查：

```go
func (gm *GitMemory) verify() error {
    out, err := gm.git("fsck")
    if err != nil {
        // 尝试自动修复
        gm.git("checkout", "HEAD")
        return fmt.Errorf("repository corrupted, auto-recovered: %s", out)
    }
    return nil
}
```

## Standard Generated
- `SPEC-MEMORY-001.md` 第 X 节：增加启动完整性检查规范
- 所有 `git()` 调用增加 defer 恢复机制
- 关键写入操作增加 WAL（Write-Ahead Log）模式

## Learned
- `kill -9` 在任何文件写入系统中都是危险的。
- 记忆系统启动时必须做 `git fsck` 完整性检查。
- `defer` 不能依赖，信号处理要单独做。

## Related Knowledge
- knowledge/git-memory-crash-recovery.md
- knowledge/agent-signal-handling.md
```

### 9.4 错误闭环必须遵守的规则

#### 规则1：先止血，再找根因

```
❌ 错误："Git 仓库损坏，Agent 启动失败"
   → 花 30 分钟分析根因，没先恢复

✅ 错误同上：
   → 1分钟：git checkout HEAD 恢复 → Agent 能启动了
   → 然后：分析 kill -9 的根因
   → 最后：写标准防止再发生
```

所有 memory 操作必须内置 "safe mode" —— 出错了不影响 Agent 主体运行：

```go
// AppendSession 必须保证错误不影响 Agent
func (gm *GitMemory) AppendSession(...) error {
    // 1. 尝试写入
    err := gm.writeSessionFile(...)
    if err != nil {
        // 2. 记录错误到日志（绝不 panic）
        log.Printf("[Memory] AppendSession failed: %v", err)
        // 3. 走 error episode 闭环
        gm.triggerErrorEpisode("AppendSession failed", err)
        // 4. 返回错误但不影响调用者
        return err  // 调用者（Agent）可以继续运行
    }
    return nil
}
```

#### 规则2：每条 error episode 必须有对应的标准产出

```go
// 验证 error episode 的完整性
func validateErrorEpisode(content string) error {
    required := []string{"## Error", "## Root Cause", "## Fix", "## Standard Generated", "## Learned"}
    for _, section := range required {
        if !strings.Contains(content, section) {
            return fmt.Errorf("error episode missing section: %s", section)
        }
    }
    return nil
}
```

#### 规则3：同类错误只走一次全流程

```
第一次遇到 "git commit failed: permission denied":
  1. 记录 error episode
  2. 分析：记忆仓库被其他进程锁了
  3. 修复：增加重试 + 超时
  4. 形成 standard：memory 操作加锁时设置 5s 超时

第二次遇到同样错误：
  → Agent 直接搜 knowledge 查到解决方案
  → 秒级处理，不再走完整闭环
  → 但可以补充一条"验证"到原有 knowledge
```

#### 规则4：无法自动修复的，主动汇报

```go
// 某些错误 Agent 自己搞不定，必须通知老大
func (gm *GitMemory) handleUnrecoverable(err error) {
    // 1. 写 error episode（记录现场）
    gm.SaveEpisode(
        "[ERROR] 记忆系统不可恢复",
        fmt.Sprintf("Error: %v\nStack: %s", err, debug.Stack()),
        false,
        "需要人工介入",
    )
    
    // 2. 立即 commit（保留现场）
    gm.Commit("error: 记忆系统不可恢复，需要人工介入")
    
    // 3. 通知
    // （后续集成邮件/事件通知系统后自动发信）
}
```

需要人工介入的场景：
- 磁盘空间不足，无法写入
- `.git` 目录被误删
- 文件系统只读

### 9.5 错误自动发现机制

Agent 在以下阶段自动检查错误：

```go
// 启动时
func (gm *GitMemory) Init() error {
    // 检查上次是否有未完成的错误闭环
    pending, _ := gm.SearchEpisodes("tag:error AND NOT closed", 1)
    if len(pending) > 0 {
        log.Printf("[Memory] ⚠️ 发现上次未完成的错误闭环: %s", pending[0].Title)
        // 尝试继续闭环（重新修复）
    }
    
    // 完整性检查
    return gm.verify()
}

// 每次心跳
func (gm *GitMemory) heartbeat() {
    // 检查是否有新错误
    recentErrors, _ := gm.SearchEpisodes("type:error AND success:false", 5)
    for _, err := range recentErrors {
        // 尝试自动修复
        // 如果失败，标记为 unrecoverable
    }
}
```

### 9.6 错误闭环的 episode 标签规范

所有错误相关的 episode 必须包含以下标签（文件头部的 Tags 字段）：

| 标签 | 含义 | 使用场景 |
|------|------|---------|
| `error` | 错误记录 | 所有错误 episode 必须加 |
| `recovery` | 恢复操作 | 自动/手动恢复后 |
| `critical` | 致命错误 | 系统级故障 |
| `bug` | 代码缺陷 | 明确代码 bug |
| `config` | 配置问题 | 配置错误导致 |
| `network` | 网络异常 | API 超时/断网 |
| `disk` | 存储问题 | 磁盘满/IO 错误 |
| `permission` | 权限问题 | 文件权限/API 鉴权 |
| `closed` | 闭环完成 | 该错误已闭环为标准 |

### 9.7 知识沉淀

当一个 error episode 闭环完成后，Agent 自动提取关键内容存入 knowledge：

```go
// error episode → knowledge 的提升规则
func promoteErrorToKnowledge(ep EpisodeSummary) bool {
    // 条件1：错误已闭环（有 Standard Generated 章节）
    // 条件2：解决方案已验证（Success == true）
    // 条件3：不是偶发问题（不是一次性环境问题）
    if !strings.Contains(ep.Learned, "Standard Generated") {
        return false
    }
    return true
}
```

knowledge 文件命名：
```
memory-error-{问题主题}.md
```

示例：
- `memory-error-crash-recovery.md` — 崩溃恢复知识
- `memory-error-git-lock.md` — Git 文件锁处理
- `memory-error-disk-full.md` — 磁盘满恢复策略

### 9.8 示例：完整闭环流程

```
场景：AppendSession 时 git commit 返回 "permission denied"

Step 1 — 实时记录（Agent 自动）
  → SaveEpisode("[ERROR] git commit permission denied", ...)
  → 写入 episodes/2026-05-31-error-git-commit-permission-denied.md
  → 记录现场：pid、文件路径、git stderr

Step 2 — 自动修复（Agent 自动）
  → 尝试重试（指数退避，3次）
  → 如果重试成功 → episode 标记 success = true
  → 如果重试失败 → 标记 unrecoverable，保留现场

Step 3 — 分析根因（Agent 自动或人工）
  → 发现：另一个 Agent 实例占用了 .git/index.lock
  → 根因：没有单例保证

Step 4 — 修复 + 标准
  → Fix: git 操作前检查 lock 文件，等待 5s 后重试
  → Standard: 新增到 SPEC-MEMORY-001 第 X 节
  → 添加自动化检测：启动时检查是否有残留 lock 文件

Step 5 — 知识沉淀（Agent 自动）
  → 提升为 knowledge/memory-error-git-lock.md
  → 下次遇到同样的 "permission denied" 错误
  → Agent 直接查 knowledge → 秒级修复

Step 6 — 闭环标记
  → 原 error episode 的 Tags 追加 "closed"
  → 关联 knowledge 文件路径
  → 整个过程在 git log 中完全可追溯
```

### 9.9 错误闭环的 KPI

| 指标 | 目标 | 触发 | 
|------|:----:|------|
| 错误闭环率 | ≥ 95% | 所有记录的错误必须在 7 天内闭环 |
| 平均闭环时间 | ≤ 2 小时 | 从错误发生到标准形成 |
| 同类错误复现率 | ≤ 5% | 闭环后同一原因的错误不再发生 |
| knowledge 覆盖率 | ≥ 80% | 可自动修复的错误必须有 knowledge |

---

## 10. 安全规范

### 10.1 禁止存储的内容

以下内容**严禁**写入记忆仓库：
1. API Key、Token、密码等凭据
2. 个人隐私信息（身份证、手机号等）
3. 超过 8KB 的大段原始数据（应引用文件路径）

### 10.2 写入白名单

`content` 参数在写入前必须通过过滤器：

```go
func sanitize(content string) (string, error) {
    // 1. 检查大小
    if len(content) > 8192 {
        content = content[:8192] + "\n... (truncated)"
    }
    
    // 2. 检查敏感信息
    patterns := []string{
        `sk-[a-zA-Z0-9]{20,}`,    // API Key
        `Bearer [a-zA-Z0-9]+`,    // Token
        `password[=:]\s*\S+`,     // 密码
    }
    for _, p := range patterns {
        // 用正则替换为 [REDACTED]
    }
    
    return content, nil
}
```

### 10.3 并发安全

Memory 实现必须是并发安全的（goroutine-safe）：
```go
type GitMemory struct {
    mu     sync.Mutex    // 保护所有写入操作
    dirty  bool
    // ...
}
```

### 9.4 启动时的验证

Agent 启动时必须验证记忆仓库完整性：
```go
func (gm *GitMemory) Init() error {
    // 1. 检查 .git 是否存在
    // 2. git fsck 验证仓库完整性
    // 3. 检查目录结构是否完整
    // 4. 如果损坏 → 自动重建（保留现有文件）
}
```

---

## 10. 附录：参考实现

### 10.1 文件位置

```
OPC/
├── src/agent/
│   ├── agent.go          ← 注入 Memory（改动约 20 行）
│   ├── memory.go         ← 新增：Memory 接口 + GitMemory 实现（约 435 行）
│   ├── memory_test.go    ← 新增：测试（约 150 行）
│   ├── tools.go          ← 不改
│   └── planner.go        ← 不改
│
├── docs/
│   └── SPEC-MEMORY-001_Git记忆系统设计规范.md  ← 本文件
```

### 10.2 代码量预估（纯新增）

| 文件 | 行数 | 说明 |
|------|:----:|------|
| `memory.go` | ~435 | 接口 + GitMemory 完整实现 |
| `memory_test.go` | ~150 | 测试仓库操作全流程 |
| `agent.go` 改动 | ~30 | 注入 + 调用的改动 |
| **新增合计** | **~585** | |

### 10.3 依赖

```
内存: ~1MB（仓库文件映射）
磁盘: ~50MB（最大仓库限制）
外部命令: git（系统预装）
编译依赖: 无（纯 Go 标准库）
```

### 10.4 测试策略

```go
func TestGitMemory(t *testing.T) {
    // 1. 初始化测试仓库（临时目录）
    root := t.TempDir()
    mem, _ := NewGitMemory(root)
    
    // 2. 测试 Init
    assert.FileExists(root + "/.git")
    assert.FileExists(root + "/sessions/")
    assert.FileExists(root + "/README.md")
    
    // 3. 测试 AppendSession 和 GetSession
    mem.AppendSession("test-001", "User", "你好")
    session, _ := mem.GetSession("test-001")
    assert.Contains(session, "你好")
    
    // 4. 测试 SaveEpisode 和 Search
    mem.SaveEpisode("测试任务", "成功", true, "学到了")
    results, _ := mem.SearchEpisodes("测试", 10)
    assert.Len(results, 1)
    
    // 5. 测试 Commit 和 History
    mem.AutoCommit()
    history, _ := mem.History(10)
    assert.Len(history, 1)
    
    // 6. 测试 Stats
    stats, _ := mem.Stats()
    assert.Equal(1, stats.EpisodeCount)
    assert.Equal(1, stats.TotalCommits)
}
```

---

## 规范版本记录

| 版本 | 日期 | 修改内容 | 作者 |
|:----:|:----:|---------|:----:|
| v1.0 | 2026-05-31 | 初始版本，完整规范 | 小智 |
| v1.1 | 2026-05-31 | 增加人类记忆模型（时间轴/联想/衰减强化/场景回忆），重写数据生命周期规范，增加 INDEX.md 关联网络 | 小智 |

---

> **本规范定稿后，memory.go 的实现必须严格遵循此规范。**
> **任何对规范的偏离都必须更新此文档后再实现。**
