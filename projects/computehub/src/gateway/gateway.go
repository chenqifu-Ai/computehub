package gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/computehub/opc/src/executor"
	"github.com/computehub/opc/src/gene"
	"github.com/computehub/opc/src/kernel"
	"github.com/computehub/opc/src/pure"
)

// logWithTimestamp 添加时间戳的日志函数
func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
}

// Request represents the incoming API call (legacy)
type Request struct {
	ID      string `json:"id"`
	Command string `json:"command"`
}

// APIRequest represents a compute hub API call
type APIRequest struct {
	ID      string        `json:"id"`
	Action  string        `json:"action"`
	Payload json.RawMessage `json:"payload,omitempty"`
}

// Response represents the physical system response
type Response struct {
	ID       string      `json:"id"`
	Success  bool        `json:"success"`
	Data     interface{} `json:"data,omitempty"`
	Error    string      `json:"error,omitempty"`
	Duration string      `json:"duration,omitempty"`
	Verified bool        `json:"verified"`
}

type SystemStatus struct {
	Kernel       KernelStatus     `json:"kernel"`
	Pipeline     PipelineStatus   `json:"pipeline"`
	Executor     ExecutorStatus   `json:"executor"`
	GeneStore    GeneStoreStatus  `json:"geneStore"`
	NodeManager  NodeManagerStatus `json:"nodeManager"`
	Uptime       string           `json:"uptime"`
}

type KernelStatus struct {
	Status          string `json:"status"`
	ScheduleLatency string `json:"schedule_latency"`
	QueueDepth      int    `json:"queue_depth"`
}

type PipelineStatus struct {
	Status        string `json:"status"`
	Interceptions int    `json:"interceptions"`
	PureLatency   string `json:"pure_latency"`
}

type ExecutorStatus struct {
	Status           string  `json:"status"`
	VerificationRate float64 `json:"verification_rate"`
	SandboxPath      string  `json:"sandbox_path"`
}

type GeneStoreStatus struct {
	Size       int    `json:"size"`
	RecallRate float64 `json:"recall_rate"`
}

type NodeManagerStatus struct {
	TotalNodes   int               `json:"total_nodes"`
	OnlineNodes  int               `json:"online_nodes"`
	TotalTasks   int               `json:"total_tasks"`
	ActiveTasks  int               `json:"active_tasks"`
	Nodes        []NodeStatus      `json:"nodes"`
}

type NodeStatus struct {
	NodeID       string    `json:"node_id"`
	Region       string    `json:"region"`
	GPUType      string    `json:"gpu_type"`
	Status       string    `json:"status"`
	ActiveTasks  int       `json:"active_tasks"`
	CPUUtil      float64   `json:"cpu_utilization"`
	GPUMetrics   []GPUMetricSummary `json:"gpu_metrics,omitempty"`
}

type GPUMetricSummary struct {
	Utilization float64 `json:"utilization"`
	Temperature float64 `json:"temperature"`
	MemoryUsed  float64 `json:"memory_used_gb"`
}

// OpcGateway provides a REST API for the ComputeHub System
type OpcGateway struct {
	Kernel    *kernel.ExtendedKernel
	Pipeline  *pure.PurePipeline
	Executor  *executor.OpcExecutor
	GeneStore *gene.GeneStore
	startTime time.Time
	mu        sync.Mutex
}

func NewOpcGateway(port int, config *GatewayConfig) *OpcGateway {
	// Use config values or fall back to defaults
	geneStorePath := "./genes.json"
	sandboxPath := "/tmp/opc-sandbox"
	bufferSize := 100
	maxStates := 1000
	maxNodes := 50

	if config != nil {
		if config.GeneStorePath != "" {
			geneStorePath = config.GeneStorePath
		}
		if config.SandboxPath != "" {
			sandboxPath = config.SandboxPath
		}
		if config.BufferSize > 0 {
			bufferSize = config.BufferSize
		}
		if config.MaxStates > 0 {
			maxStates = config.MaxStates
		}
	}

	// Initialize Internal Components
	p := pure.NewPurePipeline()
	p.AddFilter(&pure.SyntaxFilter{})
	p.AddFilter(&pure.SemanticFilter{AllowedActions: []string{"EXEC", "PING", "STATUS", "NODE_REGISTER", "TASK_SUBMIT", "NODE_HEARTBEAT", "TASK_RESULT", "GPU_MONITOR"}})
	p.AddFilter(&pure.BoundaryFilter{Blacklist: []string{"/etc/passwd", "/root/.ssh"}})
	p.AddFilter(&pure.ContextFilter{DeviceFingerprint: "OPC-GATEWAY-API"})

	kernelObj := kernel.NewExtendedKernel(bufferSize, maxStates, maxNodes)

	ex := executor.NewOpcExecutor(sandboxPath)
	gs := gene.NewGeneStore(geneStorePath)

	return &OpcGateway{
		Kernel:    kernelObj,
		Pipeline:  p,
		Executor:  ex,
		GeneStore: gs,
		startTime: time.Now(),
	}
}

// GatewayConfig holds configuration for gateway components
type GatewayConfig struct {
	GeneStorePath string
	SandboxPath   string
	BufferSize    int
	MaxStates     int
	MaxNodes      int
}

func (g *OpcGateway) Serve(port int) {
	// Legacy endpoints (backward compatible)
	http.HandleFunc("/api/dispatch", g.handleDispatch)
	http.HandleFunc("/api/health", g.handleHealth)
	http.HandleFunc("/api/status", g.handleStatus)

	// ComputeHub API endpoints
	http.HandleFunc("/api/v1/nodes/register", g.handleNodeRegister)
	http.HandleFunc("/api/v1/nodes/heartbeat", g.handleNodeHeartbeat)
	http.HandleFunc("/api/v1/nodes/list", g.handleNodeList)
	http.HandleFunc("/api/v1/nodes/metrics", g.handleNodeMetrics)
	http.HandleFunc("/api/v1/tasks/submit", g.handleTaskSubmit)
	http.HandleFunc("/api/v1/tasks/result", g.handleTaskResult)
	http.HandleFunc("/api/v1/tasks/list", g.handleTaskList)

	logWithTimestamp("🌐 ComputeHub Gateway listening on :%d", port)
	if err := http.ListenAndServe(fmt.Sprintf(":%d", port), nil); err != nil {
		logWithTimestamp("Fatal Gateway Error: %v", err)
	}
}

// ServeHTTP implements http.Handler for test integration
func (g *OpcGateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	switch r.URL.Path {
	case "/api/dispatch":
		g.handleDispatch(w, r)
	case "/api/health":
		g.handleHealth(w, r)
	case "/api/status":
		g.handleStatus(w, r)
	case "/api/v1/nodes/register":
		g.handleNodeRegister(w, r)
	case "/api/v1/nodes/heartbeat":
		g.handleNodeHeartbeat(w, r)
	case "/api/v1/nodes/list":
		g.handleNodeList(w, r)
	case "/api/v1/nodes/metrics":
		g.handleNodeMetrics(w, r)
	case "/api/v1/tasks/submit":
		g.handleTaskSubmit(w, r)
	case "/api/v1/tasks/result":
		g.handleTaskResult(w, r)
	case "/api/v1/tasks/list":
		g.handleTaskList(w, r)
	default:
		http.NotFound(w, r)
	}
}

// ==================== Legacy Endpoints ====================

func (g *OpcGateway) handleDispatch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var req Request
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Invalid JSON request"})
		return
	}

	// --- THE PHYSICAL LOOP (API VERSION) ---

	// 1. Purification
	cleaned, err := g.Pipeline.Process(req.Command)
	if err != nil {
		g.sendResponse(w, Response{ID: req.ID, Success: false, Error: fmt.Sprintf("PureLayer Blocked: %v", err)})
		return
	}

	// 2. Gene Recall
	finalCmd := cleaned.(string)
	if replacement, found := g.GeneStore.Recall(finalCmd); found {
		finalCmd = replacement
	}

	// 3. Legacy Kernel Dispatch
	action := "UNKNOWN"
	if strings.Contains(strings.ToUpper(finalCmd), "PING") {
		action = "PING"
	} else if strings.Contains(strings.ToUpper(finalCmd), "EXEC") {
		action = "EXEC"
	} else if strings.Contains(strings.ToUpper(finalCmd), "STATUS") {
		action = "STATUS"
	}

	// Handle PING and STATUS inline (no queue/goroutine dependency)
	var kResp kernel.Response
	if action == "PING" {
		kResp = kernel.Response{Success: true, Data: "PONG"}
	} else if action == "STATUS" {
		kResp = kernel.Response{Success: true, Data: "System Healthy | Kernel: Deterministic | Memory: Stable"}
	} else {
		// For EXEC, use the embedded OpcKernel dispatch (Start goroutine handles it)
		respChan := g.Kernel.OpcKernel.Dispatch(req.ID, action, finalCmd)
		kResp = <-respChan
	}

	// 4. Physical Execution (if EXEC)
	if action == "EXEC" {
		actualCmd := strings.TrimPrefix(finalCmd, "[OPC-GATEWAY-API] EXEC ")
		actualCmd = strings.TrimPrefix(actualCmd, "EXEC ")

		validator := func(res executor.ExecutionResult) bool {
			return res.ExitCode == 0
		}

		res, verified := g.Executor.VerifyAndLearn(actualCmd, validator)
		g.sendResponse(w, Response{
			ID:       req.ID,
			Success:  verified,
			Data:     res.Stdout,
			Duration: res.Duration.String(),
			Verified: verified,
		})
	} else {
		g.sendResponse(w, Response{
			ID:      req.ID,
			Success: kResp.Success,
			Data:    kResp.Data,
			Error:   fmt.Sprintf("%v", kResp.Error),
		})
	}
}

func (g *OpcGateway) handleHealth(w http.ResponseWriter, r *http.Request) {
	g.sendResponse(w, Response{Success: true, Data: "ComputeHub System Healthy"})
}

func (g *OpcGateway) handleStatus(w http.ResponseWriter, r *http.Request) {
	g.Kernel.Mu.RLock()
	kLatency := g.Kernel.LastLatency.String()
	g.Kernel.Mu.RUnlock()

	uptime := time.Since(g.startTime).String()

	// Collect node manager info
	nm := g.Kernel.NodeMgr.ListNodes()
	nodes := make([]NodeStatus, 0, len(nm))
	onlineCount := 0
	totalTasks := 0
	activeTasks := 0

	for _, state := range nm {
		ns := NodeStatus{
			NodeID:      state.Register.NodeID,
			Region:      state.Register.Region,
			GPUType:     state.Register.GPUType,
			Status:      state.Register.Status,
			ActiveTasks: state.Metrics.ActiveTasks,
			CPUUtil:     state.Metrics.CPUUtilization,
		}
		if state.Register.Status == "online" {
			onlineCount++
		}
		totalTasks += len(state.Tasks)
		activeTasks += state.Metrics.ActiveTasks

		// Summarize GPU metrics
		for _, m := range state.Metrics.GPU {
			ns.GPUMetrics = append(ns.GPUMetrics, GPUMetricSummary{
				Utilization: m.Utilization,
				Temperature: m.Temperature,
				MemoryUsed:  m.MemoryUsedGB,
			})
		}
		nodes = append(nodes, ns)
	}

	status := SystemStatus{
		Kernel: KernelStatus{
			Status:          "RUNNING",
			ScheduleLatency: kLatency,
			QueueDepth:      len(g.Kernel.LinearQueue),
		},
		Pipeline: PipelineStatus{
			Status:        "ACTIVE",
			Interceptions: 0,
			PureLatency:   g.Pipeline.LastLatency.String(),
		},
		Executor: ExecutorStatus{
			Status:           "READY",
			VerificationRate: 100.0,
			SandboxPath:      "/tmp/opc-sandbox",
		},
		GeneStore: GeneStoreStatus{
			Size:       len(g.GeneStore.Genes),
			RecallRate: 0.0,
		},
		NodeManager: NodeManagerStatus{
			TotalNodes:  len(nodes),
			OnlineNodes: onlineCount,
			TotalTasks:  totalTasks,
			ActiveTasks: activeTasks,
			Nodes:       nodes,
		},
		Uptime: uptime,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

func (g *OpcGateway) sendResponse(w http.ResponseWriter, resp Response) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

// ==================== ComputeHub API v1 Endpoints ====================

func (g *OpcGateway) handleNodeRegister(w http.ResponseWriter, r *http.Request) {
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

	var reg kernel.NodeRegister
	if err := json.Unmarshal(body, &reg); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	reg.RegisteredAt = time.Now()
	if reg.Status == "" {
		reg.Status = "online"
	}
	if reg.Region == "" {
		reg.Region = "unknown"
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeRegister, &reg)
	resp := <-respChan

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleNodeHeartbeat(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		NodeID string                      `json:"node_id"`
		GPU    *kernel.GPUMetrics          `json:"gpu,omitempty"`
		CPU    float64                     `json:"cpu_utilization"`
		Mem    float64                     `json:"memory_used_gb"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Invalid JSON"})
		return
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeHeartbeat, req.GPU)
	resp := <-respChan

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleNodeList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionRegionQuery, nil)
	resp := <-respChan

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleNodeMetrics(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodeID := r.URL.Query().Get("node_id")
	if nodeID == "" {
		// Return all nodes metrics
		g.handleNodeList(w, r)
		return
	}

	nm, err := g.Kernel.NodeMgr.GetNodeMetrics(nodeID)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: err.Error()})
		return
	}

	g.sendResponse(w, Response{
		Success:  true,
		Data:     nm,
		Duration: "0s",
	})
}

func (g *OpcGateway) handleTaskSubmit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var task kernel.TaskSubmit
	if err := json.NewDecoder(r.Body).Decode(&task); err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Invalid JSON"})
		return
	}

	task.SubmittedAt = time.Now()
	if task.Priority == 0 {
		task.Priority = 5
	}
	if task.MaxRetries == 0 {
		task.MaxRetries = 3
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionTaskSubmit, &task)
	resp := <-respChan

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

	var result kernel.TaskResult
	if err := json.NewDecoder(r.Body).Decode(&result); err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Invalid JSON"})
		return
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionTaskResult, &result)
	resp := <-respChan

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
	taskList := make(map[string][]map[string]interface{})

	for _, state := range nodes {
		tasks := make([]map[string]interface{}, 0, len(state.Tasks))
		for tid, ts := range state.Tasks {
			taskInfo := map[string]interface{}{
				"task_id":    tid,
				"source":     ts.Task.SourceType,
				"priority":   ts.Task.Priority,
				"status":     ts.Status,
				"retries":    ts.Retries,
				"created_at": ts.Created.Format(time.RFC3339),
			}
			tasks = append(tasks, taskInfo)
		}
		taskList[state.Register.NodeID] = tasks
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    taskList,
	})
}
