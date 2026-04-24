#!/usr/bin/env python3
"""
ComputeHub 任务状态机 - Go 实现

功能：
1. 任务生命周期管理 (pending → running → completed/failed)
2. 状态同步服务
3. 异常恢复机制
4. 超时处理

执行者：小智 AI 助手
时间：2026-04-22 15:28
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# === 配置 ===
GO_ORCHESTRATION = Path("/root/.openclaw/workspace/ai_agent/code/computehub/orchestration/go")
STATEMACHINE_DIR = GO_ORCHESTRATION / "internal" / "statemachine"

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

def create_statemachine():
    log("=" * 60, "INFO")
    log("ComputeHub 任务状态机 - Go 实现", "INFO")
    log("=" * 60, "INFO")
    
    # 1. 创建目录
    log("步骤 1: 创建状态机目录", "INFO")
    STATEMACHINE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"  ✅ 创建 {STATEMACHINE_DIR}", "SUCCESS")
    
    # 2. 创建状态机核心
    log("步骤 2: 创建状态机核心", "INFO")
    statemachine_go = '''package statemachine

import (
	"fmt"
	"sync"
	"time"
)

// TaskState 任务状态
type TaskState string

const (
	// 初始状态
	TaskStatePending   TaskState = "pending"    // 等待调度
	TaskStateQueued    TaskState = "queued"     // 已入队
	TaskStatePreparing TaskState = "preparing"  // 准备资源
	
	// 运行状态
	TaskStateRunning     TaskState = "running"     // 正在执行
	TaskStateVerifying   TaskState = "verifying"   // 结果验证
	
	// 终态
	TaskStateCompleted TaskState = "completed" // 成功完成
	TaskStateFailed    TaskState = "failed"    // 执行失败
	TaskStateCancelled TaskState = "cancelled" // 已取消
	TaskStateTimeout   TaskState = "timeout"   // 超时
)

// StateMachine 任务状态机
type StateMachine struct {
	mu       sync.RWMutex
	tasks    map[string]*Task
	history  []StateTransition
	config   *StateMachineConfig
}

// Task 任务定义
type Task struct {
	ID            string                 `json:"id"`
	Name          string                 `json:"name"`
	State         TaskState              `json:"state"`
	Framework     string                 `json:"framework"`
	GPUCount      int                    `json:"gpu_count"`
	MemoryGB      int                    `json:"memory_gb"`
	NodeID        string                 `json:"node_id,omitempty"`
	NodeName      string                 `json:"node_name,omitempty"`
	CreatedAt     time.Time              `json:"created_at"`
	UpdatedAt     time.Time              `json:"updated_at"`
	StartedAt     *time.Time             `json:"started_at,omitempty"`
	CompletedAt   *time.Time             `json:"completed_at,omitempty"`
	TimeoutAt     *time.Time             `json:"timeout_at,omitempty"`
	Priority      int                    `json:"priority"`
	MaxRetries    int                    `json:"max_retries"`
	RetryCount    int                    `json:"retry_count"`
	ErrorMessage  string                 `json:"error_message,omitempty"`
	Result        map[string]interface{} `json:"result,omitempty"`
	Metadata      map[string]string      `json:"metadata"`
	StateHistory  []StateTransition      `json:"state_history"`
}

// StateTransition 状态转换
type StateTransition struct {
	TaskID    string    `json:"task_id"`
	FromState TaskState `json:"from_state"`
	ToState   TaskState `json:"to_state"`
	Timestamp time.Time `json:"timestamp"`
	Reason    string    `json:"reason,omitempty"`
}

// StateMachineConfig 状态机配置
type StateMachineConfig struct {
	DefaultTimeoutHours float64 `json:"default_timeout_hours"`
	MaxRetries          int     `json:"max_retries"`
	EnableAutoRetry     bool    `json:"enable_auto_retry"`
	EnableTimeout       bool    `json:"enable_timeout"`
	CleanupIntervalMins int     `json:"cleanup_interval_mins"`
}

// DefaultConfig 默认配置
func DefaultConfig() *StateMachineConfig {
	return &StateMachineConfig{
		DefaultTimeoutHours: 24.0,
		MaxRetries:          3,
		EnableAutoRetry:     true,
		EnableTimeout:       true,
		CleanupIntervalMins: 60,
	}
}

// NewStateMachine 创建状态机
func NewStateMachine(config *StateMachineConfig) *StateMachine {
	if config == nil {
		config = DefaultConfig()
	}
	return &StateMachine{
		tasks:  make(map[string]*Task),
		config: config,
	}
}

// CreateTask 创建新任务
func (sm *StateMachine) CreateTask(task *Task) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	if task.ID == "" {
		return fmt.Errorf("task ID is required")
	}

	task.State = TaskStatePending
	task.CreatedAt = time.Now()
	task.UpdatedAt = time.Now()
	task.MaxRetries = sm.config.MaxRetries
	task.Metadata = make(map[string]string)
	task.StateHistory = []StateTransition{}

	// 设置超时时间
	if sm.config.EnableTimeout {
		timeoutAt := time.Now().Add(time.Duration(sm.config.DefaultTimeoutHours) * time.Hour)
		task.TimeoutAt = &timeoutAt
	}

	sm.tasks[task.ID] = task

	// 记录状态转换
	sm.recordTransition(task.ID, "", TaskStatePending, "task_created")

	return nil
}

// Transition 状态转换
func (sm *StateMachine) Transition(taskID string, toState TaskState, reason string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	task, exists := sm.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	fromState := task.State

	// 验证状态转换是否合法
	if !sm.isValidTransition(fromState, toState) {
		return fmt.Errorf("invalid transition from %s to %s", fromState, toState)
	}

	// 执行状态转换
	task.State = toState
	task.UpdatedAt = time.Now()

	// 更新特定状态的时间戳
	switch toState {
	case TaskStateRunning:
		now := time.Now()
		task.StartedAt = &now
	case TaskStateCompleted, TaskStateFailed, TaskStateCancelled, TaskStateTimeout:
		now := time.Now()
		task.CompletedAt = &now
	}

	// 记录状态转换
	sm.recordTransition(taskID, fromState, toState, reason)

	return nil
}

// isValidTransition 验证状态转换是否合法
func (sm *StateMachine) isValidTransition(from, to TaskState) bool {
	// 定义合法的状态转换
	validTransitions := map[TaskState][]TaskState{
		TaskStatePending:   {TaskStateQueued, TaskStateCancelled},
		TaskStateQueued:    {TaskStatePreparing, TaskStateCancelled},
		TaskStatePreparing: {TaskStateRunning, TaskStateFailed},
		TaskStateRunning:   {TaskStateVerifying, TaskStateFailed, TaskStateCancelled},
		TaskStateVerifying: {TaskStateCompleted, TaskStateFailed},
		TaskStateCompleted: {}, // 终态
		TaskStateFailed:    {}, // 终态，但可重试
		TaskStateCancelled: {}, // 终态
		TaskStateTimeout:   {}, // 终态
	}

	allowed, exists := validTransitions[from]
	if !exists {
		return false
	}

	for _, state := range allowed {
		if state == to {
			return true
		}
	}

	return false
}

// recordTransition 记录状态转换
func (sm *StateMachine) recordTransition(taskID string, from, to TaskState, reason string) {
	transition := StateTransition{
		TaskID:    taskID,
		FromState: from,
		ToState:   to,
		Timestamp: time.Now(),
		Reason:    reason,
	}

	// 更新任务历史
	if task, exists := sm.tasks[taskID]; exists {
		task.StateHistory = append(task.StateHistory, transition)
	}

	// 记录全局历史
	sm.history = append(sm.history, transition)

	// 限制历史记录大小
	if len(sm.history) > 1000 {
		sm.history = sm.history[len(sm.history)-1000:]
	}
}

// GetTask 获取任务
func (sm *StateMachine) GetTask(taskID string) (*Task, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	task, exists := sm.tasks[taskID]
	if !exists {
		return nil, fmt.Errorf("task %s not found", taskID)
	}

	return task, nil
}

// ListTasks 列出任务
func (sm *StateMachine) ListTasks(state *TaskState, limit int) []*Task {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	var result []*Task
	for _, task := range sm.tasks {
		if state != nil && task.State != *state {
			continue
		}
		result = append(result, task)
	}

	// 限制返回数量
	if limit > 0 && len(result) > limit {
		result = result[:limit]
	}

	return result
}

// RetryTask 重试任务
func (sm *StateMachine) RetryTask(taskID string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	task, exists := sm.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	if task.State != TaskStateFailed && task.State != TaskStateTimeout {
		return fmt.Errorf("can only retry failed or timeout tasks, current state: %s", task.State)
	}

	if task.RetryCount >= task.MaxRetries {
		return fmt.Errorf("max retries (%d) exceeded", task.MaxRetries)
	}

	task.RetryCount++
	task.State = TaskStatePending
	task.UpdatedAt = time.Now()
	task.ErrorMessage = ""
	task.Result = nil

	sm.recordTransition(taskID, task.State, TaskStatePending, fmt.Sprintf("retry_%d", task.RetryCount))

	return nil
}

// CancelTask 取消任务
func (sm *StateMachine) CancelTask(taskID string, reason string) error {
	return sm.Transition(taskID, TaskStateCancelled, reason)
}

// FailTask 标记任务失败
func (sm *StateMachine) FailTask(taskID string, errorMessage string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	task, exists := sm.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.State = TaskStateFailed
	task.ErrorMessage = errorMessage
	task.UpdatedAt = time.Now()
	now := time.Now()
	task.CompletedAt = &now

	sm.recordTransition(taskID, task.State, TaskStateFailed, errorMessage)

	// 自动重试
	if sm.config.EnableAutoRetry && task.RetryCount < task.MaxRetries {
		task.RetryCount++
		task.State = TaskStatePending
		task.ErrorMessage = ""
		sm.recordTransition(taskID, TaskStateFailed, TaskStatePending, fmt.Sprintf("auto_retry_%d", task.RetryCount))
	}

	return nil
}

// CompleteTask 标记任务完成
func (sm *StateMachine) CompleteTask(taskID string, result map[string]interface{}) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	task, exists := sm.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.State = TaskStateCompleted
	task.Result = result
	task.UpdatedAt = time.Now()
	now := time.Now()
	task.CompletedAt = &now

	sm.recordTransition(taskID, task.State, TaskStateCompleted, "task_completed")

	return nil
}

// GetStats 获取统计信息
func (sm *StateMachine) GetStats() map[string]interface{} {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	stats := map[string]int{
		"total":      len(sm.tasks),
		"pending":    0,
		"queued":     0,
		"preparing":  0,
		"running":    0,
		"verifying":  0,
		"completed":  0,
		"failed":     0,
		"cancelled":  0,
		"timeout":    0,
	}

	for _, task := range sm.tasks {
		switch task.State {
		case TaskStatePending:
			stats["pending"]++
		case TaskStateQueued:
			stats["queued"]++
		case TaskStatePreparing:
			stats["preparing"]++
		case TaskStateRunning:
			stats["running"]++
		case TaskStateVerifying:
			stats["verifying"]++
		case TaskStateCompleted:
			stats["completed"]++
		case TaskStateFailed:
			stats["failed"]++
		case TaskStateCancelled:
			stats["cancelled"]++
		case TaskStateTimeout:
			stats["timeout"]++
		}
	}

	return map[string]interface{}{
		"counts":     stats,
		"transitions": len(sm.history),
	}
}

// CheckTimeouts 检查超时任务
func (sm *StateMachine) CheckTimeouts() []string {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	var timedOut []string
	now := time.Now()

	for _, task := range sm.tasks {
		if task.State == TaskStateRunning || task.State == TaskStatePreparing {
			if task.TimeoutAt != nil && now.After(*task.TimeoutAt) {
				task.State = TaskStateTimeout
				task.UpdatedAt = now
				task.CompletedAt = &now
				sm.recordTransition(task.ID, task.State, TaskStateTimeout, "task_timeout")
				timedOut = append(timedOut, task.ID)
			}
		}
	}

	return timedOut
}

// CleanupCompletedTasks 清理已完成的任务
func (sm *StateMachine) CleanupCompletedTasks(olderThan time.Duration) int {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	cutoff := time.Now().Add(-olderThan)
	count := 0

	for id, task := range sm.tasks {
		if task.State == TaskStateCompleted || task.State == TaskStateCancelled {
			if task.CompletedAt != nil && task.CompletedAt.Before(cutoff) {
				delete(sm.tasks, id)
				count++
			}
		}
	}

	return count
}

// GetTaskHistory 获取任务历史
func (sm *StateMachine) GetTaskHistory(taskID string) []StateTransition {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	if task, exists := sm.tasks[taskID]; exists {
		return task.StateHistory
	}
	return []StateTransition{}
}
'''
    (STATEMACHINE_DIR / "statemachine.go").write_text(statemachine_go, encoding='utf-8')
    log("  ✅ 创建 internal/statemachine/statemachine.go", "SUCCESS")
    
    # 3. 更新 handlers 添加状态机 API
    log("步骤 3: 更新 handlers 添加状态机 API", "INFO")
    # 读取现有 handlers.go
    handlers_path = GO_ORCHESTRATION / "internal" / "handlers" / "handlers.go"
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    # 添加状态机导入
    if '"github.com/computehub/opc/orchestration/internal/statemachine"' not in handlers_content:
        handlers_content = handlers_content.replace(
            '"github.com/computehub/opc/orchestration/internal/scheduler"',
            '"github.com/computehub/opc/orchestration/internal/scheduler"\n\t"github.com/computehub/opc/orchestration/internal/statemachine"'
        )
    
    # 添加状态机字段到 Handler
    handlers_content = handlers_content.replace(
        'scheduler *scheduler.Scheduler',
        'scheduler  *scheduler.Scheduler\n\tstatemachine *statemachine.StateMachine'
    )
    
    # 更新 NewHandler
    handlers_content = handlers_content.replace(
        'scheduler: scheduler.NewScheduler(scheduler.DefaultConfig()),',
        'scheduler:     scheduler.NewScheduler(scheduler.DefaultConfig()),\n\t\tstatemachine: statemachine.NewStateMachine(statemachine.DefaultConfig()),'
    )
    
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新 internal/handlers/handlers.go (添加状态机)", "SUCCESS")
    
    # 4. 添加状态机 API 端点
    log("步骤 4: 添加状态机 API 端点", "INFO")
    # 读取 handlers.go 末尾
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    state_machine_apis = '''
// CreateTask 创建新任务
func (h *Handler) CreateTask(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var taskReq struct {
		ID          string            `json:"id"`
		Name        string            `json:"name"`
		Framework   string            `json:"framework"`
		GPUCount    int               `json:"gpu_count"`
		MemoryGB    int               `json:"memory_gb"`
		Priority    int               `json:"priority"`
		Metadata    map[string]string `json:"metadata"`
	}

	if err := json.NewDecoder(r.Body).Decode(&taskReq); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	task := &statemachine.Task{
		ID:         taskReq.ID,
		Name:       taskReq.Name,
		Framework:  taskReq.Framework,
		GPUCount:   taskReq.GPUCount,
		MemoryGB:   taskReq.MemoryGB,
		Priority:   taskReq.Priority,
		Metadata:   taskReq.Metadata,
	}

	if err := h.statemachine.CreateTask(task); err != nil {
		http.Error(w, fmt.Sprintf("Failed to create task: %v", err), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"task_id": task.ID,
		"state":   task.State,
	})
}

// GetTask 获取任务详情
func (h *Handler) GetTask(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	taskID := parts[len(parts)-1]

	task, err := h.statemachine.GetTask(taskID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(task)
}

// ListTasks 列出任务
func (h *Handler) ListTasks(w http.ResponseWriter, r *http.Request) {
	stateParam := r.URL.Query().Get("state")
	limit := 100

	var state *statemachine.TaskState
	if stateParam != "" {
		s := statemachine.TaskState(stateParam)
		state = &s
	}

	tasks := h.statemachine.ListTasks(state, limit)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"tasks": tasks,
		"total": len(tasks),
	})
}

// TransitionTask 状态转换
func (h *Handler) TransitionTask(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	taskID := parts[len(parts)-1]

	var req struct {
		ToState string `json:"to_state"`
		Reason  string `json:"reason"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	if err := h.statemachine.Transition(taskID, statemachine.TaskState(req.ToState), req.Reason); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}

// RetryTask 重试任务
func (h *Handler) RetryTask(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	taskID := parts[len(parts)-1]

	if err := h.statemachine.RetryTask(taskID); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}

// CancelTask 取消任务
func (h *Handler) CancelTask(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	taskID := parts[len(parts)-1]

	var req struct {
		Reason string `json:"reason"`
	}
	json.NewDecoder(r.Body).Decode(&req)

	if err := h.statemachine.CancelTask(taskID, req.Reason); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
	})
}

// GetTaskHistory 获取任务历史
func (h *Handler) GetTaskHistory(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	taskID := parts[len(parts)-1]

	history := h.statemachine.GetTaskHistory(taskID)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"task_id": taskID,
		"history": history,
		"total":   len(history),
	})
}

// GetTaskStats 获取任务统计
func (h *Handler) GetTaskStats(w http.ResponseWriter, r *http.Request) {
	stats := h.statemachine.GetStats()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}
'''
    
    # 添加到文件末尾
    handlers_content = handlers_content.rstrip() + '\n' + state_machine_apis
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 添加状态机 API 端点", "SUCCESS")
    
    # 5. 更新 SetupMux 注册新端点
    log("步骤 5: 更新路由注册", "INFO")
    handlers_content = handlers_path.read_text(encoding='utf-8')
    
    # 找到 SetupMux 函数中的调度器端点部分，添加状态机端点
    old_mux = '''mux.HandleFunc("GET /api/scheduler/history", h.GetScheduleHistory)

	return mux
}'''
    
    new_mux = '''mux.HandleFunc("GET /api/scheduler/history", h.GetScheduleHistory)

	// 状态机端点
	mux.HandleFunc("POST /api/tasks", h.CreateTask)
	mux.HandleFunc("GET /api/tasks", h.ListTasks)
	mux.HandleFunc("GET /api/tasks/{id}", h.GetTask)
	mux.HandleFunc("PUT /api/tasks/{id}/transition", h.TransitionTask)
	mux.HandleFunc("POST /api/tasks/{id}/retry", h.RetryTask)
	mux.HandleFunc("POST /api/tasks/{id}/cancel", h.CancelTask)
	mux.HandleFunc("GET /api/tasks/{id}/history", h.GetTaskHistory)
	mux.HandleFunc("GET /api/tasks/stats", h.GetTaskStats)

	return mux
}'''
    
    handlers_content = handlers_content.replace(old_mux, new_mux)
    handlers_path.write_text(handlers_content, encoding='utf-8')
    log("  ✅ 更新路由注册", "SUCCESS")
    
    # 6. 创建测试脚本
    log("步骤 6: 创建测试脚本", "INFO")
    test_statemachine_py = '''#!/usr/bin/env python3
"""测试任务状态机"""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8080"

def test_create_task():
    """创建测试任务"""
    print("\\n=== 创建任务 ===")
    
    task = {
        "id": f"task-{int(time.time())}",
        "name": "PyTorch Training Job",
        "framework": "pytorch",
        "gpu_count": 4,
        "memory_gb": 128,
        "priority": 5,
        "metadata": {
            "user": "test_user",
            "project": "llm_training"
        }
    }
    
    resp = requests.post(f"{BASE_URL}/api/tasks", json=task)
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"  ✅ 任务创建成功!")
        print(f"     任务 ID: {result['task_id']}")
        print(f"     状态：{result['state']}")
        return result['task_id']
    else:
        print(f"  ❌ 创建失败：{resp.text}")
        return None

def test_task_lifecycle(task_id):
    """测试任务生命周期"""
    print("\\n=== 任务生命周期测试 ===")
    
    transitions = [
        ("queued", "任务已入队"),
        ("preparing", "准备资源中"),
        ("running", "任务执行中"),
    ]
    
    for state, reason in transitions:
        print(f"  → 转换到 {state}...")
        resp = requests.put(
            f"{BASE_URL}/api/tasks/{task_id}/transition",
            json={"to_state": state, "reason": reason}
        )
        if resp.status_code == 200:
            print(f"     ✅ {state} 成功")
        else:
            print(f"     ❌ {state} 失败：{resp.text}")
            return
    
    # 获取任务详情
    print(f"  \\n  获取任务详情...")
    resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
    if resp.status_code == 200:
        task = resp.json()
        print(f"     当前状态：{task['state']}")
        print(f"     创建时间：{task['created_at']}")
        print(f"     更新时间：{task['updated_at']}")
        print(f"     状态历史：{len(task['state_history'])} 条")

def test_task_stats():
    """查看任务统计"""
    print("\\n=== 任务统计 ===")
    
    resp = requests.get(f"{BASE_URL}/api/tasks/stats")
    
    if resp.status_code == 200:
        stats = resp.json()
        counts = stats.get('counts', {})
        print(f"  总任务数：{counts.get('total', 0)}")
        print(f"  Pending: {counts.get('pending', 0)}")
        print(f"  Running: {counts.get('running', 0)}")
        print(f"  Completed: {counts.get('completed', 0)}")
        print(f"  Failed: {counts.get('failed', 0)}")

def test_list_tasks():
    """列出所有任务"""
    print("\\n=== 任务列表 ===")
    
    resp = requests.get(f"{BASE_URL}/api/tasks?limit=10")
    
    if resp.status_code == 200:
        result = resp.json()
        tasks = result.get('tasks', [])
        print(f"  共 {len(tasks)} 个任务:")
        for task in tasks[:5]:
            print(f"    - {task['id']}: {task['state']} ({task['framework']})")

if __name__ == "__main__":
    print("=" * 60)
    print("ComputeHub 任务状态机测试")
    print("=" * 60)
    
    try:
        # 创建任务
        task_id = test_create_task()
        
        if task_id:
            # 测试生命周期
            test_task_lifecycle(task_id)
        
        # 查看统计
        test_task_stats()
        
        # 列出任务
        test_list_tasks()
        
        print("\\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\\n❌ 测试失败：{e}")
'''
    (GO_ORCHESTRATION / "test_statemachine.py").write_text(test_statemachine_py, encoding='utf-8')
    log("  ✅ 创建 test_statemachine.py", "SUCCESS")
    
    # 7. 更新 main.go
    log("步骤 7: 更新 main.go", "INFO")
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
	log.Printf("🔄 Task state machine enabled")
	
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
'''
    (GO_ORCHESTRATION / "cmd" / "orchestrator" / "main.go").write_text(main_go, encoding='utf-8')
    log("  ✅ 更新 cmd/orchestrator/main.go", "SUCCESS")
    
    log("", "INFO")
    log("=" * 60, "INFO")
    log("任务状态机创建完成！", "SUCCESS")
    log(f"目录：{GO_ORCHESTRATION}", "SUCCESS")
    log("=" * 60, "INFO")
    
    return True

if __name__ == "__main__":
    success = create_statemachine()
    sys.exit(0 if success else 1)
