// Copyright (c) 2026 ComputeHub. All rights reserved.
// Agent Direct Message — 端智→Worker Agent 实时通讯
//
// 架构:
//   端智 → HTTP POST /api/v1/agent/send → Gateway WSHub.SendTo → Worker WS → Agent
//   Worker Agent 回复 → WS direct_reply → Gateway 内存队列 → 端智 HTTP poll
//
// 延迟: <1s (WS 在线) vs 10s+ (HTTP poll) vs ∞ (节点离线)

package gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"
	"time"
)

// =============================================================================
// 回复存储 — 端智通过 msg_id 轮询拉取回复
// =============================================================================

// DirectReply 存储一条 P2P 回复
type DirectReply struct {
	MsgID     string `json:"msg_id"`
	From      string `json:"from"`      // 回复方 nodeID
	Content   string `json:"content"`   // 回复内容
	Timestamp int64  `json:"timestamp"` // Unix 毫秒
}

// ReplyStore 内存回复存储（自动过期清理）
type ReplyStore struct {
	mu       sync.RWMutex
	replies  map[string]*DirectReply // key: msgID
	ttl      time.Duration           // 过期时间
	cleanup  *time.Ticker
}

// NewReplyStore 创建回复存储
func NewReplyStore() *ReplyStore {
	rs := &ReplyStore{
		replies: make(map[string]*DirectReply),
		ttl:     5 * time.Minute, // 5 分钟自动清理
		cleanup: time.NewTicker(1 * time.Minute),
	}
	go rs.cleanupLoop()
	return rs
}

// Store 存储一条回复
func (rs *ReplyStore) Store(msgID, from, content string) {
	rs.mu.Lock()
	defer rs.mu.Unlock()
	rs.replies[msgID] = &DirectReply{
		MsgID:     msgID,
		From:      from,
		Content:   content,
		Timestamp: time.Now().UnixMilli(),
	}
}

// Get 获取并删除一条回复
func (rs *ReplyStore) Get(msgID string) *DirectReply {
	rs.mu.Lock()
	defer rs.mu.Unlock()
	reply, ok := rs.replies[msgID]
	if !ok {
		return nil
	}
	delete(rs.replies, msgID)
	return reply
}

// cleanupLoop 定期清理过期回复
func (rs *ReplyStore) cleanupLoop() {
	for range rs.cleanup.C {
		rs.mu.Lock()
		now := time.Now().UnixMilli()
		cutoff := now - rs.ttl.Milliseconds()
		for id, reply := range rs.replies {
			if reply.Timestamp < cutoff {
				delete(rs.replies, id)
			}
		}
		rs.mu.Unlock()
	}
}

// =============================================================================
// Gateway 回复存储实例（全局单例）
// =============================================================================

var globalReplyStore = NewReplyStore()

// =============================================================================
// HTTP API: POST /api/v1/agent/send
// =============================================================================

// handleAgentSend 端智→Worker Agent 发送消息
//
// 请求:
//   POST /api/v1/agent/send
//   { "to": "wanlida-ubuntu", "message": "你好达智，银河计划..." }
//
// 响应:
//   { "success": true, "data": { "msg_id": "...", "sent": true, "node_online": true } }
func (g *OpcGateway) handleAgentSend(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	var req struct {
		To      string `json:"to"`
		Message string `json:"message"`
		From    string `json:"from,omitempty"` // 发送者标识，默认 "端智"
	}
	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.To == "" || req.Message == "" {
		g.sendResponse(w, Response{Success: false, Error: "to and message are required"})
		return
	}

	if req.From == "" {
		req.From = "端智"
	}

	// 生成消息 ID
	msgID := fmt.Sprintf("dm-%d-%d", time.Now().UnixNano(), g.wsHub.MessagesSent)

	// 构造 WS 消息
	wsMsg := &WSMessage{
		MsgType:  MsgTypeDirectMessage,
		SenderID: req.From,
		Content:  req.Message,
		Payload:  mustMarshalJSON(map[string]string{"msg_id": msgID, "from": req.From}),
	}

	// 通过 WSHub.SendTo 推送给目标 Worker
	nodeOnline := g.wsHub.SendTo(req.To, wsMsg)

	log.Printf("📡 Agent Send: from=%s to=%s msg_id=%s online=%v msg=%s",
		req.From, req.To, msgID, nodeOnline, truncateStr(req.Message, 80))

	g.sendResponse(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"msg_id":      msgID,
			"sent":        nodeOnline,
			"node_online": nodeOnline,
			"to":          req.To,
		},
	})
}

// =============================================================================
// HTTP API: GET /api/v1/agent/send/result?msg_id=xxx
// =============================================================================

// handleAgentSendResult 端智轮询拉取 Worker 回复
//
// 请求:
//   GET /api/v1/agent/send/result?msg_id=dm-xxx
//
// 响应:
//   { "success": true, "data": { "msg_id": "...", "from": "wanlida-ubuntu",
//     "content": "...", "timestamp": 1234567890 } }
//   或 { "success": true, "data": null } 表示尚未回复
func (g *OpcGateway) handleAgentSendResult(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	msgID := r.URL.Query().Get("msg_id")
	if msgID == "" {
		g.sendResponse(w, Response{Success: false, Error: "msg_id is required"})
		return
	}

	reply := globalReplyStore.Get(msgID)
	if reply == nil {
		g.sendResponse(w, Response{Success: true, Data: nil})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    reply,
	})
}

// =============================================================================
// WSHub 扩展：处理 Worker 的 direct_reply
// =============================================================================

// handleDirectReply 处理 Worker 发回的 direct_reply 消息
// 由 readPump 在收到 MsgTypeDirectReply 时调用
func (h *WSHub) handleDirectReply(envelope *WSMessage) {
	// 从 Payload 中提取 msg_id
	var payload struct {
		MsgID   string `json:"msg_id"`
		Content string `json:"content"`
	}
	if envelope.Payload != nil {
		json.Unmarshal(envelope.Payload, &payload)
	}

	msgID := payload.MsgID
	if msgID == "" {
		msgID = envelope.Content // fallback: 直接用 content 字段
	}

	content := payload.Content
	if content == "" {
		content = envelope.Content
	}

	globalReplyStore.Store(msgID, envelope.SenderID, content)
	log.Printf("📡 Agent Reply: from=%s msg_id=%s content=%s",
		envelope.SenderID, msgID, truncateStr(content, 80))
}

// =============================================================================
// 工具函数
// =============================================================================

func truncateStr(s string, maxLen int) string {
	runes := []rune(s)
	if len(runes) > maxLen {
		return string(runes[:maxLen]) + "..."
	}
	return s
}
