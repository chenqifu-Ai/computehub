// Remote Shell — WS 交互终端路由
//
// 架构: TUI ──WS──▶ Gateway ──WS──▶ Worker ──PTY──▶ /bin/bash
//
// 新增 WS 消息类型:
//   shell_open   — TUI→Gateway→Worker: 打开 Shell 会话
//   shell_input  — TUI→Gateway→Worker: 键盘输入
//   shell_output — Worker→Gateway→TUI:  终端输出
//   shell_resize — TUI→Gateway→Worker:  调整窗口大小
//   shell_close  — TUI→Gateway→Worker:  关闭会话
//
// Gateway 作为中转: TUI 的 WS 连接与 Worker 的 WS 连接之间的桥接

package gateway

import (
	"log"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// ShellSession 表示一个活跃的远程 Shell 会话
type ShellSession struct {
	SessionID string         // 唯一会话标识
	WorkerID  string         // 目标 Worker 节点 ID
	TUI       *ShellTUIClient // TUI 端连接
	Created   time.Time
}

// ShellTUIClient TUI 端的 WS 连接信息
type ShellTUIClient struct {
	Conn *websocket.Conn
	// NodeID 留空 — TUI 不是 Worker
}

// shellRouter 管理 Shell 会话路由
type shellRouter struct {
	mu           sync.RWMutex
	sessions     map[string]*ShellSession // sessionID → session
	tuiSession   map[*websocket.Conn]string // TUI conn → sessionID
	sessionByID  map[string]*ShellSession // Worker nodeID → session (最多一活跃)
}

func newShellRouter() *shellRouter {
	return &shellRouter{
		sessions:    make(map[string]*ShellSession),
		tuiSession:  make(map[*websocket.Conn]string),
		sessionByID: make(map[string]*ShellSession),
	}
}

// CreateSession 创建 Shell 会话，返回 sessionID
func (sr *shellRouter) CreateSession(tuiConn *websocket.Conn, workerID string) string {
	sr.mu.Lock()
	defer sr.mu.Unlock()

	// 如果该 Worker 已有活跃会话，先关闭旧的
	if old, ok := sr.sessionByID[workerID]; ok {
		sr.cleanupSessionLocked(old)
	}

	sessionID := "shell-" + formatTimestampShort() + "-" + randHex(4)
	sess := &ShellSession{
		SessionID: sessionID,
		WorkerID:  workerID,
		TUI:       &ShellTUIClient{Conn: tuiConn},
		Created:   time.Now(),
	}
	sr.sessions[sessionID] = sess
	sr.sessionByID[workerID] = sess
	sr.tuiSession[tuiConn] = sessionID

	log.Printf("💻 Shell session %s → Worker %s 已创建", sessionID, workerID)
	return sessionID
}

// RouteBySession 根据 sessionID 获取会话
func (sr *shellRouter) RouteBySession(sessionID string) *ShellSession {
	sr.mu.RLock()
	defer sr.mu.RUnlock()
	return sr.sessions[sessionID]
}

// RouteByTUI 根据 TUI 连接获取会话
func (sr *shellRouter) RouteByTUI(conn *websocket.Conn) *ShellSession {
	sr.mu.RLock()
	defer sr.mu.RUnlock()
	if s, ok := sr.tuiSession[conn]; ok {
		return sr.sessions[s]
	}
	return nil
}

// CloseBySession 按 sessionID 关闭会话
func (sr *shellRouter) CloseBySession(sessionID string) {
	sr.mu.Lock()
	defer sr.mu.Unlock()
	if sess, ok := sr.sessions[sessionID]; ok {
		sr.cleanupSessionLocked(sess)
	}
}

// CloseByTUI 按 TUI 连接关闭会话（连接断开时清理）
func (sr *shellRouter) CloseByTUI(conn *websocket.Conn) {
	sr.mu.Lock()
	defer sr.mu.Unlock()
	if sessionID, ok := sr.tuiSession[conn]; ok {
		if sess, ok := sr.sessions[sessionID]; ok {
			sr.cleanupSessionLocked(sess)
		}
	}
}

// cleanupSessionLocked 清理会话（需持有 mu.Lock）
func (sr *shellRouter) cleanupSessionLocked(sess *ShellSession) {
	delete(sr.sessions, sess.SessionID)
	if sess.TUI != nil {
		delete(sr.tuiSession, sess.TUI.Conn)
	}
	delete(sr.sessionByID, sess.WorkerID)
	log.Printf("💻 Shell session %s 已清理", sess.SessionID)
}

// ── 工具函数 ──

// formatTimestampShort 短时间戳（用于 sessionID）
func formatTimestampShort() string {
	return time.Now().Format("150405")
}

// randHex 简单随机 hex 字符串（无 crypto 依赖）
func randHex(n int) string {
	const hex = "0123456789abcdef"
	b := make([]byte, n)
	for i := range b {
		// 使用纳秒作为简单随机源
		b[i] = hex[(time.Now().UnixNano()+int64(i)*7)&0xf]
		time.Sleep(1) // 1ns 抖动
	}
	return string(b)
}