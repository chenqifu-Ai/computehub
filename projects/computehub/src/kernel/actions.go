package kernel

import (
	"crypto/rand"
	"fmt"
	"sync"
	"time"

	"github.com/computehub/opc/src/scheduler"
)

// generateShortID generates a 6-char random hex ID
func generateShortID() string {
	b := make([]byte, 3)
	rand.Read(b)
	return fmt.Sprintf("%06x", b)
}

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
	AssignedNode  string   `json:"assigned_node,omitempty"` // specific node (empty = auto-schedule)
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
	TotalTasks     int        `json:"total_tasks"`
	GPUUtilization float64    `json:"gpu_utilization"`
	Temperature    float64    `json:"temperature"`
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
	Task        *TaskSubmit
	Status      string // "pending" | "running" | "completed" | "failed" | "cancelled"
	Assigned    string // node_id
	Result      *TaskResult
	Retries     int
	Created     time.Time
	
	// Streaming output (for long-running tasks)
	StreamStdout string `json:"stream_stdout"`
	StreamStderr string `json:"stream_stderr"`
	StreamUpdated time.Time `json:"stream_updated"`
}

// AppendStreamOutput appends incremental output to the task's stream buffer
func (ts *TaskState) AppendStreamOutput(stdout, stderr string) {
	if stdout != "" {
		ts.StreamStdout += stdout
	}
	if stderr != "" {
		ts.StreamStderr += stderr
	}
	ts.StreamUpdated = time.Now()
}

// StreamOutput represents the streaming output state of a task
type StreamOutput struct {
	TaskID       string    `json:"task_id"`
	NodeID       string    `json:"node_id"`
	Stdout       string    `json:"stdout"`
	Stderr       string    `json:"stderr"`
	UpdatedAt    time.Time `json:"updated_at"`
	Running      bool      `json:"running"`
	ExitCode     int       `json:"exit_code,omitempty"`
	Duration     string    `json:"duration,omitempty"`
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

// UpdateTaskStream updates the streaming output for a running task
func (nm *NodeManager) UpdateTaskStream(taskID, nodeID, stdout, stderr string) error {
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

	ts.AppendStreamOutput(stdout, stderr)
	return nil
}

// GetTaskStream returns the current streaming output for a task
func (nm *NodeManager) GetTaskStream(taskID string) (*StreamOutput, error) {
	nm.mu.RLock()
	defer nm.mu.RUnlock()

	for _, state := range nm.nodes {
		if ts, exists := state.Tasks[taskID]; exists {
			running := ts.Status == "running" || ts.Status == "pending"
			so := &StreamOutput{
				TaskID:    taskID,
				NodeID:    state.Register.NodeID,
				Stdout:    ts.StreamStdout,
				Stderr:    ts.StreamStderr,
				UpdatedAt: ts.StreamUpdated,
				Running:   running,
			}
			if ts.Result != nil {
				so.ExitCode = ts.Result.ExitCode
				so.Duration = ts.Result.Duration
			}
			return so, nil
		}
	}
	return nil, fmt.Errorf("task %s not found", taskID)
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

	// Default MaxConcurrency to 8 if not specified
	maxTasks := reg.MaxConcurrency
	if maxTasks <= 0 {
		maxTasks = 8
	}

	nm.nodes[reg.NodeID] = &NodeManagerState{
		Register: reg,
		Metrics: &NodeMetrics{
			NodeID:        reg.NodeID,
			Region:        reg.Region,
			MaxTasks:      maxTasks,
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

	// Restore online status if it was temporarily offline
	if state.Register.Status == "offline" {
		state.Register.Status = "online"
		logWithTimestamp("[Heartbeat] 🟢 Node %s recovered to ONLINE", nodeID)
	}
	if metrics != nil {
		// Append or update GPU metrics
		m := state.Metrics
		m.GPU = append(m.GPU, *metrics)
		if len(m.GPU) > 10 {
			m.GPU = m.GPU[len(m.GPU)-10:]
		}
		// Update current metrics for node list endpoint
		m.GPUUtilization = metrics.Utilization
		m.Temperature = metrics.Temperature
		m.MemoryUsedGB = metrics.MemoryUsedGB
	}

	return nil
}

// SubmitTask submits a task with priority-aware scheduling
func (nm *NodeManager) SubmitTask(task *TaskSubmit) error {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	// Generate task ID if empty
	if task.TaskID == "" {
		task.TaskID = fmt.Sprintf("task-%d-%s", time.Now().UnixMilli(), generateShortID())
	}

	// 0. 没有任何节点注册
	if len(nm.nodes) == 0 {
		return fmt.Errorf("no nodes registered")
	}

	// 1. Convert priority from 1-10 scale to scheduler priority
	schedPriority := scheduler.TaskPriority(task.Priority)
	if schedPriority < 1 {
		schedPriority = scheduler.PriorityMedium
	}

	// 1a. Find target node: direct assignment or auto-schedule
	hasCapacity := false
	bestNodeID := ""
	bestLoad := 999999

	if task.AssignedNode != "" {
		// Direct assignment to specific node
		if state, exists := nm.nodes[task.AssignedNode]; exists {
			if state.Register.Status != "online" {
				return fmt.Errorf("assigned node %s is not online (status=%s)", task.AssignedNode, state.Register.Status)
			}
			load := state.Metrics.ActiveTasks
			if load >= state.Metrics.MaxTasks {
				return fmt.Errorf("assigned node %s has no capacity (%d/%d tasks)", task.AssignedNode, load, state.Metrics.MaxTasks)
			}
			bestNodeID = task.AssignedNode
			hasCapacity = true
			logWithTimestamp("[NodeMgr] Direct assignment: task %s → node %s", task.TaskID, task.AssignedNode)
		} else {
			return fmt.Errorf("assigned node %s not registered", task.AssignedNode)
		}
	} else {
		// Auto-schedule: find best node
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
			Status:   "pending",   // pending → Worker polls and claims
			Assigned: bestNodeID,
			Created:  time.Now(),
		}
		// Don't increment ActiveTasks until Worker actually claims it via poll
		// state.Metrics.ActiveTasks++
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
			Status:   "pending",   // pending → Worker polls and claims
			Assigned: bestNodeID,
			Created:  time.Now(),
		}
		// Don't increment ActiveTasks until claimed
		// nodeState.Metrics.ActiveTasks++

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

// NextPendingTask pops the next pending task from the priority queue.
// Returns nil if queue is empty.
func (nm *NodeManager) NextPendingTask() *TaskSubmit {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	next, ok := nm.prioQueue.PeekTask()
	if !ok {
		return nil
	}

	nm.prioQueue.PopTask()
	payload, ok := next.Payload.(*TaskSubmit)
	if !ok {
		return nil
	}
	return payload
}

// AssignTaskToNode assigns a task to a specific node with "running" status.
// Returns error if the node doesn't exist.
func (nm *NodeManager) AssignTaskToNode(taskID, nodeID string) error {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	state, exists := nm.nodes[nodeID]
	if !exists {
		return fmt.Errorf("node %s not found", nodeID)
	}

	// Mark task as running on this node
	// The task payload was already popped from queue, so we need to look
	// in the node's tasks to find it (it should have been pre-created)
	if ts, exists := state.Tasks[taskID]; exists {
		ts.Status = "running"
		ts.Assigned = nodeID
		state.Metrics.ActiveTasks++
		return nil
	}

	// Task not found — create a placeholder (shouldn't normally happen)
	logWithTimestamp("[NodeMgr] task %s not found in node %s tasks on assign; creating placeholder", taskID, nodeID)
	return fmt.Errorf("task %s not staged on node %s", taskID, nodeID)
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
	km := NewNodeManager(maxNodes)
	return &ExtendedKernel{
		OpcKernel: &OpcKernel{
			stateMirror: make([]State, 0),
			maxStates:   maxStates,
			LinearQueue: make(chan Command, bufferSize),
			done:        make(chan struct{}),
			NodeMgr:     km,
		},
		NodeMgr: km,
	}
}

// DispatchExtended queues a compute-specific action through the deterministic kernel
// queue. This ensures all commands are processed linearly (no race conditions).
//
// Note: All action names (ActionNodeRegister, ActionTaskSubmit, etc.) are defined
// in this file and processed by ExtendedKernel.executeAction → NodeMgr.
func (ek *ExtendedKernel) DispatchExtended(id, action string, payload interface{}) chan Response {
	return ek.OpcKernel.Dispatch(id, action, payload)
}

// ====== Task Runner & Dispatcher ======

// LocalTaskRunner executes tasks locally
type LocalTaskRunner struct {
	SandboxPath string
}

// NewTaskDispatcher creates a new task dispatcher
func NewTaskDispatcher(kernel *ExtendedKernel, runner *LocalTaskRunner) *TaskDispatcher {
	return &TaskDispatcher{
		kernel: kernel,
		runner: runner,
	}
}

// TaskDispatcher dispatches tasks to nodes
type TaskDispatcher struct {
	kernel *ExtendedKernel
	runner *LocalTaskRunner
}

// Start begins the task dispatcher loop
func (td *TaskDispatcher) Start(interval time.Duration) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for range ticker.C {
			td.dispatch()
		}
	}()
}

func (td *TaskDispatcher) dispatch() {
	// Placeholder: dispatch pending tasks
}

// ====== Heartbeat Monitor ======

// StartHealthMonitor starts a background goroutine that periodically checks
// node health. Dead nodes (no heartbeat for >30s) are marked offline and
// their pending/running tasks are automatically re-queued.
func (nm *NodeManager) StartHealthMonitor(interval time.Duration) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for range ticker.C {
			nm.checkNodeHealth()
		}
	}()
}

// checkNodeHealth iterates all nodes and marks any as offline if their
// heartbeat has been missing for more than 30 seconds. Tasks from
// newly-offlined nodes are reclaimed and re-queued.
func (nm *NodeManager) checkNodeHealth() {
	nm.mu.Lock()
	defer nm.mu.Unlock()

	threshold := 30 * time.Second
	now := time.Now()

	for nodeID, state := range nm.nodes {
		elapsed := now.Sub(state.Heartbeat)
		if state.Register.Status == "online" && elapsed > threshold {
			// Mark node as offline
			state.Register.Status = "offline"
			logWithTimestamp("[HealthMonitor] ⚠️ Node %s marked OFFLINE (no heartbeat for %v)", nodeID, elapsed.Round(time.Second))

			// Reclaim all tasks from this node
			nm.reclaimTasksForNodeLocked(nodeID)
		}
	}
}

// reclaimTasksForNode reclaims all pending and running tasks from a dead node,
// re-queuing them into the priority queue so they can be picked up by other nodes.
//
// NOTE: Caller MUST hold nm.mu.Lock(). Use reclaimTasksForNodeLocked internally.
func (nm *NodeManager) reclaimTasksForNode(nodeID string) {
	nm.mu.Lock()
	defer nm.mu.Unlock()
	nm.reclaimTasksForNodeLocked(nodeID)
}

// reclaimTasksForNodeLocked is the internal implementation.
// Caller must hold nm.mu.Lock().
func (nm *NodeManager) reclaimTasksForNodeLocked(nodeID string) {
	state, exists := nm.nodes[nodeID]
	if !exists {
		return
	}

	reclaimedCount := 0
	for taskID, ts := range state.Tasks {
		if ts.Status == "pending" || ts.Status == "running" {
			// Re-queue the task into the priority queue
			nm.prioQueue.PushTask(taskID, scheduler.TaskPriority(ts.Task.Priority), ts.Task)
			reclaimedCount++
			logWithTimestamp("[HealthMonitor] 🔄 Reclaimed task %s (status=%s, prio=%d) from node %s → re-queued",
				taskID, ts.Status, ts.Task.Priority, nodeID)
		}
		// Delete task record from node
		delete(state.Tasks, taskID)
	}

	// Reset active tasks count
	state.Metrics.ActiveTasks = 0

	if reclaimedCount > 0 {
		logWithTimestamp("[HealthMonitor] ✅ Reclaimed %d task(s) from offline node %s", reclaimedCount, nodeID)
	}
}

