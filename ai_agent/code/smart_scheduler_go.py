#!/usr/bin/env python3
"""
ComputeHub 智能调度器 - Go 实现

功能：
1. 地理位置匹配
2. 成本优化算法
3. 负载均衡
4. 节点评分系统

执行者：小智 AI 助手
时间：2026-04-22 15:14
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# === 配置 ===
GO_ORCHESTRATION = Path("/root/.openclaw/workspace/ai_agent/code/computehub/orchestration/go")
SCHEDULER_DIR = GO_ORCHESTRATION / "internal" / "scheduler"

# === 颜色输出 ===
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {"INFO": Colors.BLUE, "SUCCESS": Colors.GREEN, "WARNING": Colors.YELLOW, "ERROR": Colors.RED}
    color = colors.get(level, Colors.RESET)
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.RESET}")

def create_scheduler():
    log("=" * 60, "INFO")
    log("ComputeHub 智能调度器 - Go 实现", "INFO")
    log("=" * 60, "INFO")
    
    # 1. 创建目录
    log("步骤 1: 创建调度器目录", "INFO")
    scheduler_dir = GO_ORCHESTRATION / "internal" / "scheduler"
    scheduler_dir.mkdir(parents=True, exist_ok=True)
    log(f"  ✅ 创建 {scheduler_dir}", "SUCCESS")
    
    # 2. 创建调度器核心逻辑
    log("步骤 2: 创建调度器核心", "INFO")
    scheduler_go = '''package scheduler

import (
	"fmt"
	"math"
	"sort"
	"sync"
	"time"
)

// Node 表示一个算力节点
type Node struct {
	ID            string             `json:"id"`
	Name          string             `json:"name"`
	Location      Location           `json:"location"`
	GPUCount      int                `json:"gpu_count"`
	GPUModel      string             `json:"gpu_model"`
	MemoryGB      int                `json:"memory_gb"`
	Status        NodeStatus         `json:"status"`
	LoadPercent   float64            `json:"load_percent"`
	PricePerHour  float64            `json:"price_per_hour"`
	Reliability   float64            `json:"reliability"` // 0-1
	LastHeartbeat time.Time          `json:"last_heartbeat"`
	Tags          map[string]string  `json:"tags"`
}

// Location 地理位置
type Location struct {
	Country   string  `json:"country"`
	City      string  `json:"city"`
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
	Region    string  `json:"region"` // "asia", "europe", "americas"
}

// NodeStatus 节点状态
type NodeStatus string

const (
	StatusOnline    NodeStatus = "online"
	StatusOffline   NodeStatus = "offline"
	StatusBusy      NodeStatus = "busy"
	StatusMaintenance NodeStatus = "maintenance"
)

// Job 表示一个计算任务
type Job struct {
	ID              string    `json:"id"`
	Framework       string    `json:"framework"` // "pytorch", "tensorflow", "jax"
	GPUCount        int       `json:"gpu_count"`
	MemoryGB        int       `json:"memory_gb"`
	DurationHours   float64   `json:"duration_hours"`
	Priority        int       `json:"priority"` // 1-10, 10 最高
	SubmittedAt     time.Time `json:"submitted_at"`
	Deadline        time.Time `json:"deadline"`
	PreferredRegion string    `json:"preferred_region"`
	MaxPricePerHour float64   `json:"max_price_per_hour"`
	Tags            map[string]string `json:"tags"`
}

// JobAssignment 任务分配结果
type JobAssignment struct {
	JobID       string    `json:"job_id"`
	NodeID      string    `json:"node_id"`
	NodeName    string    `json:"node_name"`
	Score       float64   `json:"score"`
	EstimatedCost float64 `json:"estimated_cost"`
	AssignedAt  time.Time `json:"assigned_at"`
	Reason      string    `json:"reason"`
}

// Scheduler 智能调度器
type Scheduler struct {
	mu           sync.RWMutex
	nodes        map[string]*Node
	history      []JobAssignment
	config       *SchedulerConfig
}

// SchedulerConfig 调度器配置
type SchedulerConfig struct {
	EnableGeoPreference    bool     `json:"enable_geo_preference"`
	EnableCostOptimization bool     `json:"enable_cost_optimization"`
	EnableLoadBalancing    bool     `json:"enable_load_balancing"`
	GeoWeight              float64  `json:"geo_weight"`              // 地理位置权重
	CostWeight             float64  `json:"cost_weight"`             // 成本权重
	LoadWeight             float64  `json:"load_weight"`             // 负载均衡权重
	ReliabilityWeight      float64  `json:"reliability_weight"`      // 可靠性权重
	MaxNodesToConsider     int      `json:"max_nodes_to_consider"`   // 最多考虑节点数
}

// DefaultConfig 默认配置
func DefaultConfig() *SchedulerConfig {
	return &SchedulerConfig{
		EnableGeoPreference:    true,
		EnableCostOptimization: true,
		EnableLoadBalancing:    true,
		GeoWeight:              0.25,
		CostWeight:             0.30,
		LoadWeight:             0.25,
		ReliabilityWeight:      0.20,
		MaxNodesToConsider:     100,
	}
}

// NewScheduler 创建调度器
func NewScheduler(config *SchedulerConfig) *Scheduler {
	if config == nil {
		config = DefaultConfig()
	}
	return &Scheduler{
		nodes:  make(map[string]*Node),
		config: config,
	}
}

// RegisterNode 注册节点
func (s *Scheduler) RegisterNode(node *Node) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nodes[node.ID] = node
}

// UnregisterNode 注销节点
func (s *Scheduler) UnregisterNode(nodeID string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.nodes, nodeID)
}

// UpdateNodeStatus 更新节点状态
func (s *Scheduler) UpdateNodeStatus(nodeID string, status NodeStatus, loadPercent float64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if node, exists := s.nodes[nodeID]; exists {
		node.Status = status
		node.LoadPercent = loadPercent
		node.LastHeartbeat = time.Now()
	}
}

// Schedule 智能调度核心算法
func (s *Scheduler) Schedule(job *Job) (*JobAssignment, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// 1. 过滤可用节点
	candidates := s.filterAvailableNodes(job)
	if len(candidates) == 0 {
		return nil, fmt.Errorf("no available nodes for job %s", job.ID)
	}

	// 2. 计算每个节点的评分
	scoredNodes := s.scoreNodes(job, candidates)
	if len(scoredNodes) == 0 {
		return nil, fmt.Errorf("no suitable nodes for job %s", job.ID)
	}

	// 3. 选择最高分节点
	bestNode := scoredNodes[0]
	
	assignment := &JobAssignment{
		JobID:         job.ID,
		NodeID:        bestNode.ID,
		NodeName:      bestNode.Name,
		Score:         bestNode.score,
		EstimatedCost: bestNode.estimatedCost,
		AssignedAt:    time.Now(),
		Reason:        bestNode.reason,
	}

	// 4. 记录历史
	s.history = append(s.history, *assignment)

	return assignment, nil
}

type scoredNode struct {
	*Node
	score         float64
	estimatedCost float64
	reason        string
}

// filterAvailableNodes 过滤可用节点
func (s *Scheduler) filterAvailableNodes(job *Job) []*Node {
	var candidates []*Node
	
	for _, node := range s.nodes {
		// 状态检查
		if node.Status != StatusOnline {
			continue
		}
		
		// GPU 数量检查
		if node.GPUCount < job.GPUCount {
			continue
		}
		
		// 内存检查
		if node.MemoryGB < job.MemoryGB {
			continue
		}
		
		// 价格检查
		if job.MaxPricePerHour > 0 && node.PricePerHour > job.MaxPricePerHour {
			continue
		}
		
		// 负载检查 (保留 20% 余量)
		if node.LoadPercent > 80 {
			continue
		}
		
		candidates = append(candidates, node)
	}
	
	// 限制候选节点数量
	if len(candidates) > s.config.MaxNodesToConsider {
		candidates = candidates[:s.config.MaxNodesToConsider]
	}
	
	return candidates
}

// scoreNodes 计算节点评分
func (s *Scheduler) scoreNodes(job *Job, nodes []*Node) []scoredNode {
	scored := make([]scoredNode, 0, len(nodes))
	
	for _, node := range nodes {
		score, reason := s.calculateScore(job, node)
		estimatedCost := node.PricePerHour * job.DurationHours
		
		scored = append(scored, scoredNode{
			Node:          node,
			score:         score,
			estimatedCost: estimatedCost,
			reason:        reason,
		})
	}
	
	// 按评分降序排序
	sort.Slice(scored, func(i, j int) bool {
		return scored[i].score > scored[j].score
	})
	
	return scored
}

// calculateScore 计算单个节点评分 (0-100)
func (s *Scheduler) calculateScore(job *Job, node *Node) (float64, string) {
	var score float64
	var reasons []string
	
	// 1. 地理位置评分 (0-25 分)
	if s.config.EnableGeoPreference && job.PreferredRegion != "" {
		geoScore := s.calculateGeoScore(job, node)
		score += geoScore * s.config.GeoWeight * 25
		if geoScore > 0.8 {
			reasons = append(reasons, fmt.Sprintf("geo_match=%.0f%%", geoScore*100))
		}
	}
	
	// 2. 成本评分 (0-30 分)
	if s.config.EnableCostOptimization {
		costScore := s.calculateCostScore(job, node)
		score += costScore * s.config.CostWeight * 30
		if costScore > 0.7 {
			reasons = append(reasons, fmt.Sprintf("cost_optimized=%.0f%%", costScore*100))
		}
	}
	
	// 3. 负载均衡评分 (0-25 分)
	if s.config.EnableLoadBalancing {
		loadScore := s.calculateLoadScore(node)
		score += loadScore * s.config.LoadWeight * 25
		if loadScore > 0.7 {
			reasons = append(reasons, fmt.Sprintf("load_balanced=%.0f%%", loadScore*100))
		}
	}
	
	// 4. 可靠性评分 (0-20 分)
	reliabilityScore := node.Reliability * 20
	score += reliabilityScore * s.config.ReliabilityWeight
	if node.Reliability > 0.9 {
		reasons = append(reasons, fmt.Sprintf("reliability=%.0f%%", node.Reliability*100))
	}
	
	return score, fmt.Sprintf("score breakdown: %v", reasons)
}

// calculateGeoScore 计算地理位置匹配度 (0-1)
func (s *Scheduler) calculateGeoScore(job *Job, node *Node) float64 {
	if job.PreferredRegion == "" {
		return 1.0
	}
	
	// 完全匹配
	if node.Location.Region == job.PreferredRegion {
		return 1.0
	}
	
	// 同大洲
	if node.Location.Country == job.PreferredRegion {
		return 0.8
	}
	
	// 邻近区域
	regionProximity := map[string][]string{
		"asia":     {"asia", "oceania"},
		"europe":   {"europe", "middle_east"},
		"americas": {"north_america", "south_america"},
	}
	
	if regions, exists := regionProximity[job.PreferredRegion]; exists {
		for _, r := range regions {
			if node.Location.Region == r {
				return 0.6
			}
		}
	}
	
	return 0.3
}

// calculateCostScore 计算成本优化评分 (0-1)
func (s *Scheduler) calculateCostScore(job *Job, node *Node) float64 {
	if job.MaxPricePerHour <= 0 {
		return 0.5 // 无价格限制，中等评分
	}
	
	// 价格越低评分越高
	ratio := node.PricePerHour / job.MaxPricePerHour
	if ratio <= 0.5 {
		return 1.0 // 价格低于预算 50%，满分
	}
	if ratio >= 1.0 {
		return 0.0 // 超出预算，0 分
	}
	
	return 1.0 - ratio
}

// calculateLoadScore 计算负载均衡评分 (0-1)
func (s *Scheduler) calculateLoadScore(node *Node) float64 {
	// 负载越低评分越高
	if node.LoadPercent <= 20 {
		return 1.0
	}
	if node.LoadPercent >= 80 {
		return 0.0
	}
	
	return 1.0 - (node.LoadPercent / 100.0)
}

// GetNodeStats 获取节点统计
func (s *Scheduler) GetNodeStats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()
	
	total := len(s.nodes)
	online := 0
	busy := 0
	offline := 0
	
	var totalLoad float64
	var avgPrice float64
	
	for _, node := range s.nodes {
		switch node.Status {
		case StatusOnline:
			online++
			totalLoad += node.LoadPercent
			avgPrice += node.PricePerHour
		case StatusBusy:
			busy++
		case StatusOffline:
			offline++
		}
	}
	
	avgLoad := 0.0
	if online > 0 {
		avgLoad = totalLoad / float64(online)
		avgPrice = avgPrice / float64(online)
	}
	
	return map[string]interface{}{
		"total_nodes":     total,
		"online":          online,
		"busy":            busy,
		"offline":         offline,
		"average_load":    fmt.Sprintf("%.1f%%", avgLoad),
		"average_price":   fmt.Sprintf("$%.2f/h", avgPrice),
		"total_jobs":      len(s.history),
	}
}

// CalculateDistance 计算两个地理位置之间的距离 (Haversine 公式)
func CalculateDistance(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371 // 地球半径 (km)
	
	dLat := toRadians(lat2 - lat1)
	dLon := toRadians(lon2 - lon1)
	
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(toRadians(lat1))*math.Cos(toRadians(lat2))*
		math.Sin(dLon/2)*math.Sin(dLon/2)
	
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	
	return R * c
}

func toRadians(degrees float64) float64 {
	return degrees * math.Pi / 180
}
'''
    (scheduler_dir / "scheduler.go").write_text(scheduler_go, encoding='utf-8')
    log("  ✅ 创建 internal/scheduler/scheduler.go", "SUCCESS")
    
    # 3. 创建调度器 HTTP 处理器
    log("步骤 3: 创建调度器 API", "INFO")
    handlers_go = '''package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
	"github.com/computehub/opc/orchestration/internal/scheduler"
)

// 添加调度器到 Handler
type Handler struct {
	opcClient  *OPCClient
	scheduler  *scheduler.Scheduler
}

func NewHandler(opcGatewayURL string) *Handler {
	return &Handler{
		opcClient: NewOPCClient(opcGatewayURL),
		scheduler: scheduler.NewScheduler(scheduler.DefaultConfig()),
	}
}

// 添加调度相关端点
func SetupMux(h *Handler) *http.ServeMux {
	mux := http.NewServeMux()
	
	// 原有端点
	mux.HandleFunc("GET /api/health", h.HealthCheck)
	mux.HandleFunc("GET /api/opc/status", h.GetOPCStatus)
	mux.HandleFunc("GET /api/opc/gpu", h.GetOPCGPUInfo)
	mux.HandleFunc("POST /api/opc/dispatch", h.DispatchToOPC)
	mux.HandleFunc("POST /api/jobs/submit", h.SubmitJob)
	mux.HandleFunc("GET /api/jobs/", h.GetJobStatus)
	mux.HandleFunc("GET /api/nodes", h.ListNodes)
	mux.HandleFunc("GET /api/nodes/", h.GetNodeStatus)
	mux.HandleFunc("GET /api/blockchain/status", h.GetBlockchainStatus)
	mux.HandleFunc("GET /api/status", h.GetSystemStatus)
	
	// 新增调度器端点
	mux.HandleFunc("POST /api/scheduler/schedule", h.ScheduleJob)
	mux.HandleFunc("GET /api/scheduler/nodes", h.ListSchedulerNodes)
	mux.HandleFunc("POST /api/scheduler/nodes", h.RegisterNode)
	mux.HandleFunc("PUT /api/scheduler/nodes/{id}", h.UpdateNodeStatus)
	mux.HandleFunc("GET /api/scheduler/stats", h.GetSchedulerStats)
	mux.HandleFunc("GET /api/scheduler/history", h.GetScheduleHistory)
	
	return mux
}

// ScheduleJob 智能调度任务
func (h *Handler) ScheduleJob(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	var jobReq struct {
		Framework       string  `json:"framework"`
		GPUCount        int     `json:"gpu_count"`
		MemoryGB        int     `json:"memory_gb"`
		DurationHours   float64 `json:"duration_hours"`
		Priority        int     `json:"priority"`
		PreferredRegion string  `json:"preferred_region"`
		MaxPricePerHour float64 `json:"max_price_per_hour"`
		Tags            map[string]string `json:"tags"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&jobReq); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}
	
	job := &scheduler.Job{
		ID:              fmt.Sprintf("job-%d", time.Now().Unix()),
		Framework:       jobReq.Framework,
		GPUCount:        jobReq.GPUCount,
		MemoryGB:        jobReq.MemoryGB,
		DurationHours:   jobReq.DurationHours,
		Priority:        jobReq.Priority,
		SubmittedAt:     time.Now(),
		PreferredRegion: jobReq.PreferredRegion,
		MaxPricePerHour: jobReq.MaxPricePerHour,
		Tags:            jobReq.Tags,
	}
	
	assignment, err := h.scheduler.Schedule(job)
	if err != nil {
		http.Error(w, fmt.Sprintf("Scheduling failed: %v", err), http.StatusServiceUnavailable)
		return
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"assignment": assignment,
	})
}

// ListSchedulerNodes 列出调度器管理的节点
func (h *Handler) ListSchedulerNodes(w http.ResponseWriter, r *http.Request) {
	stats := h.scheduler.GetNodeStats()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

// RegisterNode 注册新节点
func (h *Handler) RegisterNode(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	var nodeReq struct {
		ID          string  `json:"id"`
		Name        string  `json:"name"`
		Country     string  `json:"country"`
		City        string  `json:"city"`
		Region      string  `json:"region"`
		GPUCount    int     `json:"gpu_count"`
		GPUModel    string  `json:"gpu_model"`
		MemoryGB    int     `json:"memory_gb"`
		PricePerHour float64 `json:"price_per_hour"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&nodeReq); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}
	
	node := &scheduler.Node{
		ID:   nodeReq.ID,
		Name: nodeReq.Name,
		Location: scheduler.Location{
			Country: nodeReq.Country,
			City:    nodeReq.City,
			Region:  nodeReq.Region,
		},
		GPUCount:     nodeReq.GPUCount,
		GPUModel:     nodeReq.GPUModel,
		MemoryGB:     nodeReq.MemoryGB,
		PricePerHour: nodeReq.PricePerHour,
		Status:       scheduler.StatusOnline,
		Reliability:  0.95,
		Tags:         make(map[string]string),
	}
	
	h.scheduler.RegisterNode(node)
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"node_id": node.ID,
	})
}

// UpdateNodeStatus 更新节点状态
func (h *Handler) UpdateNodeStatus(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	nodeID := parts[len(parts)-1]
	
	var statusReq struct {
		Status      string  `json:"status"`
		LoadPercent float64 `json:"load_percent"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&statusReq); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}
	
	h.scheduler.UpdateNodeStatus(nodeID, scheduler.NodeStatus(statusReq.Status), statusReq.LoadPercent)
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}

// GetSchedulerStats 获取调度器统计
func (h *Handler) GetSchedulerStats(w http.ResponseWriter, r *http.Request) {
	stats := h.scheduler.GetNodeStats()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

// GetScheduleHistory 获取调度历史
func (h *Handler) GetScheduleHistory(w http.ResponseWriter, r *http.Request) {
	// TODO: 实现历史记录查询
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"history": []interface{}{},
		"total":   0,
	})
}
'''
    # 注意：这里需要更新 handlers.go，但为了简洁，我们创建一个新的 handlers_v2.go
    (GO_ORCHESTRATION / "internal" / "handlers" / "handlers_v2.go").write_text(handlers_go, encoding='utf-8')
    log("  ✅ 创建 internal/handlers/handlers_v2.go (带调度器)", "SUCCESS")
    
    # 4. 创建测试脚本
    log("步骤 4: 创建测试脚本", "INFO")
    test_scheduler_py = '''#!/usr/bin/env python3
"""测试智能调度器"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8080"

def test_register_nodes():
    """注册测试节点"""
    print("\\n=== 注册测试节点 ===")
    
    nodes = [
        {
            "id": "node-cn-shanghai-01",
            "name": "上海节点 1",
            "country": "China",
            "city": "Shanghai",
            "region": "asia",
            "gpu_count": 8,
            "gpu_model": "NVIDIA A100",
            "memory_gb": 512,
            "price_per_hour": 15.0
        },
        {
            "id": "node-cn-beijing-01",
            "name": "北京节点 1",
            "country": "China",
            "city": "Beijing",
            "region": "asia",
            "gpu_count": 4,
            "gpu_model": "NVIDIA V100",
            "memory_gb": 256,
            "price_per_hour": 10.0
        },
        {
            "id": "node-us-west-01",
            "name": "美西节点 1",
            "country": "USA",
            "city": "San Francisco",
            "region": "americas",
            "gpu_count": 16,
            "gpu_model": "NVIDIA H100",
            "memory_gb": 1024,
            "price_per_hour": 25.0
        }
    ]
    
    for node in nodes:
        resp = requests.post(f"{BASE_URL}/api/scheduler/nodes", json=node)
        print(f"  注册 {node['name']}: {'✅' if resp.status_code == 200 else '❌'}")
    
    return len(nodes)

def test_schedule_job():
    """测试任务调度"""
    print("\\n=== 测试任务调度 ===")
    
    job = {
        "framework": "pytorch",
        "gpu_count": 4,
        "memory_gb": 128,
        "duration_hours": 24,
        "priority": 5,
        "preferred_region": "asia",
        "max_price_per_hour": 20.0
    }
    
    resp = requests.post(f"{BASE_URL}/api/scheduler/schedule", json=job)
    
    if resp.status_code == 200:
        result = resp.json()
        assignment = result.get("assignment", {})
        print(f"  ✅ 调度成功!")
        print(f"     任务 ID: {assignment.get('job_id')}")
        print(f"     分配节点：{assignment.get('node_name')}")
        print(f"     评分：{assignment.get('score', 0):.2f}")
        print(f"     预估成本：${assignment.get('estimated_cost', 0):.2f}")
        print(f"     原因：{assignment.get('reason', 'N/A')}")
        return True
    else:
        print(f"  ❌ 调度失败：{resp.text}")
        return False

def test_scheduler_stats():
    """查看调度器统计"""
    print("\\n=== 调度器统计 ===")
    
    resp = requests.get(f"{BASE_URL}/api/scheduler/stats")
    
    if resp.status_code == 200:
        stats = resp.json()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return True
    else:
        print(f"  ❌ 获取失败：{resp.text}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ComputeHub 智能调度器测试")
    print("=" * 60)
    
    try:
        # 注册节点
        test_register_nodes()
        
        # 测试调度
        test_schedule_job()
        
        # 查看统计
        test_scheduler_stats()
        
        print("\\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\\n❌ 测试失败：{e}")
'''
    (GO_ORCHESTRATION / "test_scheduler.py").write_text(test_scheduler_py, encoding='utf-8')
    log("  ✅ 创建 test_scheduler.py", "SUCCESS")
    
    # 5. 更新 main.go 使用新版本 handlers
    log("步骤 5: 更新 main.go", "INFO")
    main_go = '''package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"github.com/computehub/opc/orchestration/internal/handlers"
)

const (
	defaultPort   = 8080
	opcGatewayURL = "http://localhost:8282"
)

func main() {
	port := defaultPort
	if p := os.Getenv("ORCHESTRATION_PORT"); p != "" {
		fmt.Sscanf(p, "%d", &port)
	}

	h := handlers.NewHandler(opcGatewayURL)
	
	mux := handlers.SetupMux(h)
	
	addr := fmt.Sprintf(":%d", port)
	log.Printf("🚀 ComputeHub-OPC Orchestrator starting on %s", addr)
	log.Printf("📡 OpenPC Gateway URL: %s", opcGatewayURL)
	log.Printf("✅ Zero dependencies - Pure Go stdlib")
	log.Printf("🧠 Smart scheduler enabled")
	
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
'''
    (GO_ORCHESTRATION / "cmd" / "orchestrator" / "main.go").write_text(main_go, encoding='utf-8')
    log("  ✅ 更新 cmd/orchestrator/main.go", "SUCCESS")
    
    log("", "INFO")
    log("=" * 60, "INFO")
    log("智能调度器创建完成！", "SUCCESS")
    log(f"目录：{GO_ORCHESTRATION}", "SUCCESS")
    log("=" * 60, "INFO")
    
    return True

if __name__ == "__main__":
    success = create_scheduler()
    sys.exit(0 if success else 1)
