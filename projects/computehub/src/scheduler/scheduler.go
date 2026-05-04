package scheduler

import (
	"fmt"
	"sync"
	"time"
)

// ====== 调度器配置 ======

type SchedulerConfig struct {
	// 区域熔断阈值
	FailureRateThreshold float64 `json:"failure_rate_threshold"` // 默认 0.3 (30%)

	// 延迟阈值 (毫秒)
	L3LatencyThreshold int64 `json:"l3_latency_threshold"` // 默认 200ms

	// 负载均衡算法: "round_robin" | "least_loaded" | "latency_aware"
	LoadBalanceStrategy string `json:"load_balance_strategy"`

	// 节点健康检查间隔 (秒)
	HealthCheckInterval int `json:"health_check_interval"`

	// 节点超时时间 (秒) - 心跳超时即认为离线
	NodeTimeout int `json:"node_timeout"`

	// 任务超时时间 (秒)
	TaskTimeout int `json:"task_timeout"`

	// 最大重试次数
	MaxRetries int `json:"max_retries"`
}

// DefaultConfig 返回默认配置
func DefaultConfig() SchedulerConfig {
	return SchedulerConfig{
		FailureRateThreshold: 0.3,
		L3LatencyThreshold:   200,
		LoadBalanceStrategy:  "latency_aware",
		HealthCheckInterval:  30,
		NodeTimeout:          60,
		TaskTimeout:          300,
		MaxRetries:           3,
	}
}

// ====== 调度结果 ======

// ScheduleResult 表示任务调度结果
type ScheduleResult struct {
	NodeID       string        `json:"node_id"`
	TaskID       string        `json:"task_id"`
	AssignedAt   time.Time     `json:"assigned_at"`
	Reason       string        `json:"reason"` // 调度原因说明
	FailureRate  float64       `json:"failure_rate"`
	Latency      int64         `json:"latency"` // ms
	Priority     int           `json:"priority"`
	RegionScore  float64       `json:"region_score"`
	LoadScore    float64       `json:"load_score"`
}

// RegionInfo 区域信息
type RegionInfo struct {
	Name         string
	Nodes        map[string]*NodeInfo
	FailureRate  float64
	LastIncident time.Time
}

// NodeInfo 节点调度信息 (用于决策)
type NodeInfo struct {
	ID           string    `json:"id"`
	Region       string    `json:"region"`
	Status       string    `json:"status"` // "online" | "draining" | "offline" | "circuit_breaking"
	GPUType      string    `json:"gpu_type"`
	CPUCores     int       `json:"cpu_cores"`
	MemoryGB     float64   `json:"memory_gb"`
	GPUMemoryGB  float64   `json:"gpu_memory_gb"`
	ActiveTasks  int       `json:"active_tasks"`
	MaxTasks     int       `json:"max_tasks"`
	CPUUtil      float64   `json:"cpu_utilization"` // 0-100
	GPUUtil      float64   `json:"gpu_utilization"` // 0-100
	Temperature  float64   `json:"temperature"`     // Celsius
	NetworkLatency int64   `json:"network_latency_ms"`
	SuccessRate  float64   `json:"success_rate"`    // last 100 tasks
	FailureRate  float64   `json:"failure_rate"`    // last 100 tasks
	LastHeartbeat time.Time `json:"last_heartbeat"`
	AssignedAt    time.Time `json:"assigned_at"` // node registration time
}

// ====== 智能调度器 ======

type Scheduler struct {
	config SchedulerConfig
	mu     sync.RWMutex

	// 节点索引
	regionIndex map[string]*RegionInfo
	nodeIndex   map[string]*NodeInfo

	// 区域熔断状态
	circuitBreaker map[string]bool // region -> is_breaking

	// 调度历史 (用于分析)
	scheduleHistory []*ScheduleResult
	maxHistory      int
}

// NewScheduler 创建新的调度器
func NewScheduler(config SchedulerConfig) *Scheduler {
	if config.FailureRateThreshold == 0 {
		config.FailureRateThreshold = DefaultConfig().FailureRateThreshold
	}
	if config.L3LatencyThreshold == 0 {
		config.L3LatencyThreshold = DefaultConfig().L3LatencyThreshold
	}
	if config.HealthCheckInterval == 0 {
		config.HealthCheckInterval = DefaultConfig().HealthCheckInterval
	}
	if config.NodeTimeout == 0 {
		config.NodeTimeout = DefaultConfig().NodeTimeout
	}
	if config.TaskTimeout == 0 {
		config.TaskTimeout = DefaultConfig().TaskTimeout
	}
	if config.MaxRetries == 0 {
		config.MaxRetries = DefaultConfig().MaxRetries
	}
	if config.LoadBalanceStrategy == "" {
		config.LoadBalanceStrategy = DefaultConfig().LoadBalanceStrategy
	}

	return &Scheduler{
		config:         config,
		regionIndex:    make(map[string]*RegionInfo),
		nodeIndex:      make(map[string]*NodeInfo),
		circuitBreaker: make(map[string]bool),
		maxHistory:     1000,
	}
}

// ====== 节点管理 ======

// RegisterNode 注册节点到调度器
func (s *Scheduler) RegisterNode(info *NodeInfo) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.nodeIndex[info.ID]; exists {
		return fmt.Errorf("node %s already registered", info.ID)
	}

	// Ensure region exists
	if _, regionExists := s.regionIndex[info.Region]; !regionExists {
		s.regionIndex[info.Region] = &RegionInfo{
			Name:  info.Region,
			Nodes: make(map[string]*NodeInfo),
		}
	}

	s.regionIndex[info.Region].Nodes[info.ID] = info
	s.nodeIndex[info.ID] = info

	return nil
}

// UpdateNodeHeartbeat 更新节点心跳和指标
func (s *Scheduler) UpdateNodeHeartbeat(nodeID string, latency int64, gpuUtil, temp, memUsed float64) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	node, exists := s.nodeIndex[nodeID]
	if !exists {
		return fmt.Errorf("node %s not registered", nodeID)
	}

	node.NetworkLatency = latency
	node.GPUUtil = gpuUtil
	node.Temperature = temp
	node.LastHeartbeat = time.Now()

	// Update region failure rate if node was in circuit breaker
	region := s.regionIndex[node.Region]
	if region != nil {
		region.FailureRate = node.FailureRate // 简化：节点级别的失败率
	}

	return nil
}

// MarkNodeOffline 标记节点离线
func (s *Scheduler) MarkNodeOffline(nodeID string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if node, exists := s.nodeIndex[nodeID]; exists {
		node.Status = "offline"
	}
}

// ====== 核心调度逻辑 ======

// ScheduleTask 智能调度任务到最优节点
func (s *Scheduler) ScheduleTask(taskID, regionAffinity string, priority int) *ScheduleResult {
	s.mu.Lock()
	defer s.mu.Unlock()

	candidates := s.getCandidates(regionAffinity)
	if len(candidates) == 0 {
		return &ScheduleResult{
			Reason: "no available nodes",
		}
	}

	// 检查区域熔断
	for _, node := range candidates {
		if s.circuitBreaker[node.Region] {
			continue // 跳过熔断区域
		}
	}

	// 评分并选择最优节点
	var best *NodeInfo
	var bestScore float64

	for _, node := range candidates {
		score := s.scoreNode(node, regionAffinity, priority)
		if score > bestScore {
			bestScore = score
			best = node
		}
	}

	if best == nil {
		return &ScheduleResult{
			Reason: "no suitable node found",
		}
	}

	// 分配任务
	best.ActiveTasks++

	result := &ScheduleResult{
		NodeID:      best.ID,
		TaskID:      taskID,
		AssignedAt:  time.Now(),
		Reason:      fmt.Sprintf("best score: %.2f", bestScore),
		FailureRate: best.FailureRate,
		Latency:     best.NetworkLatency,
		Priority:    priority,
	}

	// 记录历史
	s.scheduleHistory = append(s.scheduleHistory, result)
	if len(s.scheduleHistory) > s.maxHistory {
		s.scheduleHistory = s.scheduleHistory[1:]
	}

	return result
}

// GetCandidates 获取符合条件的候选节点
func (s *Scheduler) getCandidates(regionAffinity string) []*NodeInfo {
	var candidates []*NodeInfo

	for _, node := range s.nodeIndex {
		// 必须在线
		if node.Status != "online" {
			continue
		}

		// 检查超时 (只在 heartbeat 设置后才检查)
		if !node.LastHeartbeat.IsZero() && time.Since(node.LastHeartbeat).Seconds() > float64(s.config.NodeTimeout) {
			node.Status = "offline"
			continue
		}

		// 检查容量
		if node.ActiveTasks >= node.MaxTasks {
			continue
		}

		// 区域亲和性过滤
		if regionAffinity != "" && node.Region != regionAffinity {
			continue
		}

		candidates = append(candidates, node)
	}

	return candidates
}

// scoreNode 对节点进行综合评分
func (s *Scheduler) scoreNode(node *NodeInfo, regionAffinity string, priority int) float64 {
	var score float64

	// 1. 区域亲和性 (40%)
	if node.Region == regionAffinity {
		score += 40.0
	} else if regionAffinity == "" {
		score += 20.0 // 无偏好时给基础分
	}

	// 2. 延迟分数 (30%) - L3 级匹配
	latencyScore := 0.0
	if node.NetworkLatency <= 50 {
		latencyScore = 30.0
	} else if node.NetworkLatency <= 100 {
		latencyScore = 25.0
	} else if node.NetworkLatency <= s.config.L3LatencyThreshold {
		latencyScore = 20.0
	} else {
		latencyScore = float64(s.config.L3LatencyThreshold-node.NetworkLatency) / float64(s.config.L3LatencyThreshold) * 20.0
		if latencyScore < 0 {
			latencyScore = 0
		}
	}
	score += latencyScore

	// 3. 负载分数 (20%)
	loadRatio := float64(node.ActiveTasks) / float64(node.MaxTasks)
	loadScore := (1.0 - loadRatio) * 20.0
	score += loadScore

	// 4. 成功率 (10%)
	score += node.SuccessRate * 10.0

	return score
}

// ====== 区域熔断机制 ======

// CheckCircuitBreaker 检查并可能触发区域熔断
func (s *Scheduler) CheckCircuitBreaker(region string, taskSuccess bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	regionInfo, exists := s.regionIndex[region]
	if !exists {
		return
	}

	if !taskSuccess {
		regionInfo.FailureRate = 0.9 // 标记高失败率
		regionInfo.LastIncident = time.Now()
	}

	// 触发熔断
	if regionInfo.FailureRate >= s.config.FailureRateThreshold {
		s.circuitBreaker[region] = true
		// 标记区域内所有节点
		for _, node := range regionInfo.Nodes {
			node.Status = "circuit_breaking"
		}
	}
}

// ClearCircuitBreaker 手动解除区域熔断
func (s *Scheduler) ClearCircuitBreaker(region string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.circuitBreaker[region] = false
	if regionInfo, exists := s.regionIndex[region]; exists {
		for _, node := range regionInfo.Nodes {
			node.Status = "online"
		}
	}
}

// ====== 健康检查 ======

// HealthCheck 执行节点健康检查
func (s *Scheduler) HealthCheck() map[string]string {
	s.mu.Lock()
	defer s.mu.Unlock()

	results := make(map[string]string)

	for id, node := range s.nodeIndex {
		// 检查超时
		if time.Since(node.LastHeartbeat).Seconds() > float64(s.config.NodeTimeout) {
			results[id] = "offline (timeout)"
			node.Status = "offline"
			continue
		}

		// 检查温度 (超过 90°C 告警)
		if node.Temperature > 90.0 {
			results[id] = "warning (high temp)"
		} else if node.Temperature > 80.0 {
			results[id] = "warning (elevated temp)"
		} else {
			results[id] = "healthy"
		}

		// 检查 GPU 利用率 (超过 100% 表示异常)
		if node.GPUUtil > 100.0 {
			results[id] = "error (GPU overreporting)"
		}
	}

	return results
}

// ====== 调度统计 ======

// GetStats 获取调度器统计信息
func (s *Scheduler) GetStats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	totalNodes := len(s.nodeIndex)
	onlineNodes := 0
	totalTasks := 0
	breakingRegions := 0

	for _, node := range s.nodeIndex {
		if node.Status == "online" {
			onlineNodes++
		}
		totalTasks += node.ActiveTasks
	}

	for _, breaking := range s.circuitBreaker {
		if breaking {
			breakingRegions++
		}
	}

	return map[string]interface{}{
		"total_nodes":        totalNodes,
		"online_nodes":       onlineNodes,
		"total_tasks":        totalTasks,
		"scheduled_tasks":    len(s.scheduleHistory),
		"breaking_regions":   breakingRegions,
		"load_balance":       s.config.LoadBalanceStrategy,
		"failure_threshold":  s.config.FailureRateThreshold,
		"l3_latency_ms":      s.config.L3LatencyThreshold,
	}
}

// ====== 工具函数 ======
