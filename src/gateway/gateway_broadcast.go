// Copyright (c) 2026 OpenClaw. All rights reserved.
// ARC-AI-NET 集群广播机制 — Gateway 端实现
//
// 架构：Worker A → POST /api/v1/cluster/broadcast → Gateway → 遍历所有 Worker → POST /api/v1/worker/think

package gateway

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"sync"
	"time"

	"github.com/computehub/opc/src/kernel"
)

// =============================================================================
// 消息类型枚举
// =============================================================================

const (
	EventTypeNodeJoin     = "node_join"
	EventTypeNodeLeave    = "node_leave"
	EventTypeTopology     = "topology_update"
	EventTypeHeartbeat    = "heartbeat"
	EventTypeSyncRequest  = "sync_request"
	EventTypeBroadcast    = "broadcast" // 用户自定义广播
)

// =============================================================================
// 消息结构
// =============================================================================

// BroadcastEnvelope 广播消息信封
type BroadcastEnvelope struct {
	Type     string    `json:"type"`     // "arc_net_broadcast"
	Envelope Envelope  `json:"arc_net"`  // 广播载荷
	Role     string    `json:"role"`     // "system" 或 "user"
	Content  string    `json:"content"`  // 人可读兜底
}

// Envelope 广播信封
type Envelope struct {
	Version   string              `json:"version"`   // "1.0"
	Event     string              `json:"event"`     // node_join / node_leave / ...
	Sender    SenderInfo          `json:"sender"`    // 发送节点信息
	Seq       uint64              `json:"seq"`       // 序列号（自增）
	Timestamp int64               `json:"timestamp"` // Unix 时间戳
	Payload   json.RawMessage     `json:"payload,omitempty"`
}

// SenderInfo 发送节点信息
type SenderInfo struct {
	NodeID   string `json:"node_id"`   // 节点唯一标识
	Label    string `json:"label"`     // 显示标签
	Host     string `json:"host"`      // IP 地址
	Platform string `json:"platform"`  // linux/amd64
	Model    string `json:"model"`     // 当前模型
	Version  string `json:"version"`   // OpenClaw 版本
}

// =============================================================================
// Gateway Handler — 广播入口
// =============================================================================

// handleBroadcast 处理广播请求
// POST /api/v1/cluster/broadcast
func (g *OpcGateway) handleBroadcast(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// 1. 解析广播消息
	var msg BroadcastEnvelope
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&msg); err != nil {
		http.Error(w, fmt.Sprintf("Invalid request: %v", err), http.StatusBadRequest)
		return
	}

	// 2. 验证消息类型
	if msg.Type != "arc_net_broadcast" {
		http.Error(w, "Invalid message type, expected arc_net_broadcast", http.StatusBadRequest)
		return
	}

	// 3. 获取所有在线节点
	nodes := g.Kernel.NodeMgr.ListNodes()
	log.Printf("📡 ARC-NET broadcast: %d total nodes, forwarding to %d", len(nodes), len(nodes)-1)

	// 4. 广播给所有节点（除发送者自己）
	var wg sync.WaitGroup
	var errs []error
	rateLimiter := make(chan struct{}, 4) // 并发限制 4

	for _, state := range nodes {
		// 通过 Register 访问节点信息
		reg := state.Register
		if reg == nil {
			continue
		}

		// 跳过发送者自己
		if reg.NodeID == msg.Envelope.Sender.NodeID {
			continue
		}
		// 跳过离线节点
		if reg.Status != "online" {
			continue
		}

		wg.Add(1)
		go func(s *kernel.NodeManagerState, reg *kernel.NodeRegister) {
			defer wg.Done()

			select {
			case rateLimiter <- struct{}{}:
				defer func() { <-rateLimiter }()
			default:
				return
			}

			// 构造 Worker think 请求
			thinkReq := map[string]interface{}{
				"type":    "arc_net_broadcast",
				"arc_net": msg.Envelope,
				"role":    "system",
				"content": "[ARC-NET] 系统广播",
			}

			body, err := json.Marshal(thinkReq)
			if err != nil {
				log.Printf("⚠️ 广播序列化失败 (%s): %v", reg.NodeID, err)
				errs = append(errs, err)
				return
			}

			// POST 到 Worker /api/v1/worker/think
			// Worker 默认端口 8383，但实际可能在不同端口
			// 这里用默认 8383，实际部署时需要根据节点配置调整
			url := fmt.Sprintf("http://%s:8383/api/v1/worker/think", reg.IPAddress)
			resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
			if err != nil {
				log.Printf("⚠️ 广播投递失败 (%s): %v", reg.NodeID, err)
				errs = append(errs, err)
				return
			}
			defer resp.Body.Close()

			// 读取响应（只要成功即可）
			_, _ = io.Copy(io.Discard, resp.Body)

			if resp.StatusCode != http.StatusOK {
				dump, _ := httputil.DumpResponse(resp, true)
				log.Printf("⚠️ 广播失败 (%s): HTTP %d, body: %s", reg.NodeID, resp.StatusCode, string(dump[:200]))
				errs = append(errs, fmt.Errorf("HTTP %d", resp.StatusCode))
			}
		}(state, reg)
	}

	wg.Wait()

	// 5. 返回结果
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":       "ok",
		"total_nodes":  len(nodes),
		"broadcast_to": len(nodes) - 1,
		"errors":       len(errs),
		"message":      "广播已转发",
		"timestamp":    time.Now().Unix(),
	})
}
