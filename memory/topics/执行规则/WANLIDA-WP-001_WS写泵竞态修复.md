# 🐛 WANLIDA-WP-001: WS 写泵竞态导致无限断连循环

**发现时间**: 2026-06-13  
**严重程度**: 🔴 高 — 节点完全不可用（任务无法推送）

## 问题描述

WS 读失败 → 断连 → 自动重连 → 注册被 Gateway 替换旧连接 → 旧连接被关闭 → **新连接也被关** → 再断连 → 死循环。

每秒 2-3 次连接/断开循环，Gateway 每小时记录 3700+ 次 writePump 失败。

## 根因：三个竞态交织

### 竞态 1：Gateway Register 关旧连接
```go
// gateway_ws.go: Register()
if old, ok := h.clients[nodeID]; ok {
    old.Conn.Close()  // 关旧连接
}
```

### 竞态 2：Worker wsReadLoop 失败后 close + 重连
```go
// worker_hall_client.go: wsReadLoop()
err := hc.wsConn.ReadJSON(&envelope)  // ← 读到 EOF (Gateway 关旧连接导致)
hc.wsConn.Close()                     // ← 再 close
hc.wsConn = nil
return                                  // ← 退回到 backgroundWSReconnect

// 1 秒后
hc.tryConnectWS()  // ← 重新注册，触发竞态 1
```

### 竞态 3：Unregister 里的 conn.Close() 影响新连接
```go
// gateway_ws.go: readPump()
defer func() { h.Unregister(client.NodeID) }()

// gateway_ws.go: Unregister()
client.Conn.Close()  // 此时 client 可能已经是新的连接
```

### 竞态 4：FanOut 对不稳定节点的 2s 写入超时
```go
// gateway_ws.go: FanOutAll()
client.Conn.SetWriteDeadline(time.Now().Add(2 * time.Second))
client.Conn.WriteMessage(...)  // 如果连接在 2s 内断开 → 所有 4 个节点 FanOut 都超时
```

## 恶性循环

```
t=0:  Worker 注册 WS 连接 A 到 Gateway
t=1:  Gateway FanOut 写连接 A 失败 (网络抖动)
t=2:  Worker wsReadLoop 读到 EOF → close(A) → 退回 backgroundWSReconnect
t=3:  backgroundWSReconnect 尝试 reconnect → 新连接 B 到 Gateway
t=4:  Gateway Register(nodeID, B) → old.Conn.Close() → 关 A
t=5:  Gateway readPump(B) 正常运行
t=6:  Gateway FanOut 写连接 B 失败 (网络抖动)
t=7:  Worker wsReadLoop(B) 读到 EOF → close(B) → 退回 backgroundWSReconnect
t=8:  backgroundWSReconnect → 1s 后重连 → 新连接 C
t=9:  Gateway Register(nodeID, C) → old.Conn.Close() → 关 B (刚注册!)
t=10: Gateway readPump(B) defer Unregister → conn.Close() → 可能关 C!
... 死循环 ...
```

## 修复方案（推荐：方案 B + 方案 D）

### 方案 B：Gateway Register 时不关旧连接
```go
func (h *WSHub) Register(nodeID, platform string, conn *websocket.Conn) *WSClient {
    h.mu.Lock()
    defer h.mu.Unlock()
    if old, ok := h.clients[nodeID]; ok {
        log.Printf("📡 WS Hub: %s 已有活跃连接，跳过重连注册", nodeID)
        conn.Close()
        return old
    }
    // ... 正常注册
}
```

### 方案 D：FanOut 每个节点独立 goroutine，互不阻塞
```go
func (h *WSHub) FanOutAll(msg *WSMessage, exceptID string) int {
    var wg sync.WaitGroup
    delivered := 0
    for nodeID, client := range h.clients {
        if nodeID == exceptID { continue }
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
    return delivered
}
```

## 验证

修复后重启 Gateway，观察：
- 不再有 "已有旧连接，替换" + "write failed" 循环
- 节点注册后连接稳定 > 30 秒
- FanOut 不再同时影响所有节点
