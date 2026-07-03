package kernel

import (
	"fmt"
	"sync"
	"time"
)

// AgentInfo 智能体注册信息
// Agent 是 OpenClaw 智能体，通过 Gateway 注册自身，实现 Agent 发现
type AgentInfo struct {
	Name         string            `json:"name"`                   // 智能体名称（如"小智"、"Win智"）
	AgentID      string            `json:"agent_id"`               // 唯一标识（OpenClaw agent id）
	Mode         string            `json:"mode"`                   // "chat" | "backend" | "tui"
	Platform     string            `json:"platform"`               // "linux" | "windows" | "android"
	Version      string            `json:"version"`                // OpenClaw 版本
	Capabilities []string          `json:"capabilities,omitempty"` // 能力标签 ["code", "shell", "browser", ...]
	Model        string            `json:"model,omitempty"`        // 当前使用的模型
	Status       string            `json:"status"`                 // "online" | "busy" | "offline"
	NodeID       string            `json:"node_id"`                // 所在节点（ComputeHub worker 节点名）
	IPAddress    string            `json:"ip_address"`             // Gateway 看到的客户端 IP
	Metadata     map[string]string `json:"metadata,omitempty"`     // 扩展信息
	RegisteredAt time.Time         `json:"registered_at"`
	LastHeartbeat time.Time        `json:"last_heartbeat"`
}

// AgentHeartbeat 智能体心跳请求
type AgentHeartbeat struct {
	Name       string `json:"name"`
	AgentID    string `json:"agent_id"`
	Mode       string `json:"mode"`
	Status     string `json:"status"`
	Capabilities []string `json:"capabilities,omitempty"`
	NodeID     string `json:"node_id"`
}

// AgentRegistry 智能体注册表
// 管理所有在线 AI 智能体，支持注册、心跳保活、自动过期
type AgentRegistry struct {
	mu          sync.RWMutex
	agents      map[string]*AgentInfo // key = agent_id
	expiry      time.Duration         // 无心跳超时时间
	cleanupDone chan struct{}
}

// NewAgentRegistry 创建智能体注册表
func NewAgentRegistry() *AgentRegistry {
	ar := &AgentRegistry{
		agents:      make(map[string]*AgentInfo),
		expiry:      30 * time.Second,
		cleanupDone: make(chan struct{}),
	}
	go ar.cleanupLoop()
	return ar
}

// Stop 停止后台清理协程
func (ar *AgentRegistry) Stop() {
	close(ar.cleanupDone)
}

// Register 注册或更新一个智能体
func (ar *AgentRegistry) Register(info *AgentInfo) error {
	ar.mu.Lock()
	defer ar.mu.Unlock()

	if info.AgentID == "" && info.Name == "" {
		return fmt.Errorf("agent_id or name is required")
	}

	// 如果没有 agent_id，用 name 作为 key
	key := info.AgentID
	if key == "" {
		key = info.Name
	}

	now := time.Now()
	if existing, ok := ar.agents[key]; ok {
		// 更新，保留注册时间
		existing.Name = info.Name
		existing.Mode = info.Mode
		existing.Platform = info.Platform
		existing.Version = info.Version
		existing.Capabilities = info.Capabilities
		existing.Model = info.Model
		existing.Status = info.Status
		existing.NodeID = info.NodeID
		existing.IPAddress = info.IPAddress
		existing.Metadata = info.Metadata
		existing.LastHeartbeat = now
		if info.RegisteredAt.IsZero() {
			existing.RegisteredAt = now
		} else {
			existing.RegisteredAt = info.RegisteredAt
		}
		logWithTimestamp("[AgentRegistry] ✅ 更新智能体: %s (%s)", key, info.Status)
	} else {
		info.RegisteredAt = now
		info.LastHeartbeat = now
		if info.Status == "" {
			info.Status = "online"
		}
		ar.agents[key] = info
		logWithTimestamp("[AgentRegistry] 🆕 注册智能体: %s (%s | %s)", key, info.Mode, info.Status)
	}

	return nil
}

// Heartbeat 更新智能体心跳，保持在线状态
func (ar *AgentRegistry) Heartbeat(agentID string) error {
	ar.mu.Lock()
	defer ar.mu.Unlock()

	if agent, ok := ar.agents[agentID]; ok {
		agent.LastHeartbeat = time.Now()
		return nil
	}
	return fmt.Errorf("agent %s not found", agentID)
}

// Unregister 注销智能体
func (ar *AgentRegistry) Unregister(agentID string) error {
	ar.mu.Lock()
	defer ar.mu.Unlock()

	if _, ok := ar.agents[agentID]; ok {
		delete(ar.agents, agentID)
		logWithTimestamp("[AgentRegistry] 🗑️ 注销智能体: %s", agentID)
		return nil
	}
	return fmt.Errorf("agent %s not found", agentID)
}

// List 返回所有在线智能体
func (ar *AgentRegistry) List() []*AgentInfo {
	ar.mu.RLock()
	defer ar.mu.RUnlock()

	result := make([]*AgentInfo, 0, len(ar.agents))
	for _, agent := range ar.agents {
		result = append(result, agent)
	}
	return result
}

// Get 获取单个智能体信息
func (ar *AgentRegistry) Get(agentID string) *AgentInfo {
	ar.mu.RLock()
	defer ar.mu.RUnlock()
	return ar.agents[agentID]
}

// cleanupLoop 定期清理过期智能体（无心跳超时 → 自动下线）
func (ar *AgentRegistry) cleanupLoop() {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			ar.cleanup()
		case <-ar.cleanupDone:
			return
		}
	}
}

func (ar *AgentRegistry) cleanup() {
	ar.mu.Lock()
	defer ar.mu.Unlock()

	now := time.Now()
	for key, agent := range ar.agents {
		if now.Sub(agent.LastHeartbeat) > ar.expiry {
			logWithTimestamp("[AgentRegistry] ⏰ 智能体离线 (心跳超时): %s (%s)", key, agent.Name)
			delete(ar.agents, key)
		}
	}
}