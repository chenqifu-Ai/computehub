package gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/computehub/opc/src/composer"
	"github.com/computehub/opc/src/kernel"
)

// chunkedSize 大结果分块阈值 (1MB)
const chunkedSize = 1 * 1024 * 1024

func (g *OpcGateway) handleTaskSubmit(w http.ResponseWriter, r *http.Request) {
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

	var task kernel.TaskSubmit
	if err := json.Unmarshal(body, &task); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	// Support node, node_id, and assigned_node — map everything to AssignedNode
	if task.Node != "" {
		if task.AssignedNode == "" {
			task.AssignedNode = task.Node
		}
		if task.NodeID == "" {
			task.NodeID = task.Node
		}
	}
	if task.NodeID != "" && task.AssignedNode == "" {
		task.AssignedNode = task.NodeID
	}
	if task.AssignedNode != "" && task.NodeID == "" {
		task.NodeID = task.AssignedNode
	}

	if task.Command == "" && task.Payload != "" {
		task.Command = task.Payload
	}

	task.SubmittedAt = time.Now()
	if task.Priority == 0 {
		task.Priority = 5
	}
	if task.SourceType == "" {
		task.SourceType = "api"
	}
	if task.SubmittedBy == "" {
		task.SubmittedBy = "gateway"
	}
	if task.MaxRetries == 0 {
		task.MaxRetries = 3
	}

	if g.Metrics != nil {
		g.MetricsCollector.RecordTaskSubmission()
	}

	if g.TaskTracker != nil {
		g.TaskTracker.CreateTask(task.TaskID, task.AssignedNode)
		g.TaskTracker.UpdateStage(task.TaskID, StageQueued, "submitted",
			fmt.Sprintf("任务已提交: %s", task.Command))
	}

	if g.Composer != nil && !isSimpleTask(task.Command) {
		logWithTimestamp("[Composer] 🧠 Complex task detected, decomposing: %s", task.Command)
		go func(cmd string, tid string) {
			result, err := g.Composer.Run(composer.TaskComposerInput{
				TaskID:       tid,
				OriginalTask: cmd,
			})
			if err != nil {
				logWithTimestamp("[Composer] ❌ Decompose failed: %v", err)
			} else {
				successCount := 0
				for _, r := range result.Results {
					if r.Success {
						successCount++
					}
				}
				logWithTimestamp("[Composer] ✅ Task %s: %d subtasks, %d success, final=%d chars",
					tid, len(result.Subtasks), successCount, len(result.FinalResult))
			}
		}(task.Command, task.TaskID)
	} else if g.Composer != nil {
		logWithTimestamp("[Composer] ➡️ Simple command, direct dispatch: %s", task.Command)
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionTaskSubmit, &task)
	resp := <-respChan

	if resp.Success && task.AssignedNode != "" && g.wsHub != nil {
		pollItem := &TaskPollItem{
			TaskID:     task.TaskID,
			Command:    task.Command,
			Timeout:    task.Timeout,
			Priority:   task.Priority,
			NodeID:     task.AssignedNode,
			SourceType: task.SourceType,
		}
		if g.wsHub.PushTask(task.AssignedNode, pollItem) {
			logWithTimestamp("[WS Push] 📡 任务 %s 已推送到 %s", task.TaskID, task.AssignedNode)
		} else {
			logWithTimestamp("[WS Push] ⚠️ 任务 %s WS 推送失败 (%s 不在线)，等待 HTTP poll", task.TaskID, task.AssignedNode)
		}
	}

	g.auditLog(task.NodeID, AuditTaskSubmit, "task", task.TaskID,
		fmt.Sprintf("cmd=%s priority=%d", task.Command, task.Priority), resp.Success)

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleTaskResult(w http.ResponseWriter, r *http.Request) {
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

	var result kernel.TaskResult
	if err := json.Unmarshal(body, &result); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	totalSize := len(result.Stdout) + len(result.Stderr)
	if totalSize > chunkedSize {
		logWithTimestamp("[TaskResult] ⚠️ 结果 %d bytes，建议使用 POST /api/v1/tasks/progress 流式获取", totalSize)
	}

	if g.Metrics != nil {
		duration, _ := time.ParseDuration(result.Duration)
		g.MetricsCollector.RecordTaskCompletion(result.Success, duration.Seconds())
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionTaskResult, &result)
	resp := <-respChan

	if g.TaskTracker != nil {
		if result.Success {
			g.TaskTracker.CompleteTask(result.TaskID, result.Stdout)
		} else {
			g.TaskTracker.FailTask(result.TaskID, result.Stderr)
		}
	}

	g.auditLog(result.ExecutedOn, AuditTaskSubmit, "task", result.TaskID,
		fmt.Sprintf("success=%v duration=%s", result.Success, result.Duration), resp.Success)

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleTaskList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	tasks := make(map[string][]map[string]interface{})

	for _, node := range nodes {
		tasks[node.Register.NodeID] = []map[string]interface{}{}
		ip := node.Register.IPAddress
		if ip == "" {
			ip = "127.0.0.1"
		}
		for taskID, ts := range node.Tasks {
			createdAt := ""
			if !ts.Created.IsZero() {
				createdAt = ts.Created.Format("15:04:05")
			} else if !ts.Task.SubmittedAt.IsZero() {
				createdAt = ts.Task.SubmittedAt.Format("15:04:05")
			}
			tasks[node.Register.NodeID] = append(tasks[node.Register.NodeID], map[string]interface{}{
				"task_id":      taskID,
				"status":       ts.Status,
				"command":      ts.Task.Command,
				"source_type":  ts.Task.SourceType,
				"submitted_by": ts.Task.SubmittedBy,
				"priority":     ts.Task.Priority,
				"submitted_at": createdAt,
				"node_ip":      ip,
			})
		}
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    tasks,
	})
}

func (g *OpcGateway) handleTaskCancel(w http.ResponseWriter, r *http.Request) {
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
		TaskID string `json:"task_id"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.TaskID == "" {
		g.sendResponse(w, Response{Success: false, Error: "task_id is required"})
		return
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionTaskCancel, req.TaskID)
	resp := <-respChan

	errStr := ""
	if resp.Error != nil {
		errStr = resp.Error.Error()
	}

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    errStr,
		Duration: resp.Duration,
	})
}
