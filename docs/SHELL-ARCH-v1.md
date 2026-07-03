# Shell 交互式远程终端 — 架构推演与技术说明书

> 版本: v1.3.35 (2026-06-16)
> 作者: 端智 (技术归档)

---

## 目录

1. [问题的起点：为什么要做 Shell 终端](#1-问题的起点为什么要做-shell-终端)
2. [整体架构：三层桥接模型](#2-整体架构三层桥接模型)
3. [五条消息通道详解](#3-五条消息通道详解)
4. [数据流全链路追踪](#4-数据流全链路追踪)
5. [关键技术决策](#5-关键技术决策)
6. [Bug 手册：踩过的坑](#6-bug-手册踩过的坑)
7. [使用说明书](#7-使用说明书)
8. [未来演进方向](#8-未来演进方向)

---

## 1. 问题的起点：为什么要做 Shell 终端

### 1.1 原始状态

ComputeHub 的能力核心是 **任务分发**：Gateway 发任务 → Worker 执行 → 返回结果。这是"投递-执行-回复"的单向模式。

痛点很明显：

| 场景 | 单向模式不行 |
|------|-------------|
| 实时排查 Worker 节点问题 | 要写一个 exec 任务才能运行一条命令 |
| 断点调试 | 没法打断一个运行中的进程 |
| 交互式操作 | 没法编辑文件、看实时输出 |
| 拓扑网络诊断 | 调不通需要逐层试，全得写成原子任务 |

**本质需求**: 给 Worker 一个"远程 SSH"能力，但通过 ComputeHub 自己的 WS 通道走，不依赖 SSH 端口暴露。

### 1.2 约束条件

要在 Wire 框架下解决，不是套个 SSH 壳：

- 不能依赖额外端口（Worker 只有 8383，Gateway 只有 8282）
- 必须通过现成 WS 通道复用（不新建 TCP 连接）
- 必须适配容器/PROot/原生 Linux（Termux 上跑 PROot，没有 `/dev/ptmx`）
- Worker 的 WS 连接同时承载任务 + Shell 两条流，不能互相阻塞

---

## 2. 整体架构：三层桥接模型

```
┌────────────┐    WS (独立连接)    ┌────────────┐    WS (共享连接)    ┌──────────────┐
│  TUI 客户端  │ ────────────────▶ │  Gateway   │ ────────────────▶ │  Worker 节点  │
│  (本地终端)   │ ◀──────────────── │  :8282    │ ◀──────────────── │  (bash进程)    │
│  raw mode   │   shell_output     │  三路桥接   │   shell_output    │  script -f    │
│  stdin→WS   │                    │            │                   │  pipe模式      │
└────────────┘                    └────────────┘                   └──────────────┘
       │                               │                                │
       │  /api/v1/tui/shell           │  路由器:                     │  WS 消息循环
       │  (独立 WS 连接)              │  TUI ↔ Session ↔ Worker    │  任务+Shell 复用
                                      │                                │
                                      │  三个映射表:                   │  shell_open →
                                      │  sessionID → ShellSession     │  StartShell()
                                      │  tuiConn → sessionID          │  readPipes()
                                      │  workerID → sessionID         │
```

### 2.1 三层职责

| 层 | 文件 | 职责 | 关键约束 |
|----|------|------|---------|
| **TUI** | `tui_shell.go` | 原始终端(raw mode)、键盘输入捕获、STDOUT渲染 | 独立 WS 连接，与菜单系统分离 |
| **Gateway** | `gateway_shell_ws.go` + `gateway_shell.go` | `shellRouter` 三表路由、消息格式转换 | 不解析内容，纯桥接 |
| **Worker** | `worker_shell_unix.go` | `script -f` 子进程管理、stdout/stderr 读取 | Pipe 模式无 PTY，PROot 兼容 |

### 2.2 路由器的三张表

Gateway 的 `shellRouter` 维护了三个并发安全的映射：

```go
sessions    map[string]*ShellSession  // sessionID → 会话
tuiSession  map[*websocket.Conn]string // TUI连接 → sessionID
sessionByID map[string]*ShellSession  // WorkerID → 会话 (最多1个活跃)
```

**为什么三张表？**

- `sessions` → 按 `sessionID` 查找（最常用，`routeShellOutputToTUI` 用）
- `tuiSession` → TUI 断开时清理（`CloseByTUI` 用 WS 连接指针查，不用用户维护状态）
- `sessionByID` → 防止同一 Worker 多个 Shell，新开自动关旧（互斥保障）

**并发安全**: 所有操作都经过 `sync.RWMutex`，读多写少用 `RLock`。

---

## 3. 五条消息通道详解

### 3.1 消息类型总览

| msg_type | 方向 | 触发 | 载荷 |
|----------|------|------|------|
| `shell_open` | TUI→Gateway→Worker | 用户选择节点 | `target_node`, `rows`, `cols` |
| `shell_input` | TUI→Gateway→Worker | 用户按键 | `session_id`, `data` (键盘字节) |
| `shell_output` | Worker→Gateway→TUI | 子进程 stdout | `session_id`, `data` (终端输出) |
| `shell_resize` | TUI→Gateway→Worker | 终端 resize | `session_id`, `rows`, `cols` |
| `shell_close` | TUI→Gateway→Worker | Ctrl+D / 退出 | `session_id` |

### 3.2 关键消息格式差异

这是最容易踩坑的地方——**消息字段在不同层的位置不同**：

**TUI→Gateway** (HTTP WS JSON，自由格式):
```json
{
  "msg_type": "shell_open",
  "target_node": "local-arm",
  "rows": 24,
  "cols": 80
}
```

**Gateway→Worker** (WSMessage 结构体):
`session_id` 和 `data` 放进 `Payload` 字段，因为 WSMessage 本身的 JSON 结构：

```json
{
  "msg_type": "shell_input",
  "sender_id": "gateway",
  "payload": "{\"session_id\":\"shell-005522-435e\",\"data\":\"echo hello\"}"
}
```

**Worker→Gateway** (WSMessage 结构体，但顶层字段):
Worker 直接发送：
```json
{
  "msg_type": "shell_output",
  "session_id": "shell-005522-435e",
  "data": "echo hello\r\nhello\r\n"
}
```

Gateway 收到后 `SessionID` 和 `ShellData` 从 JSON 顶层自动填充到 `WSMessage` 结构体。

**Gateway→TUI** (HTTP WS JSON):
```json
{
  "msg_type": "shell_output",
  "session_id": "shell-005522-435e",
  "data": "echo hello\r\nhello\r\n"
}
```

**ℹ️ 关键差异**: Worker→Gateway 用顶层字段，Gateway→Worker 用 `Payload` 嵌套。这是由两个方向的消息构造方式不同导致的——Worker 直接 `WriteJSON(map)`，Gateway 用 `SendToWorker(WSMessage{Payload: ...})`。

### 3.3 Gateway WSMessage 结构体

```go
// from gateway_ws.go
type WSMessage struct {
    MsgType   string          `json:"msg_type"`
    SenderID  string          `json:"sender_id"`
    
    SessionID string          `json:"session_id,omitempty"`  // Shell 会话 ID（顶层）
    ShellData string          `json:"data,omitempty"`         // Shell 数据（顶层）
    
    Payload   json.RawMessage `json:"payload,omitempty"`      // 通用嵌套载荷
    // ... 其他字段
}
```

`SessionID` 和 `ShellData` 放在顶层是为了让 Worker 直发的消息能直接从 JSON 映射进来，不需要拆 `Payload`。

---

## 4. 数据流全链路追踪

### 4.1 shell_open：开一个终端

```
Step 1: TUI
  screenInteractiveShell()
    → pickTargetWorker()          // 从 /api/v1/nodes/list 选在线节点
    → Dial WS to /api/v1/tui/shell
    → WriteJSON({shell_open, target_node, rows, cols})

Step 2: Gateway (HandleTUIShellWS)
  → json.Unmarshal → case "shell_open"
    → pickShellWorker()           // 如果 target_node="" 时自动选
    → shellRouter.CreateSession(tuiConn, workerID)
      → 生成 sessionID ("shell-005522-435e")
      → 注册三张映射表
    → SendToWorker(WSMessage {MsgTypeShellOpen, Payload: {session_id, rows, cols}})

Step 3: Gateway (SendToWorker)
  → wsHub.clients[workerID] 找到 Worker 的 WS 连接
  → conn.WriteJSON(msg)         // Payload 嵌套模式

Step 4: Worker (worker_hall_client.go: readPump)
  → case "shell_open"
    → json.Unmarshal(envelope.Payload → {SessionID, Rows, Cols})
    → GetShellManager().StartShell(sessionID, nodeID, wsConn, rows, cols)

Step 5: Worker (StartShell)
  → exec.Command("script", "-q", "-f", "-c", "bash -i", "/dev/null")
    → StdinPipe / StdoutPipe / StderrPipe
    → cmd.Start() → PID=24312
    → go readPipes(stdout, stderr)  // 持续读输出
    → go waitLoop()                  // 等进程退出
```

### 4.2 shell_input：键盘输入

```
Step 1: TUI (enterRawMode)
  → os.Stdin.Read(buf)         // 读取原始按键
  → WriteJSON({shell_input, session_id, data: "\x03"})  // Ctrl+C

Step 2: Gateway
  → case "shell_input"
    → shellRouter.RouteByTUI(conn)  → sessionID → WorkerID
    → json.Marshal({session_id, data}) → Payload
    → SendToWorker(WSMessage{MsgType: MsgTypeShellInput, Payload: ...})

Step 3: Gateway → Worker WS (同上)

Step 4: Worker (readPump)
  → case "shell_input"
    → json.Unmarshal(envelope.Payload → {SessionID, Data})
    → sm.HandleShellInput(sessionID, data, isBinary)

Step 5: Worker (HandleShellInput)
  → sess.pipeIn.Write([]byte(input))   // 写入 stdin pipe
  → 子进程 bash 收到字节
```

### 4.3 shell_output：看实时输出

```
Step 1: Worker (readPipes goroutine)
  → stdout.Read(buf) → n>0
  → s.sendOutput(string(buf[:n]))
    → conn.WriteJSON({shell_output, session_id, data: "echo hello\r\n"})

Step 2: Gateway (readPump)
  → WSMessage received
  → envelope.MsgType == "shell_output"
  → envelope.SessionID, envelope.ShellData 由 JSON 自动填充
  → routeShellOutputToTUI(&envelope)

Step 3: Gateway (routeShellOutputToTUI)
  → shellRouter.RouteBySession(envelope.SessionID) → ShellSession
  → sess.TUI.Conn (TUI 的 WS 连接)
  → tuiConn.WriteJSON({shell_output, session_id, data: envelope.ShellData})

Step 4: TUI (WS read goroutine)
  → case "shell_output"
  → os.Stdout.Write([]byte(msg.Data))   // 直接写到终端
```

### 4.4 shell_close：退出终端

```
触发方式:
  1. 用户输入 Ctrl+D → TUI 发 shell_close
  2. 子进程退出 → readPipes 检测到 EOF → Worker 发 shell_close
  3. TUI WS 断开 → Gateway CloseByTUI 清理
  4. Worker WS 断开 → Worker CloseAllByConn 清理

TUI主动退出:
  TUI → WriteJSON({shell_close, session_id})
  → Gateway → SendToWorker(WSMessage{MsgTypeShellClose, Payload: {session_id}})
  → Worker → CloseSession → sess.Close()
    → pipeIn.Close() + process.Kill()

进程退出:
  Worker waitLoop → 子进程 Wait() 返回
  → conn.WriteJSON({shell_close, session_id, status:"exited"})
  → Gateway → 转发给 TUI
  → 清理路由器映射表
```

---

## 5. 关键技术决策

### 5.1 Pipe 模式 vs PTY 模式

| | Pipe 模式 (当前) | PTY 模式 |
|---|---|---|
| 实现 | `script -q -f -c "bash -i"` | `os.StartProcess` 开 PTY |
| 兼容性 | ✅ PROot / 容器 / 原生 | ❌ PROot 无 `/dev/ptmx` |
| 输出缓冲 | 可能被 `stdbuf` 影响 | 全程即时 |
| ANSI 颜色 | ✅ 通过 | ✅ 原生 |
| Resize | ❌ 不支持 | ✅ 支持 `TIOCSWINSZ` |
| 额外依赖 | `script` 命令 | 无 |

**为什么选 Pipe 模式**: 我们的 Worker 大量跑在 Termux PROot 上，那里没有 PTY 设备。`script -q -f -c "bash -i"` 在没有 TTY 的进程中模拟出一个伪终端上下文，让 bash 认为自己在交互模式下运行（输出行缓冲而非全缓冲）。

### 5.2 三张路由器映射表的必要性

单表方案（只有 `sessions`）的问题：
- TUI 断线时没法知道这个 TUI 开了哪些 session（只能遍历全表）
- 同一 Worker 开第二个 session 时不知道要关第一个（需要持续追踪 Worker→session 关系）

三表方案 = O(1) 的三种查找路径，各自解耦。

### 5.3 为什么 TUI 要单独 WS 连接

TUI 主菜单用 HTTP 请求（短连接），Shell 需要长连维持实时双向流。共用一个 WS 的话：
- 菜单的 HTTP 请求会阻塞
- 消息类型混淆（HTTP 响应 vs WS 推送）
- 断开一个 Shell 不会影响主菜单

所以 `/api/v1/tui/shell` 是独立 WS 端点，与 Worker 侧的 `/api/v1/ws` 也不同。

### 5.4 为什么 shell_input 走 Payload 而 shell_output 走顶层

这不是设计，是**历史遗留**。Gateway→Worker 的 `SendToWorker` 统一走了 `WSMessage{Payload: ...}` 模式（早期用于任务分发）。Worker→Gateway 的方向，Worker 自由构造 JSON 所以 `session_id` 和 `data` 都放顶层。

这导致了 `routeShellOutputToTUI` 需要两种路径解析——先试顶层，不行再试 Payload。早期版本只读了 `Payload`，所以 shell_output 始终为空——这就是今天早上修的 bug。

---

## 6. Bug 手册：踩过的坑

### Bug #1: shell_output 在 routeShellOutputToTUI 解析为空

**现象**: TUI 反复收到 `{msg_type: "shell_output", session_id: "shell-xxx", data: ""}`。Worker 那边明明有输出。

**根因**: `routeShellOutputToTUI` 从 `envelope.Payload` 读，但 Worker 直发的 WS 消息中 `session_id` 和 `data` 在 JSON 顶层，不在 `Payload` 里。

**修复**: 
```go
// 先读顶层
sessionID := envelope.SessionID
if sessionID == "" {
    // 再 fallback 到 Payload（旧格式兼容）
    ...
}
```

### Bug #2: PS1 显示被吞（WSL 场景）

**现象**: Shell prompt `root@localhost:~#` 里有 ANSI 转义序列但显示不全。

**根因**: Worker 用 `script -q -f -c "bash -i"` 启动，bash 的 PS1 包含 `\[\]` 包装的 ANSI，pipe 模式下 `script` 会嵌入 `\x1b[?2004h`（ bracketed paste mode 标记）。

**现状**: 不影响功能，终端渲染正常。纯文本命令输出如 `echo MARCO-OUTPUT` 完全正常。如需清理可配置 `PS1='$ '`。

### Bug #3: Worker panic — 在已关闭连接上 WriteJSON

**现象**: Worker 反复 panic，堆栈指向 `sendOutput` 的 `conn.WriteJSON`。

**根因**: 时序竞争——`readPipes` goroutine 还在读管道往 WS 写，但 `CloseSession` 已经把 `sess.conn` 清了或 WS 连接已断。

**修复**（前瞻性设计）: 
```go
func (s *ShellSession) sendOutput(data string) {
    s.mu.Lock()
    conn := s.conn
    s.mu.Unlock()
    if conn == nil {
        return
    }
    // 只有拿到 conn 才写
}
```

锁保护 + nil 检查，即使 close 和 sendOutput 并发也不会 panic。

### Bug #4: randHex "随机"不够随机

```go
func randHex(n int) string {
    b := make([]byte, n)
    for i := range b {
        b[i] = hex[(time.Now().UnixNano()+int64(i)*7)&0xf]
        time.Sleep(1) // 1ns
    }
    return string(b)
}
```

**问题**: 纳秒级时间戳作为随机源，相同纳秒内调两次会碰撞。4 位 hex = 65536 种组合，高频场景可能冲突。

**影响**: 低。sessionID 前缀 `shell-` + `HHMMSS` 时间戳已经是秒级唯一了，4 位 hex 只是防止同一秒内同 Worker 开多个。

**改进建议**: 可接 `crypto/rand` 但当前够用。

---

## 7. 使用说明书

### 7.1 快速开始

终端输入 `shell` 进入交互终端：

```
ComputeHub TUI (v1.3.35)
  gateway   🔗 Gateway管理
  exec      发送命令任务
  monitor   📊 Worker监控
  shell     💻 交互式远程终端       <── 选这个
  ...
```

选择 Worker：

```
> shell
选择目标 Worker:
  1. local-arm
  2. ecs-p2ph
  3. Windows-mobile
  (直接回车选第一个) > 1
```

进入终端后就是完整的 bash 环境：

```
╔═══════════════════════════════════════════╗
║  💻 交互式远程终端                         ║
║  Worker: local-arm                         ║
║  Ctrl+D  退出  Ctrl+C  中断               ║
╚═══════════════════════════════════════════╝

root@localhost:~$ 
```

### 7.2 快捷键

| 按键 | 作用 | 说明 |
|------|------|------|
| 普通按键 | 输入字符 | 所有 ASCII 按键直接传递给远程终端 |
| `Ctrl+C` | SIGINT | 中断当前运行的程序 |
| `Ctrl+D` | 退出 Shell | 关闭远程终端，返回 TUI 菜单 |
| `Enter` | 执行命令 | 回车传递到远程 bash |

### 7.3 可用命令

远程终端是完整的 bash，所有标准 Linux 命令都可用：

```bash
# 系统信息
uname -a
free -h
df -h
ps aux

# 文件操作
ls -la
cat /etc/os-release
tail -f /var/log/syslog

# 网络诊断
ping -c 4 8.8.8.8
curl -I https://example.com
netstat -tlnp

# 进程管理
top -b -n 1
kill -9 <PID>

# 编辑器
vi /tmp/test.txt
```

### 7.4 适用于哪些场景

| 场景 | 以前怎么做 | 现在 |
|------|-----------|------|
| Worker 节点宕机排查 | 写 exec 任务一条一条跑 | 直接 `top` + `dmesg` 实时看 |
| 网络连通性调试 | 写 ping 任务等返回 | 直接 `ping -c 4 8.8.8.8` 看实时输出 |
| 配置文件快速修改 | 下载→改→上传 | `vi /etc/xxx.conf` 直接改 |
| Python 临时调试 | 不可能 | `python3 -c "print('hello')"` |
| 批量日志查看 | 分页发任务 | `tail -f /var/log/app.log` |
| 打不开了 SSH 时 | 死路 | 只要有 Worker WS 在线就能 Shell |

### 7.5 局限性

- **Pipe 模式无 resize**: Worker 不知道终端窗口变了，`top` 等全屏工具可能排版错位
- **无文件传输**: 只是终端，要传文件还得走任务（或 rsync/curl）
- **单 Worker 会话互斥**: 同一 Worker 同一时间只能一个 Shell 会话（防止 `.bashrc` 冲突）
- **Windows 不支持**: `worker_shell_stub.go` 是空实现（Go 编译标记 `!linux && !darwin`）
- **需要 Worker Agent 模式**: 仅 `--agent` 模式 Worker 才开启 Shell 功能

---

## 8. 未来演进方向

### 短期（v1.4.x）

1. **PTY 回退机制**: 有 PTY 时开 PTY（支持 resize），没有时自动降级到 `script` Pipe 模式
2. **文件上传/下载**: 在 `shell_close` 前增加一个文件传输协议（base64 编解码 over WS）
3. **会话持久化**: 断开后保留 30s，允许重新连接恢复上下文（防止断线丢失）

### 中期（v1.5.x）

4. **多 Tab 终端**: 一个 TUI 连接同时管理多个 Shell 会话（用标签页切换）
5. **历史回放**: 记录 Shell 会话输出，退出后可以回溯

### 长期

6. **Web 终端**: Gallery 页面集成 Web 版 xterm.js 终端，浏览器直接远程 Shell
7. **协作模式**: 多个 TUI 同时查看同一 Shell 会话

---

> 💡 **核心设计哲学**: Shell 是 Worker 能力的补充，不是替代。任务分发（exec）适合自动化、批量、幂等的操作，Shell 适合临时排查、调试、探索。两者互补，一起覆盖了集群管理的全场景。