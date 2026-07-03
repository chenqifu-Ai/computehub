package gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/computehub/opc/src/kernel"
)

// AgentRegisterRequest 智能体注册请求
type AgentRegisterRequest struct {
	Name         string            `json:"name"`
	AgentID      string            `json:"agent_id"`
	Mode         string            `json:"mode"`
	Platform     string            `json:"platform"`
	Version      string            `json:"version"`
	Capabilities []string          `json:"capabilities,omitempty"`
	Model        string            `json:"model,omitempty"`
	Status       string            `json:"status,omitempty"`
	NodeID       string            `json:"node_id"`
	Metadata     map[string]string `json:"metadata,omitempty"`
}

// AgentHeartbeatRequest 智能体心跳请求
type AgentHeartbeatRequest struct {
	AgentID string `json:"agent_id"`
}

// handleAgentRegister — POST /api/v1/agents/register
// 智能体注册自身到 Gateway，实现 Agent 发现
func (g *OpcGateway) handleAgentRegister(w http.ResponseWriter, r *http.Request) {
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

	var req AgentRegisterRequest
	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.Name == "" && req.AgentID == "" {
		g.sendResponse(w, Response{Success: false, Error: "name or agent_id is required"})
		return
	}

	agentReg := g.Kernel.AgentReg
	ip := extractClientIP(r)

	info := &kernel.AgentInfo{
		Name:         req.Name,
		AgentID:      req.AgentID,
		Mode:         req.Mode,
		Platform:     req.Platform,
		Version:      req.Version,
		Capabilities: req.Capabilities,
		Model:        req.Model,
		Status:       req.Status,
		NodeID:       req.NodeID,
		IPAddress:    ip,
		Metadata:     req.Metadata,
		RegisteredAt: time.Now(),
		LastHeartbeat: time.Now(),
	}

	if info.Status == "" {
		info.Status = "online"
	}

	if err := agentReg.Register(info); err != nil {
		g.sendResponse(w, Response{Success: false, Error: err.Error()})
		return
	}

	logWithTimestamp("[AgentApi] ✅ Agent注册: %s (%s | %s | %s)", info.Name, info.Mode, info.Status, ip)

	g.sendResponse(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"agent": info,
			"message": fmt.Sprintf("Agent '%s' registered", info.Name),
		},
	})
}

// handleAgentHeartbeat — POST /api/v1/agents/heartbeat
// 智能体心跳保活
func (g *OpcGateway) handleAgentHeartbeat(w http.ResponseWriter, r *http.Request) {
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

	var req AgentHeartbeatRequest
	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.AgentID == "" {
		g.sendResponse(w, Response{Success: false, Error: "agent_id is required"})
		return
	}

	agentReg := g.Kernel.AgentReg
	if err := agentReg.Heartbeat(req.AgentID); err != nil {
		g.sendResponse(w, Response{Success: false, Error: err.Error()})
		return
	}

	g.sendResponse(w, Response{Success: true, Data: map[string]string{"status": "ok"}})
}

// handleAgentUnregister — POST /api/v1/agents/unregister
// 智能体主动注销
func (g *OpcGateway) handleAgentUnregister(w http.ResponseWriter, r *http.Request) {
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
		AgentID string `json:"agent_id"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.AgentID == "" {
		g.sendResponse(w, Response{Success: false, Error: "agent_id is required"})
		return
	}

	if err := g.Kernel.AgentReg.Unregister(req.AgentID); err != nil {
		g.sendResponse(w, Response{Success: false, Error: err.Error()})
		return
	}

	g.sendResponse(w, Response{Success: true, Data: map[string]string{"status": "unregistered"}})
}

// handleAgentList — GET /api/v1/agents/list
// 获取所有在线智能体列表（Agent 发现）
func (g *OpcGateway) handleAgentList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	agents := g.Kernel.AgentReg.List()

	g.sendResponse(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"agents": agents,
			"total":  len(agents),
		},
	})
}

// handleAgentGet — GET /api/v1/agents/get?agent_id=xxx
// 获取单个智能体信息
func (g *OpcGateway) handleAgentGet(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	agentID := r.URL.Query().Get("agent_id")
	if agentID == "" {
		g.sendResponse(w, Response{Success: false, Error: "agent_id query parameter is required"})
		return
	}

	agent := g.Kernel.AgentReg.Get(agentID)
	if agent == nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Agent '%s' not found", agentID)})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    agent,
	})
}

// handleOpenClawStatus — GET /api/v1/openclaw/status
// 查询所有 Worker 节点上的 OpenClaw 实例状态
// 只查询本地节点（127.0.0.1），远程节点跳过（无 Agent 端点可达）
func (g *OpcGateway) handleOpenClawStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	if nodes == nil {
		nodes = []*kernel.NodeManagerState{}
	}

	type ocNodeStatus struct {
		NodeID       string `json:"node_id"`
		Installed    bool   `json:"installed"`
		Running      bool   `json:"running"`
		Version      string `json:"version"`
		Port         int    `json:"port"`
		HealthOK     bool   `json:"health_ok"`
		LastHealth   string `json:"last_health"`
		RestartCount int    `json:"restart_count"`
		LastError    string `json:"last_error"`
		AutoHeal     bool   `json:"auto_heal"`
		Platform     string `json:"platform"`
		Reachable    bool   `json:"reachable"`
		Error        string `json:"error,omitempty"`
	}

	results := make([]ocNodeStatus, 0)

	for _, node := range nodes {
		if node.Register == nil {
			continue
		}
		nodeID := node.Register.NodeID
		if nodeID == "" {
			continue
		}

		status := ocNodeStatus{
			NodeID:    nodeID,
			Platform:  node.Register.Platform,
			Reachable: false,
		}

		// 只查询本地节点（127.0.0.1），远程节点跳过
		// 本地节点有 Worker Agent (8383) 可直接查询
		if node.Register.IPAddress != "127.0.0.1" {
			status.Error = "remote node (no local agent endpoint)"
			results = append(results, status)
			continue
		}

		// 直接 HTTP 查询本地 Worker Agent，不走任务分发（避免阻塞 WS 心跳）
		client := &http.Client{Timeout: 5 * time.Second}
		resp, err := client.Get("http://127.0.0.1:8383/api/v1/worker/openclaw_status")
		if err != nil {
			status.Error = fmt.Sprintf("Agent unreachable: %v", err)
			results = append(results, status)
			continue
		}
		defer resp.Body.Close()

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			status.Error = fmt.Sprintf("Read response: %v", err)
			results = append(results, status)
			continue
		}

		var agentResp struct {
			Success bool         `json:"success"`
			Data    ocNodeStatus `json:"data"`
			Error   string       `json:"error"`
		}
		if err := json.Unmarshal(body, &agentResp); err != nil {
			status.Error = fmt.Sprintf("Parse error: %v", err)
			results = append(results, status)
			continue
		}

		if !agentResp.Success {
			status.Error = agentResp.Error
			results = append(results, status)
			continue
		}

		agentResp.Data.Reachable = true
		agentResp.Data.NodeID = nodeID
		results = append(results, agentResp.Data)
	}

	g.sendResponse(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"nodes": results,
			"total": len(results),
		},
	})
}