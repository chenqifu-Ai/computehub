package api

import (
	"fmt"
	"sync"
	"time"
)

// ====== 任务生命周期状态机 ======

// TaskState 任务生命周期状态
type TaskState int

const (
	TaskPending TaskState = iota // 等待调度
	TaskQueued                   // 已调度，等待执行
	TaskRunning                  // 执行中
	TaskCompleted                // 执行完成
	TaskFailed                   // 执行失败
	TaskCancelled                // 已取消
	TaskRetrying                 // 重试中
	TaskVerifying                // 结果验证中
)

func (s TaskState) String() string {
	switch s {
	case TaskPending:
		return "PENDING"
	case TaskQueued:
		return "QUEUED"
	case TaskRunning:
		return "RUNNING"
	case TaskCompleted:
		return "COMPLETED"
	case TaskFailed:
		return "FAILED"
	case TaskCancelled:
		return "CANCELLED"
	case TaskRetrying:
		return "RETRYING"
	case TaskVerifying:
		return "VERIFYING"
	default:
		return "UNKNOWN"
	}
}

// ====== 状态转换规则 ======

// StateTransition 定义有效的状态转换
type StateTransition struct {
	From      TaskState
	To        TaskState
	Action    string  // 触发转换的动作
	Condition string  // 转换条件描述
}

// ValidTransitions 定义所有允许的状态转换
var ValidTransitions = map[TaskState][]StateTransition{
	TaskPending: {
		{From: TaskPending, To: TaskQueued, Action: "DISPATCH", Condition: "调度器分配节点"},
		{From: TaskPending, To: TaskCancelled, Action: "CANCEL", Condition: "用户取消"},
	},
	TaskQueued: {
		{From: TaskQueued, To: TaskRunning, Action: "EXECUTE", Condition: "节点开始执行"},
		{From: TaskQueued, To: TaskCancelled, Action: "CANCEL", Condition: "用户取消"},
		{From: TaskQueued, To: TaskPending, Action: "REQUEUE", Condition: "节点故障，重新排队"},
	},
	TaskRunning: {
		{From: TaskRunning, To: TaskCompleted, Action: "SUCCESS", Condition: "执行成功"},
		{From: TaskRunning, To: TaskFailed, Action: "FAILED", Condition: "执行失败"},
		{From: TaskRunning, To: TaskRetrying, Action: "RETRY", Condition: "自动重试"},
		{From: TaskRunning, To: TaskCancelled, Action: "CANCEL", Condition: "用户取消"},
		{From: TaskRunning, To: TaskVerifying, Action: "VERIFY", Condition: "结果验证"},
	},
	TaskRetrying: {
		{From: TaskRetrying, To: TaskQueued, Action: "RETRY", Condition: "重试重新调度"},
		{From: TaskRetrying, To: TaskFailed, Action: "MAX_RETRIES", Condition: "超过最大重试次数"},
		{From: TaskRetrying, To: TaskCancelled, Action: "CANCEL", Condition: "用户取消"},
	},
	TaskVerifying: {
		{From: TaskVerifying, To: TaskCompleted, Action: "VERIFIED", Condition: "验证通过"},
		{From: TaskVerifying, To: TaskFailed, Action: "VERIFY_FAILED", Condition: "验证失败"},
		{From: TaskVerifying, To: TaskRetrying, Action: "RETRY", Condition: "验证失败需重试"},
	},
	TaskCompleted: {
		{From: TaskCompleted, To: TaskCompleted, Action: "KEEP", Condition: "终态，保持不变"},
	},
	TaskFailed: {
		{From: TaskFailed, To: TaskFailed, Action: "KEEP", Condition: "终态，保持不变"},
		{From: TaskFailed, To: TaskPending, Action: "RETRY", Condition: "手动重试"},
	},
	TaskCancelled: {
		{From: TaskCancelled, To: TaskCancelled, Action: "KEEP", Condition: "终态，保持不变"},
	},
}

// ====== 状态机 ======

type StateMachine struct {
	mu         sync.RWMutex
	tasks      map[string]*TaskStateRecord
	maxHistory int
}

type TaskStateRecord struct {
	TaskID        string            `json:"task_id"`
	CurrentState  TaskState         `json:"current_state"`
	StateHistory  []StateTransition `json:"state_history"`
	Transitions   []TransitionEvent `json:"transitions"`
	AssignedNode  string            `json:"assigned_node,omitempty"`
	CreatedAt     time.Time         `json:"created_at"`
	UpdatedAt     time.Time         `json:"updated_at"`
}

type TransitionEvent struct {
	From      TaskState `json:"from"`
	To        TaskState `json:"to"`
	Action    string    `json:"action"`
	Timestamp time.Time `json:"timestamp"`
	Reason    string    `json:"reason,omitempty"`
	NodeID    string    `json:"node_id,omitempty"`
}

// NewStateMachine 创建新的状态机
func NewStateMachine() *StateMachine {
	return &StateMachine{
		tasks:      make(map[string]*TaskStateRecord),
		maxHistory: 100,
	}
}

// CreateTask 创建新任务 (初始状态 PENDING)
func (sm *StateMachine) CreateTask(taskID string) *TaskStateRecord {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	record := &TaskStateRecord{
		TaskID:       taskID,
		CurrentState: TaskPending,
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
		Transitions:  make([]TransitionEvent, 0),
	}

	sm.tasks[taskID] = record
	return record
}

// Transition 执行状态转换
func (sm *StateMachine) Transition(taskID string, from TaskState, to TaskState, action, reason, nodeID string) (*TransitionEvent, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	record, exists := sm.tasks[taskID]
	if !exists {
		return nil, fmt.Errorf("task %s not found", taskID)
	}

	// 验证当前状态
	if record.CurrentState != from {
		return nil, fmt.Errorf("expected state %s, got %s", from, record.CurrentState)
	}

	// 验证转换是否允许
	transitions, allowed := ValidTransitions[from]
	if !allowed {
		return nil, fmt.Errorf("no transitions defined for state %s", from)
	}

	found := false
	for _, t := range transitions {
		if t.To == to && t.Action == action {
			found = true
			break
		}
	}

	if !found {
		return nil, fmt.Errorf("invalid transition: %s -> %s (action: %s)", from, to, action)
	}

	// 执行转换
	event := TransitionEvent{
		From:      from,
		To:        to,
		Action:    action,
		Timestamp: time.Now(),
		Reason:    reason,
		NodeID:    nodeID,
	}

	record.Transitions = append(record.Transitions, event)
	record.CurrentState = to
	record.UpdatedAt = time.Now()

	// 限制历史记录数量
	if len(record.Transitions) > sm.maxHistory {
		record.Transitions = record.Transitions[len(record.Transitions)-sm.maxHistory:]
	}

	return &event, nil
}

// GetTaskState 获取任务当前状态
func (sm *StateMachine) GetTaskState(taskID string) (*TaskStateRecord, bool) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	record, exists := sm.tasks[taskID]
	if !exists {
		return nil, false
	}

	// 深拷贝
	cp := *record
	cp.Transitions = make([]TransitionEvent, len(record.Transitions))
	copy(cp.Transitions, record.Transitions)

	return &cp, true
}

// GetTasksByState 按状态筛选任务
func (sm *StateMachine) GetTasksByState(filter TaskState) []string {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	var taskIDs []string
	for id, record := range sm.tasks {
		if record.CurrentState == filter {
			taskIDs = append(taskIDs, id)
		}
	}

	return taskIDs
}

// GetActiveTasks 获取所有活跃任务 (非终态)
func (sm *StateMachine) GetActiveTasks() []string {
	terminalStates := map[TaskState]bool{
		TaskCompleted: true,
		TaskFailed:    true,
		TaskCancelled: true,
	}

	sm.mu.RLock()
	defer sm.mu.RUnlock()

	var taskIDs []string
	for id, record := range sm.tasks {
		if !terminalStates[record.CurrentState] {
			taskIDs = append(taskIDs, id)
		}
	}

	return taskIDs
}

// GetTaskStats 获取任务统计
func (sm *StateMachine) GetTaskStats() map[TaskState]int {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	stats := make(map[TaskState]int)
	for _, record := range sm.tasks {
		stats[record.CurrentState]++
	}

	return stats
}

// RemoveTask 移除任务记录
func (sm *StateMachine) RemoveTask(taskID string) bool {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	if _, exists := sm.tasks[taskID]; !exists {
		return false
	}

	delete(sm.tasks, taskID)
	return true
}

// GetTransitionHistory 获取任务的状态转换历史
func (sm *StateMachine) GetTransitionHistory(taskID string) ([]TransitionEvent, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	record, exists := sm.tasks[taskID]
	if !exists {
		return nil, fmt.Errorf("task %s not found", taskID)
	}

	history := make([]TransitionEvent, len(record.Transitions))
	copy(history, record.Transitions)

	return history, nil
}
