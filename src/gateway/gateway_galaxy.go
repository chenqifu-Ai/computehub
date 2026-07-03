// Package gateway — 银河计划 Phase 2 & Phase 3
//
// Phase 2:
// 1. 任务智能分配（Scheduler 集成）
// 2. 进度跟踪系统（TaskTracker）
// 3. 安全审计（Audit Middleware）
//
// Phase 3:
// 4. 自主进化 API（委派给 Agent.Phase3）
//
// SPEC-GALAXY-002 v1.0 / SPEC-GALAXY-003 v1.0

package gateway

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"sync"
	"time"

	"github.com/computehub/opc/src/agent"
)

// ══════════════════════════════════════════════════════════════════════
// 1. 任务智能分配 — Scheduler 集成
// ══════════════════════════════════════════════════════════════════════

// ScheduleRequest 调度请求
type ScheduleRequest struct {
	TaskID         string  `json:"task_id"`
	Priority       int     `json:"priority"`        // 1-10
	RegionAffinity string  `json:"region_affinity"` // 区域偏好
	GPURequired    bool    `json:"gpu_required"`
	MinMemoryGB    float64 `json:"min_memory_gb"`
	Timeout        int     `json:"timeout"` // 秒
}

// ScheduleResponse 调度响应
type ScheduleResponse struct {
	NodeID     string  `json:"node_id"`
	TaskID     string  `json:"task_id"`
	Score      float64 `json:"score"`
	Reason     string  `json:"reason"`
	AssignedAt string  `json:"assigned_at"`
}

// handleSchedule 智能调度端点
// POST /api/v1/scheduler/schedule
func (g *OpcGateway) handleSchedule(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req ScheduleRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid request: %v", err)})
		return
	}

	if req.TaskID == "" {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "task_id is required"})
		return
	}

	// 使用 Scheduler 进行智能调度
	result := g.Scheduler.ScheduleTask(req.TaskID, req.RegionAffinity, req.Priority)

	if result.NodeID == "" {
		g.sendJSON(w, map[string]interface{}{
			"success": false,
			"error":   "no suitable node found: " + result.Reason,
		})
		return
	}

	// 记录审计
	g.auditLog("system", AuditSchedule, "task", req.TaskID, result.Reason, true)

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data": ScheduleResponse{
			NodeID:     result.NodeID,
			TaskID:     result.TaskID,
			Score:      result.RegionScore + result.LoadScore,
			Reason:     result.Reason,
			AssignedAt: result.AssignedAt.Format(time.RFC3339),
		},
	})
}

// handleSchedulerStats 调度器统计
// GET /api/v1/scheduler/stats
func (g *OpcGateway) handleSchedulerStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	stats := g.Scheduler.GetStats()
	health := g.Scheduler.HealthCheck()

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"stats":  stats,
			"health": health,
		},
	})
}

// ══════════════════════════════════════════════════════════════════════
// 2. 进度跟踪系统 — TaskTracker
// ══════════════════════════════════════════════════════════════════════

// GalaxyTaskStage 任务阶段（与 gallery.TaskProgress 区分）
type GalaxyTaskStage string

const (
	StagePending    GalaxyTaskStage = "pending"
	StageQueued     GalaxyTaskStage = "queued"
	StageScheduled  GalaxyTaskStage = "scheduled"
	StageRunning    GalaxyTaskStage = "running"
	StageCompleted  GalaxyTaskStage = "completed"
	StageFailed     GalaxyTaskStage = "failed"
	StageCancelled  GalaxyTaskStage = "cancelled"
	StageRetrying   GalaxyTaskStage = "retrying"
)

// GalaxyTaskProgress 任务进度（银河计划专用，与 gallery.TaskProgress 区分）
type GalaxyTaskProgress struct {
	TaskID      string          `json:"task_id"`
	NodeID      string          `json:"node_id"`
	Stage       GalaxyTaskStage `json:"stage"`
	Percent     int             `json:"percent"`      // 0-100
	Message     string          `json:"message"`      // 当前阶段描述
	SubStage    string          `json:"sub_stage"`    // 子阶段
	StartedAt   time.Time       `json:"started_at"`
	UpdatedAt   time.Time       `json:"updated_at"`
	CompletedAt time.Time       `json:"completed_at,omitempty"`
	Duration    string          `json:"duration,omitempty"`
	RetryCount  int             `json:"retry_count"`
	MaxRetries  int             `json:"max_retries"`
	Error       string          `json:"error,omitempty"`
	Output      string          `json:"output,omitempty"`
}

// TaskTracker 任务进度跟踪器
type TaskTracker struct {
	mu      sync.RWMutex
	tasks   map[string]*GalaxyTaskProgress
	history []*GalaxyTaskProgress
	maxHist int
}

// NewTaskTracker 创建任务跟踪器
func NewTaskTracker() *TaskTracker {
	return &TaskTracker{
		tasks:   make(map[string]*GalaxyTaskProgress),
		history: make([]*GalaxyTaskProgress, 0, 100),
		maxHist: 500,
	}
}

// CreateTask 创建任务进度记录
func (tt *TaskTracker) CreateTask(taskID, nodeID string) {
	tt.mu.Lock()
	defer tt.mu.Unlock()

	tt.tasks[taskID] = &GalaxyTaskProgress{
		TaskID:     taskID,
		NodeID:     nodeID,
		Stage:      StagePending,
		Percent:    0,
		Message:    "任务已创建",
		StartedAt:  time.Now(),
		UpdatedAt:  time.Now(),
		MaxRetries: 3,
	}
}

// UpdateProgress 更新任务进度
func (tt *TaskTracker) UpdateProgress(taskID string, percent int, message string) error {
	tt.mu.Lock()
	defer tt.mu.Unlock()

	task, exists := tt.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	if percent < 0 || percent > 100 {
		return fmt.Errorf("percent must be 0-100")
	}

	task.Percent = percent
	task.Message = message
	task.UpdatedAt = time.Now()

	if percent == 0 {
		task.Stage = StageQueued
	} else if percent < 100 {
		task.Stage = StageRunning
	} else {
		task.Stage = StageCompleted
		task.CompletedAt = time.Now()
		task.Duration = time.Since(task.StartedAt).Round(time.Second).String()
	}

	return nil
}

// UpdateStage 更新任务阶段
func (tt *TaskTracker) UpdateStage(taskID string, stage GalaxyTaskStage, subStage, message string) error {
	tt.mu.Lock()
	defer tt.mu.Unlock()

	task, exists := tt.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.Stage = stage
	task.SubStage = subStage
	task.Message = message
	task.UpdatedAt = time.Now()

	switch stage {
	case StageRunning:
		if task.StartedAt.IsZero() {
			task.StartedAt = time.Now()
		}
	case StageCompleted:
		task.Percent = 100
		task.CompletedAt = time.Now()
		task.Duration = time.Since(task.StartedAt).Round(time.Second).String()
	case StageFailed:
		task.Error = message
		task.CompletedAt = time.Now()
		task.Duration = time.Since(task.StartedAt).Round(time.Second).String()
	case StageRetrying:
		task.RetryCount++
		task.Message = fmt.Sprintf("重试 %d/%d: %s", task.RetryCount, task.MaxRetries, message)
	}

	return nil
}

// RecordRetry 记录重试
func (tt *TaskTracker) RecordRetry(taskID, reason string) error {
	tt.mu.Lock()
	defer tt.mu.Unlock()

	task, exists := tt.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.RetryCount++
	task.Stage = StageRetrying
	task.Message = fmt.Sprintf("重试 %d/%d: %s", task.RetryCount, task.MaxRetries, reason)
	task.UpdatedAt = time.Now()

	return nil
}

// GetProgress 获取任务进度
func (tt *TaskTracker) GetProgress(taskID string) (*GalaxyTaskProgress, error) {
	tt.mu.RLock()
	defer tt.mu.RUnlock()

	task, exists := tt.tasks[taskID]
	if !exists {
		return nil, fmt.Errorf("task %s not found", taskID)
	}

	return task, nil
}

// ListActive 列出所有活跃任务
func (tt *TaskTracker) ListActive() []*GalaxyTaskProgress {
	tt.mu.RLock()
	defer tt.mu.RUnlock()

	var active []*GalaxyTaskProgress
	for _, task := range tt.tasks {
		if task.Stage != StageCompleted && task.Stage != StageFailed && task.Stage != StageCancelled {
			active = append(active, task)
		}
	}

	sort.Slice(active, func(i, j int) bool {
		return active[i].UpdatedAt.After(active[j].UpdatedAt)
	})

	return active
}

// ListByNode 列出某节点的所有任务
func (tt *TaskTracker) ListByNode(nodeID string) []*GalaxyTaskProgress {
	tt.mu.RLock()
	defer tt.mu.RUnlock()

	var tasks []*GalaxyTaskProgress
	for _, task := range tt.tasks {
		if task.NodeID == nodeID {
			tasks = append(tasks, task)
		}
	}

	sort.Slice(tasks, func(i, j int) bool {
		return tasks[i].UpdatedAt.After(tasks[j].UpdatedAt)
	})

	return tasks
}

// CompleteTask 完成任务并移入历史
func (tt *TaskTracker) CompleteTask(taskID, result string) error {
	tt.mu.Lock()
	defer tt.mu.Unlock()

	task, exists := tt.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.Stage = StageCompleted
	task.Percent = 100
	task.Message = result
	task.CompletedAt = time.Now()
	task.Duration = time.Since(task.StartedAt).Round(time.Second).String()
	task.UpdatedAt = time.Now()

	tt.history = append(tt.history, task)
	if len(tt.history) > tt.maxHist {
		tt.history = tt.history[len(tt.history)-tt.maxHist:]
	}

	delete(tt.tasks, taskID)
	return nil
}

// FailTask 标记任务失败
func (tt *TaskTracker) FailTask(taskID, errMsg string) error {
	tt.mu.Lock()
	defer tt.mu.Unlock()

	task, exists := tt.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.Stage = StageFailed
	task.Error = errMsg
	task.CompletedAt = time.Now()
	task.Duration = time.Since(task.StartedAt).Round(time.Second).String()
	task.UpdatedAt = time.Now()

	tt.history = append(tt.history, task)
	if len(tt.history) > tt.maxHist {
		tt.history = tt.history[len(tt.history)-tt.maxHist:]
	}

	delete(tt.tasks, taskID)
	return nil
}

// GetStats 获取跟踪器统计
func (tt *TaskTracker) GetStats() map[string]interface{} {
	tt.mu.RLock()
	defer tt.mu.RUnlock()

	active := 0
	completed := 0
	failed := 0
	running := 0

	for _, task := range tt.tasks {
		switch task.Stage {
		case StageRunning:
			running++
			active++
		case StagePending, StageQueued, StageScheduled:
			active++
		}
	}

	for _, task := range tt.history {
		switch task.Stage {
		case StageCompleted:
			completed++
		case StageFailed:
			failed++
		}
	}

	return map[string]interface{}{
		"active_tasks":  active,
		"running":       running,
		"completed":     completed,
		"failed":        failed,
		"total_tracked": len(tt.tasks) + len(tt.history),
	}
}

// ── TaskTracker API Handlers ──

// handleTaskTrack 创建/更新任务进度
// POST /api/v1/tracker/track
func (g *OpcGateway) handleTaskTrack(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		TaskID   string `json:"task_id"`
		NodeID   string `json:"node_id"`
		Action   string `json:"action"`    // "create" | "progress" | "stage" | "complete" | "fail" | "retry"
		Percent  int    `json:"percent"`
		Stage    string `json:"stage"`
		SubStage string `json:"sub_stage"`
		Message  string `json:"message"`
		Error    string `json:"error"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid request: %v", err)})
		return
	}

	if req.TaskID == "" {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "task_id is required"})
		return
	}

	var err error
	switch req.Action {
	case "create":
		g.TaskTracker.CreateTask(req.TaskID, req.NodeID)
	case "progress":
		err = g.TaskTracker.UpdateProgress(req.TaskID, req.Percent, req.Message)
	case "stage":
		err = g.TaskTracker.UpdateStage(req.TaskID, GalaxyTaskStage(req.Stage), req.SubStage, req.Message)
	case "complete":
		err = g.TaskTracker.CompleteTask(req.TaskID, req.Message)
	case "fail":
		err = g.TaskTracker.FailTask(req.TaskID, req.Error)
	case "retry":
		err = g.TaskTracker.RecordRetry(req.TaskID, req.Message)
	default:
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("unknown action: %s", req.Action)})
		return
	}

	if err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}

	g.sendJSON(w, map[string]interface{}{"success": true})
}

// handleTaskTrackerQuery 查询任务进度
// GET /api/v1/tracker/query?task_id=xxx
// GET /api/v1/tracker/active
// GET /api/v1/tracker/node?node_id=xxx
func (g *OpcGateway) handleTaskTrackerQuery(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	taskID := r.URL.Query().Get("task_id")
	nodeID := r.URL.Query().Get("node_id")
	view := r.URL.Query().Get("view") // "active" | "node" | "stats"

	switch view {
	case "active":
		tasks := g.TaskTracker.ListActive()
		g.sendJSON(w, map[string]interface{}{
			"success": true,
			"data":    tasks,
			"count":   len(tasks),
		})
		return

	case "node":
		if nodeID == "" {
			g.sendJSON(w, map[string]interface{}{"success": false, "error": "node_id is required for node view"})
			return
		}
		tasks := g.TaskTracker.ListByNode(nodeID)
		g.sendJSON(w, map[string]interface{}{
			"success": true,
			"data":    tasks,
			"count":   len(tasks),
		})
		return

	case "stats":
		stats := g.TaskTracker.GetStats()
		g.sendJSON(w, map[string]interface{}{
			"success": true,
			"data":    stats,
		})
		return
	}

	if taskID == "" {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "task_id or view is required"})
		return
	}

	progress, err := g.TaskTracker.GetProgress(taskID)
	if err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data":    progress,
	})
}

// ══════════════════════════════════════════════════════════════════════
// 3. 安全审计系统
// ══════════════════════════════════════════════════════════════════════

// AuditAction 审计操作类型
type AuditAction string

const (
	AuditLogin        AuditAction = "LOGIN"
	AuditLogout       AuditAction = "LOGOUT"
	AuditTaskSubmit   AuditAction = "TASK_SUBMIT"
	AuditTaskCancel   AuditAction = "TASK_CANCEL"
	AuditTaskAssign   AuditAction = "TASK_ASSIGN"
	AuditNodeRegister AuditAction = "NODE_REGISTER"
	AuditNodeRemove   AuditAction = "NODE_REMOVE"
	AuditConfigChange AuditAction = "CONFIG_CHANGE"
	AuditSchedule     AuditAction = "SCHEDULE_TASK"
	AuditUpgrade      AuditAction = "UPGRADE"
	AuditUnauthorized AuditAction = "UNAUTHORIZED"
	AuditSystem       AuditAction = "SYSTEM"
)

// AuditEntry 审计日志条目
type AuditEntry struct {
	ID        string      `json:"id"`
	Timestamp time.Time   `json:"timestamp"`
	Actor     string      `json:"actor"`
	Action    AuditAction `json:"action"`
	Resource  string      `json:"resource"`
	Target    string      `json:"target"`
	Success   bool        `json:"success"`
	Detail    string      `json:"detail"`
	IP        string      `json:"ip,omitempty"`
}

// AuditStore 审计日志存储
type AuditStore struct {
	mu      sync.RWMutex
	entries []AuditEntry
	maxSize int
}

// NewAuditStore 创建审计日志存储
func NewAuditStore(maxSize int) *AuditStore {
	return &AuditStore{
		entries: make([]AuditEntry, 0, 100),
		maxSize: maxSize,
	}
}

// Log 记录审计日志
func (as *AuditStore) Log(actor string, action AuditAction, resource, target, detail string, success bool, ip string) {
	as.mu.Lock()
	defer as.mu.Unlock()

	entry := AuditEntry{
		ID:        fmt.Sprintf("audit-%d", time.Now().UnixNano()),
		Timestamp: time.Now(),
		Actor:     actor,
		Action:    action,
		Resource:  resource,
		Target:    target,
		Success:   success,
		Detail:    detail,
		IP:        ip,
	}

	as.entries = append(as.entries, entry)

	if len(as.entries) > as.maxSize {
		as.entries = as.entries[len(as.entries)-as.maxSize:]
	}
}

// Query 查询审计日志
func (as *AuditStore) Query(filter AuditFilter) []AuditEntry {
	as.mu.RLock()
	defer as.mu.RUnlock()

	var results []AuditEntry
	for _, entry := range as.entries {
		if filter.Actor != "" && entry.Actor != filter.Actor {
			continue
		}
		if filter.Action != "" && entry.Action != filter.Action {
			continue
		}
		if filter.Resource != "" && entry.Resource != filter.Resource {
			continue
		}
		if filter.Success != nil && entry.Success != *filter.Success {
			continue
		}
		if !filter.Since.IsZero() && entry.Timestamp.Before(filter.Since) {
			continue
		}
		results = append(results, entry)
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Timestamp.After(results[j].Timestamp)
	})

	if filter.Limit > 0 && len(results) > filter.Limit {
		results = results[:filter.Limit]
	}

	return results
}

// GetStats 获取审计统计
func (as *AuditStore) GetStats() map[string]interface{} {
	as.mu.RLock()
	defer as.mu.RUnlock()

	actionCount := make(map[string]int)
	successCount := 0
	failCount := 0
	actorSet := make(map[string]bool)

	for _, entry := range as.entries {
		actionCount[string(entry.Action)]++
		if entry.Success {
			successCount++
		} else {
			failCount++
		}
		actorSet[entry.Actor] = true
	}

	return map[string]interface{}{
		"total_entries":  len(as.entries),
		"success_count":  successCount,
		"fail_count":     failCount,
		"unique_actors":  len(actorSet),
		"by_action":      actionCount,
	}
}

// AuditFilter 审计查询过滤
type AuditFilter struct {
	Actor    string      `json:"actor,omitempty"`
	Action   AuditAction `json:"action,omitempty"`
	Resource string      `json:"resource,omitempty"`
	Success  *bool       `json:"success,omitempty"`
	Since    time.Time   `json:"since,omitempty"`
	Limit    int         `json:"limit,omitempty"`
}

// ── Gateway 审计方法 ──

// auditLog 记录审计日志（Gateway 方法）
func (g *OpcGateway) auditLog(actor string, action AuditAction, resource, target, detail string, success bool) {
	if g.AuditStore == nil {
		return
	}
	g.AuditStore.Log(actor, action, resource, target, detail, success, "")
}

// auditLogWithIP 记录审计日志（含 IP）
func (g *OpcGateway) auditLogWithIP(actor string, action AuditAction, resource, target, detail string, success bool, ip string) {
	if g.AuditStore == nil {
		return
	}
	g.AuditStore.Log(actor, action, resource, target, detail, success, ip)
}

// ── Audit API Handlers ──

// handleAuditLog 记录审计日志
// POST /api/v1/audit/log
func (g *OpcGateway) handleAuditLog(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Actor    string `json:"actor"`
		Action   string `json:"action"`
		Resource string `json:"resource"`
		Target   string `json:"target"`
		Success  bool   `json:"success"`
		Detail   string `json:"detail"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid request: %v", err)})
		return
	}

	if req.Actor == "" || req.Action == "" {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "actor and action are required"})
		return
	}

	ip := extractClientIP(r)
	g.auditLogWithIP(req.Actor, AuditAction(req.Action), req.Resource, req.Target, req.Detail, req.Success, ip)

	g.sendJSON(w, map[string]interface{}{"success": true})
}

// handleAuditQuery 查询审计日志
// GET /api/v1/audit/query?actor=xxx&action=xxx&limit=50
func (g *OpcGateway) handleAuditQuery(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	filter := AuditFilter{
		Actor:    r.URL.Query().Get("actor"),
		Resource: r.URL.Query().Get("resource"),
		Limit:    50,
	}

	if action := r.URL.Query().Get("action"); action != "" {
		filter.Action = AuditAction(action)
	}

	if limitStr := r.URL.Query().Get("limit"); limitStr != "" {
		if _, err := fmt.Sscanf(limitStr, "%d", &filter.Limit); err != nil {
			filter.Limit = 50
		}
	}

	if sinceStr := r.URL.Query().Get("since"); sinceStr != "" {
		if t, err := time.Parse(time.RFC3339, sinceStr); err == nil {
			filter.Since = t
		}
	}

	successStr := r.URL.Query().Get("success")
	if successStr == "true" {
		s := true
		filter.Success = &s
	} else if successStr == "false" {
		s := false
		filter.Success = &s
	}

	entries := g.AuditStore.Query(filter)

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data":    entries,
		"count":   len(entries),
	})
}

// handleAuditStats 审计统计
// GET /api/v1/audit/stats
func (g *OpcGateway) handleAuditStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	stats := g.AuditStore.GetStats()
	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data":    stats,
	})
}

// ── 审计中间件 ──

// auditMiddleware 审计中间件（记录所有 API 请求）
func (g *OpcGateway) auditMiddleware(next http.HandlerFunc, action AuditAction, resource string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		recorder := &responseRecorder{ResponseWriter: w, statusCode: http.StatusOK}
		next(recorder, r)

		actor := r.URL.Query().Get("node_id")
		if actor == "" {
			actor = extractClientIP(r)
		}

		success := recorder.statusCode < 400
		g.auditLogWithIP(actor, action, resource, r.URL.Path, fmt.Sprintf("HTTP %d", recorder.statusCode), success, extractClientIP(r))
	}
}

// responseRecorder 用于记录 HTTP 响应状态码
type responseRecorder struct {
	http.ResponseWriter
	statusCode int
}

func (rr *responseRecorder) WriteHeader(code int) {
	rr.statusCode = code
	rr.ResponseWriter.WriteHeader(code)
}

// ══════════════════════════════════════════════════════════════════════
//  银河计划 Phase 3 API
// ══════════════════════════════════════════════════════════════════════

// handlePhase3Stats 获取 Phase 3 整体统计
// GET /api/v1/galaxy/phase3/stats
func (g *OpcGateway) handlePhase3Stats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil || g.Agent.Phase3 == nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "Phase 3 not initialized"})
		return
	}

	stats := g.Agent.Phase3.GetStats()
	summary := g.Agent.Phase3.GetSummary()

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data":    stats,
		"summary": summary,
	})
}

// handlePhase3SelfLearning 自主学习统计
// GET /api/v1/galaxy/phase3/self-learning
func (g *OpcGateway) handlePhase3SelfLearning(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil || g.Agent.Phase3 == nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "Phase 3 not initialized"})
		return
	}

	stats := g.Agent.Phase3.SelfLearning.GetStats()
	g.sendJSON(w, map[string]interface{}{"success": true, "data": stats})
}

// handlePhase3Innovation 创新探索统计
// GET /api/v1/galaxy/phase3/innovation
func (g *OpcGateway) handlePhase3Innovation(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil || g.Agent.Phase3 == nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "Phase 3 not initialized"})
		return
	}

	stats := g.Agent.Phase3.Innovation.GetStats()
	g.sendJSON(w, map[string]interface{}{"success": true, "data": stats})
}

// handlePhase3CrossDomain 跨领域协作
// POST /api/v1/galaxy/phase3/cross-domain
func (g *OpcGateway) handlePhase3CrossDomain(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil || g.Agent.Phase3 == nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "Phase 3 not initialized"})
		return
	}

	var req struct {
		Task string `json:"task"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid request: %v", err)})
		return
	}

	if req.Task == "" {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "task is required"})
		return
	}

	// 分解任务
	tasks, err := g.Agent.Phase3.CrossDomain.DecomposeTask(req.Task)
	if err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}

	// 执行协作
	record, err := g.Agent.Phase3.CrossDomain.ExecuteCollaboration(req.Task, tasks)
	if err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data":    record,
	})
}

// handlePhase3SelfOrg 自组织委派
// POST /api/v1/galaxy/phase3/delegate
func (g *OpcGateway) handlePhase3SelfOrg(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil || g.Agent.Phase3 == nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "Phase 3 not initialized"})
		return
	}

	var req struct {
		Task string `json:"task"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid request: %v", err)})
		return
	}

	if req.Task == "" {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "task is required"})
		return
	}

	result, err := g.Agent.Phase3.SelfOrg.AutoDelegate(req.Task)
	if err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": err.Error()})
		return
	}

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data":    result,
	})
}

// handlePhase3Summary Phase 3 摘要
// GET /api/v1/galaxy/phase3/summary
func (g *OpcGateway) handlePhase3Summary(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil || g.Agent.Phase3 == nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": "Phase 3 not initialized"})
		return
	}

	summary := g.Agent.Phase3.GetSummary()
	g.sendJSON(w, map[string]interface{}{"success": true, "data": summary})
}

// ══════════════════════════════════════════════════════════════════════
// Phase 3 事件缓冲 + 控制 API
// ══════════════════════════════════════════════════════════════════════

// Phase3Event 一条 Phase 3 操作日志（Gateway 侧存储）
type Phase3Event struct {
	Time      string `json:"time"`
	Source    string `json:"source"`     // self_learning / innovation / cross_domain / self_org
	Action    string `json:"action"`     // 操作类型
	Detail    string `json:"detail"`     // 描述
	LLMCalled bool   `json:"llm_called"` // 是否调用了 LLM
	Success   bool   `json:"success"`
	NodeID    string `json:"node_id"`    // 来源节点
}

// Phase3EventBuffer Gateway 侧的 Phase 3 事件缓冲区
type Phase3EventBuffer struct {
	mu     sync.RWMutex
	events []Phase3Event
	max    int
}

// NewPhase3EventBuffer 创建事件缓冲区
func NewPhase3EventBuffer(max int) *Phase3EventBuffer {
	return &Phase3EventBuffer{
		events: make([]Phase3Event, 0, max),
		max:    max,
	}
}

// Push 添加一条事件
func (b *Phase3EventBuffer) Push(evt Phase3Event) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.events = append(b.events, evt)
	if len(b.events) > b.max {
		b.events = b.events[len(b.events)-b.max:]
	}
}

// List 获取事件列表
func (b *Phase3EventBuffer) List(limit int) []Phase3Event {
	b.mu.RLock()
	defer b.mu.RUnlock()
	if limit <= 0 || limit > len(b.events) {
		limit = len(b.events)
	}
	start := len(b.events) - limit
	if start < 0 {
		start = 0
	}
	out := make([]Phase3Event, limit)
	copy(out, b.events[start:])
	return out
}

// handlePhase3Event POST — 接收 Worker 推送的 Phase 3 事件
func (g *OpcGateway) handlePhase3Event(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var evt Phase3Event
	if err := json.NewDecoder(r.Body).Decode(&evt); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid event: %v", err)})
		return
	}

	if g.Phase3EventBuffer != nil {
		// 从请求 IP 或 Header 获取节点 ID
		nodeID := r.Header.Get("X-Node-ID")
		if nodeID == "" {
			nodeID = "unknown"
		}
		evt.NodeID = nodeID
		g.Phase3EventBuffer.Push(evt)
	}

	g.sendJSON(w, map[string]interface{}{"success": true})
}

// handlePhase3Events GET — 获取 Phase 3 事件列表
func (g *OpcGateway) handlePhase3Events(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	limit := 50
	r.ParseForm()
	if l := r.FormValue("limit"); l != "" {
		fmt.Sscanf(l, "%d", &limit)
	}

	var events []Phase3Event
	if g.Phase3EventBuffer != nil {
		events = g.Phase3EventBuffer.List(limit)
	} else {
		events = []Phase3Event{}
	}

	g.sendJSON(w, map[string]interface{}{
		"success": true,
		"data":    events,
		"total":   len(events),
	})
}

// handlePhase3Control POST — 控制 Phase 3 运行模式
func (g *OpcGateway) handlePhase3Control(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Mode            string `json:"mode,omitempty"`             // "observe" 或 "active"
		ReflectInterval *int   `json:"reflect_interval,omitempty"` // 反思间隔
		ExploreInterval *int   `json:"explore_interval,omitempty"` // 探索间隔
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendJSON(w, map[string]interface{}{"success": false, "error": fmt.Sprintf("invalid request: %v", err)})
		return
	}

	// 检查本地 Agent 是否有 Phase 3
	hasLocal := g.Agent != nil && g.Agent.Phase3 != nil

	// 应用 mode 变更
	if req.Mode != "" {
		mode := agent.Phase3ModeActive
		if req.Mode == "observe" {
			mode = agent.Phase3ModeObserve
		}
		change := fmt.Sprintf("mode=%s", req.Mode)

		// 本地 Agent
		if hasLocal {
			g.Agent.Phase3.SetMode(mode)
		}

		// 推送给所有远程节点
		g.broadcastPhase3Control(change)

		g.sendJSON(w, map[string]interface{}{
			"success": true,
			"message": fmt.Sprintf("Phase 3 mode 已切换为 %s", req.Mode),
			"local":   hasLocal,
		})
		return
	}

	// 应用间隔变更
	if req.ReflectInterval != nil && *req.ReflectInterval > 0 {
		change := fmt.Sprintf("reflect_interval=%d", *req.ReflectInterval)
		if hasLocal {
			g.Agent.Phase3.SetReflectInterval(*req.ReflectInterval)
		}
		g.broadcastPhase3Control(change)
		g.sendJSON(w, map[string]interface{}{"success": true, "message": fmt.Sprintf("反思间隔已设为 %d 次任务", *req.ReflectInterval)})
		return
	}

	if req.ExploreInterval != nil && *req.ExploreInterval > 0 {
		change := fmt.Sprintf("explore_interval=%d", *req.ExploreInterval)
		if hasLocal {
			g.Agent.Phase3.SetExploreInterval(*req.ExploreInterval)
		}
		g.broadcastPhase3Control(change)
		g.sendJSON(w, map[string]interface{}{"success": true, "message": fmt.Sprintf("探索间隔已设为 %d 次任务", *req.ExploreInterval)})
		return
	}

	g.sendJSON(w, map[string]interface{}{"success": false, "error": "no valid control parameters"})
}

// broadcastPhase3Control 广播 Phase 3 控制指令到所有 Worker
func (g *OpcGateway) broadcastPhase3Control(change string) {
	// 通过 Hall 广播控制指令
	PostHallMessage("system", "gateway", "控制中心", "all", fmt.Sprintf("🔄 Phase 3 设置变更: %s", change))
}

// handlePhase3Page GET — Phase 3 监控页面
func (g *OpcGateway) handlePhase3Page(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(phase3PageHTML)
}

// ══════════════════════════════════════════════════════════════════════
// Phase 3 监控页面（内嵌 HTML）
// ══════════════════════════════════════════════════════════════════════

var phase3PageHTML = []byte(`<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🌌 Phase 3 自主进化监控</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:1200px;margin:0 auto}
h1{font-size:22px;color:#f7971e;margin-bottom:16px;display:flex;align-items:center;gap:10px}
h1 small{font-size:12px;color:#555;font-weight:normal}
.header{display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.06)}
.header .nav-links{display:flex;gap:8px;margin-left:auto}
.header .nav-links a{color:#666;text-decoration:none;font-size:12px;padding:4px 10px;border-radius:4px;transition:all 0.12s}
.header .nav-links a:hover{color:#f7971e;background:rgba(247,151,30,0.08)}
.controls{display:flex;gap:12px;align-items:center;margin-bottom:20px;flex-wrap:wrap}
.control-group{display:flex;gap:8px;align-items:center;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:8px 12px}
.control-group label{font-size:12px;color:#8b949e}
.control-group select,.control-group input{background:#161b22;border:1px solid #30363d;border-radius:4px;color:#c9d1d9;padding:4px 8px;font-size:13px}
.control-group button{background:#f7971e;border:none;border-radius:4px;color:#000;padding:4px 12px;font-size:12px;cursor:pointer;font-weight:600}
.control-group button:hover{background:#ffa726}
.control-group button.secondary{background:#30363d;color:#c9d1d9}
.control-group button.secondary:hover{background:#3d444d}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:20px}
.stat-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;text-align:center}
.stat-val{font-size:22px;font-weight:700;color:#f7971e}
.stat-label{font-size:11px;color:#8b949e;margin-top:2px}
.mode-badge{display:inline-block;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:600}
.mode-active{background:rgba(46,160,67,0.15);color:#3fb950;border:1px solid rgba(46,160,67,0.3)}
.mode-observe{background:rgba(210,153,34,0.15);color:#d29922;border:1px solid rgba(210,153,34,0.3)}
.event-log{background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden}
.event-log table{width:100%;border-collapse:collapse}
.event-log th{background:#21262d;padding:8px 10px;text-align:left;font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:0.5px}
.event-log td{padding:6px 10px;border-top:1px solid #21262d;font-size:12px}
.event-log tr:hover{background:rgba(255,255,255,0.02)}
.event-llm{color:#58a6ff;font-weight:600}
.event-no-llm{color:#555}
.source-tag{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600}
.source-self_learning{background:rgba(88,166,255,0.15);color:#58a6ff}
.source-innovation{background:rgba(247,151,30,0.15);color:#f7971e}
.loading{text-align:center;padding:40px;color:#555}
.error{color:#ef4444;text-align:center;padding:20px}
</style>
</head>
<body>
<div class="header">
  <h1>🌌 Phase 3 自主进化监控</h1>
  <span id="modeBadge" class="mode-badge mode-active">active</span>
  <div class="nav-links">
    <a href="/ai">🏛️ AI 大厅</a>
    <a href="/memory">🧠 记忆管理</a>
    <a href="/trigger">⚡ 触发引擎</a>
  </div>
</div>

<div class="controls">
  <div class="control-group">
    <label>模式</label>
    <select id="modeSelect">
      <option value="active">active — 正常执行</option>
      <option value="observe">observe — 仅观察</option>
    </select>
    <button onclick="setMode()">应用</button>
  </div>
  <div class="control-group">
    <label>反思间隔</label>
    <input type="number" id="reflectInterval" value="5" min="1" style="width:60px">
    <label style="font-size:11px">次任务</label>
    <button class="secondary" onclick="setReflect()">设置</button>
  </div>
  <div class="control-group">
    <label>探索间隔</label>
    <input type="number" id="exploreInterval" value="10" min="1" style="width:60px">
    <label style="font-size:11px">次任务</label>
    <button class="secondary" onclick="setExplore()">设置</button>
  </div>
  <div class="control-group" style="border-color:rgba(247,151,30,0.25)">
    <label>🎙️ 圆桌</label>
    <button id="rtBtn" onclick="toggleRoundTable()" style="background:#238636;border:none;border-radius:4px;color:#fff;padding:4px 12px;font-size:12px;cursor:pointer;font-weight:600">启动</button>
    <label style="font-size:11px">间隔</label>
    <input type="number" id="rtInterval" value="300" min="30" style="width:60px;background:#161b22;border:1px solid #30363d;border-radius:4px;color:#c9d1d9;padding:4px 8px;font-size:13px">
    <label style="font-size:11px">秒</label>
    <button class="secondary" onclick="setRtInterval()">设</button>
    <button class="secondary" onclick="throwNow()">抛话题</button>
  </div>
</div>

<div class="stats" id="stats">
  <div class="stat-card"><div class="stat-val" id="statTotal">-</div><div class="stat-label">总任务</div></div>
  <div class="stat-card"><div class="stat-val" id="statSuccess">-</div><div class="stat-label">成功率</div></div>
  <div class="stat-card"><div class="stat-val" id="statKnowledge">-</div><div class="stat-label">知识提取</div></div>
  <div class="stat-card"><div class="stat-val" id="statExplore">-</div><div class="stat-label">探索次数</div></div>
  <div class="stat-card"><div class="stat-val" id="statDiscoveries">-</div><div class="stat-label">发现数量</div></div>
  <div class="stat-card"><div class="stat-val" id="statEvents">-</div><div class="stat-label">事件数</div></div>
</div>

<div class="event-log" id="eventLog">
  <table>
    <thead><tr><th>时间</th><th>来源</th><th>操作</th><th>详情</th><th>LLM</th></tr></thead>
    <tbody id="eventBody"></tbody>
  </table>
</div>

<script>
function loadEvents() {
  fetch('/api/v1/galaxy/phase3/events?limit=50').then(r=>r.json()).then(d=>{
    if(!d.success)return;
    const evts = d.data || [];
    document.getElementById('statEvents').textContent = d.total || evts.length;
    const tbody = document.getElementById('eventBody');
    tbody.innerHTML = evts.reverse().map(e => {
      const llmIcon = e.llm_called ? '🧠' : '—';
      const llmClass = e.llm_called ? 'event-llm' : 'event-no-llm';
      const sourceClass = 'source-' + (e.source || 'unknown');
      return '<tr>' +
        '<td style="color:#8b949e;font-size:11px">' + (e.time || '') + '</td>' +
        '<td><span class="source-tag ' + sourceClass + '">' + (e.source || '') + '</span></td>' +
        '<td>' + (e.action || '') + '</td>' +
        '<td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + (e.detail || '') + '</td>' +
        '<td class="' + llmClass + '">' + llmIcon + '</td>' +
        '</tr>';
    }).join('');
  }).catch(()=>{});
}

function loadStats() {
  fetch('/api/v1/galaxy/phase3/stats').then(r=>r.json()).then(d=>{
    if(!d.success)return;
    const s = d.data || {};
    const self = s.self_learning || {};
    const innov = s.innovation || {};
    document.getElementById('statTotal').textContent = self.total_tasks || 0;
    document.getElementById('statSuccess').textContent = self.success_rate || '0%';
    document.getElementById('statKnowledge').textContent = self.knowledge_count || 0;
    document.getElementById('statExplore').textContent = innov.exploration_count || 0;
    document.getElementById('statDiscoveries').textContent = innov.discovery_count || 0;
  }).catch(()=>{});
}

function setMode() {
  const mode = document.getElementById('modeSelect').value;
  fetch('/api/v1/galaxy/phase3/control', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({mode:mode})
  }).then(r=>r.json()).then(d=>{
    if(d.success){
      document.getElementById('modeBadge').textContent = mode;
      document.getElementById('modeBadge').className = 'mode-badge mode-' + mode;
    }
  }).catch(()=>{});
}

function setReflect() {
  const n = parseInt(document.getElementById('reflectInterval').value);
  if(n<1)return;
  fetch('/api/v1/galaxy/phase3/control', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({reflect_interval:n})
  }).then(r=>r.json()).then(d=>{
    if(d.success) loadEvents();
  }).catch(()=>{});
}

function setExplore() {
  const n = parseInt(document.getElementById('exploreInterval').value);
  if(n<1)return;
  fetch('/api/v1/galaxy/phase3/control', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({explore_interval:n})
  }).then(r=>r.json()).then(d=>{
    if(d.success) loadEvents();
  }).catch(()=>{});
}

// ── 圆桌讨论 ──
let rtRunning = false;

function loadRtStatus() {
  fetch('/api/v1/hall/roundtable/status').then(r=>r.json()).then(d=>{
    if(!d.success)return;
    rtRunning = d.data.running;
    const btn = document.getElementById('rtBtn');
    btn.textContent = rtRunning ? '🟢 运行中' : '启动';
    btn.style.background = rtRunning ? '#da3633' : '#238636';
    if(d.data.interval_sec) document.getElementById('rtInterval').value = d.data.interval_sec;
  }).catch(()=>{});
}

function toggleRoundTable() {
  const ep = rtRunning ? '/api/v1/hall/roundtable/stop' : '/api/v1/hall/roundtable/start';
  fetch(ep, {method:'POST'}).then(r=>r.json()).then(d=>{
    if(d.success) loadRtStatus();
  }).catch(()=>{});
}

function setRtInterval() {
  const n = parseInt(document.getElementById('rtInterval').value);
  if(n<10)return;
  fetch('/api/v1/hall/roundtable/interval', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({interval:n})
  }).then(r=>r.json()).then(()=>{}).catch(()=>{});
}

function throwNow() {
  fetch('/api/v1/hall/roundtable/now', {method:'POST'})
    .then(r=>r.json()).then(()=>{}).catch(()=>{});
}

// Auto-refresh
loadEvents(); loadStats(); loadRtStatus();
setInterval(loadEvents, 3000);
setInterval(loadStats, 5000);
setInterval(loadRtStatus, 3000);
</script>
</body>
</html>`)
