# ComputeHub WS 连接稳定性修复计划 v1.3.32

**创建时间**: 2026-06-13 07:08
**目标**: 彻底解决 wanlida-opc01 节点每秒断连重连问题

---

## 一、问题现象

wanlida-opc01 节点（Linux ARM64，不稳定网络环境）：
- 每秒断连重连 2-3 次
- Gateway 每小时记录 3700+ 次 `writePump` 失败日志
- 所有任务推送（`FanOut` / `FanOutAll`）全部失败
- 节点永远处于 `WS 连接 → 注册 → 1-3秒后断连 → 重连` 的死循环

---

## 二、根因分析

### 2.1 竞态链路（5 步死循环）

```
[1] Gateway FanOut 向不稳定节点写入失败
      ↓
[2] Worker wsReadLoop 读到 EOF → Close(conn) → 退回 backgroundWSReconnect()
      ↓
[3] 1s 后 Worker 重连 → Gateway Register(nodeID) → 注册新连接
      ↓
[4] 旧连接 readPump 的 defer Unregister 触发
    → Unregister 调用 conn.Close()
    → 可能误关新注册连接（旧连接刚被 Register 标记为"已替换"但 conn 还活着）
      ↓
[5] 新连接被误关 → wsReadLoop 再次读到 EOF → 回到 [2]
```

### 2.2 FanOut 互相阻塞

```
FanOutAll() 顺序遍历所有节点，每个节点写超时 2s：
  - 节点A（网络抖动）写入失败 → 阻塞 2s
  - 节点B 还没轮到 → 被连带阻塞
  - 节点C 还没轮到 → 被连带阻塞
  - 全部节点都被不稳定的一个节点拖垮
```

### 2.3 backgroundWSReconnect 递归调用栈堆积

```
StartPollLoop() → tryConnectWS() → wsReadLoop() → [断线] → 返回
  → backgroundWSReconnect() → tryConnectWS() → wsReadLoop() → [断线] → 返回
    → backgroundWSReconnect() → tryConnectWS() → wsReadLoop() → [断线] → ...

每次断连都会在 goroutine 链上再叠一层调用，
导致：
  - goroutine 栈越来越深
  - 多个 wsReadLoop 可能并发执行（tryConnectWS 在新 goroutine 中？不，没有 goroutine）
  - 实际上 backgroundWSReconnect 调用 wsReadLoop 是同步的，
    所以不会并发，但每次断连都会新起一帧栈
```

### 2.4 Worker 端问题

`wsReadLoop()` 读失败后立即 `Close()` + 设 nil，然后返回：
```go
err := hc.wsConn.ReadJSON(&envelope)
if err != nil {
    hc.wsConn.Close()       // ← 立即关
    hc.wsConn = nil         // ← 设 nil
    return                   // ← 退回 caller
}
```

`backgroundWSReconnect()` 收到返回后立即 `tryConnectWS()`：
```go
if hc.tryConnectWS() {
    hc.wsReadLoop() // 同步调用，栈上堆积
    backoff = 1 * time.Second
    continue
}
```

---

## 三、修复方案

### 修复 1: Register 不再关旧连接 ✅ 已做

**文件**: `src/gateway/gateway_ws.go` → `Register()`

当前代码（已改好）:
```go
func (h *WSHub) Register(nodeID, platform string, conn *websocket.Conn) *WSClient {
    h.mu.Lock()
    defer h.mu.Unlock()
    if old, ok := h.clients[nodeID]; ok {
        log.Printf("📡 WS Hub: %s 已有活跃连接，跳过重连注册", nodeID)
        conn.Close()       // 关新连接（不碰旧连接）
        return old         // 返回旧 client
    }
    // ... 正常注册
}
```

**原理**: 让旧连接的 `readPump` 自行检测到断连后调用 `Unregister`，避免 `Register` 直接关旧连接导致 `Unregister` 竞态。

### 修复 2: Unregister 安全检查 ✅ 已做

**文件**: `src/gateway/gateway_ws.go` → `Unregister()`

当前代码（已改好）:
```go
func (h *WSHub) Unregister(nodeID string) {
    h.mu.Lock()
    defer h.mu.Unlock()
    if client, ok := h.clients[nodeID]; ok {
        client.Conn.Close()
        delete(h.clients, nodeID)
        h.DisconnectCount++
    }
}
```

**原理**: 检查 client 仍在 map 中再 close，防止 `Register` 替换后 `Unregister` 关错连接。

### 修复 3: FanOut 改为 goroutine 并发写 ⬜ 待做

**文件**: `src/gateway/gateway_ws.go` → `FanOut()` 和 `FanOutAll()`

改动:
```go
// FanOut 中写入循环改为:
delivered := int32(0)
var wg sync.WaitGroup
for nodeID, client := range h.clients {
    if nodeID == exceptID || !client.Topics[topic] {
        continue
    }
    wg.Add(1)
    go func(nid string, c *WSClient) {
        defer wg.Done()
        c.Conn.SetWriteDeadline(time.Now().Add(2 * time.Second))
        if err := c.Conn.WriteMessage(websocket.TextMessage, payload); err == nil {
            atomic.AddInt32(&delivered, 1)
        }
    }(nodeID, client)
}
wg.Wait()
```

**注意**: 需要在 goroutine 中拿 client 副本，不要闭包引用。

### 修复 4: writePump 检测 readPump 退出 ⬜ 待做

**文件**: `src/gateway/gateway_ws.go` → `writePump()`

当前 `writePump` 和 `readPump` 各自独立，没有相互感知。当一个 goroutine 退出后，另一个还在空转写日志。

改动: 引入 `done` channel 让 `writePump` 在 `readPump` 退出时同步停止：
```go
func (h *WSHub) HandleWSUpgrade(...) {
    // ...
    done := make(chan struct{})
    go h.readPump(client, done)
    go h.writePump(client, done)
}

func (h *WSHub) readPump(client *WSClient, done chan struct{}) {
    defer func() {
        h.Unregister(client.NodeID)
        close(done) // 通知 writePump 退出
    }()
    // ...
}

func (h *WSHub) writePump(client *WSClient, done chan struct{}) {
    ticker := time.NewTicker(10 * time.Second)
    defer ticker.Stop()
    for {
        select {
        case <-done:
            return
        case <-ticker.C:
            // ... write ping
        }
    }
}
```

### 修复 5: Worker 端 wsReadLoop 防递归栈堆积 ⬜ 待做

**文件**: `src/workercmd/worker_hall_client.go` → `backgroundWSReconnect()`

当前 `wsReadLoop()` 是同步调用，断连后退回 `backgroundWSReconnect()` 再调 `tryConnectWS()` 再调 `wsReadLoop()`，导致栈越来越深。

改动: 用循环替代递归调用：
```go
func (hc *HallClient) backgroundWSReconnect() {
    backoff := 1 * time.Second
    maxBackoff := 30 * time.Second

    for {
        select {
        case <-hc.stopCh:
            return
        default:
        }

        if hc.tryConnectWS() {
            fmt.Printf(" [HallClient:%s] ✅ WS 重连成功，切换回 WS 模式\n", hc.nodeID)
            hc.sendIntroMessage()
            hc.wsReadLoop() // 断线后直接 continue，不再递归调用
            fmt.Printf(" [HallClient:%s] ⚠️ WS 再次断开，重试重连\n", hc.nodeID)
            backoff = 1 * time.Second
            continue  // ← 不是 return，而是继续外层循环
        }

        time.Sleep(backoff)
        backoff *= 2
        if backoff > maxBackoff {
            backoff = maxBackoff
        }
    }
}
```

注意：当前代码 `wsReadLoop()` 后面直接 `backoff = 1` + `continue`，这已经不会递归了（因为 `continue` 回到外层 for 循环）。但问题是**初次启动时** `StartPollLoop` 也是同步调用：

```go
func (hc *HallClient) StartPollLoop() {
    go func() {
        time.Sleep(3 * time.Second)
        if hc.tryConnectWS() {
            hc.sendIntroMessage()
            hc.wsReadLoop()       // ← 同步调用，栈上
        }
        go hc.backgroundWSReconnect()  // ← wsReadLoop 返回后才启动
        // ... HTTP poll
    }()
}
```

这里 `wsReadLoop()` 在匿名 goroutine 中同步调用，返回后 `backgroundWSReconnect` 才启动。这本身没问题（都在一个 goroutine 中），但两个断连循环（外层 `wsReadLoop` 和 `backgroundWSReconnect`）可能重叠。

需要确保 **只有一个重连循环在工作**。当前 `StartPollLoop` 在 WS 成功后启动 `wsReadLoop`，`wsReadLoop` 失败返回后启动 `backgroundWSReconnect`。但 `backgroundWSReconnect` 内部也会调 `wsReadLoop`，形成循环。这个设计在功能上是对的，但**在频繁断连时，两次 `wsReadLoop` 调用之间的 time.Sleep 被省略了（backoff 重置为 1s）**，导致重连频率过高。

**建议**: 无论断连原因，至少等待 2-5 秒再重连。

### 修复 6: WS 连接空闲检测 + 提前清理 ⬜ 待做

**文件**: `src/gateway/gateway_ws.go`

不稳定网络环境下，TCP 连接可能已经断开但 Go 层不知道。建议添加：
1. 每 30s 发一次 ping，90s 无 pong 标记为 dead
2. dead 连接在下次 FanOut 前关闭

---

## 四、修改文件清单

| # | 文件 | 改动 | 优先级 |
|---|------|------|--------|
| 1 | `src/gateway/gateway_ws.go` → `FanOut()` | goroutine 并发写 | P0 |
| 2 | `src/gateway/gateway_ws.go` → `FanOutAll()` | goroutine 并发写 | P0 |
| 3 | `src/gateway/gateway_ws.go` → `writePump()` | 加 done channel | P1 |
| 4 | `src/gateway/gateway_ws.go` → `readPump()` | 传 done channel | P1 |
| 5 | `src/workercmd/worker_hall_client.go` → `StartPollLoop()` | 重连延迟 | P1 |
| 6 | `src/workercmd/worker_hall_client.go` → `backgroundWSReconnect()` | 确保不递归堆积 | P1 |
| 7 | `src/gateway/gateway_ws.go` → 新增 | 连接空闲检测 | P2 |

---

## 五、实施步骤

### Phase 1: P0 并发 FanOut（消除互相阻塞）
1. 改 `FanOut()` — for 循环内 spawn goroutine
2. 改 `FanOutAll()` — 同上
3. `go build` 验证编译
4. `GOOS=linux GOARCH=amd64` 编译
5. 更新 `deploy/version.txt` → v1.3.32
6. 全平台交叉编译 + SHA256
7. 部署到 ECS → Gateway systemd restart

### Phase 2: P1 writePump + Worker 端优化
1. 改 `writePump()` + `readPump()` done channel
2. 改 Worker 端重连逻辑
3. 全平台编译 + 部署

### Phase 3: P2 空闲检测
1. 实现连接空闲检测
2. 全平台编译 + 部署

### 验证方法
1. 观察 wanlida-opc01 节点连接稳定性（目标：连续在线 > 5 分钟）
2. Gateway 日志中 `writePump` 失败次数应 < 10/小时
3. 任务推送成功率 > 99%

---

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| goroutine FanOut 可能 OOM | 大量节点同时写 | 单 goroutine 写超时 2s，会自动失败退出 |
| writePump done channel 导致误关 | 连接还活着但写退出 | done 只在 readPump 退出时 close，readPump 退出 = 连接已断 |
| Worker 重连延迟增加 | 短暂断连恢复慢 2-5s | 可接受，避免高频重连风暴 |
| 并发 FanOut 改变 FanOut 顺序 | 节点收到消息顺序不同 | 不影响功能，消息有 seq 保证顺序 |

---

## 七、版本信息

- **当前版本**: v1.3.30（wanlida-opc01 开始不稳定）
- **目标版本**: v1.3.32
- **预计改动**: 2 个文件，~100 行改动
- **部署时间**: < 5 分钟
