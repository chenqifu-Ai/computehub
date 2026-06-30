// Package workercmd — Worker 本地 Kernel 实现
// 让 Worker Agent 的 execShell 不经过 Gateway，直接在本地执行 shell 命令
// v2: 支持远程节点执行—目标节点==自己→本地执行，目标节点==其他节点→通过 Gateway HTTP 调度
package workercmd

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/computehub/opc/src/agent"
	"github.com/computehub/opc/src/executil"
	"github.com/computehub/opc/src/kernel"
)

// WorkerKernelProvider 本地 Kernel 实现
// 让 Agent 在 Worker 上自包含地执行 shell 命令
type WorkerKernelProvider struct {
	mu         sync.RWMutex
	nodeID     string
	gatewayURL string
	httpClient *http.Client
	nodeMgr    *kernel.NodeManager
	localTasks map[string]*localTaskState
}

type localTaskState struct {
	TaskID    string
	Command   string
	Status    string // pending → running → completed / failed
	Stdout    string
	Stderr    string
	ExitCode  int
	StartedAt time.Time
	DoneAt    time.Time
}

func NewWorkerKernelProvider(nodeID, gatewayURL string, gpuType string, cpuCores int, memoryGB int) *WorkerKernelProvider {
	nm := kernel.NewNodeManager(10)

	// 注册本地节点
	nm.RegisterNode(&kernel.NodeRegister{
		NodeID:   nodeID,
		Platform: runtime.GOOS + "/" + runtime.GOARCH,
		GPUType:  gpuType,
		CPUCores: cpuCores,
		MemoryGB: float64(memoryGB),
		Status:   "online",
	})

	wp := &WorkerKernelProvider{
		nodeID:     nodeID,
		gatewayURL: strings.TrimRight(gatewayURL, "/"),
		httpClient: &http.Client{Timeout: 120 * time.Second},
		nodeMgr:    nm,
		localTasks: make(map[string]*localTaskState),
	}
	return wp
}

// DispatchExtended 处理 Agent 发来的动作
// - 任务目标节点==本节点 → 本地执行
// - 任务目标节点==其他节点 → 通过 Gateway HTTP 提交
func (wp *WorkerKernelProvider) DispatchExtended(traceID string, action string, data interface{}) chan kernel.Response {
	respChan := make(chan kernel.Response, 1)

	switch action {
	case kernel.ActionTaskSubmit:
		task, ok := data.(*kernel.TaskSubmit)
		if !ok {
			respChan <- kernel.Response{Success: false, Error: fmt.Errorf("WorkerKernelProvider: invalid task type")}
			return respChan
		}
		// 判断目标节点
		targetNode := task.AssignedNode
		if targetNode == "" {
			targetNode = task.NodeID
		}
		// 本节点 → 本地执行
		if targetNode == "" || targetNode == wp.nodeID {
			go wp.executeLocal(task, traceID, respChan)
		} else {
			// 其他节点 → 通过 Gateway 调度
			go wp.executeRemote(task, traceID, respChan)
		}
	default:
		respChan <- kernel.Response{
			Success: false,
			Error:   fmt.Errorf("WorkerKernelProvider: unknown action %s", action),
		}
	}
	return respChan
}

// GetNodeManager 返回 NodeManager（Agent execShell 用 ListNodes 轮询任务结果）
func (wp *WorkerKernelProvider) GetNodeManager() *kernel.NodeManager {
	return wp.nodeMgr
}

// SyncNodes 从 Gateway 同步所有在线节点到本地 NodeManager。
// 让 Agent 的 buildSystemPrompt 能列举所有可用节点，支持跨节点调度。
func (wp *WorkerKernelProvider) SyncNodes() {
	resp, err := wp.httpClient.Get(wp.gatewayURL + "/api/v1/nodes/list")
	if err != nil {
		fmt.Printf(" [SyncNodes] ❌ HTTP 请求失败: %v\n", err)
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf(" [SyncNodes] ❌ 读取响应失败: %v\n", err)
		return
	}

	var wrapper struct {
		Success bool                     `json:"success"`
		Data    []map[string]interface{} `json:"data"`
	}
	if err := json.Unmarshal(body, &wrapper); err != nil {
		fmt.Printf(" [SyncNodes] ❌ JSON 解析失败: %v\n", err)
		return
	}
	if !wrapper.Success {
		fmt.Printf(" [SyncNodes] ❌ API 返回失败\n")
		return
	}

	registered := 0
	for _, n := range wrapper.Data {
		nodeID, _ := n["node_id"].(string)
		if nodeID == "" || nodeID == wp.nodeID {
			continue // 跳过自己（已注册）
		}
		gpuType, _ := n["gpu_type"].(string)
		if gpuType == "" {
			gpuType = "CPU"
		}
		region, _ := n["region"].(string)
		status, _ := n["status"].(string)
		platform, _ := n["platform"].(string)
		nodeType, _ := n["node_type"].(string)

		// 注册到本地 NodeManager（upsert — 已存在会更新）
		wp.nodeMgr.RegisterNode(&kernel.NodeRegister{
			NodeID:   nodeID,
			NodeType: nodeType,
			Platform: platform,
			GPUType:  gpuType,
			Region:   region,
			Status:   status,
			CPUCores: 4,
			MemoryGB: 8.0,
		})
		registered++
	}

	if registered > 0 {
		fmt.Printf(" [SyncNodes] ✅ 同步 %d 个远程节点\n", registered)
	}
}

// StartSyncLoop 启动节点同步循环（每 30s 同步一次）。
// 确保 Agent 能始终看到完整的集群节点列表（包括延迟注册的节点）。
func (wp *WorkerKernelProvider) StartSyncLoop() {
	// 第一次同步：延迟 3 秒，给其他节点时间注册
	time.Sleep(3 * time.Second)
	wp.SyncNodes()

	// 循环同步：每 30 秒
	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			wp.SyncNodes()
		}
	}()
}

// ═══════════════════════════════════════════
// Gateway 结果回写（修复：任务执行后不通知 Gateway → 槽位永久锁死）
// ═══════════════════════════════════════════

// submitTaskResult POSTs 任务结果到 Gateway /api/v1/tasks/result
// 这是执行完任务后必须调用的步骤，否则 Gateway 的 NodeMgr 永远停留在 "running"
func (wp *WorkerKernelProvider) submitTaskResult(result *kernel.TaskResult) {
	body, _ := json.Marshal(result)
	resp, err := wp.httpClient.Post(
		wp.gatewayURL+"/api/v1/tasks/result",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		fmt.Printf(" [WorkerKernelProvider] ❌ 结果回传失败: %v\n", err)
		return
	}
	resp.Body.Close()
}

// ═══════════════════════════════════════════
// 本地执行
// ═══════════════════════════════════════════

func (wp *WorkerKernelProvider) executeLocal(task *kernel.TaskSubmit, traceID string, respChan chan kernel.Response) {
	lt := &localTaskState{
		TaskID:    task.TaskID,
		Command:   task.Command,
		Status:    "running",
		StartedAt: time.Now(),
	}

	wp.mu.Lock()
	wp.localTasks[task.TaskID] = lt
	wp.mu.Unlock()

	// 确认任务已接收
	respChan <- kernel.Response{Success: true, Data: map[string]string{"task_id": task.TaskID}}

	// ── 安全检查：拦截 SSH 自连接攻击 ──
	if err := agent.DetectSSHSelfAttack(task.Command); err != nil {
		lt.Status = "failed"
		lt.Stderr = fmt.Sprintf("❌ 安全拦截: %v", err)
		tr := &kernel.TaskResult{
			TaskID:   task.TaskID,
			Stdout:   "",
			Stderr:   lt.Stderr,
			ExitCode: -1,
			Duration: "0s",
		}
		wp.nodeMgr.CompleteTask(task.TaskID, wp.nodeID, tr)
		wp.submitTaskResult(tr) // ← 修复：通知 Gateway
		return
	}

	// 执行命令 — 平台差异化 shell
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(task.Timeout)*time.Second)
	defer cancel()

	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		// Windows: 直接用 powershell，不走 cmd.exe（避免 Access denied）
		cmd = exec.CommandContext(ctx, "powershell", "-Command", task.Command)
	} else {
		// Linux/Mac: 用 sh -c（兼容 Termux 安全 syscall）
		shPath := executil.SafeLookPath("sh")
		cmd = exec.CommandContext(ctx, shPath, "-c", task.Command)
	}
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	startTime := time.Now()
	err := cmd.Run()
	elapsed := time.Since(startTime)

	lt.Stdout = strings.TrimSpace(stdout.String())
	lt.Stderr = strings.TrimSpace(stderr.String())
	lt.DoneAt = time.Now()

	exitCode := 0
	status := "completed"

	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else if ctx.Err() == context.DeadlineExceeded {
			exitCode = -1
			status = "failed"
		} else {
			exitCode = -1
			status = "failed"
		}
	}

	lt.ExitCode = exitCode
	lt.Status = status

	// 更新本地 NodeManager + 通知 Gateway
	tr := &kernel.TaskResult{
		TaskID:     task.TaskID,
		ExecutedOn: wp.nodeID,
		Stdout:     lt.Stdout,
		Stderr:     lt.Stderr,
		ExitCode:   exitCode,
		Duration:   elapsed.Round(time.Millisecond).String(),
		Success:    status == "completed" && exitCode == 0,
	}
	wp.nodeMgr.CompleteTask(task.TaskID, wp.nodeID, tr)
	wp.submitTaskResult(tr) // ← 修复：通知 Gateway
}

// ═══════════════════════════════════════════
// 远程执行（通过 Gateway HTTP 调度）
// ═══════════════════════════════════════════

func (wp *WorkerKernelProvider) executeRemote(task *kernel.TaskSubmit, traceID string, respChan chan kernel.Response) {
	taskID := task.TaskID
	if taskID == "" {
		taskID = fmt.Sprintf("agent-%d", time.Now().UnixNano())
		task.TaskID = taskID
	}

	// 在本地 NodeManager 注册一个任务占位（running 态，让 Agent 能轮询）
	wp.nodeMgr.SubmitTask(&kernel.TaskSubmit{
		TaskID:       taskID,
		Command:      task.Command,
		AssignedNode: task.AssignedNode,
		NodeID:       task.NodeID,
	})

	// 确认任务已接收
	respChan <- kernel.Response{Success: true, Data: map[string]string{"task_id": taskID}}

	// 1. POST 任务到 Gateway
	submitBody, _ := json.Marshal(task)
	resp, err := wp.httpClient.Post(wp.gatewayURL+"/api/v1/tasks/submit", "application/json", bytes.NewReader(submitBody))
	if err != nil {
		tr := &kernel.TaskResult{
			TaskID:   taskID,
			Stdout:   "",
			Stderr:   fmt.Sprintf("Gateway 连接失败: %v", err),
			ExitCode: -1,
			Duration: "0s",
		}
		wp.nodeMgr.CompleteTask(taskID, wp.nodeID, tr)
		wp.submitTaskResult(tr) // ← 修复：通知 Gateway
		return
	}
	resp.Body.Close()

	// 2. 轮询任务完成（每 500ms，最多超时 +30s）
	deadline := time.Now().Add(time.Duration(task.Timeout+30) * time.Second)
	for time.Now().Before(deadline) {
		time.Sleep(500 * time.Millisecond)

		detailURL := fmt.Sprintf("%s/api/v1/tasks/detail?task_id=%s&node_id=%s",
			wp.gatewayURL, taskID, task.AssignedNode)
		resp, err := wp.httpClient.Get(detailURL)
		if err != nil {
			continue
		}

		var wrapper struct {
			Success bool                   `json:"success"`
			Data    map[string]interface{} `json:"data"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&wrapper); err != nil {
			resp.Body.Close()
			continue
		}
		resp.Body.Close()

		if !wrapper.Success {
			continue
		}

		status, _ := wrapper.Data["status"].(string)
		switch status {
		case "completed", "failed", "cancelled":
			stdout, _ := wrapper.Data["stdout"].(string)
			stderr, _ := wrapper.Data["stderr"].(string)
			exitCode := 0
			if ec, ok := wrapper.Data["exit_code"].(float64); ok {
				exitCode = int(ec)
			}
			duration, _ := wrapper.Data["duration"].(string)
			success := status == "completed" && exitCode == 0

			tr := &kernel.TaskResult{
				TaskID:     taskID,
				ExecutedOn: task.AssignedNode,
				Stdout:     stdout,
				Stderr:     stderr,
				ExitCode:   exitCode,
				Duration:   duration,
				Success:    success,
			}
			wp.nodeMgr.CompleteTask(taskID, task.AssignedNode, tr)
			wp.submitTaskResult(tr) // ← 修复：通知 Gateway
			return
		}
	}

	// 超时
	tr := &kernel.TaskResult{
		TaskID:     taskID,
		ExecutedOn: task.AssignedNode,
		Stderr:     fmt.Sprintf("任务超时 (%ds内未完成)", task.Timeout+30),
		ExitCode:   -1,
		Duration:   (time.Duration(task.Timeout+30) * time.Second).Round(time.Second).String(),
	}
	wp.nodeMgr.CompleteTask(taskID, task.AssignedNode, tr)
	wp.submitTaskResult(tr) // ← 修复：通知 Gateway
}