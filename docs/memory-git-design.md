# OPC Git 记忆系统设计

> v1.0 | 2026-05-31 | 基于现有 workspace memory 模式
> 目标：让 Agent 不再"每次都是白纸"

---

## 一、设计理念

### 为什么用 Git？

| 需求 | Git 方案 | 比文件/数据库好在哪里 |
|------|----------|---------------------|
| 版本追溯 | `git log` | 天然就有，不用自己实现 |
| 搜索历史 | `git grep` + `git log -S` | 全文搜索，支持正则 |
| 回滚误操作 | `git revert` | 恢复任意历史状态 |
| 多 Agent 共享 | `git pull/push` | Gateway ⇄ Worker 自动同步 |
| 灾难恢复 | 仓库随便 clone | 丢失了从另一节点恢复 |
| 可视化 | 任何 Git GUI | 直接看 commit 历史就知道 Agent 做过什么 |

### 数据分类

```
记忆按"衰减速度"分为三类：
  ┌─────────────────────────────────────────────┐
  │ 短期记忆 (Session)      留存: 对话期间       │
  │  Agent 和用户/Worker 的对话上下文            │
  │  50条以内，超出后压缩摘要                     │
  ├─────────────────────────────────────────────┤
  │ 中期记忆 (Episodes)     留存: 30 天          │
  │  Agent 执行过的任务 + 结果 + 学到的经验        │
  │  自动清理旧记录，只保留"有价值"的              │
  ├─────────────────────────────────────────────┤
  │ 长期记忆 (Knowledge)    留存: 永久            │
  │  技能定义、系统配置、反复验证的知识             │
  │  Agent 自己总结的"经验教训"                   │
  └─────────────────────────────────────────────┘
```

---

## 二、存储结构

### 目录布局

```
<memory_root>/                  ← Git 仓库根目录（默认: /home/computehub/opc-memory/）
├── sessions/                    ← 短期记忆：对话记录
│   ├── session-abc123.md        ← 单个 session 的完整对话
│   ├── session-def456.md
│   └── ...
│
├── episodes/                    ← 中期记忆：做过的事、学到的经验
│   ├── 2026-05-31-analyze-logs.md
│   ├── 2026-05-31-fix-disk-space.md
│   └── ...
│
├── knowledge/                   ← 长期记忆：验证过的知识
│   ├── gpu-detection-windows.md
│   ├── schtasks-tips.md
│   └── ...
│
├── system/                      ← 系统当前状态快照（每次心跳更新）
│   ├── cluster-status.md        ← 节点列表 + 健康状态
│   ├── agent-config.md          ← Agent 当前配置
│   └── task-queue.md            ← 队列状态
│
└── INDEX.md                     ← 自动生成的搜索索引
```

### 文件名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| Session | `session-{8位短ID}.md` | `session-a1b2c3d4.md` |
| Episode | `{YYYY-MM-DD}-{动作描述}.md` | `2026-05-31-analyze-server-logs.md` |
| Knowledge | `{主题-简短}.md` | `windows-gpu-detection.md` |
| System | `{name}.md` | `cluster-status.md` |

### 文件内容格式

**Session 文件**（示例）：
```markdown
# Session: session-a1b2c3d4
> Created: 2026-05-31 14:30:22
> Last Updated: 2026-05-31 14:35:10

## Context
- User: 老大 (TUI)
- Node: ecs-p2ph
- Task: 分析服务器日志

## 14:30:22 — User
帮我分析一下所有节点的日志，看看有没有异常

## 14:30:23 — Assistant (thought)
需要先收集各节点日志，然后用 LLM 分析。

## 14:30:24 — Action: exec_shell
```
Node: ecs-p2ph
Command: grep -i error /var/log/syslog | tail -50
```
→ ✅ 完成 (0.3s) 输出 12 行...

## 14:30:25 — Action: exec_shell
```
Node: windows-mobile
Command: findstr /i "error" C:\var\log\*.log
```
→ ✅ 完成 (0.8s) 输出 3 行...

## 14:31:00 — Assistant (result)
分析完成！发现 15 个异常，其中 3 个需要关注：
1. ecs-p2ph: OOM killer 在 05:30 触发了一次...
```

**Episode 文件**（示例）：
```markdown
# Episode: Fix Disk Space — 2026-05-31
> Type: auto_recovery
> Trigger: disk > 80% threshold
> Success: ✅

## What Happened
Agent 发现 ecs-p2ph 磁盘使用率 83%
→ 自动执行了 /tmp 清理释放 2.3GB
→ 执行 `docker system prune` 释放 1.1GB
→ 总计释放 3.4GB，使用率降到 72%

## Learned
- `/tmp` 是最大的可回收空间来源
- Docker 镜像缓存经常被忽略
- 应该每周自动执行一次清理

## Action Item
- [ ] 创建一个定时技能：每周日凌晨3点自动清理 /tmp 和 docker 缓存
```

**Knowledge 文件**（示例）：
```markdown
# Knowledge: Windows GPU Detection via WMI
> Verified: 2026-05-30
> Author: Agent (auto-discovery)

## Problem
Windows 节点无法通过 nvidia-smi 检测 GPU，需要 WMI 回退。

## Solution
使用 `Get-WmiObject Win32_VideoController` 命令，
但不能通过 `cmd /c` 中转（会导致输出混入命令本身），
必须直接 `exec.Command("powershell", "-Command", psCmd)`。

## Verification
Windows-mobile 节点成功检测到 "Microsoft Basic Display Adapter"
（非英伟达卡，WMI 回退正常工作）

## Related Files
- src/workercmd/worker_util_windows.go:45-78
```

---

## 三、Memory API 设计

### Go 接口

```go
// Memory 记忆系统接口
type Memory interface {
    // ── 短期记忆：对话 ──

    // AppendSession 追加一条对话记录
    // 自动处理 session 创建/追加/超限压缩
    AppendSession(sessionID string, role string, content string) error

    // GetSession 获取完整对话历史
    GetSession(sessionID string, maxLines int) (string, error)

    // GetRecentSessions 获取最近的 session 摘要列表
    GetRecentSessions(limit int) ([]SessionSummary, error)

    // SummarizeSession 压缩长对话为摘要
    SummarizeSession(sessionID string) error


    // ── 中期记忆：经验 ──

    // SaveEpisode 记录一次执行经验
    SaveEpisode(task string, result string, success bool, learned string) error

    // SearchEpisodes 搜索相关经验（关键词匹配）
    SearchEpisodes(query string, limit int) ([]Episode, error)

    // GetRecentEpisodes 获取最近的经验
    GetRecentEpisodes(limit int) ([]Episode, error)

    // CleanOldEpisodes 清理 30 天前的旧记录
    CleanOldEpisodes() error


    // ── 长期记忆：知识 ──

    // SaveKnowledge 保存一条知识
    SaveKnowledge(topic string, content string) error

    // SearchKnowledge 搜索知识库
    SearchKnowledge(query string, limit int) ([]KnowledgeEntry, error)


    // ── Agent 系统状态 ──

    // UpdateSystemStatus 更新集群状态快照
    UpdateSystemStatus(statusJSON string) error

    // GetSystemStatus 读取系统状态
    GetSystemStatus() (string, error)


    // ── Git 操作 ──

    // Commit 提交当前改动（自动写 commit message）
    Commit(message string) error

    // GetHistory 查看历史 commit 列表
    GetHistory(limit int) ([]CommitInfo, error)

    // Diff 查看某次 commit 的改动
    Diff(commitHash string) (string, error)

    // Sync 同步到远程仓库（可选）
    // Sync() error


    // ── 维护 ──

    // Init 初始化仓库（如果不存在则 git init）
    Init() error

    // Compact 压缩/整理记忆库
    Compact() error

    // Stats 返回记忆统计信息
    Stats() (*MemoryStats, error)
}

type SessionSummary struct {
    ID        string    `json:"id"`
    CreatedAt time.Time `json:"created_at"`
    MessageCount int    `json:"message_count"`
    Summary   string    `json:"summary"`
}

type Episode struct {
    ID        string    `json:"id"`
    Date      string    `json:"date"`
    Task      string    `json:"task"`
    Result    string    `json:"result"`
    Success   bool      `json:"success"`
    Learned   string    `json:"learned"`
}

type KnowledgeEntry struct {
    Topic    string `json:"topic"`
    Content  string `json:"content"`
    Verified string `json:"verified"`
}

type MemoryStats struct {
    SessionCount  int   `json:"session_count"`
    EpisodeCount  int   `json:"episode_count"`
    KnowledgeCount int  `json:"knowledge_count"`
    TotalCommits  int   `json:"total_commits"`
    RepoSize      string `json:"repo_size"`  // 友好显示 "1.2MB"
}
```

### 关键行为设计

#### 1. 自动 commit 策略

```
不是每次 AppendSession 都 commit，而是：
- 每 5 分钟自动 commit一次（如果 5min 内有改动）
- 每次重要的 Action 完成后立即 commit
- "重要"的定义：任务完成 / Episode 记录 / 知识更新
- commit message 格式: "[session|episode|knowledge|system] 简短描述"
```

#### 2. 对话压缩策略

```
当 session 超过 50 条消息：
1. Agent 调 LLM 将前半部分压缩为摘要
2. 用摘要替换前半部分
3. 保留最近 20 条完整消息 + 摘要
4. commit 记录这个压缩操作

示例：
Before: session-a1b2.md (80 条消息，~12KB)
After:  session-a1b2.md (22 条消息 + 1 段摘要，~4KB)
```

#### 3. 记忆检索策略

```
Agent 每次开始 think 时：
1. 读取最近 10 个 Episode（了解最近做过什么）
2. 读取当前系统状态
3. 可选：根据当前任务关键词搜索 Knowledge
4. 全部注入到 LLM 系统提示中

这样 Agent 就知道：
- "上周刚修过 GPU 检测"
- "Windows 更新有 3 个已知坑"
- "磁盘清理策略之前优化过"
```

---

## 四、代码实现

### 文件结构

```
src/agent/
├── agent.go       ← 已有：Agent 主逻辑（注入 Memory）
├── memory.go      ← 新增：Memory 接口定义 + Git 实现
├── memory_test.go ← 新增：测试
├── tools.go       ← 已有：工具注册表
├── planner.go     ← 已有：计划生成
└── brain.go       ← 已有（骨架）：注入 Memory
```

### memory.go 核心实现

```go
package agent

import (
    "bytes"
    "fmt"
    "os"
    "os/exec"
    "path/filepath"
    "strings"
    "sync"
    "time"
)

// GitMemory Git 驱动的记忆系统
type GitMemory struct {
    root   string       // 仓库根目录
    mu     sync.Mutex
    dirty  bool         // 是否有未提交的改动
    lastCommit time.Time
}

// NewGitMemory 创建/初始化记忆仓库
func NewGitMemory(root string) (*GitMemory, error) {
    if root == "" {
        root = "/home/computehub/opc-memory"
    }
    gm := &GitMemory{
        root:       root,
        lastCommit: time.Now(),
    }
    if err := gm.Init(); err != nil {
        return nil, fmt.Errorf("init memory: %w", err)
    }
    return gm, nil
}

// Init 初始化 Git 仓库
func (gm *GitMemory) Init() error {
    // 1. 创建目录
    dirs := []string{
        filepath.Join(gm.root, "sessions"),
        filepath.Join(gm.root, "episodes"),
        filepath.Join(gm.root, "knowledge"),
        filepath.Join(gm.root, "system"),
    }
    for _, d := range dirs {
        os.MkdirAll(d, 0755)
    }

    // 2. 检查是否已初始化
    if _, err := os.Stat(filepath.Join(gm.root, ".git")); err == nil {
        return nil // 已初始化
    }

    // 3. git init
    if out, err := gm.git("init"); err != nil {
        return fmt.Errorf("git init: %s: %w", out, err)
    }

    // 4. 写个 README
    readme := "# OPC Agent Memory\n"
    readme += "> Auto-managed by ComputeHub Agent\n\n"
    readme += "## Directory Structure\n"
    readme += "- sessions/ — Conversation history\n"
    readme += "- episodes/ — Task execution records\n"
    readme += "- knowledge/ — Verified knowledge\n"
    readme += "- system/ — System state snapshots\n"
    os.WriteFile(filepath.Join(gm.root, "README.md"), []byte(readme), 0644)

    // 5. 创建 .gitignore
    os.WriteFile(filepath.Join(gm.root, ".gitignore"), []byte("# OPC Memory\n*.swp\n*.tmp\n"), 0644)

    // 6. 首次提交
    gm.git("add", "-A")
    gm.git("commit", "-m", "init: OPC Agent Memory repository")

    return nil
}

// AppendSession 追加对话记录
func (gm *GitMemory) AppendSession(sessionID, role, content string) error {
    gm.mu.Lock()
    defer gm.mu.Unlock()

    path := filepath.Join(gm.root, "sessions", sessionID+".md")
    
    // 如果文件不存在，创建 header
    if _, err := os.Stat(path); os.IsNotExist(err) {
        header := fmt.Sprintf("# Session: %s\n> Created: %s\n\n", sessionID, time.Now().Format("2006-01-02 15:04:05"))
        os.WriteFile(path, []byte(header), 0644)
    }

    // 追加内容
    now := time.Now().Format("15:04:05")
    entry := fmt.Sprintf("\n## %s — %s\n%s\n\n", now, role, content)
    
    f, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0644)
    if err != nil {
        return fmt.Errorf("append session: %w", err)
    }
    defer f.Close()
    
    if _, err := f.WriteString(entry); err != nil {
        return fmt.Errorf("write session: %w", err)
    }

    gm.dirty = true
    return nil
}

// SaveEpisode 记录经验
func (gm *GitMemory) SaveEpisode(task, result string, success bool, learned string) error {
    gm.mu.Lock()
    defer gm.mu.Unlock()

    // 文件名用日期 + 简短动作
    slug := slugify(task[:min(len(task), 40)])
    path := filepath.Join(gm.root, "episodes", 
        fmt.Sprintf("%s-%s.md", time.Now().Format("2006-01-02"), slug))
    
    icon := "✅"
    if !success { icon = "❌" }

    content := fmt.Sprintf(`# Episode: %s
> Date: %s
> Success: %s

## Task
%s

## Result
%s

## Learned
%s
`, task, time.Now().Format("2006-01-02 15:04:05"), icon, task, result, learned)

    if err := os.WriteFile(path, []byte(content), 0644); err != nil {
        return fmt.Errorf("save episode: %w", err)
    }

    gm.dirty = true
    
    // 重要事件立即提交
    return gm.Commit(fmt.Sprintf("episode: %s (%s)", slug, icon))
}

// SearchEpisodes 在 episodes 中搜索
func (gm *GitMemory) SearchEpisodes(query string, limit int) ([]Episode, error) {
    if limit <= 0 { limit = 10 }

    // 用 git grep 搜索
    out, err := gm.git("grep", "-l", "-i", query, "--", "episodes/")
    if err != nil {
        // No matches
        return nil, nil
    }

    files := strings.Split(strings.TrimSpace(out), "\n")
    if len(files) > limit {
        files = files[:limit]
    }

    var episodes []Episode
    for _, file := range files {
        data, _ := os.ReadFile(filepath.Join(gm.root, file))
        episodes = append(episodes, Episode{
            ID:    file,
            Task:  extractTitle(string(data)),
        })
    }
    return episodes, nil
}

// Commit 提交当前改动
func (gm *GitMemory) Commit(message string) error {
    if !gm.dirty { return nil }

    gm.git("add", "-A")
    out, err := gm.git("commit", "-m", message)
    if err != nil {
        return fmt.Errorf("commit: %s: %w", out, err)
    }
    gm.dirty = false
    gm.lastCommit = time.Now()
    return nil
}

// AutoCommit 自动提交（供定时器调用）
func (gm *GitMemory) AutoCommit() error {
    if !gm.dirty { return nil }
    return gm.Commit(fmt.Sprintf("auto: memory update at %s", 
        time.Now().Format("2006-01-02 15:04")))
}

// Stats 记忆统计
func (gm *GitMemory) Stats() (*MemoryStats, error) {
    stats := &MemoryStats{}

    // 计数
    sessions, _ := filepath.Glob(filepath.Join(gm.root, "sessions", "*.md"))
    episodes, _ := filepath.Glob(filepath.Join(gm.root, "episodes", "*.md"))
    knowledge, _ := filepath.Glob(filepath.Join(gm.root, "knowledge", "*.md"))
    stats.SessionCount = len(sessions)
    stats.EpisodeCount = len(episodes)
    stats.KnowledgeCount = len(knowledge)

    // commit 数
    out, _ := gm.git("rev-list", "--count", "HEAD")
    fmt.Sscanf(out, "%d", &stats.TotalCommits)

    // 仓库大小
    out, _ = gm.git("count-objects", "-H")
    stats.RepoSize = strings.TrimSpace(out)

    return stats, nil
}

// ── Git 命令执行 ──
func (gm *GitMemory) git(args ...string) (string, error) {
    cmd := exec.Command("git", args...)
    cmd.Dir = gm.root
    var stdout, stderr bytes.Buffer
    cmd.Stdout = &stdout
    cmd.Stderr = &stderr
    err := cmd.Run()
    if err != nil {
        return stderr.String(), fmt.Errorf("git %s: %v", strings.Join(args, " "), err)
    }
    return stdout.String(), nil
}
```

### 代码量预估

| 函数 | 行数 | 复杂度 |
|------|:----:|:------:|
| NewGitMemory + Init | ~50 | 低 |
| AppendSession | ~40 | 低 |
| GetSession | ~15 | 低 |
| SummarizeSession | ~40 | 中（调LLM） |
| SaveEpisode | ~35 | 低 |
| SearchEpisodes | ~35 | 低 |
| SaveKnowledge | ~25 | 低 |
| SearchKnowledge | ~30 | 低 |
| UpdateSystemStatus | ~20 | 低 |
| Commit / AutoCommit | ~30 | 低 |
| GetHistory / Diff | ~25 | 低 |
| Compact | ~40 | 中 |
| Stats | ~30 | 低 |
| git() 工具函数 | ~20 | 低 |
| **合计** | **~435** | **大部分简单** |

---

## 五、集成到 Agent

### Agent 启动时加载记忆

```go
// agent.go
type Agent struct {
    llm      *composer.LLMClient
    tools    *ToolRegistry
    memory   *GitMemory         // ← 新增
    kernel   kernelProvider
    nodes    nodeProvider
    sessions map[string][]composer.ChatMessage
}

func NewAgent(llm *composer.LLMClient, tools *ToolRegistry, memoryRoot string) *Agent {
    // ...
    gm, _ := NewGitMemory(memoryRoot)
    return &Agent{
        llm:      llm,
        tools:    tools,
        memory:   gm,
        sessions: make(map[string][]composer.ChatMessage),
    }
}
```

### Agent think 时注入记忆上下文

```go
// buildSystemPrompt 中注入记忆
func (a *Agent) buildSystemPrompt(req *AgentRequest) string {
    prompt := "你是 ComputeHub 的 AI 智能体..."
    
    // 注入最近的经历
    if a.memory != nil {
        recent, _ := a.memory.GetRecentEpisodes(5)
        if len(recent) > 0 {
            prompt += "\n\n## 最近的经验\n"
            for _, ep := range recent {
                status := "✅"
                if !ep.Success { status = "❌" }
                prompt += fmt.Sprintf("- %s %s: %s\n", status, ep.Date, ep.Task)
            }
        }
        
        // 注入集群状态
        status, _ := a.memory.GetSystemStatus()
        if status != "" {
            prompt += "\n\n## 当前集群状态\n" + status
        }
    }
    return prompt
}
```

### 每次 Action 后自动记录

```go
// agent.go executePlan 中
func (a *Agent) executePlan(ctx context.Context, plan []PlanStep, req *AgentRequest) error {
    // ...
    for i := range plan {
        // 执行步骤...
        
        // 记录到记忆
        if a.memory != nil {
            icon := "✅"
            if plan[i].Status == "failed" { icon = "❌" }
            a.memory.AppendSession(req.SessionID, "action", 
                fmt.Sprintf("%s Step %d: %s (%s)", icon, plan[i].ID, plan[i].Command, plan[i].Duration))
        }
    }
    
    // 任务完成后保存经验
    if a.memory != nil {
        success := true
        for _, step := range plan {
            if step.Status == "failed" { success = false; break }
        }
        a.memory.SaveEpisode(req.Task, summarizeResult(plan), success, extractLearnings(plan))
    }
}
```

### Brain 心跳 + 记忆维护

```go
// brain.go
func (b *Brain) heartbeatLoop() {
    ticker := time.NewTicker(30 * time.Second)
    memoryTicker := time.NewTicker(5 * time.Minute) // 5min auto commit
    cleanupTicker := time.NewTicker(24 * time.Hour) // 1day cleanup
    
    for {
        select {
        case <-ticker.C:
            // 心跳决策...
            
        case <-memoryTicker.C:
            b.memory.AutoCommit() // 自动提交
            
        case <-cleanupTicker.C:
            b.memory.CleanOldEpisodes() // 清理 30 天前的
            b.memory.Compact()          // 仓库瘦身
        }
    }
}
```

---

## 六、Git 优势的具体体现

### `git log` — 看到 Agent 的一生
```bash
$ git log --oneline -10

a1b2c3d  auto: memory update at 2026-05-31 15:00
e4f5a6b  episode: analyze-logs (✅)
b7c8d9e  auto: memory update at 2026-05-31 14:55
f0a1b2c  knowledge: windows-gpu-wmi-fallback
c3d4e5f  auto: memory update at 2026-05-31 14:50
a6b7c8d  session: 分析服务器日志 (4 messages)
d9e0f1a  system: cluster-status update
g2h3i4j  auto: memory update at 2026-05-31 14:40
k5l6m7n  episode: disk-cleanup (✅) learned: /tmp is most valuable
o8p9q0r  init: OPC Agent Memory repository
```

### `git diff` — 看这次干了什么
```bash
$ git diff HEAD~1 --shortstat
 2 files changed, 45 insertions(+), 0 deletions(-)

$ git diff HEAD~1 -- episodes/2026-05-31-analyze-logs.md
+# Episode: Analyze Logs
+> Date: 2026-05-31 14:30
+> Success: ✅
+## Task
+## Learned
+Windows 的 findstr 和 Linux 的 grep 行为不同...
```

### `git grep` — 搜索历史知识
```bash
$ git grep -i "gpu" knowledge/
knowledge/windows-gpu-detection.md:GPU detection via WMI
knowledge/windows-gpu-detection.md:Windows GPU 检测的 WMI 方法

$ git log --all --oneline -S "gpu"
f0a1b2c knowledge: windows-gpu-wmi-fallback
```

---

## 七、实施步骤

如果你同意这个方案，我按这个顺序做：

### Step 1: 写 memory.go (核心，~1小时)
- Memory 接口定义
- GitMemory 完整实现（Init / AppendSession / SaveEpisode / Commit / Search）
- 先不接 Agent，独立可用的代码

### Step 2: 写测试 (~30分钟)
- 初始化测试仓库
- 验证 AppendSession + Commit
- 验证 SaveEpisode + Search
- 验证 Stats

### Step 3: 集成到 Agent (~30分钟)
- NewAgent 传入 memoryRoot
- buildSystemPrompt 注入近期记忆
- executePlan 自动记录 action
- Think 完成后 SaveEpisode

### Step 4: Brain 整合 AutoCommit (~20分钟)
- brain.go 加 memoryTicker 5min
- brain.go 加 cleanupTicker 24h

### 总计: ~2-3 小时

---

## 八、最终效果

```
启动前:                      启动后:
Agent 是白纸                Agent 知道自己是谁
  ┌──────────┐               ┌──────────┐
  │ whoami?  │               │ 记忆      │
  │ 什么都不会│               │ 📂 50次对话  │
  │ 从零开始 │               │ 📂 30个经验  │
  └──────────┘               │ 📂 15条知识  │
                             │ git log    │
                             │ 150 commits│
                             └──────────┘
```

**用户感知**: Agent 越用越聪明 — 记得上次怎么做的、知道哪些坑踩过了、能主动建议优化方案。

---

老大，这就是 Git 记忆系统的完整设计。用 workspace 已经跑通的 `scripts/git-memory-search.py` 和 `scripts/git-memory-manager.py` 的模式，移植到 Go 里，但更深度集成到 Agent 循环中。

你觉得方向对吗？如果 OK 我接下来就开写 `memory.go`，先从 Agent 独立验证再集成进去。
