// Copyright (c) 2026 OpenClaw. All rights reserved.
// ARC-AI-NET v1.1 — 集群广播 + 离线检测 + 全量同步

package gateway

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync/atomic"
	"time"

	"github.com/computehub/opc/src/kernel"
	"github.com/computehub/opc/src/version"
)

// =============================================================================
// 两阶段离线检测常量
// =============================================================================

const (
	// SuspectAfter 心跳停止多久标记为 suspect（可疑）
	SuspectAfter = 30 * time.Second

	// OfflineAfter 从 suspect 开始多久标记为 offline（离线）
	OfflineAfter = 90 * time.Second

	// BroadcastProbeInterval 健康检查间隔
	BroadcastProbeInterval = 15 * time.Second
)

// =============================================================================
// 序列号管理
// =============================================================================

var broadcastSeq atomic.Uint64

// NextBroadcastSeq 获取下一个全局广播序列号
func NextBroadcastSeq() uint64 {
	return broadcastSeq.Add(1)
}

// =============================================================================
// 节点生命周期事件广播
// =============================================================================

// BroadcastNodeEvent 广播节点生命周期事件（join / leave / update）
// BroadcastNodeEvent 广播节点生命周期事件（SPEC-WS-001 §3.3）
// WS 优先 → HTTP fallback
func (g *OpcGateway) BroadcastNodeEvent(event string, reg *kernel.NodeRegister) {
	seq := NextBroadcastSeq()

	// 构建 WS 格式的消息
	payload, _ := json.Marshal(map[string]interface{}{
		"node_id":  reg.NodeID,
		"host":     reg.IPAddress,
		"platform": reg.Platform,
		"status":   reg.Status,
		"version":  reg.Version,
	})

	wsMsg := &WSMessage{
		MsgType:   MsgTypeArcNet,
		Seq:       seq,
		Timestamp: time.Now().UnixMilli(),
		SenderID:  "gateway",
		Event:     event,
		Payload:   payload,
		Content:   fmt.Sprintf("[ARC-NET] Node %s: %s", reg.NodeID, event),
	}

	// WS 优先发送
	if g.wsHub != nil && g.wsHub.OnlineCount() > 0 {
		delivered := g.wsHub.FanOutAll(wsMsg, "gateway")
		if delivered > 0 {
			log.Printf("📡 ARC-NET 广播完成 (WS): event=%s, node=%s, seq=%d, delivered=%d",
				event, reg.NodeID, seq, delivered)
			return
		}
	}

	// Fallback: 无 WS 连接时走旧 HTTP（兼容旧 Worker）
	log.Printf("⚠️ ARC-NET WS 无可送达连接, fallback HTTP: event=%s, node=%s", event, reg.NodeID)
	g.broadcastHTTPFallback(event, reg, seq)
}

// broadcastHTTPFallback 旧 HTTP 广播方式（向后兼容）
func (g *OpcGateway) broadcastHTTPFallback(event string, reg *kernel.NodeRegister, seq uint64) {
	env := Envelope{
		Version:   "1.1",
		Event:     event,
		Seq:       seq,
		Timestamp: time.Now().Unix(),
		Sender: SenderInfo{
			NodeID:   "gateway",
			Label:    "ComputeHub Gateway",
			Host:     "gateway",
			Platform: "linux/amd64",
			Model:    "",
			Version:  g.getVersion(),
		},
		Payload: g.marshalNodePayload(reg),
	}

	msg := BroadcastEnvelope{
		Type:     "arc_net_broadcast",
		Envelope: env,
		Role:     "system",
		Content:  fmt.Sprintf("[ARC-NET] Node %s: %s", reg.NodeID, event),
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	if len(nodes) == 0 {
		return
	}

	for _, state := range nodes {
		r := state.Register
		if r == nil || r.Status != "online" || r.NodeID == "gateway" {
			continue
		}
		g.postToWorkerHTTP(r, msg)
	}
}

// postToWorkerHTTP 旧版 HTTP POST 方式（向后兼容 fallback）
func (g *OpcGateway) postToWorkerHTTP(reg *kernel.NodeRegister, msg BroadcastEnvelope) {
	body, err := json.Marshal(msg)
	if err != nil {
		log.Printf("⚠️ ARC-NET HTTP fallback 序列化失败 (%s): %v", reg.NodeID, err)
		return
	}

	// 端口从 topology 获取（默认 8383）
	port := 8383
	url := fmt.Sprintf("http://%s:%d/api/v1/worker/arc_net", reg.IPAddress, port)
	client := &http.Client{Timeout: 3 * time.Second}
		resp, err := client.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		log.Printf("⚠️ ARC-NET HTTP fallback 投递失败 (%s): %v", reg.NodeID, err)
		return
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)
}

func (g *OpcGateway) getVersion() string {
	return version.VERSION
}

func (g *OpcGateway) marshalNodePayload(reg *kernel.NodeRegister) json.RawMessage {
	data, _ := json.Marshal(map[string]interface{}{
		"node_id":   reg.NodeID,
		"host":      reg.IPAddress,
		"platform":  reg.Platform,
		"region":    reg.Region,
		"gpu":       reg.GPUType,
		"status":    reg.Status,
		"version":   reg.Version,
		"joined_at": reg.RegisteredAt,
	})
	return data
}

// =============================================================================
// 两阶段健康检查监控
// =============================================================================

// StartArcNetMonitor 启动 ARC-AI-NET 监控协程
// 每 BroadcastProbeInterval 检查一次：
//   - heartbeat 停止 > SuspectAfter  → suspect（可疑）
//   - suspect 持续 > OfflineAfter    → offline（触发下线广播）
func (g *OpcGateway) StartArcNetMonitor() {
	go func() {
		ticker := time.NewTicker(BroadcastProbeInterval)
		defer ticker.Stop()

		for range ticker.C {
			g.checkNodeHealthV2()
		}
	}()
	log.Printf("📡 ARC-AI-NET 监控已启动: suspect=%s, offline=%s, interval=%s",
		SuspectAfter, OfflineAfter, BroadcastProbeInterval)
}

// checkNodeHealthV2 两阶段健康检查
func (g *OpcGateway) checkNodeHealthV2() {
	nm := g.Kernel.NodeMgr
	if nm == nil {
		return
	}

	// 收集需要广播下线的事件
	var toOffline []*kernel.NodeRegister

	nm.WithLock(func() {
		now := time.Now()
		for nodeID, state := range nm.GetNodes() {
			if state.Register == nil || state.Register.NodeID == "gateway" {
				continue
			}
			if state.Register.Status == "offline" {
				continue
			}

			elapsed := now.Sub(state.Heartbeat)

			if state.Register.Status == "online" && elapsed > SuspectAfter && elapsed <= OfflineAfter {
				// 第一阶段：suspect（仅警告，不广播）
				if !state.Suspect {
					state.Suspect = true
					log.Printf("📡 ARC-NET ⚠️ Node %s SUSPECT (no heartbeat for %v)", nodeID, elapsed.Round(time.Second))
				}
			}

			if elapsed > OfflineAfter {
				// 第二阶段：offline
				if state.Register.Status != "offline" {
					state.Register.Status = "offline"
					toOffline = append(toOffline, state.Register)
					log.Printf("📡 ARC-NET 🔴 Node %s OFFLINE (no heartbeat for %v)", nodeID, elapsed.Round(time.Second))

					// 回收任务
					g.Kernel.NodeMgr.ReclaimTasksForNode(nodeID)
				}
			}
		}
	})

	// 在锁外广播下线事件
	for _, reg := range toOffline {
		g.BroadcastNodeEvent(EventTypeNodeLeave, reg)
	}
}

// =============================================================================
// Extension: 向 kernel.NodeManagerState 注入 Suspect 字段
// 在 kernel/actions.go 中处理心跳时重置 Suspect
// =============================================================================

// =============================================================================
// 全量同步端点
// =============================================================================

// handleTopologySync 返回集群全量拓扑
// GET /api/v1/cluster/topology
func (g *OpcGateway) handleTopologySync(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()

	type TopologyNode struct {
		NodeID    string  `json:"node_id"`
		Host      string  `json:"host"`
		Platform  string  `json:"platform"`
		Region    string  `json:"region"`
		GPU       string  `json:"gpu"`
		CPU       int     `json:"cpu"`
		Memory    float64 `json:"memory"`
		Status    string  `json:"status"`
		Version   string  `json:"version"`
		Uptime    string  `json:"uptime"`
		Suspect   bool    `json:"suspect"`
		LastSeen  string  `json:"last_seen"`
	}

	topology := make([]TopologyNode, 0, len(nodes))
	for _, state := range nodes {
		reg := state.Register
		if reg == nil {
			continue
		}
		tn := TopologyNode{
			NodeID:   reg.NodeID,
			Host:     reg.IPAddress,
			Platform: reg.Platform,
			Region:   reg.Region,
			GPU:      reg.GPUType,
			CPU:      reg.CPUCores,
			Memory:   reg.MemoryGB,
			Status:   reg.Status,
			Version:  reg.Version,
			Suspect:  state.Suspect,
			LastSeen: state.Heartbeat.Format(time.RFC3339),
			Uptime:   time.Since(reg.RegisteredAt).Round(time.Second).String(),
		}
		topology = append(topology, tn)
	}

	w.Header().Set("Content-Type", "application/json")
	wsCount := 0
	if g.wsHub != nil {
		wsCount = g.wsHub.OnlineCount()
	}
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":       "ok",
		"total_nodes":  len(topology),
		"nodes":        topology,
		"ws_online":    wsCount, // WebSocket 连接数
		"timestamp":    time.Now().Unix(),
	})
}

// =============================================================================
// 端点注册（需要在 NewOpcGateway 或 setupRoutes 中调用）
// =============================================================================

func (g *OpcGateway) registerArcNetRoutes() {
	http.HandleFunc("/api/v1/cluster/topology", g.handleTopologySync)
	logWithTimestamp("📡 ARC-AI-NET topology sync registered: /api/v1/cluster/topology")
}