// Copyright (c) 2026 ComputeHub. All rights reserved.
// Worker 大厅客户端 — WebSocket 版本（SPEC-WS-001）
//
// ARC-AI-NET-003 协议：
//   Worker 启动时通过 WS 连接 Gateway，接收即时消息推送
//   WS 失败时自动 fallback 到 HTTP poll（向后兼容）

package workercmd

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"runtime"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/computehub/opc/src/agent"
	"github.com/gorilla/websocket"
)

// ── Hall 消息结构（与 Gateway 侧一致） ──

// WSMessage WebSocket 消息（匹配 gateway.WSMessage 结构）
type WSMessage struct {
	MsgType   string          `json:"msg_type"`
	Seq       uint64          `json:"seq,omitempty"`
	Timestamp int64           `json:"ts"`
	TraceID   string          `json:"trace_id,omitempty"`
	SenderID  string          `json:"sender_id"`
	Priority  int             `json:"p,omitempty"`

	// 注册/心跳
	NodeID    string   `json:"node_id,omitempty"`
	Platform  string   `json:"platform,omitempty"`
	SubTopics []string `json:"sub_topics,omitempty"`
	Status    string   `json:"status,omitempty"`
	Error     string   `json:"error,omitempty"`

	// 数据消息
	Topic    string `json:"topic,omitempty"`
	From     string `json:"from,omitempty"`
	FromName string `json:"from_name,omitempty"`
	To       string `json:"to,omitempty"`
	Content  string `json:"content,omitempty"`

	// 广播/拓扑
	Event   string          `json:"event,omitempty"`
	Payload json.RawMessage `json:"payload,omitempty"`
}

// HallMessage 大厅消息结构（与 Gateway 匹配）
type HallMessage struct {
	MsgID     string    `json:"msg_id"`
	Topic     string    `json:"topic"`
	From      string    `json:"from"`
	FromName  string    `json:"from_name"`
	To        string    `json:"to"`
	Content   string    `json:"content"`
	Timestamp time.Time `json:"timestamp"`
	Seq       int64     `json:"seq"`
}

// circuitBreaker 熔断器状态（SPEC-WS-001 §5.3）
type circuitBreaker struct {
	mu               sync.Mutex
	consecutiveFails int
	lastFailTime     time.Time
	poweredDown      bool
	poweredDownUntil time.Time
}

// HallClient 大厅客户端 — 每个 Worker 一个（SPEC-WS-001 §5.1）
type HallClient struct {
	mu          sync.Mutex
	nodeID      string
	nodeName    string
	gatewayURL  string
	httpClient  *http.Client
	wsConn      *websocket.Conn    // WS 连接
	wsMu        sync.Mutex         // WS 写锁（gorilla 不支持并发写）
	agt         *agent.Agent
	lastSeqs    map[string]int64
	enabled     bool
	stopCh      chan struct{}
	stopOnce    sync.Once          // BUGFIX: 保护 close(stopCh) 不 panic
	replyChan   chan HallMessage
	processedIDs map[string]bool
	orderedIDs   []string           // LRU 顺序：按添加顺序记录 msgID
	thinkSem    chan struct{}
	cb          *circuitBreaker
	cancelHall  context.CancelFunc  // 取消所有 Hall 相关 goroutine
	cancelOnce  sync.Once          // BUGFIX: 保护 cancelHall 不 panic（二次调用）
	hallCtx     context.Context     // Hall 生命周期 context
	taskHandler func(taskID, command string, timeout int) // Phase 3: WS 任务推送处理器

	// WS 状态通知：指向 WorkerState.isWSConnected (atomic int32)
	// WS 连接成功 → Store(1), 断开 → Store(0)
	wsOnlineFlag *int32
}

// NewHallClient 创建大厅客户端（SPEC-WS-001 §5.1）
func NewHallClient(nodeID, nodeName, gatewayURL string) *HallClient {
	// 自定义 DNS 解析（8.8.8.8），解决 Android 无本地 DNS 的问题
	resolver := &net.Resolver{
		PreferGo: true,
		Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
			d := net.Dialer{}
			return d.DialContext(ctx, "udp", "8.8.8.8:53")
		},
	}
	dialer := &net.Dialer{
		Timeout:  5 * time.Second,
		Resolver: resolver,
	}
	transport := &http.Transport{
		DialContext: dialer.DialContext,
	}
	return &HallClient{
		nodeID:       nodeID,
		nodeName:     nodeName,
		gatewayURL:   strings.TrimRight(gatewayURL, "/"),
		httpClient:   &http.Client{Timeout: 10 * time.Second, Transport: transport},
		lastSeqs:     make(map[string]int64),
		stopCh:       make(chan struct{}),
		replyChan:    make(chan HallMessage, 20),
		processedIDs: make(map[string]bool),
		enabled:      true,
		thinkSem:     make(chan struct{}, 3),
		cb:           &circuitBreaker{},
	}
}

// SetWSOnlineFlag 设置 WS 连接状态通知指针
// 外部调用：传入 WorkerState.isWSConnected 的 & 地址
func (hc *HallClient) SetWSOnlineFlag(flag *int32) {
	hc.mu.Lock()
	defer hc.mu.Unlock()
	hc.wsOnlineFlag = flag
	// 初始值：未连接
	if flag != nil {
		atomic.StoreInt32(flag, 0)
	}
}
func (hc *HallClient) SetAgent(agt *agent.Agent) {
	hc.mu.Lock()
	defer hc.mu.Unlock()
	hc.agt = agt
}

// SetTaskHandler 设置 WS 任务推送处理器（Phase 3）
// 当 Gateway 通过 WS 推送任务时，调用此处理器执行任务
func (hc *HallClient) SetTaskHandler(handler func(taskID, command string, timeout int)) {
	hc.mu.Lock()
	defer hc.mu.Unlock()
	hc.taskHandler = handler
}

// Enable/Disable 控制开关
func (hc *HallClient) Enable()  { hc.mu.Lock(); defer hc.mu.Unlock(); hc.enabled = true }
func (hc *HallClient) Disable() { hc.mu.Lock(); defer hc.mu.Unlock(); hc.enabled = false }

// ── WS 连接主循环（SPEC-WS-001 §3.4） ──

// StartPollLoop 启动消息接收循环
// 先尝试 WS，失败则用 HTTP poll 兜底
func (hc *HallClient) StartPollLoop() {
	ctx, cancel := context.WithCancel(context.Background())
	hc.cancelHall = cancel
	hc.hallCtx = ctx

	go func() {
		time.Sleep(3 * time.Second) // 等 Gateway 就绪

		// 先尝试 WS 连接
		if hc.tryConnectWS() {
			fmt.Printf(" [HallClient:%s] ✅ 使用 WebSocket 模式\n", hc.nodeID)
			hc.sendIntroMessage() // 发自我介绍
			hc.wsReadLoop()       // 进入 WS 接收循环（阻塞，断线返回）
		}

		// WS 失败（或断线），启动 HTTP poll 后台重连
		fmt.Printf(" [HallClient:%s] ⚠️ 使用 HTTP poll 模式（后台重试 WS）\n", hc.nodeID)
		go hc.backgroundWSReconnect()
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-hc.stopCh:
				fmt.Printf(" [HallClient:%s] ⏹ 停止\n", hc.nodeID)
				return
			case <-ticker.C:
				hc.pollOnce()
			}
		}
	}()
}

// tryConnectWS 尝试建立 WS 连接 + 注册
func (hc *HallClient) tryConnectWS() bool {
	wsURL := strings.Replace(hc.gatewayURL, "http://", "ws://", 1) + "/api/v1/ws"

	dialer := websocket.Dialer{
		HandshakeTimeout: 5 * time.Second,
	}

	conn, _, err := dialer.Dial(wsURL, nil)
	if err != nil {
		fmt.Printf(" [HallClient:%s] ⚠️ WS 连接失败: %v\n", hc.nodeID, err)
		return false
	}

	// 发送注册消息
	regMsg := WSMessage{
		MsgType:   "register",
		NodeID:    hc.nodeID,
		Platform:  runtime.GOOS + "/" + runtime.GOARCH,
		SubTopics: []string{"general", "alerts", hc.nodeID},
	}

	hc.wsMu.Lock()
	err = conn.WriteJSON(regMsg)
	hc.wsMu.Unlock()
	if err != nil {
		fmt.Printf(" [HallClient:%s] ⚠️ WS 注册发送失败: %v\n", hc.nodeID, err)
		conn.Close()
		return false
	}

	// 读取注册确认
	var resp WSMessage
	err = conn.ReadJSON(&resp)
	if err != nil {
		fmt.Printf(" [HallClient:%s] ⚠️ WS 注册读取响应失败: %v\n", hc.nodeID, err)
		conn.Close()
		return false
	}

	if resp.Status != "ok" {
		fmt.Printf(" [HallClient:%s] ⚠️ WS 注册被拒: %s\n", hc.nodeID, resp.Error)
		conn.Close()
		return false
	}

	// 注册成功，保存连接并标记 WS 在线
	hc.wsMu.Lock()
	hc.wsConn = conn
	hc.wsMu.Unlock()
	if hc.wsOnlineFlag != nil {
		atomic.StoreInt32(hc.wsOnlineFlag, 1)
	}

	fmt.Printf(" [HallClient:%s] ✅ WS 连接注册成功\n", hc.nodeID)
	return true
}

// wsReadLoop 持续读取 WS 消息（替代 pollOnce）
func (hc *HallClient) wsReadLoop() {
	conn := hc.wsConn

	// BUGFIX: 设置 pong 处理器 + 读超时
	// Gateway writePump 每 30s 发 ping，Worker 回复 pong
	// Worker 读超时 60s — 超过 60s 无消息（含 ping）即断连
	// readPump 可以读到 ping 但不会产生 pong 事件，所以我们自己在 ping 处理器里处理
	// 注意 setReadDeadline 只在 ReadMessage/ReadJSON 时生效
	conn.SetReadDeadline(time.Now().Add(60 * time.Second))

	for {
		select {
		case <-hc.stopCh:
			return
		default:
		}

		var envelope WSMessage
		err := conn.ReadJSON(&envelope)
		if err != nil {
			// BUGFIX: 区分正常断开和读超时
			if websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
				fmt.Printf(" [HallClient:%s] ⚠️ WS 正常断开: %v\n", hc.nodeID, err)
			} else if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
				fmt.Printf(" [HallClient:%s] ⚠️ WS 读超时 (60s 无消息), 断连触发重连\n", hc.nodeID)
			} else {
				fmt.Printf(" [HallClient:%s] ⚠️ WS 读消息失败: %v\n", hc.nodeID, err)
			}
			// BUGFIX: 只关此 wsReadLoop 开头捕获的 conn，不碰 hc.wsConn
			// backgroundWSReconnect 可能已替换 hc.wsConn 为新连接
			conn.Close()
			hc.wsMu.Lock()
			if hc.wsConn == conn {
				hc.wsConn = nil
			}
			hc.wsMu.Unlock()
			if hc.wsOnlineFlag != nil {
				atomic.StoreInt32(hc.wsOnlineFlag, 0)
			}
			return
		}

		// BUGFIX: 每收到一条消息重置读超时（续命 60s 窗口）
		conn.SetReadDeadline(time.Now().Add(60 * time.Second))

		switch envelope.MsgType {
		case "ping":
			hc.wsMu.Lock()
			hc.wsConn.WriteJSON(WSMessage{MsgType: "pong", SenderID: hc.nodeID, NodeID: hc.nodeID})
			hc.wsMu.Unlock()

		case "pong":
			// 心跳回复，不需要处理

		case "hall", "hall_message":
			// 构造 HallMessage 并触发 Agent
			hallMsg := HallMessage{
				MsgID:     fmt.Sprintf("ws-%d", time.Now().UnixNano()),
				Topic:     envelope.Topic,
				From:      envelope.From,
				FromName:  envelope.FromName,
				To:        envelope.To,
				Content:   envelope.Content,
				Timestamp: time.Now(),
				Seq:       int64(envelope.Seq),
			}

			if hallMsg.Topic == "" {
				hallMsg.Topic = "general"
			}
			if hallMsg.To == "" {
				hallMsg.To = "all"
			}

			// 去重
			hc.mu.Lock()
			if hc.processedIDs[hallMsg.MsgID] {
				hc.mu.Unlock()
				continue
			}
			hc.markProcessed(hallMsg.MsgID)
			if hallMsg.Seq > hc.lastSeqs[hallMsg.Topic] {
				hc.lastSeqs[hallMsg.Topic] = hallMsg.Seq
			}
			hc.mu.Unlock()

			// 跳过自己发的消息
			if hallMsg.From == hc.nodeID {
				continue
			}

			// 清理 processedIDs（LRU 淘汰，保留最近 300 条）
			hc.mu.Lock()
			hc.trimProcessedIDs()
			hc.mu.Unlock()

			// 触发 Agent 回复
			go hc.thinkAndReply(hallMsg)

		case "arc_net":
			// ARC-NET 广播 - 不需要 Agent 处理，日志即可
			fmt.Printf(" [HallClient:%s] 📡 ARC-NET: event=%s, sender=%s\n",
				hc.nodeID, envelope.Event, envelope.SenderID)

		case "task":
			// Phase 3: Gateway 通过 WS 推送任务，无需 HTTP 轮询
			if envelope.SenderID == "gateway" && envelope.Payload != nil {
				var task struct {
					TaskID     string `json:"task_id"`
					Command    string `json:"command"`
					Timeout    int    `json:"timeout"`
					Priority   int    `json:"priority"`
					NodeID     string `json:"node_id"`
					SourceType string `json:"source_type"`
				}
				if err := json.Unmarshal(envelope.Payload, &task); err == nil && task.TaskID != "" {
					fmt.Printf(" [HallClient:%s] 📡 WS 收到任务推送: %s\n", hc.nodeID, task.TaskID)

					// 回复 ACK
					hc.wsMu.Lock()
					if hc.wsConn != nil {
						hc.wsConn.WriteJSON(WSMessage{
							MsgType:  "task_ack",
							SenderID: hc.nodeID,
							Content:  task.TaskID,
						})
					}
					hc.wsMu.Unlock()

					// 调用任务处理器执行（异步，不阻塞 WS 读取循环）
					hc.mu.Lock()
					handler := hc.taskHandler
					hc.mu.Unlock()
					if handler != nil {
						go handler(task.TaskID, task.Command, task.Timeout)
					}
				}
			}

		// ── Shell 交互终端 ──
		case "shell_open":
			// Gateway 通知 Worker 打开 Shell 会话
			var shellCmd struct {
				SessionID string `json:"session_id"`
				Rows      uint16 `json:"rows,omitempty"`
				Cols      uint16 `json:"cols,omitempty"`
			}
			if envelope.Payload != nil {
				json.Unmarshal(envelope.Payload, &shellCmd)
			}
			if shellCmd.Rows == 0 {
				shellCmd.Rows = 24
			}
			if shellCmd.Cols == 0 {
				shellCmd.Cols = 80
			}
			sm := GetShellManager()
			if err := sm.StartShell(shellCmd.SessionID, hc.nodeID, hc.wsConn, shellCmd.Rows, shellCmd.Cols); err != nil {
				log.Printf("💻 [Shell] 启动会话 %s 失败: %v", shellCmd.SessionID, err)
			}

		case "shell_input":
			// Gateway 转发 TUI 键盘输入
			var input struct {
				SessionID string `json:"session_id"`
				Data      string `json:"data"`
			}
			if envelope.Payload != nil {
				json.Unmarshal(envelope.Payload, &input)
			}
			if input.SessionID != "" {
				sm := GetShellManager()
				if data, err := json.Marshal(map[string]string{"data": input.Data}); err == nil {
					sm.HandleShellInput(input.SessionID, data, false)
				}
			}

		case "shell_resize":
			// Gateway 转发 TUI 窗口大小变化
			var resize struct {
				SessionID string `json:"session_id"`
				Rows      uint16 `json:"rows"`
				Cols      uint16 `json:"cols"`
			}
			if envelope.Payload != nil {
				json.Unmarshal(envelope.Payload, &resize)
			}
			if resize.SessionID != "" {
				sm := GetShellManager()
				sm.HandleShellResize(resize.SessionID, resize.Rows, resize.Cols)
			}

		case "shell_close":
			// Gateway 通知 Worker 关闭 Shell 会话
			var closeMsg struct {
				SessionID string `json:"session_id"`
			}
			if envelope.Payload != nil {
				json.Unmarshal(envelope.Payload, &closeMsg)
			}
			if closeMsg.SessionID != "" {
				sm := GetShellManager()
				sm.CloseSession(closeMsg.SessionID, hc.wsConn)
			}

		case "direct_message":
			// 端智→Worker: P2P 直接消息（银河计划 Phase 2）
			// 提取 msg_id 和 from
			var dmPayload struct {
				MsgID string `json:"msg_id"`
				From  string `json:"from"`
			}
			if envelope.Payload != nil {
				json.Unmarshal(envelope.Payload, &dmPayload)
			}
			msgID := dmPayload.MsgID
			senderName := dmPayload.From
			if senderName == "" {
				senderName = envelope.SenderID
			}
			if senderName == "" {
				senderName = "端智"
			}

			fmt.Printf(" [HallClient:%s] 📬 DM 来自 %s: %s\n", hc.nodeID, senderName, truncateStr(envelope.Content, 100))

			// 异步调用 Agent 思考并回复
			go hc.thinkAndReplyDirect(msgID, senderName, envelope.Content)

		default:
			fmt.Printf(" [HallClient:%s] 📬 WS 未知消息: %s\n", hc.nodeID, envelope.MsgType)
		}
	}
}

// backgroundWSReconnect 后台重试 WS 连接（指数退避）
// 修复: wsReadLoop 返回后至少等待 2s 再重试，避免频繁断连时的重连风暴
func (hc *HallClient) backgroundWSReconnect() {
	backoff := 2 * time.Second // 最低 2s 等待，避免重连风暴
	maxBackoff := 30 * time.Second
	minBackoff := 2 * time.Second

	for {
		select {
		case <-hc.stopCh:
			return
		default:
		}

		fmt.Printf(" [HallClient:%s] ⏳ 重连等待 %v...\n", hc.nodeID, backoff)
		time.Sleep(backoff)

		if hc.tryConnectWS() {
			fmt.Printf(" [HallClient:%s] ✅ WS 重连成功，切换回 WS 模式\n", hc.nodeID)
			hc.sendIntroMessage()

			// BUGFIX: 记录 wsReadLoop 开始时间，判断是"稳定连接"还是"秒断"
			loopStart := time.Now()
			hc.wsReadLoop() // WS 循环结束返回后说明又断了
			loopDuration := time.Since(loopStart)

			fmt.Printf(" [HallClient:%s] ⚠️ WS 再次断开 (持续 %v), 重试重连\n", hc.nodeID, loopDuration.Round(time.Second))

			// BUGFIX: 如果连接只持续了 <15s，说明网络不稳定，不要归零 backoff
			// 而是翻倍 backoff 防止重新连接风暴
			if loopDuration < 15*time.Second {
				backoff *= 2
				if backoff > maxBackoff {
					backoff = maxBackoff
				}
				fmt.Printf(" [HallClient:%s] ⚠️ 连接不稳定 (仅持续 %v), backoff=%v\n", hc.nodeID, loopDuration.Round(time.Second), backoff)
			} else {
				backoff = minBackoff
			}
			continue
		}

		// 指数退避
		backoff *= 2
		if backoff > maxBackoff {
			backoff = maxBackoff
		}
	}
}

// sendIntroMessage 发送自我介绍消息
func (hc *HallClient) sendIntroMessage() {
	hc.postMessage("general", hc.nodeID, hc.nodeName, "all",
		fmt.Sprintf("🏛️ %s (%s) 已加入大厅 (WS)", hc.nodeName, hc.nodeID))
}

// ── HTTP Poll 方式（向后兼容） ──

// pollOnce 单次 HTTP 轮询
func (hc *HallClient) pollOnce() {
	hc.mu.Lock()
	agt := hc.agt
	enabled := hc.enabled
	hc.mu.Unlock()

	if !enabled || agt == nil {
		return
	}

	hc.mu.Lock()
	var maxSeq int64
	for _, seq := range hc.lastSeqs {
		if seq > maxSeq {
			maxSeq = seq
		}
	}
	hc.mu.Unlock()

	pollURL := fmt.Sprintf("%s/api/v1/hall/poll?node_id=%s&since_seq=%d", hc.gatewayURL, hc.nodeID, maxSeq)

	resp, err := hc.httpClient.Get(pollURL)
	if err != nil {
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return
	}

	var wrapper struct {
		Success bool `json:"success"`
		Data    struct {
			Messages []HallMessage `json:"messages"`
		} `json:"data"`
	}
	if err := json.Unmarshal(body, &wrapper); err != nil {
		return
	}

	if !wrapper.Success || len(wrapper.Data.Messages) == 0 {
		return
	}

	messages := wrapper.Data.Messages
	if len(messages) > 3 {
		hc.mu.Lock()
		skipCount := len(messages) - 3
		for i := 0; i < skipCount; i++ {
			msg := messages[i]
			if msg.Seq > hc.lastSeqs[msg.Topic] {
				hc.lastSeqs[msg.Topic] = msg.Seq
			}
			hc.processedIDs[msg.MsgID] = true
		}
		hc.mu.Unlock()
		messages = messages[len(messages)-3:]
	}

	for i := range messages {
		msg := messages[i]
		hc.mu.Lock()
		if hc.processedIDs[msg.MsgID] {
			hc.mu.Unlock()
			continue
		}
		hc.markProcessed(msg.MsgID)
		if msg.Seq > hc.lastSeqs[msg.Topic] {
			hc.lastSeqs[msg.Topic] = msg.Seq
		}
		hc.mu.Unlock()

		if msg.From == hc.nodeID {
			continue
		}

		go hc.thinkAndReply(msg)
	}
}

// ── 发送消息 ──

// PostMessage 发送一条消息到大庭（公开接口）
func (hc *HallClient) PostMessage(topic, to, content string) {
	hc.postMessage(topic, hc.nodeID, hc.nodeName, to, content)
}

// postMessage 发送消息 — WS 优先，HTTP fallback
func (hc *HallClient) postMessage(topic, from, fromName, to, content string) {
	// WS 优先发送
	hc.wsMu.Lock()
	if hc.wsConn != nil {
		msg := WSMessage{
			MsgType:  "hall",
			Topic:    topic,
			From:     from,
			FromName: fromName,
			To:       to,
			Content:  content,
		}
		err := hc.wsConn.WriteJSON(msg)
		hc.wsMu.Unlock()
		if err == nil {
			return
		}
		// WS 失败
		fmt.Printf(" [HallClient:%s] ⚠️ WS 发送失败, fallback HTTP: %v\n", hc.nodeID, err)
	} else {
		hc.wsMu.Unlock()
	}

	// HTTP fallback
	payload := map[string]string{
		"topic":     topic,
		"from":      from,
		"node_name": fromName,
		"to":        to,
		"content":   content,
	}
	body, _ := json.Marshal(payload)
	resp, err := hc.httpClient.Post(
		hc.gatewayURL+"/api/v1/hall/post",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		fmt.Printf(" [HallClient:%s] ❌ HTTP 发消息失败: %v\n", hc.nodeID, err)
		return
	}
	resp.Body.Close()
}

// ── Agent 回复（含智能节流） ──

// thinkAndReply 使用 Agent 思考并回复消息（限流 + 熔断保护）
func (hc *HallClient) thinkAndReply(msg HallMessage) {
	hc.mu.Lock()
	agt := hc.agt
	hc.mu.Unlock()
	if agt == nil {
		return
	}

	// ── 智能节流（SPEC-WS-001 §Phase 3） ──
	// 话题=general 且未 @ 本节点，不调 LLM
	if msg.Topic == "general" && !strings.Contains(msg.Content, "@"+hc.nodeID) {
		fmt.Printf(" [HallClient:%s] 🔇 跳过 LLM 回复 (topic=general, 未@本节点)\n", hc.nodeID)
		return
	}

	// 熔断检查
	hc.cb.mu.Lock()
	if hc.cb.poweredDown {
		if time.Now().Before(hc.cb.poweredDownUntil) {
			remaining := time.Until(hc.cb.poweredDownUntil).Round(time.Second)
			fmt.Printf(" [HallClient:%s] ⛔ 熔断中，跳过消息（剩余 %v）\n", hc.nodeID, remaining)
			hc.cb.mu.Unlock()
			return
		}
		hc.cb.poweredDown = false
		hc.cb.consecutiveFails = 0
		fmt.Printf(" [HallClient:%s] 🔄 熔断恢复\n", hc.nodeID)
	}
	hc.cb.mu.Unlock()

	// 限流：获取信号量
	select {
	case hc.thinkSem <- struct{}{}:
	default:
		fmt.Printf(" [HallClient:%s] ⏳ 处理队列满，跳过消息 %s\n", hc.nodeID, msg.MsgID)
		return
	}
	defer func() { <-hc.thinkSem }()

	// 构建 Agent 任务
	task := fmt.Sprintf(
		"【大厅群聊】话题: %s | 来自: %s (%s) | 内容: %s\n\n"+
			"你是 Computing 集群中的 %s (%s)，请回应这条消息。"+
			"确认收到即可，不超过 2 句话。使用 exec_local 工具查看本节点状态后回复。"+
			"回复格式: 用中文，体现出你知道其他节点也在线。"+
			"回复后，把回复内容用 ARC-AI-NET-003 协议 POST 到 Gateway 大厅（topic=%s, to=all）。",
		msg.Topic, msg.FromName, msg.From, msg.Content,
		hc.nodeName, hc.nodeID, msg.Topic)

	// 使用 HallClient 的 cancellable context 作为父 context
	// 当 StopPollLoop 调用 cancelHall 时，所有正在运行的 thinkAndReply 立即退出
	hc.mu.Lock()
	hallCtx := hc.hallCtx
	hc.mu.Unlock()

	var ctx context.Context
	var cancel context.CancelFunc
	if hallCtx != nil {
		ctx, cancel = context.WithTimeout(hallCtx, 60*time.Second)
	} else {
		ctx, cancel = context.WithTimeout(context.Background(), 60*time.Second)
	}
	defer cancel()

	resp, err := agt.Think(ctx, &agent.AgentRequest{
		Task:      task,
		SessionID: fmt.Sprintf("hall-%s-%d", hc.nodeID, time.Now().UnixNano()),
		FastReply: true, // 群聊回复用快速模式：1 次 LLM 调用，跳过 plan
	})
	if err != nil {
		fmt.Printf(" [HallClient:%s] ❌ Agent 思考失败: %v\n", hc.nodeID, err)
		hc.cb.mu.Lock()
		hc.cb.consecutiveFails++
		hc.cb.lastFailTime = time.Now()
		if hc.cb.consecutiveFails >= 3 {
			hc.cb.poweredDown = true
			duration := time.Duration(hc.cb.consecutiveFails*15) * time.Second
			if duration > 120*time.Second {
				duration = 120 * time.Second
			}
			hc.cb.poweredDownUntil = time.Now().Add(duration)
			fmt.Printf(" [HallClient:%s] 🛑 连续 %d 次失败，熔断暂停 %v\n", hc.nodeID, hc.cb.consecutiveFails, duration)
		}
		hc.cb.mu.Unlock()
		return
	}

	hc.cb.mu.Lock()
	hc.cb.consecutiveFails = 0
	hc.cb.mu.Unlock()

	replyContent := resp.Result
	if replyContent == "" {
		replyContent = resp.Thought
	}
	if replyContent == "" {
		replyContent = fmt.Sprintf("✅ 收到 %s 的消息！", msg.FromName)
	}
	if len(replyContent) > 500 {
		replyContent = replyContent[:500] + "..."
	}

	hc.postMessage(msg.Topic, hc.nodeID, hc.nodeName, "all",
		fmt.Sprintf("💬 [回复 %s] %s", msg.FromName, replyContent))

	fmt.Printf(" [HallClient:%s] 💬 回复了 %s 的消息\n", hc.nodeID, msg.FromName)
}

// thinkAndReplyDirect 处理端智发来的 direct_message，回复走 WS direct_reply
func (hc *HallClient) thinkAndReplyDirect(msgID, senderName, content string) {
	hc.mu.Lock()
	agt := hc.agt
	hc.mu.Unlock()
	if agt == nil {
		return
	}

	// 熔断检查
	hc.cb.mu.Lock()
	if hc.cb.poweredDown {
		if time.Now().Before(hc.cb.poweredDownUntil) {
			remaining := time.Until(hc.cb.poweredDownUntil).Round(time.Second)
			fmt.Printf(" [HallClient:%s] ⛔ 熔断中，跳过 DM（剩余 %v）\n", hc.nodeID, remaining)
			hc.cb.mu.Unlock()
			return
		}
		hc.cb.poweredDown = false
		hc.cb.consecutiveFails = 0
		fmt.Printf(" [HallClient:%s] 🔄 熔断恢复\n", hc.nodeID)
	}
	hc.cb.mu.Unlock()

	// 限流
	select {
	case hc.thinkSem <- struct{}{}:
	default:
		fmt.Printf(" [HallClient:%s] ⏳ 处理队列满，跳过 DM\n", hc.nodeID)
		return
	}
	defer func() { <-hc.thinkSem }()

	// 构建 Agent 任务 — 直接消息，要求回复
	task := fmt.Sprintf(
		"【直接消息】来自: %s | 内容: %s\n\n"+
			"你是 Computing 集群中的 %s (%s)，请直接回复这条消息。"+
			"回复要简洁、直接、有用，不超过 3 句话。",
		senderName, content,
		hc.nodeName, hc.nodeID)

	hc.mu.Lock()
	hallCtx := hc.hallCtx
	hc.mu.Unlock()

	var ctx context.Context
	var cancel context.CancelFunc
	if hallCtx != nil {
		ctx, cancel = context.WithTimeout(hallCtx, 60*time.Second)
	} else {
		ctx, cancel = context.WithTimeout(context.Background(), 60*time.Second)
	}
	defer cancel()

	resp, err := agt.Think(ctx, &agent.AgentRequest{
		Task:      task,
		SessionID: fmt.Sprintf("dm-%s-%d", hc.nodeID, time.Now().UnixNano()),
		FastReply: true,
	})
	if err != nil {
		fmt.Printf(" [HallClient:%s] ❌ DM Agent 思考失败: %v\n", hc.nodeID, err)
		hc.cb.mu.Lock()
		hc.cb.consecutiveFails++
		hc.cb.lastFailTime = time.Now()
		if hc.cb.consecutiveFails >= 3 {
			hc.cb.poweredDown = true
			duration := time.Duration(hc.cb.consecutiveFails*15) * time.Second
			if duration > 120*time.Second {
				duration = 120 * time.Second
			}
			hc.cb.poweredDownUntil = time.Now().Add(duration)
			fmt.Printf(" [HallClient:%s] 🛑 连续 %d 次失败，熔断暂停 %v\n", hc.nodeID, hc.cb.consecutiveFails, duration)
		}
		hc.cb.mu.Unlock()
		return
	}

	hc.cb.mu.Lock()
	hc.cb.consecutiveFails = 0
	hc.cb.mu.Unlock()

	replyContent := resp.Result
	if replyContent == "" {
		replyContent = resp.Thought
	}
	if replyContent == "" {
		replyContent = fmt.Sprintf("✅ 收到 %s 的消息！", senderName)
	}
	if len(replyContent) > 2000 {
		replyContent = replyContent[:2000] + "..."
	}

	// 通过 WS 发送 direct_reply 回 Gateway
	hc.wsMu.Lock()
	if hc.wsConn != nil {
		replyMsg := WSMessage{
			MsgType:  "direct_reply",
			SenderID: hc.nodeID,
			Content:  replyContent,
			Payload:  mustMarshalJSON(map[string]string{"msg_id": msgID, "content": replyContent}),
		}
		err := hc.wsConn.WriteJSON(replyMsg)
		hc.wsMu.Unlock()
		if err != nil {
			fmt.Printf(" [HallClient:%s] ❌ DM 回复 WS 发送失败: %v\n", hc.nodeID, err)
		} else {
			fmt.Printf(" [HallClient:%s] 💬 DM 回复 %s: %s\n", hc.nodeID, senderName, truncateStr(replyContent, 80))
		}
	} else {
		hc.wsMu.Unlock()
		fmt.Printf(" [HallClient:%s] ⚠️ DM 回复失败: WS 未连接\n", hc.nodeID)
	}
}

// mustMarshalJSON 安全的 JSON 序列化
func mustMarshalJSON(v interface{}) json.RawMessage {
	data, err := json.Marshal(v)
	if err != nil {
		return json.RawMessage("{}")
	}
	return json.RawMessage(data)
}

// StopPollLoop 停止轮询
func (hc *HallClient) StopPollLoop() {
	hc.wsMu.Lock()
	if hc.wsConn != nil {
		hc.wsConn.Close()
		hc.wsConn = nil
	}
	hc.wsMu.Unlock()

	// BUGFIX: 用 sync.Once 保护 close(stopCh)，避免二次调用时 panic
	hc.stopOnce.Do(func() {
		close(hc.stopCh)
	})

	// 取消所有正在运行的 thinkAndReply goroutine
	// BUGFIX: 用 sync.Once 保护 cancelHall，避免二次调用 panic
	hc.cancelOnce.Do(func() {
		if hc.cancelHall != nil {
			hc.cancelHall()
		}
	})
}

// ── Tool 注册 ──

// registerHallTools 注册 hall_speak 和 hall_listen 工具到 Agent 工具集
func registerHallTools(tr *agent.ToolRegistry, hc *HallClient) {
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "hall_speak",
			Description: "向 Gateway AI Hall 发送群聊消息，所有在线 Worker Agent 都能看到。topic=话题, to=all(全体) 或具体节点ID, content=消息内容",
			Parameters: []agent.Param{
				{Name: "topic", Type: "string", Required: true, Description: "话题名称，如 general"},
				{Name: "to", Type: "string", Required: true, Description: "目标: 'all' 全体或 node_id"},
				{Name: "content", Type: "string", Required: true, Description: "消息内容"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			topic, _ := args["topic"].(string)
			to, _ := args["to"].(string)
			content, _ := args["content"].(string)
			if topic == "" {
				topic = "general"
			}
			if to == "" {
				to = "all"
			}
			if content == "" {
				return "", fmt.Errorf("content is required")
			}
			hc.PostMessage(topic, to, content)
			return fmt.Sprintf("✅ 已向大厅 [%s] 发送消息", topic), nil
		},
	})

	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "hall_listen",
			Description: "查看 Gateway AI Hall 最近的消息和话题。通过参数 topic 指定话题，默认 general。获取该话题最近的消息列表。",
			Parameters: []agent.Param{
				{Name: "topic", Type: "string", Required: false, Description: "话题名称，默认 general"},
				{Name: "limit", Type: "int", Required: false, Description: "返回消息数，默认 10"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			topic, _ := args["topic"].(string)
			if topic == "" {
				topic = "general"
			}
			limit := 10
			if l, ok := args["limit"].(float64); ok {
				limit = int(l)
			}
			return hc.listen(topic, limit), nil
		},
	})
}

// listen 从大厅拉取消息（HTTP fallback 方式）
func (hc *HallClient) listen(topic string, limit int) string {
	url := fmt.Sprintf("%s/api/v1/hall/messages?topic=%s&limit=%d&node_id=%s",
		hc.gatewayURL, topic, limit, hc.nodeID)
	resp, err := hc.httpClient.Get(url)
	if err != nil {
		return fmt.Sprintf("❌ 连接失败: %v", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var wrapper struct {
		Success bool `json:"success"`
		Data    struct {
			Messages []HallMessage `json:"messages"`
			Topic    string        `json:"topic"`
		} `json:"data"`
	}
	if err := json.Unmarshal(body, &wrapper); err != nil {
		return fmt.Sprintf("❌ 解析失败: %v", err)
	}
	if !wrapper.Success {
		return "❌ 获取失败"
	}

	msgs := wrapper.Data.Messages
	if len(msgs) == 0 {
		return fmt.Sprintf("📭 话题 [%s] 暂无新消息", wrapper.Data.Topic)
	}

	var b strings.Builder
	b.WriteString(fmt.Sprintf("📋 话题 [%s] 最近 %d 条消息:\n", wrapper.Data.Topic, len(msgs)))
	for _, m := range msgs {
		b.WriteString(fmt.Sprintf("  [%s] %s: %s\n", m.FromName, m.From, truncateStr(m.Content, 100)))
	}
	return b.String()
}

func truncateStr(s string, maxLen int) string {
	runes := []rune(s)
	if len(runes) > maxLen {
		return string(runes[:maxLen]) + "..."
	}
	return s
}

// ── 工具函数 ──

// trimProcessedIDs LRU 淘汰 processedIDs，避免暴力清空导致去重失效
// 保留最近 300 条，淘汰最旧的
func (hc *HallClient) trimProcessedIDs() {
	if len(hc.processedIDs) <= 500 {
		return
	}
	removed := len(hc.processedIDs) - 300
	newIDs := make(map[string]bool, 300)
	newOrder := make([]string, 0, 300)
	for i, id := range hc.orderedIDs {
		if i >= removed {
			newIDs[id] = true
			newOrder = append(newOrder, id)
		}
	}
	hc.processedIDs = newIDs
	hc.orderedIDs = newOrder
}

// markProcessed 标记消息已处理（加入 processedIDs + orderedIDs）
func (hc *HallClient) markProcessed(msgID string) {
	hc.processedIDs[msgID] = true
	hc.orderedIDs = append(hc.orderedIDs, msgID)
	hc.trimProcessedIDs()
}

// ── 冗余声明（用作占位，避免编译错误） ──

// log 函数保留
var _ = log.Printf

// 确保 HallClient 实现了必要接口
var _ interface {
	SetAgent(*agent.Agent)
	StartPollLoop()
	StopPollLoop()
	PostMessage(string, string, string)
} = (*HallClient)(nil)