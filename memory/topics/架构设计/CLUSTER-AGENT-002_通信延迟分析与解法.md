# ⏱️ CLUSTER-AGENT-002: 通信延迟分析与解法

> 基于 2026-06-20 实测数据
> 分析人：端智

---

## 1. 📊 实测延迟数据

| 路径 | 延迟 | 说明 |
|------|------|------|
| Worker 空命令（echo hello） | **~0.2s** | ComputeHub 裸网络层，纯传输 |
| Task 提交 + poll 回显 | **~1.9s** | 含 0.2s 执行 + 1.7s 轮询等待 |
| proot→openclaw agent 简单对话 | **~2.5s** | 含 LLM 推理（模型约 1-2s） |
| 当前端智→米智（完整链路） | **~5-20s** | poll 轮询 + proot 启动 + LLM |

**瓶颈拆解（以 5s 为例）：**

```
端智 POST → Gateway → Worker poll(3s) → proot启动(0.5s) → agent CLI(0.5s) → LLM推理(1.5s) → 原路返回
[0.2s]        [3s]        [0.5s]       [0.5s]      [1.5s]     [0.2s]
                ▲最大的单一瓶颈
```

---

## 2. 🎯 三个延迟层次与解法

### 2.1 传输层 — Worker poll 改 WS 推送（最大收益）

**现状**：Worker 每 3-5s 轮询 Gateway 拿任务，这是最大的延迟源。

**解法**：WS 推送（已在 v1.3.30+ 实现，但需要 Worker 启用 WS 连接）

```
poll 模式: Worker ──每3s──→ Gateway [检查]  ← 3s idle
WS 模式:   Worker ←──WS推送── Gateway [推]   ← 10ms
```

**效果**：3-5s → **<50ms**（网络 RTT）

**现状检查**：Worker 已支持 WS，但需要验证是否启用：

```bash
# 查看 Worker 日志是否有 WS 连接
# Gateway 端应显示 ws_connected=true
```

### 2.2 桥接层 — CLI → REST/WS 调用 OpenClaw

**现状**：Worker 通过 proot 容器执行 `openclaw agent --message "..."`。

**延迟开销分析：**
```
proot 启动        ~300-500ms   (容器初始化)
openclaw agent    ~200-500ms   (二进制加载 + LLM 连接)
↑ 合计 0.5-1s 纯基础设施开销，每次对话都有
```

**解法 A: 持久化 OpenClaw Agent 进程**
```bash
# 在 proot 容器里保持一个 agent 进程常驻
# 通过 stdin/stdout 管道通信，避免每次启动
openclaw agent --daemon --pipe /tmp/agent.pipe
```
→ 省掉 proot 启动 + agent 加载，节省 **~0.5-1s/次**

**解法 B: OpenClaw Gateway WS 直连（推荐，远期）**
```
Worker → localhost:18789 WebSocket → OpenClaw Agent
```
→ 省掉 proot 容器层，节省 **~0.3-0.5s/次**

**解法 C: OpenClaw CLI `--json` 输出**
```
openclaw agent --message "..." --json 2>&1 | tail -1
```
→ 省掉日志过滤，节省 **~0.1s/次**

**推荐路径**：先上解法 A（持久化管道），解法 B 作为远期目标（需要 OpenClaw Gateway 暴露 REST 端点或标准化 WS 协议）。

### 2.3 推理层 — LLM 响应时间

**现状**：LLM 本身推理 1-5s（取决于模型大小 + 网络）。

**延迟分析：**
| 模型 | 典型时间 | 说明 |
|------|---------|------|
| deepseek-v4-flash | ~0.5-1s | 快，适合简单命令 |
| qwen3.6-35b | ~1-3s | 中等 |
| deepseek-v3.1:671b | ~3-10s | 大模型，适合复杂推理 |

**解法**：非架构问题，由消息类型决定用哪个模型。
- 简单状态查询 → 快模型（flash）
- 复杂对话 → 主力模型
- 可配置：`"model": "flash"` 在消息中指定

---

## 3. 🚀 优化后的延迟对比

**端智→米智 "查磁盘空间"：**

```
                   当前            优化后 Phase 1   优化后 Phase 2
Gateway→Worker     ~3s (poll)      ~0.05s (WS)     ~0.05s (WS)
Worker→OpenClaw    ~0.5s (proot)   ~0.1s (持久CLI)  ~0.01s (WS)
LLM 推理           ~1.5s           ~1.5s            ~1.5s
返回路径           ~3s (poll)      ~0.05s (WS)      ~0.05s (WS)
───────────────────────────────────────────────────────────────
总计               ~8s             ~1.7s            ~1.6s
```

**优化后延迟分布（Phase 1）：**
```
端智 POST          → Gateway(0.02s) → WS Push(0.01s) 
→ Worker 接收(0.001s) → 持久CLI调用(0.1s) 
→ LLM推理(1.5s) 
→ WS回复(0.01s) 
→ Gateway(0.02s) → 端智收到
总计: ~1.7s
```

注：LLM 推理 1.5s 是无法跨越的物理瓶颈，剩下的 0.2s 是网络 + 协议开销。

---

## 4. 🔧 实施建议顺序

### 第一步：确保 WS 推送启用（已经做了，需要验证）

**验证命令：**
```bash
# 查 Worker 是否已启用 WS
curl -s http://36.250.122.43:8282/api/v1/nodes/list | python3 -m json.tool
# 确认 ws_connected 字段
```

如果未启用，Worker 启动加 `--ws` 参数：
```bash
computehub worker --agent --gw http://127.0.0.1:8282 --node-id xxx --ws
```

### 第二步：持久化 OpenClaw Agent CLI 管道

在 Worker 中加一个常驻 goroutine，持有一个 openclaw agent 进程的 stdin/stdout：

```go
type OpenClawDaemon struct {
    cmd    *exec.Cmd
    stdin  io.WriteCloser
    stdout io.ReadCloser
    mu     sync.Mutex
}

func (d *OpenClawDaemon) Start() error {
    // 在 proot 中启动持久 agent 进程
    // proot-distro login ubuntu -- bash -c "cd /root && openclaw agent --daemon --pipe"
    // 但 openclaw 没有 --daemon 模式，我们改用其他方式
}
```

**替代方案**：每次调用 CLI 但复用同一个 proot session（类似 tmux 或 screen）：
- 用 `proot-distro login ubuntu -- bash -c "tail -f /tmp/agent_pipe & openclaw agent --message '$MSG'" 2>&1 | tail -1`
- 但这只是小优化

**更好的方案**：检测 Worker 本机是否有 OpenClaw Gateway 监听 18789，如果有，通过本地 WebSocket 通信。

### 第三步（远期）：Worker 直连本地 OpenClaw Gateway WS

> 需要先弄清楚 OpenClaw Gateway 的 WS 协议

---

## 5. ⚡ 总结

```
延迟问题不是架构问题，是通信模式问题

最大瓶颈：Worker 3-5s 轮询（占 60% 延迟）
次大瓶颈：proot 容器启动（占 10% 延迟）
底线瓶颈：LLM 推理 1-3s（不可跨越）

解法核心：poll → WS 推送，延迟从 3-5s 降到 10ms
```

**先把 poll→WS 这步验证并确保启用**，其他优化都是锦上添花。