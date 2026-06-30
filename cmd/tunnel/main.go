// Copyright (c) 2026 ComputeHub. All rights reserved.
// WebSocket Tunnel — TCP-over-WebSocket 隧道
//
// 用法:
//   server:  tunnel --mode server --ws ws://36.250.122.43:8282/api/v1/ws --target localhost:18789
//   client:  tunnel --mode client --ws ws://36.250.122.43:8282/api/v1/ws --listen :18790
//
// 架构:
//   TCP Client (:18790) ←→ tunnel-client ←WS→ 8282 WSHub ←WS→ tunnel-server ←TCP→ :18789
//
// 特性:
//   - 自动重连（指数退避，最大 60s）
//   - 空闲 Session 自动清理（默认 5 分钟无数据）
//   - 优雅退出（SIGINT/SIGTERM 关闭所有连接）
//   - 统计报告（每 60s 输出活跃 Session 数和流量）

package main

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
)

// =============================================================================
// 常量
// =============================================================================

const (
	MsgTypeRegister   = "register"
	MsgTypeRegistered = "registered"
	MsgTypePing       = "ping"
	MsgTypePong       = "pong"
	MsgTypeTunnelData = "tunnel_data"

	readBufferSize    = 32 * 1024  // TCP 读缓冲 32KB
	maxReconnectDelay = 60         // 最大重连间隔（秒）
	idleSessionTTL    = 5 * time.Minute // 空闲 Session 超时
	statsInterval     = 60 * time.Second // 统计报告间隔
)

// =============================================================================
// 消息结构（与 gateway_ws.go 保持一致）
// =============================================================================

type WSMessage struct {
	MsgType    string          `json:"msg_type"`
	Seq        uint64          `json:"seq,omitempty"`
	Timestamp  int64           `json:"ts,omitempty"`
	SenderID   string          `json:"sender_id,omitempty"`
	NodeID     string          `json:"node_id,omitempty"`
	Platform   string          `json:"platform,omitempty"`
	Status     string          `json:"status,omitempty"`
	Error      string          `json:"error,omitempty"`
	SessionID  string          `json:"session_id,omitempty"`
	TargetNode string          `json:"target_node,omitempty"`
	Content    string          `json:"content,omitempty"`
	Payload    json.RawMessage `json:"payload,omitempty"`
}

type TunnelPayload struct {
	Close bool `json:"close,omitempty"`
}

// =============================================================================
// 统计指标
// =============================================================================

type TunnelStats struct {
	SessionsCreated int64
	SessionsClosed  int64
	BytesSent       int64
	BytesReceived   int64
	Reconnects      int64
	Errors          int64
}

// =============================================================================
// Session 管理
// =============================================================================

type TunnelSession struct {
	ID        string
	Conn      net.Conn
	CreatedAt time.Time
	LastActivity time.Time
	mu        sync.Mutex
	closed    bool
}

type SessionManager struct {
	mu       sync.RWMutex
	sessions map[string]*TunnelSession
	nextID   uint64
	stats    TunnelStats
}

func NewSessionManager() *SessionManager {
	return &SessionManager{
		sessions: make(map[string]*TunnelSession),
	}
}

func (sm *SessionManager) NewSessionID() string {
	id := atomic.AddUint64(&sm.nextID, 1)
	b := make([]byte, 4)
	rand.Read(b)
	return fmt.Sprintf("tun-%d-%s", id, hex.EncodeToString(b))
}

func (sm *SessionManager) Add(s *TunnelSession) {
	sm.mu.Lock()
	sm.sessions[s.ID] = s
	atomic.AddInt64(&sm.stats.SessionsCreated, 1)
	sm.mu.Unlock()
}

func (sm *SessionManager) Get(id string) *TunnelSession {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return sm.sessions[id]
}

func (sm *SessionManager) Remove(id string) {
	sm.mu.Lock()
	if s, ok := sm.sessions[id]; ok {
		s.mu.Lock()
		if !s.closed {
			s.Conn.Close()
		}
		s.closed = true
		s.mu.Unlock()
		delete(sm.sessions, id)
		atomic.AddInt64(&sm.stats.SessionsClosed, 1)
	}
	sm.mu.Unlock()
}

func (sm *SessionManager) CloseAll() {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	for id, s := range sm.sessions {
		s.mu.Lock()
		if !s.closed {
			s.Conn.Close()
		}
		s.closed = true
		s.mu.Unlock()
		delete(sm.sessions, id)
		atomic.AddInt64(&sm.stats.SessionsClosed, 1)
	}
}

func (sm *SessionManager) CleanIdle() int {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	now := time.Now()
	cleaned := 0
	for id, s := range sm.sessions {
		if now.Sub(s.LastActivity) > idleSessionTTL {
			s.mu.Lock()
			if !s.closed {
				s.Conn.Close()
			}
			s.closed = true
			s.mu.Unlock()
			delete(sm.sessions, id)
			atomic.AddInt64(&sm.stats.SessionsClosed, 1)
			cleaned++
		}
	}
	return cleaned
}

func (sm *SessionManager) ActiveCount() int {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return len(sm.sessions)
}

// =============================================================================
// WebSocket 连接管理
// =============================================================================

type WSConn struct {
	conn   *websocket.Conn
	mu     sync.Mutex
	nodeID string
	url    string
}

func dialWS(url, nodeID string) (*WSConn, error) {
	dialer := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
	}
	c, _, err := dialer.Dial(url, nil)
	if err != nil {
		return nil, fmt.Errorf("dial WS %s: %w", url, err)
	}

	wc := &WSConn{
		conn:   c,
		nodeID: nodeID,
		url:    url,
	}

	// 设置原生 ping/pong handler
	c.SetPingHandler(func(appData string) error {
		wc.mu.Lock()
		err := c.WriteMessage(websocket.PongMessage, []byte(appData))
		wc.mu.Unlock()
		return err
	})
	c.SetPongHandler(func(string) error {
		return nil
	})

	// 发送注册消息
	regMsg := WSMessage{
		MsgType:  MsgTypeRegister,
		NodeID:   nodeID,
		Platform: "tunnel",
	}
	if err := wc.WriteJSON(regMsg); err != nil {
		c.Close()
		return nil, fmt.Errorf("register: %w", err)
	}

	// 等待注册确认
	c.SetReadDeadline(time.Now().Add(15 * time.Second))
	_, msg, err := c.ReadMessage()
	c.SetReadDeadline(time.Time{})
	if err != nil {
		c.Close()
		return nil, fmt.Errorf("read register response: %w", err)
	}
	var resp WSMessage
	if err := json.Unmarshal(msg, &resp); err != nil {
		c.Close()
		return nil, fmt.Errorf("parse register response: %w", err)
	}
	if resp.Status != "ok" {
		c.Close()
		return nil, fmt.Errorf("register failed: %s", resp.Error)
	}

	log.Printf("🔌 WS 注册成功: %s", nodeID)
	return wc, nil
}

func (w *WSConn) WriteJSON(v interface{}) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.conn.WriteJSON(v)
}

func (w *WSConn) ReadMessage() (int, []byte, error) {
	return w.conn.ReadMessage()
}

func (w *WSConn) Close() {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.conn.Close()
}

// =============================================================================
// 重连辅助
// =============================================================================

// reconnectLoop 带指数退避的重连循环
// 返回新的 WSConn（成功时）或 error（放弃时）
func reconnectLoop(url, nodeID string, stats *TunnelStats) *WSConn {
	delay := 1
	for {
		time.Sleep(time.Duration(delay) * time.Second)
		ws, err := dialWS(url, nodeID)
		if err == nil {
			atomic.AddInt64(&stats.Reconnects, 1)
			log.Printf("🔄 重连成功 (间隔 %ds)", delay)
			return ws
		}
		log.Printf("❌ 重连失败 (间隔 %ds): %v", delay, err)
		delay = delay * 2
		if delay > maxReconnectDelay {
			delay = maxReconnectDelay
		}
	}
}

// =============================================================================
// Server 模式
// =============================================================================

func runServer(wsURL, targetAddr string) {
	log.Printf("🚀 Tunnel Server 启动")
	log.Printf("   WS: %s", wsURL)
	log.Printf("   Target: %s", targetAddr)

	sm := NewSessionManager()
	stopCh := make(chan struct{})

	// 连接 WS
	ws, err := dialWS(wsURL, "tunnel-server")
	if err != nil {
		log.Fatalf("❌ WS 连接失败: %v", err)
	}
	defer ws.Close()

	// 心跳
	go heartbeatLoop(ws, stopCh)

	// 空闲 Session 清理
	go idleCleanupLoop(sm, stopCh)

	// 统计报告
	go statsReportLoop(sm, stopCh)

	// 读消息循环（带自动重连）
	for {
		_, msg, err := ws.ReadMessage()
		if err != nil {
			log.Printf("❌ WS 读消息失败: %v", err)
			ws.Close()
			sm.CloseAll()
			ws = reconnectLoop(wsURL, "tunnel-server", &sm.stats)
			if ws == nil {
				log.Fatalf("❌ 重连放弃")
			}
			go heartbeatLoop(ws, stopCh)
			continue
		}

		var envelope WSMessage
		if err := json.Unmarshal(msg, &envelope); err != nil {
			continue
		}

		switch envelope.MsgType {
		case MsgTypePing:
			ws.WriteJSON(WSMessage{MsgType: MsgTypePong})
		case MsgTypePong:
			// 忽略
		case MsgTypeTunnelData:
			handleServerTunnelData(ws, sm, &envelope, targetAddr)
		default:
			// 忽略未知类型
		}
	}
}

func handleServerTunnelData(ws *WSConn, sm *SessionManager, envelope *WSMessage, targetAddr string) {
	sessionID := envelope.SessionID
	data, close, err := decodeTunnelData(envelope)
	if err != nil {
		log.Printf("⚠️ 解码隧道数据失败: %v", err)
		atomic.AddInt64(&sm.stats.Errors, 1)
		return
	}

	if close {
		sm.Remove(sessionID)
		log.Printf("🔌 Session 关闭: %s", sessionID)
		return
	}

	s := sm.Get(sessionID)
	if s == nil {
		// 新连接：连接到目标
		conn, err := net.DialTimeout("tcp", targetAddr, 10*time.Second)
		if err != nil {
			log.Printf("❌ 连接目标 %s 失败: %v", targetAddr, err)
			closeMsg := encodeTunnelData(sessionID, envelope.SenderID, nil, true)
			ws.WriteJSON(closeMsg)
			atomic.AddInt64(&sm.stats.Errors, 1)
			return
		}
		s = &TunnelSession{
			ID:           sessionID,
			Conn:         conn,
			CreatedAt:    time.Now(),
			LastActivity: time.Now(),
		}
		sm.Add(s)
		log.Printf("🔌 Session 创建: %s → %s", sessionID, targetAddr)

		// TCP → WS 转发
		go func(sid string, tcpConn net.Conn) {
			buf := make([]byte, readBufferSize)
			for {
				n, err := tcpConn.Read(buf)
				if err != nil {
					closeMsg := encodeTunnelData(sid, envelope.SenderID, nil, true)
					ws.WriteJSON(closeMsg)
					sm.Remove(sid)
					return
				}
				atomic.AddInt64(&sm.stats.BytesSent, int64(n))
				dataMsg := encodeTunnelData(sid, envelope.SenderID, buf[:n], false)
				if err := ws.WriteJSON(dataMsg); err != nil {
					return
				}
			}
		}(sessionID, conn)
	}

	// 写入 TCP
	if len(data) > 0 {
		s.mu.Lock()
		if !s.closed {
			if _, err := s.Conn.Write(data); err != nil {
				s.mu.Unlock()
				log.Printf("⚠️ Session %s TCP 写失败: %v", sessionID, err)
				s.Conn.Close()
				sm.Remove(sessionID)
				closeMsg := encodeTunnelData(sessionID, envelope.SenderID, nil, true)
				ws.WriteJSON(closeMsg)
				atomic.AddInt64(&sm.stats.Errors, 1)
				return
			}
			atomic.AddInt64(&sm.stats.BytesReceived, int64(len(data)))
			s.LastActivity = time.Now()
		}
		s.mu.Unlock()
	}
}

// =============================================================================
// Client 模式
// =============================================================================

func runClient(wsURL, listenAddr string) {
	log.Printf("🚀 Tunnel Client 启动")
	log.Printf("   WS: %s", wsURL)
	log.Printf("   Listen: %s", listenAddr)

	sm := NewSessionManager()
	stopCh := make(chan struct{})

	// 连接 WS
	ws, err := dialWS(wsURL, "tunnel-client")
	if err != nil {
		log.Fatalf("❌ WS 连接失败: %v", err)
	}
	defer ws.Close()

	// 心跳
	go heartbeatLoop(ws, stopCh)

	// 空闲 Session 清理
	go idleCleanupLoop(sm, stopCh)

	// 统计报告
	go statsReportLoop(sm, stopCh)

	// WS 读消息（处理 server 返回的数据，带自动重连）
	go func() {
		for {
			_, msg, err := ws.ReadMessage()
			if err != nil {
				log.Printf("❌ WS 读消息失败: %v", err)
				ws.Close()
				sm.CloseAll()
				ws = reconnectLoop(wsURL, "tunnel-client", &sm.stats)
				if ws == nil {
					return
				}
				go heartbeatLoop(ws, stopCh)
				continue
			}

			var envelope WSMessage
			if err := json.Unmarshal(msg, &envelope); err != nil {
				continue
			}

			switch envelope.MsgType {
			case MsgTypePing:
				ws.WriteJSON(WSMessage{MsgType: MsgTypePong})
			case MsgTypePong:
				// 忽略
			case MsgTypeTunnelData:
				handleClientTunnelData(sm, &envelope)
			}
		}
	}()

	// 监听 TCP
	listener, err := net.Listen("tcp", listenAddr)
	if err != nil {
		log.Fatalf("❌ 监听 %s 失败: %v", listenAddr, err)
	}
	defer listener.Close()

	log.Printf("📡 监听 %s", listenAddr)

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("❌ Accept 失败: %v", err)
			continue
		}

		sessionID := sm.NewSessionID()
		s := &TunnelSession{
			ID:           sessionID,
			Conn:         conn,
			CreatedAt:    time.Now(),
			LastActivity: time.Now(),
		}
		sm.Add(s)
		log.Printf("🔌 新连接: %s (from %s)", sessionID, conn.RemoteAddr())

		// TCP → WS 转发
		go func(sid string, tcpConn net.Conn) {
			buf := make([]byte, readBufferSize)
			for {
				n, err := tcpConn.Read(buf)
				if err != nil {
					closeMsg := encodeTunnelData(sid, "tunnel-server", nil, true)
					ws.WriteJSON(closeMsg)
					sm.Remove(sid)
					return
				}
				atomic.AddInt64(&sm.stats.BytesSent, int64(n))
				dataMsg := encodeTunnelData(sid, "tunnel-server", buf[:n], false)
				if err := ws.WriteJSON(dataMsg); err != nil {
					return
				}
			}
		}(sessionID, conn)
	}
}

func handleClientTunnelData(sm *SessionManager, envelope *WSMessage) {
	sessionID := envelope.SessionID
	data, close, err := decodeTunnelData(envelope)
	if err != nil {
		log.Printf("⚠️ 解码隧道数据失败: %v", err)
		atomic.AddInt64(&sm.stats.Errors, 1)
		return
	}

	if close {
		sm.Remove(sessionID)
		return
	}

	s := sm.Get(sessionID)
	if s != nil && len(data) > 0 {
		s.mu.Lock()
		if !s.closed {
			if _, err := s.Conn.Write(data); err != nil {
				s.mu.Unlock()
				log.Printf("⚠️ Session %s TCP 写失败: %v", sessionID, err)
				s.Conn.Close()
				sm.Remove(sessionID)
				atomic.AddInt64(&sm.stats.Errors, 1)
				return
			}
			atomic.AddInt64(&sm.stats.BytesReceived, int64(len(data)))
			s.LastActivity = time.Now()
		}
		s.mu.Unlock()
	}
}

// =============================================================================
// 辅助函数
// =============================================================================

func heartbeatLoop(ws *WSConn, stopCh chan struct{}) {
	ticker := time.NewTicker(25 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-stopCh:
			return
		case <-ticker.C:
			if err := ws.WriteJSON(WSMessage{MsgType: MsgTypePing}); err != nil {
				log.Printf("⚠️ 心跳发送失败: %v", err)
				return
			}
		}
	}
}

func idleCleanupLoop(sm *SessionManager, stopCh chan struct{}) {
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-stopCh:
			return
		case <-ticker.C:
			cleaned := sm.CleanIdle()
			if cleaned > 0 {
				log.Printf("🧹 清理 %d 个空闲 Session", cleaned)
			}
		}
	}
}

func statsReportLoop(sm *SessionManager, stopCh chan struct{}) {
	ticker := time.NewTicker(statsInterval)
	defer ticker.Stop()
	for {
		select {
		case <-stopCh:
			return
		case <-ticker.C:
			active := sm.ActiveCount()
			s := &sm.stats
			log.Printf("📊 统计: 活跃=%d 创建=%d 关闭=%d 发送=%s 接收=%s 重连=%d 错误=%d",
				active,
				atomic.LoadInt64(&s.SessionsCreated),
				atomic.LoadInt64(&s.SessionsClosed),
				formatBytes(atomic.LoadInt64(&s.BytesSent)),
				formatBytes(atomic.LoadInt64(&s.BytesReceived)),
				atomic.LoadInt64(&s.Reconnects),
				atomic.LoadInt64(&s.Errors))
		}
	}
}

func formatBytes(b int64) string {
	if b < 1024 {
		return fmt.Sprintf("%dB", b)
	} else if b < 1024*1024 {
		return fmt.Sprintf("%.1fKB", float64(b)/1024)
	} else {
		return fmt.Sprintf("%.1fMB", float64(b)/(1024*1024))
	}
}

// =============================================================================
// 编解码
// =============================================================================

func encodeTunnelData(sessionID, targetNode string, data []byte, close bool) *WSMessage {
	msg := &WSMessage{
		MsgType:    MsgTypeTunnelData,
		SenderID:   "tunnel",
		TargetNode: targetNode,
		SessionID:  sessionID,
		Content:    base64.StdEncoding.EncodeToString(data),
		Timestamp:  time.Now().UnixMilli(),
	}
	if close {
		p := TunnelPayload{Close: true}
		payload, _ := json.Marshal(p)
		msg.Payload = payload
	}
	return msg
}

func decodeTunnelData(msg *WSMessage) (data []byte, close bool, err error) {
	data, err = base64.StdEncoding.DecodeString(msg.Content)
	if err != nil {
		return nil, false, err
	}
	if len(msg.Payload) > 0 {
		var p TunnelPayload
		if err := json.Unmarshal(msg.Payload, &p); err == nil {
			close = p.Close
		}
	}
	return data, close, nil
}

// =============================================================================
// Main
// =============================================================================

func main() {
	mode := flag.String("mode", "", "server 或 client")
	wsURL := flag.String("ws", "ws://36.250.122.43:8282/api/v1/ws", "WebSocket Hub 地址")
	target := flag.String("target", "localhost:18789", "server 模式: 目标 TCP 地址")
	listen := flag.String("listen", ":18790", "client 模式: 监听地址")
	flag.Parse()

	log.SetFlags(log.Ldate | log.Ltime | log.Lmicroseconds)

	if *mode == "" {
		fmt.Println("ComputeHub WebSocket Tunnel — TCP-over-WebSocket 隧道")
		fmt.Println()
		fmt.Println("用法: tunnel --mode server|client [选项]")
		fmt.Println()
		fmt.Println("Server 模式 (运行在 ECS, 连接目标服务):")
		fmt.Println("  tunnel --mode server --ws ws://host:8282/api/v1/ws --target localhost:18789")
		fmt.Println()
		fmt.Println("Client 模式 (运行在 Windows, 暴露本地端口):")
		fmt.Println("  tunnel --mode client --ws ws://host:8282/api/v1/ws --listen :18790")
		fmt.Println()
		fmt.Println("示例 — 打通 Windows OpenClaw → ECS OpenClaw:")
		fmt.Println("  # ECS 上: tunnel --mode server --target 127.0.0.1:18789")
		fmt.Println("  # Windows 上: tunnel --mode client --listen :18790")
		fmt.Println("  # Windows 上配置 OpenClaw gateway.bind=127.0.0.1:18790")
		fmt.Println()
		fmt.Println("选项:")
		flag.PrintDefaults()
		os.Exit(1)
	}

	// 优雅退出
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		sig := <-sigCh
		log.Printf("🛑 收到 %v 信号, 正在关闭...", sig)
		os.Exit(0)
	}()

	switch *mode {
	case "server":
		runServer(*wsURL, *target)
	case "client":
		runClient(*wsURL, *listen)
	default:
		log.Fatalf("未知模式: %s (必须是 server 或 client)", *mode)
	}
}
