// Package kernel implements the deterministic task scheduler kernel.
// It enforces strict state machine transitions and eliminates race conditions
// through linear command processing.
//
// Inspired by OpenPC's deterministic kernel philosophy.
package kernel

import (
	"fmt"
	"sync"
	"time"
)

// ─── 状态常量 ───

const (
	StatePending     = "PENDING"
	StateAllocated   = "ALLOCATED"
	StateExecuting   = "EXECUTING"
	StateVerifying   = "VERIFYING"
	StateCompleted   = "COMPLETED"
	StateFailed      = "FAILED"
	StateCancelled   = "CANCELLED"
)

// ─── 物理状态快照 ───

// State represents a physical snapshot of system state at a timestamp.
type State struct {
	Timestamp time.Time       `json:"timestamp"`
	Nodes     int             `json:"nodes"`
	Tasks     TaskStats       `json:"tasks"`
	Resources ResourceUsage   `json:"resources"`
	Meta      map[string]any  `json:"meta,omitempty"`
}

// TaskStats tracks task counts by state.
type TaskStats struct {
	Total     int `json:"total"`
	Pending   int `json:"pending"`
	Running   int `json:"running"`
	Completed int `json:"completed"`
	Failed    int `json:"failed"`
}

// ResourceUsage tracks current resource consumption.
type ResourceUsage struct {
	GPUs     int     `json:"gpus"`
	CPUs     int     `json:"cpus"`
	MemBytes uint64  `json:"mem_bytes"`
	MemPct   float64 `json:"mem_pct"`
}

// ─── 任务定义 ───

// TaskAction represents a deterministic task action.
type TaskAction string

const (
	TaskActionSubmit   TaskAction = "SUBMIT"
	TaskActionExecute  TaskAction = "EXECUTE"
	TaskActionCancel   TaskAction = "CANCEL"
	TaskActionStatus   TaskAction = "STATUS"
	TaskActionResource TaskAction = "RESOURCE"
)

// ComputeTask is the fundamental unit of work in ComputeHub.
type ComputeTask struct {
	ID           string            `json:"id"`
	Action       TaskAction        `json:"action"`
	Framework    string            `json:"framework"`     // pytorch, tensorflow, jax
	ResourceType string            `json:"resource_type"` // gpu, cpu, tpu
	GPUCount     int               `json:"gpu_count"`
	CPUCount     int               `json:"cpu_count"`
	MemoryGB     int               `json:"memory_gb"`
	DurationSecs int               `json:"duration_secs"`
	Requirements map[string]string `json:"requirements,omitempty"`
	Source       string            `json:"source"`      // tui, api, sdk
	AssignedNode string            `json:"assigned_node,omitempty"`
	Status       string            `json:"status"`
	StartTime    time.Time         `json:"start_time,omitempty"`
	EndTime      time.Time         `json:"end_time,omitempty"`
	Result       map[string]any    `json:"result,omitempty"`
}

// Command is a linearized task instruction.
type Command struct {
	ID       string
	Task     *ComputeTask
	Response chan *Response
}

// Response is the kernel's reply to a command.
type Response struct {
	Success bool
	Data    any
	Error   error
}

// ─── 配额管理器 ───

// Quota defines resource limits.
type Quota struct {
	MaxGPUs         int
	MaxCPUs         int
	MaxMemoryGB     int
	MaxConcurrent   int
	MaxPendingTasks int
}

// DefaultQuota returns sensible defaults.
func DefaultQuota() Quota {
	return Quota{
		MaxGPUs:         8,
		MaxCPUs:         32,
		MaxMemoryGB:     128,
		MaxConcurrent:   10,
		MaxPendingTasks: 500,
	}
}

// ─── 确定性内核 ───

// Kernel is the deterministic task scheduler.
// All task processing happens sequentially through LinearQueue,
// eliminating race conditions across the entire system.
type Kernel struct {
	mu            sync.RWMutex
	stateMirror   []State
	maxStates     int
	LinearQueue   chan *Command
	LastLatency   time.Duration
	tasks         map[string]*ComputeTask
	currentTasks  map[string]*ComputeTask // tasks in EXECUTING state
	taskCounter   int
	quota         Quota
	startTime     time.Time
}

// NewKernel creates a new deterministic kernel with given capacity.
func NewKernel(bufferSize int, maxStates int) *Kernel {
	return &Kernel{
		stateMirror: make([]State, 0),
		maxStates:   maxStates,
		LinearQueue: make(chan *Command, bufferSize),
		tasks:       make(map[string]*ComputeTask),
		currentTasks: make(map[string]*ComputeTask),
		taskCounter: 0,
		quota:       DefaultQuota(),
		startTime:   time.Now(),
	}
}

// NewKernelDefaults creates a kernel with default buffer size.
func NewKernelDefaults() *Kernel {
	return NewKernel(500, 5000)
}

// Start begins the linearized task processing loop.
// This goroutine ensures ALL task processing is serial.
func (k *Kernel) Start() {
	go func() {
		for cmd := range k.LinearQueue {
			k.processCommand(cmd)
		}
	}()
}

// processCommand executes a single command deterministically.
func (k *Kernel) processCommand(cmd *Command) {
	start := time.Now()

	// 1. Snapshot current state before any modification
	k.snapshotState()

	// 2. Execute command based on action
	var resp *Response
	switch cmd.Task.Action {
	case TaskActionSubmit:
		resp = k.handleSubmit(cmd.Task)
	case TaskActionExecute:
		resp = k.handleExecute(cmd.Task)
	case TaskActionCancel:
		resp = k.handleCancel(cmd.Task)
	case TaskActionStatus:
		resp = k.handleStatus(cmd.Task)
	case TaskActionResource:
		resp = k.handleResource(cmd.Task)
	default:
		resp = &Response{
			Success: false,
			Error:   fmt.Errorf("unknown action: %s", cmd.Task.Action),
		}
	}

	// 3. Record latency
	duration := time.Since(start)
	k.mu.Lock()
	k.LastLatency = duration
	k.mu.Unlock()

	// 4. Send response
	cmd.Response <- resp
}

// handleSubmit processes a new task submission.
func (k *Kernel) handleSubmit(task *ComputeTask) *Response {
	k.mu.Lock()
	defer k.mu.Unlock()

	// Check quota
	if len(k.currentTasks) >= k.quota.MaxConcurrent {
		return &Response{
			Success: false,
			Error:   fmt.Errorf("concurrent task limit reached: %d/%d", len(k.currentTasks), k.quota.MaxConcurrent),
		}
	}

	if len(k.tasks)+1 > k.quota.MaxPendingTasks {
		return &Response{
			Success: false,
			Error:   fmt.Errorf("pending task limit reached: %d/%d", len(k.tasks), k.quota.MaxPendingTasks),
		}
	}

	// Check GPU quota
	var usedGPUs int
	for _, t := range k.tasks {
		if t.ResourceType == "gpu" {
			usedGPUs += t.GPUCount
		}
	}
	if usedGPUs+task.GPUCount > k.quota.MaxGPUs {
		return &Response{
			Success: false,
			Error:   fmt.Errorf("GPU quota exceeded: %d/%d", usedGPUs+task.GPUCount, k.quota.MaxGPUs),
		}
	}

	// Assign task ID
	task.ID = fmt.Sprintf("task-%d", k.taskCounter)
	k.taskCounter++
	task.Status = StatePending
	task.StartTime = time.Now()

	// Register task
	k.tasks[task.ID] = task

	return &Response{
		Success: true,
		Data: map[string]any{
			"task_id": task.ID,
			"status":  task.Status,
		},
	}
}

// handleExecute allocates and starts task execution.
func (k *Kernel) handleExecute(task *ComputeTask) *Response {
	k.mu.Lock()
	defer k.mu.Unlock()

	existing, exists := k.tasks[task.ID]
	if !exists {
		return &Response{
			Success: false,
			Error:   fmt.Errorf("task not found: %s", task.ID),
		}
	}

	if existing.Status != StatePending {
		return &Response{
			Success: false,
			Error:   fmt.Errorf("task cannot be executed in state: %s", existing.Status),
		}
	}

	// State transition: PENDING → ALLOCATED → EXECUTING
	existing.Status = StateExecuting
	existing.StartTime = time.Now()
	k.currentTasks[task.ID] = existing

	return &Response{
		Success: true,
		Data: map[string]any{
			"task_id": task.ID,
			"status":  StateExecuting,
			"message": "Task allocated and executing",
		},
	}
}

// handleCancel stops a task.
func (k *Kernel) handleCancel(task *ComputeTask) *Response {
	k.mu.Lock()
	defer k.mu.Unlock()

	existing, exists := k.tasks[task.ID]
	if !exists {
		return &Response{
			Success: false,
			Error:   fmt.Errorf("task not found: %s", task.ID),
		}
	}

	if existing.Status == StateCompleted || existing.Status == StateCancelled {
		return &Response{
			Success: false,
			Error:   fmt.Errorf("task cannot be cancelled in state: %s", existing.Status),
		}
	}

	existing.Status = StateCancelled
	existing.EndTime = time.Now()
	delete(k.currentTasks, task.ID)

	return &Response{
		Success: true,
		Data: map[string]any{
			"task_id": task.ID,
			"status":  StateCancelled,
		},
	}
}

// handleStatus returns task information.
func (k *Kernel) handleStatus(task *ComputeTask) *Response {
	k.mu.RLock()
	defer k.mu.RUnlock()

	if task.ID == "" {
		// Return aggregate stats
		return &Response{
			Success: true,
			Data: k.getTaskStats(),
		}
	}

	existing, exists := k.tasks[task.ID]
	if !exists {
		return &Response{
			Success: false,
			Error:   fmt.Errorf("task not found: %s", task.ID),
		}
	}

	return &Response{
		Success: true,
		Data:    existing,
	}
}

// handleResource returns resource usage information.
func (k *Kernel) handleResource(task *ComputeTask) *Response {
	k.mu.RLock()
	defer k.mu.RUnlock()

	var usedGPUs, usedCPUs, totalMem int
	for _, t := range k.tasks {
		if t.Status == StateExecuting {
			usedGPUs += t.GPUCount
			usedCPUs += t.CPUCount
			totalMem += t.MemoryGB
		}
	}

	return &Response{
		Success: true,
		Data: map[string]any{
			"gpu_used":    usedGPUs,
			"gpu_total":   k.quota.MaxGPUs,
			"cpu_used":    usedCPUs,
			"cpu_total":   k.quota.MaxCPUs,
			"mem_used_gb": totalMem,
			"mem_total_gb": k.quota.MaxMemoryGB,
			"concurrent_tasks": len(k.currentTasks),
			"max_concurrent": k.quota.MaxConcurrent,
		},
	}
}

// ─── 状态镜像 ───

// snapshotState saves a physical state snapshot.
func (k *Kernel) snapshotState() {
	k.mu.Lock()
	defer k.mu.Unlock()

	stats := k.getTaskStatsLocked()

	state := State{
		Timestamp: time.Now(),
		Nodes:     1, // Local node count
		Tasks:     stats,
		Resources: ResourceUsage{
			GPUs:    stats.Running,
			CPUs:    stats.Running,
			MemBytes: uint64(stats.Running) * 32 * 1024 * 1024 * 1024, // ~32GB per task
			MemPct:  float64(stats.Running) / float64(k.quota.MaxConcurrent) * 100,
		},
	}

	k.stateMirror = append(k.stateMirror, state)
	if len(k.stateMirror) > k.maxStates {
		k.stateMirror = k.stateMirror[1:]
	}
}

// getStateHistory returns recent state snapshots.
func (k *Kernel) getStateHistory(n int) []State {
	k.mu.RLock()
	defer k.mu.RUnlock()

	if n > len(k.stateMirror) {
		n = len(k.stateMirror)
	}
	if n == 0 {
		return k.stateMirror
	}
	return k.stateMirror[len(k.stateMirror)-n:]
}

// ─── 状态查询 ───

func (k *Kernel) getTaskStats() TaskStats {
	k.mu.RLock()
	defer k.mu.RUnlock()
	return k.getTaskStatsLocked()
}

func (k *Kernel) getTaskStatsLocked() TaskStats {
	stats := TaskStats{}
	for _, t := range k.tasks {
		stats.Total++
		switch t.Status {
		case StatePending:
			stats.Pending++
		case StateExecuting:
			stats.Running++
		case StateCompleted:
			stats.Completed++
		case StateFailed:
			stats.Failed++
		}
	}
	return stats
}

// ─── 系统信息 ───

// Info returns kernel system information.
func (k *Kernel) Info() map[string]any {
	k.mu.RLock()
	defer k.mu.RUnlock()

	stats := k.getTaskStatsLocked()
	uptime := time.Since(k.startTime)

	return map[string]any{
		"status":          "RUNNING",
		"schedule_latency": k.LastLatency.String(),
		"queue_depth":     len(k.LinearQueue),
		"total_tasks":     stats.Total,
		"pending_tasks":   stats.Pending,
		"running_tasks":   stats.Running,
		"completed_tasks": stats.Completed,
		"failed_tasks":    stats.Failed,
		"uptime":          uptime.String(),
		"version":         "2.0.0",
		"architecture":    "distributed-computehub",
	}
}

// SetQuota updates resource quota limits.
func (k *Kernel) SetQuota(q Quota) {
	k.mu.Lock()
	defer k.mu.Unlock()
	k.quota = q
}

// GetQuota returns current quota.
func (k *Kernel) GetQuota() Quota {
	k.mu.RLock()
	defer k.mu.RUnlock()
	return k.quota
}

// GetTaskStats returns current task statistics.
func (k *Kernel) GetTaskStats() TaskStats {
	return k.getTaskStats()
}

// Dispatch sends a command to the linear processing queue.
// All commands are processed strictly in order.
func (k *Kernel) Dispatch(task *ComputeTask) *Response {
	respChan := make(chan *Response, 1)
	k.LinearQueue <- &Command{
		ID:       task.ID,
		Task:     task,
		Response: respChan,
	}
	return <-respChan
}

// Stop gracefully shuts down the kernel.
func (k *Kernel) Stop() {
	close(k.LinearQueue)
}
