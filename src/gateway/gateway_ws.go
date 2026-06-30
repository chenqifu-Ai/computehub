// Copyright (c) 2026 ComputeHub. All rights reserved.
// WebSocket Hub — 持久连接替代 HTTP 轮询
//
// SPEC-WS-001 Step 1+2: 数据结构定义 + WSHub 核心
//
// 架构: Worker ──WS──▶ Gateway WSHub ──FanOut──▶ 所有 Worker WS
//       消息即时推送，延迟 <50ms，空轮询归零

package gateway

import (
	"encoding/json"
	"log"
	"net"
	"net/http"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

// =============================================================================
// Step 1: 数据结构和常量
// =============================================================================

// MsgType 消息类型常量
const (
	// 系统消息（连接生命周期）
	MsgTypeRegister   = "register"     // Worker → Gateway: 注册连接
	MsgTypeRegistered = "registered"   // Gateway → Worker: 注册成功
	MsgTypePing       = "ping"         // Gateway → Worker | Worker → Gateway: 心跳
	MsgTypePong       = "pong"         // 回复 ping
	MsgTypeSubscribe  = "subscribe"    // Worker → Gateway: 变更订阅话题
	MsgTypeSubscribed = "subscribed"   // Gateway → Worker: 订阅成功

	// 数据消息
	MsgTypeHall      = "hall"      // 大厅群聊消息
	MsgTypeArcNet    = "arc_net"   // ARC-NET 广播消息
	MsgTypeHeartbeat = "heartbeat" // 心跳载荷
	MsgTypeTask      = "task"      // 任务推送（Phase 3）
	MsgTypeTaskACK   = "task_ack"  // 任务确认（Worker 收到任务后回复）
	MsgTypeTaskCancel = "task_cancel" // 任务取消通知

	// Shell 交互终端（Phase 4 — 2026-06-16）
	MsgTypeShellOpen   = "shell_open"   // TUI→Gateway→Worker: 打开 Shell 会话
	MsgTypeShellInput  = "shell_input"  // TUI→Gateway→Worker: 键盘输入
	MsgTypeShellOutput = "shell_output" // Worker→Gateway→TUI:  终端输出
	MsgTypeShellResize = "shell_resize" // TUI→Gateway→Worker: 调整窗口大小
	MsgTypeShellClose  = "shell_close"  // TUI→Gateway→Worker:  关闭会话

	// 保留
	MsgTypeP2P = "p2p" // 跨节点直连
	MsgTypeACK = "ack" // 消息确认

	// Agent Direct Message（银河计划 Phase 2 — 2026-06-30）
	MsgTypeDirectMessage = "direct_message" // 端智→Worker: P2P 消息
	MsgTypeDirectReply   = "direct_reply"   // Worker→端智: P2P 回复
)

// WSMessage WebSocket 消息通用外壳（SPEC-WS-001 §2.1）
type WSMessage struct {
	MsgType   string          `json:"msg_type"`             // 消息类型
	Seq       uint64          `json:"seq,omitempty"`        // 序列号
	Timestamp int64           `json:"ts"`                   // Unix 毫秒时间戳
	TraceID   string          `json:"trace_id,omitempty"`   // 追踪ID（Phase 4）
	SenderID  string          `json:"sender_id"`            // 发送方 nodeID
	Priority  int             `json:"p,omitempty"`          // 0=CRIT, 1=NORM, 2=GOSSIP

	// --- 注册/心跳 ---
	NodeID    string   `json:"node_id,omitempty"`     // 注册时用
	Platform  string   `json:"platform,omitempty"`    // 注册时用
	SubTopics []string `json:"sub_topics,omitempty"`  // 订阅话题
	Status    string   `json:"status,omitempty"`      // "ok" / "error"
	Error     string   `json:"error,omitempty"`

	// --- 数据消息 ---
	Topic    string `json:"topic,omitempty"`      // 话题
	From     string `json:"from,omitempty"`       // 发送者
	FromName string `json:"from_name,omitempty"`
	To       string `json:"to,omitempty"`         // "all" 或具体 nodeID
	Content  string `json:"content,omitempty"`    // 消息正文

	// --- Shell 交互终端 ---
	SessionID string          `json:"session_id,omitempty"` // Shell 会话 ID
	ShellData string          `json:"data,omitempty"`       // Shell 数据（键盘输入/终端输出）
	TargetNode string         `json:"target_node,omitempty"` // 目标 Worker 节点

	// --- 广播/拓扑 ---
	Event   string          `json:"event,omitempty"`      // node_join / node_leave / ...
	Payload json.RawMessage `json:"payload,omitempty"`    // 事件载荷
}

// WSClient 代表一个 WebSocket 客户端连接（SPEC-WS-001 §2.3）
type WSClient struct {
	NodeID   string            // Worker 节点 ID
	Platform string            // "linux/arm64", "windows/amd64"
	Conn     *websocket.Conn   // WS 连接实例
	Topics   map[string]bool   // 订阅的话题集合
	RegAt    time.Time         // 注册时间
	LastPing time.Time         // 最近一次 ping/pong 时间
	Seq      uint64            // 本地序列号
	UserData map[string]string // 预留扩展字段

	// BUGFIX: gorilla/websocket 不支持并发写
	// writePump + FanOut + SendTo 都可能写同一 conn，必须加写锁
	WriteMu sync.Mutex
}

// WSHub WebSocket 管理中心（Gateway 端单例）（SPEC-WS-001 §2.3）
type WSHub struct {
	mu      sync.RWMutex
	clients map[string]*WSClient // key: nodeID

	// 指标
	MessagesSent     int64
	MessagesReceived int64
	ConnectCount     int64
	DisconnectCount  int64

	// PushTask ACK 等待：PushTask 发送后读次 pump 等 ACK
	// key: taskID, value: ack 通知 channel
	ackMu   sync.Mutex
	ackChs  map[string]chan struct{} // taskID → 收到 ACK 时关闭

	// Shell 会话路由（交互式终端）
	shellRouter *shellRouter
}

// upgrader HTTP→WebSocket 升级器
var upgrader = websocket.Upgrader{
	ReadBufferSize:  4096,
	WriteBufferSize: 4096,
	CheckOrigin: func(r *http.Request) bool {
		return true // 集群内部通信，允许所有来源
	},
}

// =============================================================================
// Step 2: WSHub 核心方法
// =============================================================================

// NewWSHub 创建 WSHub 实例
func NewWSHub() *WSHub {
	return &WSHub{
		clients: make(map[string]*WSClient),
		ackChs:  make(map[string]chan struct{}),
	}
}

// Register 注册 WS 连接（SPEC-WS-001 §3.1）
func (h *WSHub) Register(nodeID, platform string, conn *websocket.Conn) *WSClient {
	h.mu.Lock()
	defer h.mu.Unlock()

	// 清理旧连接（双重保护）：
	// 1. 关闭旧 conn → 触发旧 readPump 的 ReadMessage 失败 → defer Unregister
	// 2. 抹掉旧 client.NodeID → 旧 writePump 的 Unregister 打不到新连接
	if old, ok := h.clients[nodeID]; ok {
		log.Printf("📡 WS Hub: %s 替换旧连接", nodeID)
		delete(h.clients, nodeID)
		old.NodeID = "" // BUGFIX: 旧 writePump 的 Unregister 不再能匹配此 nodeID
		old.Conn.Close()
		h.DisconnectCount++
	}

	client := &WSClient{
		NodeID:   nodeID,
		Platform: platform,
		Conn:     conn,
		Topics:   map[string]bool{"general": true}, // 默认订阅 general
		RegAt:    time.Now(),
		LastPing: time.Now(),
		UserData: make(map[string]string),
	}
	h.clients[nodeID] = client
	h.ConnectCount++

	log.Printf("📡 WS Hub: %s 已连接 (共 %d 个连接)", nodeID, len(h.clients))
	return client
}

// Unregister 注销 WS 连接（SPEC-WS-001 §3.1）
func (h *WSHub) Unregister(nodeID string) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if client, ok := h.clients[nodeID]; ok {
		client.Conn.Close()
		delete(h.clients, nodeID)
		h.DisconnectCount++
		log.Printf("📡 WS Hub: %s 已断开 (剩余 %d 个连接)", nodeID, len(h.clients))
	}
}

// Subscribe 设置节点订阅的话题（SPEC-WS-001 §3.1）
func (h *WSHub) Subscribe(nodeID string, topics []string) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if client, ok := h.clients[nodeID]; ok {
		client.Topics = make(map[string]bool)
		for _, t := range topics {
			client.Topics[t] = true
		}
		log.Printf("📡 WS Hub: %s 订阅话题 %v", nodeID, topics)
	}
}

// GetClient 获取指定节点连接
func (h *WSHub) GetClient(nodeID string) *WSClient {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.clients[nodeID]
}

// OnlineCount 返回在线 WS 连接数
func (h *WSHub) OnlineCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.clients)
}

// ListClients 列出所有在线 WS 客户端 nodeID
func (h *WSHub) ListClients() []string {
	h.mu.RLock()
	defer h.mu.RUnlock()
	ids := make([]string, 0, len(h.clients))
	for id := range h.clients {
		ids = append(ids, id)
	}
	return ids
}

// FanOut 向指定话题的所有订阅者分发消息（SPEC-WS-001 §3.2）
// - topic: 话题名称
// - msg: 消息体（会补充 sender_id, timestamp, seq）
// - exceptID: 排除的 nodeID（空字符串 = 不排除任何节点）
func (h *WSHub) FanOut(topic string, msg *WSMessage, exceptID string) int {
	h.mu.RLock()
	defer h.mu.RUnlock()

	// 补充元数据
	if msg.Timestamp == 0 {
		msg.Timestamp = time.Now().UnixMilli()
	}
	if msg.Seq == 0 {
		msg.Seq = uint64(time.Now().UnixNano())
	}

	payload, err := json.Marshal(msg)
	if err != nil {
		log.Printf("📡 WS FanOut 序列化失败: %v", err)
		return 0
	}

	// 快照：拷贝所有候选 client（避免 FanOut 期间 Unregister 删了 conn）
	// 死连接清理：收集需要清理的 nodeID，在 RLock 外统一处理
	// 避免 RLock→Lock→Unlock→RLock 竞态
	const deadThreshold = 90 * time.Second
	type clientSnapshot struct {
		nodeID string
		conn   *websocket.Conn
		mu     *sync.Mutex // BUGFIX: 并发写保护
	}
	snapshots := make([]clientSnapshot, 0, len(h.clients))
	deadNodes := make([]string, 0)
	now := time.Now()
	for nodeID, client := range h.clients {
		if nodeID == exceptID {
			continue
		}
		if !client.Topics[topic] {
			continue
		}
		// 空闲检测：90s 无 pong 标记为 dead（只收集，不清理）
		if now.Sub(client.LastPing) > deadThreshold {
			log.Printf("📡 WS FanOut: %s 超过 %v 无 pong，标记 dead", nodeID, now.Sub(client.LastPing))
			deadNodes = append(deadNodes, nodeID)
			continue
		}
		snapshots = append(snapshots, clientSnapshot{nodeID, client.Conn, &client.WriteMu})
	}
	// RLock 释放后统一清理死连接（避免竞态）
	if len(deadNodes) > 0 {
		go func(ids []string) {
			time.Sleep(100 * time.Millisecond) // 等 FanOut 写完
			for _, nodeID := range ids {
				h.mu.Lock()
				if c, ok := h.clients[nodeID]; ok {
					c.Conn.Close()
					delete(h.clients, nodeID)
					h.DisconnectCount++
					log.Printf("📡 WS Hub: %s 空闲清理 (剩余 %d 个连接)", nodeID, len(h.clients))
				}
				h.mu.Unlock()
			}
		}(deadNodes)
	}

	// goroutine 并发写：一个节点阻塞不影响其他节点
	var wg sync.WaitGroup
	delivered := int32(0)
	for _, snap := range snapshots {
		wg.Add(1)
		go func(nid string, c *websocket.Conn, mu *sync.Mutex) {
			defer wg.Done()
			mu.Lock()
			c.SetWriteDeadline(time.Now().Add(10 * time.Second))
			err := c.WriteMessage(websocket.TextMessage, payload)
			mu.Unlock()
			if err == nil {
				atomic.AddInt32(&delivered, 1)
			} else {
				log.Printf("📡 WS FanOut 投递失败 (%s): %v", nid, err)
			}
		}(snap.nodeID, snap.conn, snap.mu)
	}

	wg.Wait()
	h.MessagesSent += int64(delivered)
	log.Printf("📡 WS FanOut: topic=%s, delivered=%d, total=%d", topic, delivered, len(h.clients))
	return int(delivered)
}

// FanOutAll 向所有在线节点分发（跳过 exceptID）
func (h *WSHub) FanOutAll(msg *WSMessage, exceptID string) int {
	h.mu.RLock()
	defer h.mu.RUnlock()

	// 补充元数据
	if msg.Timestamp == 0 {
		msg.Timestamp = time.Now().UnixMilli()
	}
	if msg.Seq == 0 {
		msg.Seq = uint64(time.Now().UnixNano())
	}

	payload, err := json.Marshal(msg)
	if err != nil {
		log.Printf("📡 WS FanOutAll 序列化失败: %v", err)
		return 0
	}

	// 快照 + goroutine 并发写
	type clientSnapshot struct {
		nodeID string
		conn   *websocket.Conn
	}
	type allSnapshot struct {
		nodeID string
		conn   *websocket.Conn
		mu     *sync.Mutex
	}
	allSnapshots := make([]allSnapshot, 0, len(h.clients))
	for nodeID, client := range h.clients {
		if nodeID == exceptID {
			continue
		}
		allSnapshots = append(allSnapshots, allSnapshot{nodeID, client.Conn, &client.WriteMu})
	}

	var wg sync.WaitGroup
	delivered := int32(0)
	for _, snap := range allSnapshots {
		wg.Add(1)
		go func(nid string, c *websocket.Conn, mu *sync.Mutex) {
			defer wg.Done()
			mu.Lock()
			c.SetWriteDeadline(time.Now().Add(10 * time.Second))
			err := c.WriteMessage(websocket.TextMessage, payload)
			mu.Unlock()
			if err == nil {
				atomic.AddInt32(&delivered, 1)
			}
		}(snap.nodeID, snap.conn, snap.mu)
	}

	wg.Wait()
	h.MessagesSent += int64(delivered)
	log.Printf("📡 WS FanOutAll: delivered=%d, total=%d", delivered, len(h.clients))
	return int(delivered)
}

// SendTo 向指定节点发送消息（Phase 3 P2P 基础）
func (h *WSHub) SendTo(nodeID string, msg *WSMessage) bool {
	h.mu.RLock()
	defer h.mu.RUnlock()

	client, ok := h.clients[nodeID]
	if !ok {
		return false
	}

	if msg.Timestamp == 0 {
		msg.Timestamp = time.Now().UnixMilli()
	}
	if msg.Seq == 0 {
		msg.Seq = uint64(time.Now().UnixNano())
	}

	payload, err := json.Marshal(msg)
	if err != nil {
		return false
	}

	// BUGFIX: 用 WriteMu 保护并发写冲突
	client.WriteMu.Lock()
	err = client.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
	if err != nil {
		client.WriteMu.Unlock()
		return false
	}

	err = client.Conn.WriteMessage(websocket.TextMessage, payload)
	client.WriteMu.Unlock()

	if err != nil {
		log.Printf("📡 WS SendTo (%s): %v", nodeID, err)
		return false
	}

	h.MessagesSent++
	return true
}

// PushTask 向指定节点推送任务（Phase 3：WS 推送替代 HTTP 轮询）
// 返回 true 表示推送成功且 Worker 5s 内回复了 ACK
// 返回 false 表示推送失败或 ACK 超时
// 推送失败时调用方应回退到 HTTP poll 兜底
func (h *WSHub) PushTask(nodeID string, task *TaskPollItem) bool {
	msg := &WSMessage{
		MsgType:  MsgTypeTask,
		SenderID: "gateway",
		Content:  task.TaskID,
		Payload:  mustMarshalJSON(task),
	}

	// 注册 ACK waiter（PushTask 前注册，防止 ACK 先于 PushTask 到达）
	ackCh := make(chan struct{})
	h.ackMu.Lock()
	h.ackChs[task.TaskID] = ackCh
	h.ackMu.Unlock()
	defer func() {
		h.ackMu.Lock()
		delete(h.ackChs, task.TaskID)
		h.ackMu.Unlock()
	}()

	// 发送
	sent := h.SendTo(nodeID, msg)
	if !sent {
		return false
	}

	// 等 ACK：5s 超时
	select {
	case <-ackCh:
		return true
	case <-time.After(5 * time.Second):
		log.Printf("📡 WS PushTask (%s): 任务 %s ACK 超时", nodeID, task.TaskID)
		return false
	}
}

// signalACK 通知 PushTask 调用方 Worker 已回复 ACK
func (h *WSHub) signalACK(taskID string) {
	h.ackMu.Lock()
	ch, ok := h.ackChs[taskID]
	h.ackMu.Unlock()
	if ok {
		close(ch)
	}
}

// mustMarshalJSON 安全的 JSON 序列化（panic 时返回空对象）
func mustMarshalJSON(v interface{}) json.RawMessage {
	data, err := json.Marshal(v)
	if err != nil {
		return json.RawMessage("{}")
	}
	return json.RawMessage(data)
}

// =============================================================================
// Step 2: HTTP→WS Upgrade Handler
// =============================================================================

// HandleWSUpgrade 处理 HTTP→WS 升级（SPEC-WS-001 §3.1）
// 客户端连接后首条消息必须是 register
func (h *WSHub) HandleWSUpgrade(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("📡 WS upgrade 失败: %v", err)
		return
	}

	// 读取第一条消息：注册信息
	_, msg, err := conn.ReadMessage()
	if err != nil {
		log.Printf("📡 WS 读注册消息失败: %v", err)
		conn.Close()
		return
	}

	var regMsg WSMessage
	if err := json.Unmarshal(msg, &regMsg); err != nil {
		log.Printf("📡 WS 非法 JSON: %s", string(msg))
		conn.WriteJSON(WSMessage{MsgType: MsgTypeRegistered, Status: "error", Error: "invalid JSON"})
		conn.Close()
		return
	}

	if regMsg.MsgType != MsgTypeRegister || regMsg.NodeID == "" {
		log.Printf("📡 WS 非法注册消息 (type=%s, node_id=%s)", regMsg.MsgType, regMsg.NodeID)
		conn.WriteJSON(WSMessage{
			MsgType: MsgTypeRegistered,
			Status:  "error",
			Error:   "first message must be register with node_id",
		})
		conn.Close()
		return
	}

	nodeID := regMsg.NodeID
	platform := regMsg.Platform
	if platform == "" {
		platform = "unknown"
	}

	// 注册客户端
	client := h.Register(nodeID, platform, conn)

	// 设置订阅
	if len(regMsg.SubTopics) > 0 {
		h.Subscribe(nodeID, regMsg.SubTopics)
	}

	// 回复注册成功
	conn.WriteJSON(WSMessage{
		MsgType:  MsgTypeRegistered,
		Status:   "ok",
		SenderID: "gateway",
		Seq:      client.Seq,
	})

	log.Printf("📡 WS: %s (%s) 注册成功 (话题: %v)", nodeID, platform, regMsg.SubTopics)

	// 进入读写循环（带 done channel 同步）
	done := make(chan struct{})
	go h.readPump(client, done)
	go h.writePump(client, done)
}

// readPump 持续读取客户端消息（SPEC-WS-001 §5.1）
// 处理: ping/pong, hall_send, broadcast, subscribe
// done: 当 readPump 退出时关闭，通知 writePump 同步停止
func (h *WSHub) readPump(client *WSClient, done chan struct{}) {
	defer func() {
		h.Unregister(client.NodeID)
		close(done)
	}()

	conn := client.Conn
	conn.SetReadLimit(16 * 1024) // 单帧最大 16KB
	conn.SetReadDeadline(time.Now().Add(60 * time.Second)) // BUGFIX: 读超时，避免死连接无限阻塞
	conn.SetPongHandler(func(string) error {
		client.LastPing = time.Now()
		// BUGFIX: 收到 pong 后重置读超时（延长 60s 窗口续命）
		conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, msg, err := conn.ReadMessage()
		if err != nil {
			// BUGFIX: 读超时 → 正常断连（重连比死连接好）
			if websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("📡 WS readPump (%s): 正常断开: %v", client.NodeID, err)
			} else if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
				log.Printf("📡 WS readPump (%s): 读超时, 断开 (Worker 会在 2s 后重连)", client.NodeID)
			} else {
				log.Printf("📡 WS readPump (%s): %v", client.NodeID, err)
			}
			return
		}

		// BUGFIX: 每次读到消息就重置读超时
		conn.SetReadDeadline(time.Now().Add(60 * time.Second))

		h.MessagesReceived++

		var envelope WSMessage
		if err := json.Unmarshal(msg, &envelope); err != nil {
			continue
		}

		switch envelope.MsgType {
		case MsgTypePing:
			// 回复 pong（WriteMu 保护并发写）
			client.WriteMu.Lock()
			conn.WriteJSON(WSMessage{
				MsgType:  MsgTypePong,
				SenderID: "gateway",
			})
			client.WriteMu.Unlock()

		case MsgTypePong:
			client.LastPing = time.Now()
			// BUGFIX: JSON pong 不走 SetPongHandler，必须手动重置读超时
			conn.SetReadDeadline(time.Now().Add(60 * time.Second))

		case MsgTypeSubscribe:
			// 变更订阅
			if len(envelope.SubTopics) > 0 {
				h.Subscribe(client.NodeID, envelope.SubTopics)
			}
			client.WriteMu.Lock()
			conn.WriteJSON(WSMessage{
				MsgType:  MsgTypeSubscribed,
				Status:   "ok",
				SenderID: "gateway",
			})
			client.WriteMu.Unlock()

		case MsgTypeHall:
			// 收到 Hall 消息 → 存入 HallState → FanOut
			if envelope.Topic == "" {
				envelope.Topic = "general"
			}
			// 通过现有 PostHallMessage 存储到 HallState
			PostHallMessage(envelope.Topic, envelope.From, envelope.FromName, envelope.To, envelope.Content)
			// FanOut 给所有订阅者（排除发送者自己）
			envelope.SenderID = client.NodeID
			h.FanOut(envelope.Topic, &envelope, client.NodeID)

		case MsgTypeArcNet:
			// ArcNet 广播由 Gateway 统一调度（COM-STD-001），不在 readPump 转发
			// envelope 丢弃，不 FanOut

		case MsgTypeTaskACK:
			// Worker 确认收到任务推送 → signal PushTask waiter
			log.Printf("📡 WS readPump (%s): 任务 %s 已确认", client.NodeID, envelope.Content)
			h.signalACK(envelope.Content)

		// ── Shell 交互终端 ──
		case MsgTypeShellOutput:
			// Worker→Gateway: Shell 输出 → 转发给 TUI
			h.routeShellOutputToTUI(&envelope)

		// ── TCP 隧道 ──
		case MsgTypeTunnelData:
			// tunnel-client→Gateway→tunnel-server: 转发 TCP 数据
			h.HandleTunnelData(&envelope)

		// ── Agent Direct Message 回复 ──
		case MsgTypeDirectReply:
			// Worker→Gateway: Agent 回复 → 存入 ReplyStore
			h.handleDirectReply(&envelope)

		default:
			log.Printf("📡 WS readPump (%s): 未知消息类型 %s", client.NodeID, envelope.MsgType)
		}
	}
}

// writePump 定期发送 ping 心跳（SPEC-WS-001 §5.1）
// done: 当 readPump 退出时关闭，通知 writePump 同步停止
//
// BUGFIX: writePump 检测到写失败时必须主动 Unregister，否则
// readPump 仍认为连接正常，Gateway 侧死连接不清理，任务推送失败。
// writePump 的 return 前调用 Unregister → conn.Close() → 触发
// readPump 的 ReadMessage 失败 → 走 readPump 的 defer Unregister
// （Unregister 是幂等的，二次调用时 client 已不在 map 中）。
//
// Android 兼容: Android 后台进程网络会被系统定期挂起（~30s 窗口）。
// ping 间隔从 10s 拉到 30s，减少命中 Android 网络休眠窗口的概率。
// 即使 ping 超时 → writePump Unregister → Worker 自动重连（2s 退避）。
func (h *WSHub) writePump(client *WSClient, done chan struct{}) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	conn := client.Conn

	for {
		select {
		case <-done:
			// readPump 已退出（连接已断），停止写
			return
		case <-ticker.C:
			// BUGFIX: WriteMu 保护并发写（FanOut/SendTo 可能同时写）
			client.WriteMu.Lock()
			err := conn.WriteJSON(WSMessage{
				MsgType:  MsgTypePing,
				SenderID: "gateway",
			})
			client.WriteMu.Unlock()
			if err != nil {
				log.Printf("📡 WS writePump (%s): %v → Unregister", client.NodeID, err)
				h.Unregister(client.NodeID) // BUGFIX: 主动清理死连接
				return
			}
		}
	}
}

// Close 关闭所有 WS 连接
func (h *WSHub) Close() {
	h.mu.Lock()
	defer h.mu.Unlock()

	for _, client := range h.clients {
		client.Conn.Close()
	}
	h.clients = make(map[string]*WSClient)
	log.Printf("📡 WS Hub: 已关闭所有连接")
}

// =============================================================================
// 工具函数
// =============================================================================

// IsWSConnected 检查节点是否通过 WS 连接
func (h *WSHub) IsWSConnected(nodeID string) bool {
	h.mu.RLock()
	defer h.mu.RUnlock()
	_, ok := h.clients[nodeID]
	return ok
}