package health

import (
	"fmt"
	"net"
	"sync"
	"time"
)

// ====== 节点健康检查模块 ======
// 基于 TCP ping 的真实延迟测量，不使用 mock 数据

// HealthCheckResult 单次健康检查结果
type HealthCheckResult struct {
	NodeID       string        `json:"node_id"`
	Success      bool          `json:"success"`
	Latency      time.Duration `json:"latency"`
	TCPConnected bool          `json:"tcp_connected"`
	DNSLookup    time.Duration `json:"dns_lookup"`
	Error        string        `json:"error,omitempty"`
	Timestamp    time.Time     `json:"timestamp"`
}

// NodeHealth 节点健康状态
type NodeHealth struct {
	NodeID          string             `json:"node_id"`
	Status          string             `json:"status"` // "healthy" | "degraded" | "unhealthy"
	LastCheck       time.Time          `json:"last_check"`
	SuccessRate     float64            `json:"success_rate"`
	TotalChecks     int                `json:"total_checks"`
	Failures        int                `json:"failures"`
	AvgLatency      time.Duration      `json:"avg_latency"`
	RecentChecks    []HealthCheckResult `json:"recent_checks"`
	MaxRecentChecks int                `json:"-"` // 内部字段，不序列化
}

// HealthMonitor 健康监控器
type HealthMonitor struct {
	mu                sync.RWMutex
	nodeHealth        map[string]*NodeHealth
	checkInterval     time.Duration
	timeout           time.Duration
	healthyThreshold  int    // 连续成功 N 次后标记 healthy
	unhealthyThreshold int   // 连续失败 N 次后标记 unhealthy
	maxRecentChecks   int    // 保留最近 N 条记录
	checkFunc         func(nodeID string) (HealthCheckResult, error)
}

// HealthMonitorConfig 健康监控配置
type HealthMonitorConfig struct {
	CheckInterval      time.Duration
	Timeout            time.Duration
	HealthyThreshold   int
	UnhealthyThreshold int
	MaxRecentChecks    int
}

// DefaultHealthConfig 默认配置
func DefaultHealthConfig() HealthMonitorConfig {
	return HealthMonitorConfig{
		CheckInterval:      30 * time.Second,
		Timeout:            5 * time.Second,
		HealthyThreshold:   3,
		UnhealthyThreshold: 3,
		MaxRecentChecks:    10,
	}
}

// NewHealthMonitor 创建健康监控器
func NewHealthMonitor(config HealthMonitorConfig) *HealthMonitor {
	if config.CheckInterval == 0 {
		config.CheckInterval = DefaultHealthConfig().CheckInterval
	}
	if config.Timeout == 0 {
		config.Timeout = DefaultHealthConfig().Timeout
	}
	if config.HealthyThreshold == 0 {
		config.HealthyThreshold = DefaultHealthConfig().HealthyThreshold
	}
	if config.UnhealthyThreshold == 0 {
		config.UnhealthyThreshold = DefaultHealthConfig().UnhealthyThreshold
	}
	if config.MaxRecentChecks == 0 {
		config.MaxRecentChecks = DefaultHealthConfig().MaxRecentChecks
	}

	return &HealthMonitor{
		nodeHealth:        make(map[string]*NodeHealth),
		checkInterval:     config.CheckInterval,
		timeout:           config.Timeout,
		healthyThreshold:  config.HealthyThreshold,
		unhealthyThreshold: config.UnhealthyThreshold,
		maxRecentChecks:   config.MaxRecentChecks,
		checkFunc:         defaultTCPPing,
	}
}

// SetCheckFunc 设置自定义健康检查函数
func (hm *HealthMonitor) SetCheckFunc(fn func(nodeID string) (HealthCheckResult, error)) {
	hm.checkFunc = fn
}

// RegisterNode 注册节点到监控
func (hm *HealthMonitor) RegisterNode(nodeID string) {
	hm.mu.Lock()
	defer hm.mu.Unlock()

	if _, exists := hm.nodeHealth[nodeID]; !exists {
		hm.nodeHealth[nodeID] = &NodeHealth{
			NodeID:          nodeID,
			Status:          "unknown",
			TotalChecks:     0,
			MaxRecentChecks: hm.maxRecentChecks,
		}
	}
}

// UnregisterNode 从监控中移除节点
func (hm *HealthMonitor) UnregisterNode(nodeID string) {
	hm.mu.Lock()
	defer hm.mu.Unlock()

	delete(hm.nodeHealth, nodeID)
}

// CheckNode 执行节点健康检查
func (hm *HealthMonitor) CheckNode(nodeID string) (HealthCheckResult, error) {
	if hm.checkFunc == nil {
		return HealthCheckResult{}, fmt.Errorf("no check function set")
	}

	result, err := hm.checkFunc(nodeID)
	if err != nil {
		result.Error = err.Error()
	}

	// 更新节点健康状态
	hm.updateNodeHealth(nodeID, result)

	return result, nil
}

// GetNodeHealth 获取节点健康状态
func (hm *HealthMonitor) GetNodeHealth(nodeID string) (*NodeHealth, error) {
	hm.mu.RLock()
	defer hm.mu.RUnlock()

	health, exists := hm.nodeHealth[nodeID]
	if !exists {
		return nil, fmt.Errorf("node %s not registered", nodeID)
	}

	// 返回副本
	c := *health
	return &c, nil
}

// GetAllHealth 获取所有节点健康状态
func (hm *HealthMonitor) GetAllHealth() map[string]*NodeHealth {
	hm.mu.RLock()
	defer hm.mu.RUnlock()

	result := make(map[string]*NodeHealth)
	for id, health := range hm.nodeHealth {
		c := *health
		result[id] = &c
	}
	return result
}

// GetHealthyCount 获取健康节点数量
func (hm *HealthMonitor) GetHealthyCount() int {
	hm.mu.RLock()
	defer hm.mu.RUnlock()

	count := 0
	for _, health := range hm.nodeHealth {
		if health.Status == "healthy" {
			count++
		}
	}
	return count
}

// GetUnhealthyCount 获取不健康节点数量
func (hm *HealthMonitor) GetUnhealthyCount() int {
	hm.mu.RLock()
	defer hm.mu.RUnlock()

	count := 0
	for _, health := range hm.nodeHealth {
		if health.Status == "unhealthy" {
			count++
		}
	}
	return count
}

// GetStats 获取监控统计信息
func (hm *HealthMonitor) GetStats() map[string]interface{} {
	hm.mu.RLock()
	defer hm.mu.RUnlock()

	total := len(hm.nodeHealth)
	healthy := 0
	degraded := 0
	unhealthy := 0

	for _, health := range hm.nodeHealth {
		switch health.Status {
		case "healthy":
			healthy++
		case "degraded":
			degraded++
		case "unhealthy":
			unhealthy++
		}
	}

	return map[string]interface{}{
		"total_nodes":   total,
		"healthy":       healthy,
		"degraded":      degraded,
		"unhealthy":     unhealthy,
		"check_interval": hm.checkInterval.String(),
		"timeout":        hm.timeout.String(),
	}
}

// ====== 内部方法 ======

func (hm *HealthMonitor) updateNodeHealth(nodeID string, result HealthCheckResult) {
	hm.mu.Lock()
	defer hm.mu.Unlock()

	health, exists := hm.nodeHealth[nodeID]
	if !exists {
		return
	}

	health.LastCheck = time.Now()
	health.TotalChecks++
	health.RecentChecks = append(health.RecentChecks, result)

	// 限制最近检查数量
	if len(health.RecentChecks) > health.MaxRecentChecks {
		health.RecentChecks = health.RecentChecks[1:]
	}

	// 更新成功率
	health.SuccessRate = float64(health.TotalChecks-health.Failures) / float64(health.TotalChecks)

	// 更新平均延迟
	var totalLatency time.Duration
	for _, r := range health.RecentChecks {
		totalLatency += r.Latency
	}
	health.AvgLatency = totalLatency / time.Duration(len(health.RecentChecks))

	// 更新状态 - 计算连续成功/失败次数（从最近检查向前）
	consecutiveSuccess := 0
	consecutiveFailures := 0
	for i := len(health.RecentChecks) - 1; i >= 0; i-- {
		if health.RecentChecks[i].Success {
			consecutiveSuccess++
		} else {
			break
		}
	}
	for i := len(health.RecentChecks) - 1; i >= 0; i-- {
		if !health.RecentChecks[i].Success {
			consecutiveFailures++
		} else {
			break
		}
	}

	prevStatus := health.Status

	if consecutiveSuccess >= hm.healthyThreshold {
		health.Status = "healthy"
	} else if consecutiveFailures >= hm.unhealthyThreshold {
		health.Status = "unhealthy"
		health.Failures++
	} else if consecutiveFailures > 0 {
		health.Status = "degraded"
	}

	// 状态变更时记录
	if prevStatus != health.Status && prevStatus != "unknown" {
		fmt.Printf("[HealthMonitor] Node %s status changed: %s -> %s\n",
			nodeID, prevStatus, health.Status)
	}
}

// ====== 默认 TCP Ping 检查 ======

func defaultTCPPing(nodeID string) (HealthCheckResult, error) {
	result := HealthCheckResult{
		NodeID:    nodeID,
		Timestamp: time.Now(),
	}

	// 解析节点地址
	parts := splitNodeID(nodeID)
	if len(parts) < 2 {
		result.Success = false
		result.Error = "invalid node ID format, expected 'hostname:port'"
		return result, fmt.Errorf("invalid node ID: %s", nodeID)
	}

	host, port := parts[0], parts[1]

	// DNS 查找计时
	dnsStart := time.Now()
	_, err := net.LookupHost(host)
	result.DNSLookup = time.Since(dnsStart)

	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("DNS lookup failed: %v", err)
		return result, err
	}

	// TCP 连接计时
	connStart := time.Now()
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(host, port), 5*time.Second)
	result.Latency = time.Since(connStart)

	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("TCP connection failed: %v", err)
		return result, err
	}
	defer conn.Close()

	result.Success = true
	result.TCPConnected = true
	return result, nil
}

// 简单的节点 ID 解析
func splitNodeID(nodeID string) []string {
	for i := len(nodeID) - 1; i >= 0; i-- {
		if nodeID[i] == ':' {
			return []string{nodeID[:i], nodeID[i+1:]}
		}
	}
	return []string{nodeID}
}
