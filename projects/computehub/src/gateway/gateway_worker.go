package gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// handleTaskPoll — Worker 轮询认领待处理任务
// Worker 调用此接口获取一个 pending 任务并认领为自己的
func (g *OpcGateway) handleTaskPoll(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	var req struct {
		NodeID      string   `json:"node_id"`
		GPUType     string   `json:"gpu_type,omitempty"`
		Region      string   `json:"region,omitempty"`
		RunningTaskCount int  `json:"running_task_count,omitempty"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.NodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required"})
		return
	}

	// Search the kernel's priority queue for pending tasks
	// First: check if any node has a "pending" task assigned to this Worker
	pendingTask := g.findPendingTaskForNode(req.NodeID)

	if pendingTask == nil {
		// If no task found, respond with no task
		g.sendResponse(w, Response{
			Success: true,
			Data:    map[string]interface{}{"task": nil, "message": "no pending tasks"},
		})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"task": pendingTask,
		},
	})
}

// findPendingTaskForNode 查找该 Worker 可认领的待处理任务
// 优先查找已经分配给该节点的 pending 任务，再查找队列中未分配的
func (g *OpcGateway) findPendingTaskForNode(nodeID string) *TaskPollItem {
	// Phase 1: 检查该节点上是否有 pending 状态的任务
	nodes := g.Kernel.NodeMgr.ListNodes()
	for _, state := range nodes {
		if state.Register.NodeID != nodeID {
			continue
		}
		for taskID, ts := range state.Tasks {
			if ts.Status == "pending" {
				ts.Status = "running"
				state.Metrics.ActiveTasks++
				return &TaskPollItem{
					TaskID:    taskID,
					Command:   ts.Task.Command,
					Timeout:   ts.Task.Timeout,
					Priority:  ts.Task.Priority,
					NodeID:    nodeID,
					SourceType: ts.Task.SourceType,
				}
			}
		}
	}

	// Phase 2: 检查优先级队列中是否有等待的任务（全局未分配）
	// 需要访问 NodeManager 内部的优先级队列
	task := g.Kernel.NodeMgr.NextPendingTask()
	if task != nil {
		// Claim this task for the requesting node
		err := g.Kernel.NodeMgr.AssignTaskToNode(task.TaskID, nodeID)
		if err == nil {
			return &TaskPollItem{
				TaskID:    task.TaskID,
				Command:   task.Command,
				Timeout:   task.Timeout,
				Priority:  task.Priority,
				NodeID:    nodeID,
				SourceType: task.SourceType,
			}
		}
	}

	return nil
}

// TaskPollItem is what the Worker receives on poll
type TaskPollItem struct {
	TaskID     string `json:"task_id"`
	Command    string `json:"command"`
	Timeout    int    `json:"timeout"`
	Priority   int    `json:"priority"`
	NodeID     string `json:"node_id,omitempty"`
	SourceType string `json:"source_type,omitempty"`
}

// handleTaskDetailWithNode — 增强版任务详情，支持按节点过滤
func (g *OpcGateway) handleTaskDetail(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	taskID := r.URL.Query().Get("task_id")
	nodeID := r.URL.Query().Get("node_id")

	if taskID == "" {
		g.sendResponse(w, Response{Success: false, Error: "task_id is required"})
		return
	}

	// Search all nodes for this task
	nodes := g.Kernel.NodeMgr.ListNodes()
	for _, state := range nodes {
		// If node_id filter is provided, only check that node
		if nodeID != "" && state.Register.NodeID != nodeID {
			continue
		}
		if ts, exists := state.Tasks[taskID]; exists {
			result := map[string]interface{}{
				"task_id":     taskID,
				"node_id":     state.Register.NodeID,
				"status":      ts.Status,
				"command":     ts.Task.Command,
				"priority":    ts.Task.Priority,
				"timeout":     ts.Task.Timeout,
				"source_type": ts.Task.SourceType,
			}
			if ts.Result != nil {
				result["exit_code"] = ts.Result.ExitCode
				result["stdout"] = ts.Result.Stdout
				result["stderr"] = ts.Result.Stderr
				result["duration"] = ts.Result.Duration
				result["success"] = ts.Result.Success
				result["verified"] = ts.Result.Verified
			}
			g.sendResponse(w, Response{Success: true, Data: result})
			return
		}
	}

	g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("task %s not found", taskID)})
}
