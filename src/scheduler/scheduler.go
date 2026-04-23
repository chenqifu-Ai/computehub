// Package scheduler implements intelligent task scheduling for distributed nodes.
// Selects optimal nodes based on GPU availability, load balancing, latency,
// and geographic proximity.
package scheduler

import (
	"fmt"
	"math"
	"sync"
	"time"

	"github.com/chenqifu-Ai/computehub/src/node"
)

// ─── 调度策略 ───

// Strategy defines how tasks are assigned to nodes.
type Strategy string

const (
	StrategyLeastLoad    Strategy = "least_load"    // Minimum active tasks
	StrategyGPUFirst     Strategy = "gpu_first"      // Prefer GPU nodes
	StrategyLatency      Strategy = "latency"        // Lowest latency first
	StrategyGeoProximity Strategy = "geo_proximity"   // Closest region first
	StrategyRoundRobin   Strategy = "round_robin"    // Round robin
	StrategyBalanced     Strategy = "balanced"       // GPU + load weighted
)

// ─── 任务要求 ───

// TaskRequirement describes what a task needs.
type TaskRequirement struct {
	Framework  string
	ResourceType string // gpu, cpu
	GPUCount   int
	CPUCount   int
	MemoryGB   int
	MaxDurationSecs int
	Region     string // preferred region, "" = any
	Priority   int    // higher = more urgent
}

// ─── 调度器 ───

// Scheduler assigns tasks to the best available nodes.
type Scheduler struct {
	mu        sync.RWMutex
	primary   Strategy
	nodeMgr   *node.NodeManager
	taskQueue chan scheduledTask
	strategy  map[Strategy]*strategyState

	// Stats
	totalScheduled int64
	totalFailed    int64
	avgLatency     time.Duration
}

type strategyState struct {
	rrIndex  int
	lastUsed map[string]time.Time // nodeID -> last task time
}

// NewScheduler creates a scheduler with the given node manager.
func NewScheduler(nodeMgr *node.NodeManager, primary Strategy) *Scheduler {
	s := &Scheduler{
		primary:     primary,
		nodeMgr:     nodeMgr,
		taskQueue:   make(chan scheduledTask, 1000),
		strategy: map[Strategy]*strategyState{
			StrategyLeastLoad:    {rrIndex: 0, lastUsed: make(map[string]time.Time)},
			StrategyRoundRobin:  {rrIndex: 0, lastUsed: make(map[string]time.Time)},
			StrategyGPUFirst:    {rrIndex: 0, lastUsed: make(map[string]time.Time)},
			StrategyLatency:     {rrIndex: 0, lastUsed: make(map[string]time.Time)},
			StrategyGeoProximity:{rrIndex: 0, lastUsed: make(map[string]time.Time)},
			StrategyBalanced:    {rrIndex: 0, lastUsed: make(map[string]time.Time)},
		},
	}

	// Start queue processor
	go s.processQueue()

	return s
}

// ─── 核心调度 ───

// Schedule assigns a task to the best available node.
func (s *Scheduler) Schedule(taskID string, req TaskRequirement) (*node.Node, error) {
	candidates := s.filterCandidates(req)
	if len(candidates) == 0 {
		return nil, fmt.Errorf("no available node for task %s (requirement: %s GPU, %d CPU, %dGB RAM)",
			taskID, req.ResourceType, req.CPUCount, req.MemoryGB)
	}

	// Score and pick best node
	best := s.scoreCandidates(candidates, req)
	best.IncrementTasksRunning()
	s.totalScheduled++

	return best, nil
}

// ScheduleBatch assigns multiple tasks to nodes (batch scheduling).
func (s *Scheduler) ScheduleBatch(tasks []scheduledTask) []batchResult {
	results := make([]batchResult, 0, len(tasks))

	for _, task := range tasks {
		node, err := s.Schedule(task.TaskID, task.Requirement)
		results = append(results, batchResult{
			TaskID: task.TaskID,
			Node:   node,
			Error:  err,
		})
	}

	return results
}

// ─── 节点筛选 ───

func (s *Scheduler) filterCandidates(req TaskRequirement) []*node.Node {
	nodes := s.nodeMgr.GetOnlineNodes()
	candidates := make([]*node.Node, 0)

	for _, n := range nodes {
		// Circuit breaker check
		// (simplified: skip nodes that are offline)
		if n.Status != node.NodeStatusOnline && n.Status != node.NodeStatusBusy {
			continue
		}

		// Resource check
		if !s.meetsRequirements(n, req) {
			continue
		}

		// Region preference
		if req.Region != "" && n.Region != req.Region {
			continue // Prefer region-matched nodes
		}

		candidates = append(candidates, n)
	}

	return candidates
}

func (s *Scheduler) meetsRequirements(n *node.Node, req TaskRequirement) bool {
	// GPU requirement
	if req.ResourceType == "gpu" && req.GPUCount > 0 {
		if !n.Capability.GPUEnabled {
			return false
		}
		if len(n.Capability.GPUs) < req.GPUCount {
			return false
		}
	}

	// CPU requirement
	if req.CPUCount > 0 {
		if n.Capability.CPUCores < req.CPUCount {
			return false
		}
	}

	// Memory requirement
	if req.MemoryGB > 0 {
		memMB := uint64(req.MemoryGB) * 1024
		if n.Capability.MemTotalMB < memMB {
			return false
		}
	}

	return true
}

// ─── 节点评分 ───

func (s *Scheduler) scoreCandidates(candidates []*node.Node, req TaskRequirement) *node.Node {
	if len(candidates) == 1 {
		return candidates[0]
	}

	bestNode := candidates[0]
	bestScore := -math.MaxFloat64

	switch s.primary {
	case StrategyGPUFirst:
		for _, n := range candidates {
			score := s.scoreGPUFirst(n)
			if score > bestScore {
				bestScore = score
				bestNode = n
			}
		}
	case StrategyLatency:
		for _, n := range candidates {
			score := s.scoreLatency(n)
			if score > bestScore {
				bestScore = score
				bestNode = n
			}
		}
	case StrategyGeoProximity:
		for _, n := range candidates {
			score := s.scoreGeoProximity(n, req)
			if score > bestScore {
				bestScore = score
				bestNode = n
			}
		}
	case StrategyRoundRobin:
		bestNode = s.scoreRoundRobin(candidates)
	case StrategyLeastLoad:
		for _, n := range candidates {
			score := s.scoreLeastLoad(n)
			if score > bestScore {
				bestScore = score
				bestNode = n
			}
		}
	default: // StrategyBalanced
		for _, n := range candidates {
			score := s.scoreBalanced(n, req)
			if score > bestScore {
				bestScore = score
				bestNode = n
			}
		}
	}

	return bestNode
}

// ─── 评分策略 ───

// GPUFirst: prefer nodes with more GPU memory
func (s *Scheduler) scoreGPUFirst(n *node.Node) float64 {
	score := float64(len(n.Capability.GPUs)) * 100
	for _, gpu := range n.Capability.GPUs {
		score += float64(gpu.MemMB) / 1024 // GB
	}
	// Penalize loaded nodes
	score -= float64(n.TasksRunning) * 10
	return score
}

// Latency: prefer nodes with low load (proxy for latency)
func (s *Scheduler) scoreLatency(n *node.Node) float64 {
	// Lower load = higher score
	loadScore := (1.0 - n.Load) * 100
	return loadScore
}

// GeoProximity: prefer nodes in the same or nearby region
func (s *Scheduler) scoreGeoProximity(n *node.Node, req TaskRequirement) float64 {
	if req.Region == "" || n.Region == "local" {
		return 100 // Local nodes get top priority
	}
	if n.Region == req.Region {
		return 90
	}
	// Cross-region: base score minus penalty
	return 50
}

// RoundRobin: cyclic selection
func (s *Scheduler) scoreRoundRobin(candidates []*node.Node) *node.Node {
	st := s.strategy[StrategyRoundRobin]
	idx := st.rrIndex % len(candidates)
	st.rrIndex++
	return candidates[idx]
}

// LeastLoad: prefer nodes with fewest running tasks
func (s *Scheduler) scoreLeastLoad(n *node.Node) float64 {
	// Lower tasks_running = higher score
	baseScore := 100.0
	penalty := float64(n.TasksRunning) * 15.0
	return baseScore - penalty
}

// Balanced: weighted combination of GPU, load, and region
func (s *Scheduler) scoreBalanced(n *node.Node, req TaskRequirement) float64 {
	score := 0.0

	// GPU score (40%)
	if n.Capability.GPUEnabled {
		score += 40.0
		for _, gpu := range n.Capability.GPUs {
			score += float64(gpu.MemMB) / 500.0 // Normalize
		}
	} else if req.ResourceType != "gpu" {
		score += 20.0 // CPU-only nodes get partial score
	}

	// Load score (30%) - lower load is better
	score += float64(30.0 * (1.0 - n.Load))

	// Region score (30%)
	if req.Region != "" && n.Region == req.Region {
		score += 30.0
	} else if req.Region == "" || n.Region == "local" {
		score += 15.0
	}

	// Capacity bonus
	totalCapacity := float64(n.Capability.CPUCores) * float64(n.Capability.MemTotalMB)
	score += math.Min(totalCapacity/100000, 10.0)

	return score
}

// ─── 任务队列处理 ───

type scheduledTask struct {
	TaskID      string
	Requirement TaskRequirement
}

type batchResult struct {
	TaskID string
	Node   *node.Node
	Error  error
}

func (s *Scheduler) processQueue() {
	for task := range s.taskQueue {
		node, err := s.Schedule(task.TaskID, task.Requirement)
		_ = node
		_ = err
	}
}

// SubmitToQueue adds a task to the scheduled queue.
func (s *Scheduler) SubmitToQueue(taskID string, req TaskRequirement) {
	select {
	case s.taskQueue <- scheduledTask{TaskID: taskID, Requirement: req}:
	default:
		// Queue full, schedule synchronously
		s.Schedule(taskID, req)
	}
}

// ─── 统计信息 ───

// Stats returns scheduler statistics.
func (s *Scheduler) Stats() map[string]any {
	s.mu.Lock()
	defer s.mu.Unlock()

	successRate := float64(0)
	total := s.totalScheduled + s.totalFailed
	if total > 0 {
		successRate = float64(s.totalScheduled) / float64(total) * 100
	}

	return map[string]any{
		"primary_strategy": string(s.primary),
		"total_scheduled": s.totalScheduled,
		"total_failed":    s.totalFailed,
		"success_rate":    fmt.Sprintf("%.1f%%", successRate),
		"avg_latency":     s.avgLatency.String(),
		"queue_depth":     len(s.taskQueue),
	}
}

// ─── 可用调度策略列表 ───

// AvailableStrategies lists all supported scheduling strategies.
func AvailableStrategies() []Strategy {
	return []Strategy{
		StrategyLeastLoad,
		StrategyGPUFirst,
		StrategyLatency,
		StrategyGeoProximity,
		StrategyRoundRobin,
		StrategyBalanced,
	}
}
