package kernel

import (
	"fmt"
	"sync"
	"time"

	"github.com/computehub/opc/src/scheduler"
)

// ====== 算力调度 Action 定义 ======

// ComputeAction 新增算力相关的 Action 类型
const (
	ActionNodeRegister  = "NODE_REGISTER"
	ActionNodeUnregister = "NODE_UNREGISTER"
	ActionNodeHeartbeat = "NODE_HEARTBEAT"
	ActionNodeOffline   = "NODE_OFFLINE"
	ActionTaskSubmit    = "TASK_SUBMIT"
	ActionTaskResult    = "TASK_RESULT"
	ActionTaskCancel    = "TASK_CANCEL"
	ActionGPUMonitor    = "GPU_MONITOR"
	ActionRegionQuery   = "REGION_QUERY"
	ActionMetricsReport = "METRICS_REPORT"
)

// NodeRegister 节点注册信息
type NodeRegister struct {
	NodeID        string    `json:"node_id"`
	NodeType      string    `json:"node_type"` // "gpu" | "cpu" | "mixed"
	GPUType       string    `json:"gpu_type"`  // "A100" | "H100" | "V100" | "RTX4090" etc.
	Region        string    `json:"region"`    // "us-east" | "eu-west" | "ap-southeast"
	CPUCores      int       `json:"cpu_cores"`
	MemoryGB      float64   `json:"memory_gb"`
	GPUMemoryGB   float64   `json:"gpu_memory_gb"`
	MaxConcurrency int      `json:"max_concurrency"`
	IPAddress     string    `json:"ip_address"`
	RegisteredAt  time.Time `json:"registered_at"`
	Status        string    `json:"status"` // "online" | "draining" | "offline"
}

// GPUMetrics GPU 物理指标
type GPUMetrics struct {
	NodeID         string    `json:"node_id"`
	Utilization    float64   `json:"utilization"` // 0-100
	Temperature    float64   `json:"temperature"` // Celsius
	MemoryUsedGB   float64   `json:"memory_used_gb"`
	MemoryTotalGB  float64   `json:"memory_total_gb"`
	PowerWatts     float64   `json:"power_watts"`
	PCIeBandwidth  float64   `json:"pcie_bandwidth"` // GB/s
	 measuredAt    time.Time `json:"-"`
}

// TaskSubmit 任务提交信息
type TaskSubmit struct {
	TaskID       string    `json:"task_id"`
	SourceType   string    `json:"source_type"` // "direct" | "scheduled" | "auto"
	Priority     int       `json:"priority"`    // 1-10, 10 highest
	RegionAffinity string  `json:"region_affinity"` // preferred region
	Timeout      int       `json:"timeout"`     // seconds
	Command      string    `json:"command"`     // command to execute
	EnvVars      map[string]string `json:"env_vars,omitempty"`
	MaxRetries   int       `json:"max_retries"`
	SubmittedAt  time.Time `json:"submitted_at"`
}

// TaskResult 任务执行结果
type TaskResult struct {
	TaskID     string `json:"task_id"`
	Success    bool   `json:"success"`
	ExitCode   int    `json:"exit_code"`
	Stdout     string `json:"stdout"`
	Stderr     string `json:"stderr"`
	Duration   string `json:"duration"`
	ExecutedOn string `json:"executed_on"` // node_id
	Verified   bool   `json:"verified"`
}

// NodeMetrics 节点综合指标 (用于调度和熔断)
type NodeMetrics struct {
	NodeID         string     `json:"node_id"`
	CPUUtilization float64    `json:"cpu_utilization"`
	MemoryUsedGB   float64    `json:"memory_used_gb"`
	GPU            []GPUMetrics `json:"gpu"`
	NetworkLatency float64    `json:"network_latency"` // ms to gateway
	ActiveTasks    int        `json:"active_tasks"`
	MaxTasks       int        `json:"max_tasks"`
	SuccessRate    float64    `json:"success_rate"` // last 100 tasks
	Region         string     `json:"region"`
	LastHeartbeat  time.Time  `json:"last_heartbeat"`
}

// ====== 算力调度内核扩展 ======

// NodeManager 管理算力节点
type NodeManager struct {
	mu          sync.RWMutex
	nodes       map[string]*NodeManagerState
	maxNodes    int
	prioSched   *scheduler.PriorityScheduler
	preemptMgr  *scheduler.PreemptManager
	prioQueue   *scheduler.PriorityQueue
}

type NodeManagerState struct {
	Register  *NodeRegister
	Metrics   *NodeMetrics
	Heartbeat time.Time
	Tasks     map[string]*TaskState
}

type TaskState struct {
	Task     *TaskSubmit
	Status   string // "pending" | "running" | "completed" | "failed" | "cancelled"
	Assigned string // node_id
	Result   *TaskResult
	Retries  int
	Created  time.Time
}

// NewNodeManager creates a new node manager
func NewNodeManager(maxNodes int) *NodeManager {
	prioQueue := scheduler.NewPriorityQueue()
	return &NodeManager{
		nodes:       make(map[string]*NodeManagerState),
		maxNodes:    maxNodes,
		prioQueue:   prioQueue,
		prioSched:   scheduler.NewPriorityScheduler(scheduler.DefaultConfig()),
		preemptMgr:  scheduler.NewPreemptManager(prioQueue),
	}
}

// RegisterNode registers a new compute node
func (nm *NodeManager) RegisterNode(reg *NodeRegister) error {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	if _, exists := nm.nodes[reg.NodeID]; exists {
		return fmt.Errorf("node %s already registered", reg.NodeID)
	}

	if len(nm.nodes) >= nm.maxNodes {
		return fmt.Errorf("max nodes reached (%d)", nm.maxNodes)
	}

	nm.nodes[reg.NodeID] = &NodeManagerState{
		Register:  reg,
		Metrics: &NodeMetrics{
			NodeID:        reg.NodeID,
			Region:        reg.Region,
			MaxTasks:      reg.MaxConcurrency,
			ActiveTasks:   0,
			SuccessRate:   1.0,
			LastHeartbeat: time.Now(),
		},
		Tasks: make(map[string]*TaskState),
	}

	return nil
}

// UnregisterNode removes a node from the manager
func (nm *NodeManager) UnregisterNode(nodeID string) error {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	_, exists := nm.nodes[nodeID]
	if !exists {
		return fmt.Errorf("node %s not found", nodeID)
	}

	delete(nm.nodes, nodeID)
	return nil
}

// Heartbeat receives node heartbeat
func (nm *NodeManager) Heartbeat(nodeID string, metrics *GPUMetrics) error {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	state, exists := nm.nodes[nodeID]
	if !exists {
		return fmt.Errorf("node %s not registered", nodeID)
	}

	state.Heartbeat = time.Now()
	if metrics != nil {
		// Append or update GPU metrics
		m := state.Metrics
		m.GPU = append(m.GPU, *metrics)
		if len(m.GPU) > 10 {
			m.GPU = m.GPU[len(m.GPU)-10:]
		}
		m.MemoryUsedGB = metrics.MemoryUsedGB
	}

	return nil
}

// SubmitTask submits a task with priority-aware scheduling
func (nm *NodeManager) SubmitTask(task *TaskSubmit) error {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	// 0. 没有任何节点注册
	if len(nm.nodes) == 0 {
		return fmt.Errorf("no nodes registered")
	}

	// 1. Convert priority from 1-10 scale to scheduler priority
	schedPriority := scheduler.TaskPriority(task.Priority)
	if schedPriority < 1 {
		schedPriority = scheduler.PriorityMedium
	}

	// 2. Check if any node has capacity
	hasCapacity := false
	var bestNodeID string
	var bestLoad int = 999999

	for nid, state := range nm.nodes {
		if state.Register.Status != "online" {
			continue
		}
		load := state.Metrics.ActiveTasks
		if load < state.Metrics.MaxTasks {
			hasCapacity = true
			if load < bestLoad {
				bestLoad = load
				bestNodeID = nid
			}
		}
	}

	// 3. No capacity at all → push to queue or try preempt
	if !hasCapacity {
		// 尝试抢占低优先级任务
		result, _ := nm.preemptMgr.TryPreempt(task.TaskID, schedPriority, task)

		if result != nil && result.NodeID != "" {
			// 找到可被抢占的节点
			for nid, state := range nm.nodes {
				if nid == result.NodeID {
					if tid, ok := nm.findLowestPriorityTask(state); ok {
						if ts, exists := state.Tasks[tid]; exists {
							logWithTimestamp("[NodeMgr] Preempting task %s (prio=%d) for %s (prio=%d)",
								tid, ts.Task.Priority, task.TaskID, task.Priority)
							ts.Status = "preempted"
							state.Metrics.ActiveTasks--
							bestNodeID = nid
							hasCapacity = true
							break
						}
					}
				}
			}
		}

		if !hasCapacity {
			// 所有人都在忙，入队列等待
			logWithTimestamp("[NodeMgr] All nodes busy, queuing task %s (prio=%d)", task.TaskID, schedPriority)
			nm.prioQueue.PushTask(task.TaskID, schedPriority, task)
			return nil // 不返回错误，任务在队列中等
		}
	}

	// 4. Have capacity (or freed by preemption), assign directly
	if hasCapacity && bestNodeID != "" {
		state := nm.nodes[bestNodeID]
		state.Tasks[task.TaskID] = &TaskState{
			Task:     task,
			Status:   "running",
			Assigned: bestNodeID,
			Created:  time.Now(),
		}
		state.Metrics.ActiveTasks++
		logWithTimestamp("[NodeMgr] Assigned task %s (prio=%d) → node %s", task.TaskID, task.Priority, bestNodeID)
		return nil
	}

	// 5. Fall through → push to queue
	nm.prioQueue.PushTask(task.TaskID, schedPriority, task)
	return nil
}

// findLowestPriorityTask 找到节点上最低优先级的任务ID
func (nm *NodeManager) findLowestPriorityTask(state *NodeManagerState) (string, bool) {
	var lowestTaskID string
	lowestPriority := 999
	for tid, ts := range state.Tasks {
		if ts.Status == "running" && ts.Task.Priority < lowestPriority {
			lowestPriority = ts.Task.Priority
			lowestTaskID = tid
		}
	}
	if lowestTaskID != "" {
		return lowestTaskID, true
	}
	return "", false
}

// CompleteTask marks a task as completed and schedules next from queue
func (nm *NodeManager) CompleteTask(taskID, nodeID string, result *TaskResult) error {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	state, exists := nm.nodes[nodeID]
	if !exists {
		return fmt.Errorf("node %s not found", nodeID)
	}

	ts, exists := state.Tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found on node %s", taskID, nodeID)
	}

	ts.Status = "completed"
	ts.Result = result
	state.Metrics.ActiveTasks--

	// 任务完成后，检查优先级队列是否有等待的任务
	nm.dispatchFromQueue()

	return nil
}

// dispatchFromQueue 从优先级队列调度等待中的任务
func (nm *NodeManager) dispatchFromQueue() {
	for {
		nextTask, ok := nm.prioQueue.PeekTask()
		if !ok {
			return // 队列为空
		}

		// 找个可用节点
		var bestNodeID string
		var bestLoad int = 999999
		for nid, nodeState := range nm.nodes {
			if nodeState.Register.Status != "online" {
				continue
			}
			load := nodeState.Metrics.ActiveTasks
			if load < nodeState.Metrics.MaxTasks && load < bestLoad {
				bestLoad = load
				bestNodeID = nid
			}
		}

		if bestNodeID == "" {
			return // 没有可用节点，等待下次
		}

		// 出队并分配
		nm.prioQueue.PopTask()
		taskPayload, ok := nextTask.Payload.(*TaskSubmit)
		if !ok {
			continue
		}

		nodeState := nm.nodes[bestNodeID]
		nodeState.Tasks[nextTask.TaskID] = &TaskState{
			Task:     taskPayload,
			Status:   "running",
			Assigned: bestNodeID,
			Created:  time.Now(),
		}
		nodeState.Metrics.ActiveTasks++

		logWithTimestamp("[NodeMgr] Dispatched queued task %s (prio=%d) → node %s",
			nextTask.TaskID, nextTask.Priority, bestNodeID)
	}
}

// GetNodeMetrics returns metrics for a node
func (nm *NodeManager) GetNodeMetrics(nodeID string) (*NodeMetrics, error) {
	nm.mu.RLock()
	defer nm.mu.RUnlock()

	state, exists := nm.nodes[nodeID]
	if !exists {
		return nil, fmt.Errorf("node %s not found", nodeID)
	}
	return state.Metrics, nil
}

// GetNodeState returns the full node state including task details.
func (nm *NodeManager) GetNodeState(nodeID string) (*NodeManagerState, error) {
	nm.mu.RLock()
	defer nm.mu.RUnlock()

	state, exists := nm.nodes[nodeID]
	if !exists {
		return nil, fmt.Errorf("node %s not found", nodeID)
	}
	return state, nil
}

// ListNodes returns all registered nodes
func (nm *NodeManager) ListNodes() []*NodeManagerState {
	nm.mu.RLock()
	defer nm.mu.RUnlock()

	result := make([]*NodeManagerState, 0, len(nm.nodes))
	for _, state := range nm.nodes {
		result = append(result, state)
	}
	return result
}

// ====== Kernel 算力调度扩展 ======

// ExtendedKernel 扩展的确定性内核
type ExtendedKernel struct {
	*OpcKernel
	NodeMgr *NodeManager
}

// NewExtendedKernel creates a kernel with node management
func NewExtendedKernel(bufferSize, maxStates, maxNodes int) *ExtendedKernel {
	return &ExtendedKernel{
		OpcKernel: NewKernel(bufferSize, maxStates),
		NodeMgr:   NewNodeManager(maxNodes),
	}
}

// DispatchExtended handles compute-specific actions
func (ek *ExtendedKernel) DispatchExtended(id, action string, payload interface{}) chan Response {
	respChan := make(chan Response, 1)

	start := time.Now()

	switch action {
	case ActionNodeRegister:
		reg, ok := payload.(*NodeRegister)
		if !ok {
			respChan <- Response{Success: false, Error: fmt.Errorf("invalid NodeRegister payload")}
		} else if err := ek.NodeMgr.RegisterNode(reg); err != nil {
			respChan <- Response{Success: false, Error: err}
		} else {
			respChan <- Response{
				Success:  true,
				Data:     map[string]string{"message": "node registered", "node_id": reg.NodeID},
				Duration: time.Since(start).String(),
			}
		}
		return respChan

	case ActionNodeUnregister:
		nodeID, ok := payload.(string)
		if !ok {
			respChan <- Response{Success: false, Error: fmt.Errorf("invalid node_id")}
		} else if err := ek.NodeMgr.UnregisterNode(nodeID); err != nil {
			respChan <- Response{Success: false, Error: err}
		} else {
			respChan <- Response{
				Success:  true,
				Data:     map[string]string{"message": "node removed", "node_id": nodeID},
				Duration: time.Since(start).String(),
			}
		}
		return respChan

	case ActionTaskSubmit:
		task, ok := payload.(*TaskSubmit)
		if !ok {
			respChan <- Response{Success: false, Error: fmt.Errorf("invalid TaskSubmit payload")}
		} else if err := ek.NodeMgr.SubmitTask(task); err != nil {
			respChan <- Response{Success: false, Error: err}
		} else {
			respChan <- Response{
				Success:  true,
				Data:     map[string]string{"message": "task submitted", "task_id": task.TaskID},
				Duration: time.Since(start).String(),
			}
		}
		return respChan

	case ActionGPUMonitor:
		metrics, ok := payload.(*GPUMetrics)
		if !ok {
			respChan <- Response{Success: false, Error: fmt.Errorf("invalid GPUMetrics payload")}
		} else if err := ek.NodeMgr.Heartbeat(metrics.NodeID, metrics); err != nil {
			respChan <- Response{Success: false, Error: err}
		} else {
			respChan <- Response{
				Success:  true,
				Data:     metrics,
				Duration: time.Since(start).String(),
			}
		}
		return respChan

	case ActionTaskResult:
		result, ok := payload.(*TaskResult)
		if !ok {
			respChan <- Response{Success: false, Error: fmt.Errorf("invalid TaskResult payload")}
		} else if err := ek.NodeMgr.CompleteTask(result.TaskID, result.ExecutedOn, result); err != nil {
			respChan <- Response{Success: false, Error: err}
		} else {
			respChan <- Response{
				Success:  true,
				Data:     map[string]interface{}{"task_id": result.TaskID, "verified": result.Verified},
				Duration: time.Since(start).String(),
			}
		}
		return respChan

	case ActionNodeHeartbeat:
		respChan <- Response{
			Success:  true,
			Data:     map[string]string{"message": "heartbeat acknowledged"},
			Duration: time.Since(start).String(),
		}
		return respChan

	case ActionNodeOffline:
		respChan <- Response{Success: false, Error: fmt.Errorf("not yet implemented"), Duration: time.Since(start).String()}
		return respChan

	case ActionTaskCancel:
		respChan <- Response{Success: false, Error: fmt.Errorf("not yet implemented"), Duration: time.Since(start).String()}
		return respChan

	case ActionRegionQuery:
		respChan <- Response{Success: true, Data: ek.NodeMgr.ListNodes(), Duration: time.Since(start).String()}
		return respChan

	case ActionMetricsReport:
		respChan <- Response{Success: true, Data: ek.NodeMgr.ListNodes(), Duration: time.Since(start).String()}
		return respChan

	default:
		// Fall through to base kernel for PING/STATUS - direct call, no goroutine wrapper
		baseChan := ek.OpcKernel.Dispatch(id, action, payload)
		baseResp := <-baseChan
		respChan <- Response{
			Success:  baseResp.Success,
			Data:     baseResp.Data,
			Error:    baseResp.Error,
			Duration: time.Since(start).String(),
		}
		return respChan
	}
}
