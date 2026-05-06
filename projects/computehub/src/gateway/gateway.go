package gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/computehub/opc/src/composer"
	"github.com/computehub/opc/src/executor"
	"github.com/computehub/opc/src/gene"
	"github.com/computehub/opc/src/kernel"
	"github.com/computehub/opc/src/prometheus"
	"github.com/computehub/opc/src/pure"
	"github.com/computehub/opc/src/scheduler"
)

// logWithTimestamp 添加时间戳的日志函数
func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
}

// Response is a standardized API response structure
type Response struct {
	ID       string      `json:"id"`
	Success  bool        `json:"success"`
	Data     interface{} `json:"data,omitempty"`
	Error    string      `json:"error,omitempty"`
	Verified bool        `json:"verified"`
	Duration string      `json:"duration"`
}

// ==================== Gateway Component Status ====================

// PipelineStatus represents pipeline component status
type PipelineStatus struct {
	Status        string `json:"status"`
	Interceptions int    `json:"interceptions"`
	PureLatency   string `json:"pure_latency"`
}

// ExecutorStatus represents executor component status
type ExecutorStatus struct {
	Status           string  `json:"status"`
	VerificationRate float64 `json:"verification_rate"`
	SandboxPath      string  `json:"sandbox_path"`
}

// KernelStatus represents kernel component status
type KernelStatus struct {
	Status         string `json:"status"`
	ScheduleLatency string `json:"schedule_latency"`
	QueueDepth     int    `json:"queue_depth"`
}

// GeneStoreStatus represents gene store component status
type GeneStoreStatus struct {
	Size       int     `json:"size"`
	RecallRate float64 `json:"recall_rate"`
}

// NodeStatus represents a single node's status
type NodeStatus struct {
	NodeID        string  `json:"node_id"`
	Region        string  `json:"region"`
	GPUType       string  `json:"gpu_type"`
	Status        string  `json:"status"`
	ActiveTasks   int     `json:"active_tasks"`
	CPUUtilization float64 `json:"cpu_utilization"`
}

// NodeManagerStatus represents the overall node manager status
type NodeManagerStatus struct {
	TotalNodes  int           `json:"total_nodes"`
	OnlineNodes int           `json:"online_nodes"`
	TotalTasks  int           `json:"total_tasks"`
	ActiveTasks int           `json:"active_tasks"`
	Nodes       []NodeStatus  `json:"nodes"`
}

// SystemStatus represents the overall system status
type SystemStatus struct {
	Pipeline    PipelineStatus    `json:"pipeline"`
	Executor    ExecutorStatus    `json:"executor"`
	Kernel      KernelStatus      `json:"kernel"`
	GeneStore   GeneStoreStatus   `json:"geneStore"`
	NodeManager NodeManagerStatus `json:"nodeManager"`
	Uptime      string            `json:"uptime"`
}

// OpcGateway provides a REST API for the ComputeHub System
type OpcGateway struct {
	Kernel                 *kernel.ExtendedKernel
	Pipeline               *pure.PurePipeline
	Executor               *executor.OpcExecutor
	GeneStore              *gene.GeneStore
	Composer               *composer.TaskComposer
	startTime              time.Time
	mu                     sync.Mutex
	unregisterSimFallback  func(nodeID string) error
	TaskDispatcher         *kernel.TaskDispatcher
	Metrics                *prometheus.Metrics
	MetricsCollector       *prometheus.Collector
	Scheduler              *scheduler.Scheduler
}

// SetSimUnregisterFallback sets a fallback for deleting simulated nodes
func (g *OpcGateway) SetSimUnregisterFallback(fn func(nodeID string) error) {
	g.unregisterSimFallback = fn
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
		if config.MaxNodes > 0 {
			maxNodes = config.MaxNodes
		}
	}

	// Initialize Internal Components
	p := pure.NewPurePipeline()
	p.AddFilter(&pure.SyntaxFilter{})
	p.AddFilter(&pure.SemanticFilter{AllowedActions: []string{"EXEC", "PING", "STATUS", "NODE_REGISTER", "TASK_SUBMIT", "NODE_HEARTBEAT", "TASK_RESULT", "GPU_MONITOR"}})
	p.AddFilter(&pure.BoundaryFilter{Blacklist: []string{"/etc/passwd", "/root/.ssh"}})
	p.AddFilter(&pure.ContextFilter{DeviceFingerprint: "OPC-GATEWAY-API"})

	kernelObj := kernel.NewExtendedKernel(bufferSize, maxStates, maxNodes)
	kernelObj.Start() // Start kernel processing goroutine

	ex := executor.NewOpcExecutor(sandboxPath)
	gs := gene.NewGeneStore(geneStorePath)

	// Initialize TaskComposer with default config
	composerCfg := composer.DefaultConfig()
	if config != nil && config.ComposerModel != "" {
		composerCfg.DecomposeModel = config.ComposerModel
	}
	if config != nil && len(config.ComposerExecModels) > 0 {
		composerCfg.ExecuteModels = config.ComposerExecModels
	}
	if config != nil && config.ComposerMaxConcurrency > 0 {
		composerCfg.MaxConcurrency = config.ComposerMaxConcurrency
	}
	composerAPI := ""
	composerKey := ""
	if config != nil {
		composerAPI = config.ComposerAPIURL
		composerKey = config.ComposerKey
	}
	composerObj := composer.NewTaskComposer(composerCfg, composerAPI, composerKey)

	// Create gateway instance before sim registration (needed for self-reference)
	gw := &OpcGateway{
		Kernel:    kernelObj,
		Pipeline:  p,
		Executor:  ex,
		GeneStore: gs,
		Composer:  composerObj,
		startTime: time.Now(),
	}

	// Create Prometheus metrics and registerer
	metricsReg := prometheus.NewRegistry()
	gw.Metrics = metricsReg.CreateMetrics()
	gw.MetricsCollector = prometheus.NewCollector(gw.Metrics)

	// Start metrics collector (updates every 5s from kernel state)
	gw.MetricsCollector.Start(5 * time.Second)
	logWithTimestamp("✅ Prometheus metrics collector started (interval=5s)")

	logWithTimestamp("✅ Gateway initialized, ready to serve")

	// Start task dispatcher (picks up pending tasks from kernel queue)
	runner := &kernel.LocalTaskRunner{SandboxPath: sandboxPath}
	dispatcher := kernel.NewTaskDispatcher(kernelObj, runner)
	dispatcher.Start(2 * time.Second)
	gw.TaskDispatcher = dispatcher
	logWithTimestamp("✅ Task dispatcher started (interval=2s)")

	// Initialize Scheduler connected to real NodeManager
	sched := scheduler.NewScheduler(scheduler.DefaultConfig())
	// Register real nodes into scheduler (from kernel's NodeMgr)
	nodes := kernelObj.NodeMgr.ListNodes()
	for _, state := range nodes {
		reg := state.Register
		sched.RegisterNode(&scheduler.NodeInfo{
			ID:           reg.NodeID,
			Region:       reg.Region,
			Status:       reg.Status,
			GPUType:      reg.GPUType,
			CPUCores:     reg.CPUCores,
			MemoryGB:     reg.MemoryGB,
			GPUMemoryGB:  reg.GPUMemoryGB,
			MaxTasks:     reg.MaxConcurrency,
			SuccessRate:  1.0,
		})
	}
	gw.Scheduler = sched
	logWithTimestamp("✅ Scheduler initialized with %d real nodes", len(nodes))

	return gw
}

// GatewayConfig holds configuration for gateway components
type GatewayConfig struct {
	GeneStorePath      string
	SandboxPath        string
	BufferSize         int
	MaxStates          int
	MaxNodes           int
	ComposerModel      string
	ComposerExecModels []string
	ComposerAPIURL     string
	ComposerKey        string
	ComposerMaxConcurrency int
}

func (g *OpcGateway) Serve(port int, dashboardDir ...string) {
	// Legacy endpoints (backward compatible)
	http.HandleFunc("/api/dispatch", g.handleDispatch)
	http.HandleFunc("/api/health", g.handleHealth)
	http.HandleFunc("/api/status", g.handleStatus)

	// ComputeHub API endpoints
	http.HandleFunc("/api/v1/nodes/register", g.handleNodeRegister)
	http.HandleFunc("/api/v1/nodes/unregister", g.handleNodeUnregister)
	http.HandleFunc("/api/v1/nodes/heartbeat", g.handleNodeHeartbeat)
	http.HandleFunc("/api/v1/nodes/list", g.handleNodeList)
	http.HandleFunc("/api/v1/nodes/metrics", g.handleNodeMetrics)
	http.HandleFunc("/api/v1/tasks/submit", g.handleTaskSubmit)
	http.HandleFunc("/api/v1/tasks/result", g.handleTaskResult)
	http.HandleFunc("/api/v1/tasks/cancel", g.handleTaskCancel)
	http.HandleFunc("/api/v1/tasks/list", g.handleTaskList)
	http.HandleFunc("/api/v1/tasks/detail", g.handleTaskDetail)
	http.HandleFunc("/api/v1/tasks/poll", g.handleTaskPoll)
	http.HandleFunc("/api/v1/tasks/progress", g.handleTaskProgress) // streaming output

	// Prometheus metrics endpoint
	http.HandleFunc("/metrics", prometheus.MetricsHandler(g.Metrics.Registry))
	logWithTimestamp("📈 Prometheus /metrics endpoint registered")

	// Dashboard static files (if directory provided)
	if len(dashboardDir) > 0 && dashboardDir[0] != "" {
		fs := http.FileServer(http.Dir(dashboardDir[0]))
		http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			// Don't intercept API/WS paths
			if strings.HasPrefix(r.URL.Path, "/api/") || strings.HasPrefix(r.URL.Path, "/ws/") {
				http.NotFound(w, r)
				return
			}
			fs.ServeHTTP(w, r)
		})
		logWithTimestamp("📂 Dashboard static files: %s", dashboardDir[0])
	}

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
	case "/api/v1/nodes/unregister":
		g.handleNodeUnregister(w, r)
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
	case "/api/v1/tasks/cancel":
		g.handleTaskCancel(w, r)
	case "/api/v1/tasks/list":
		g.handleTaskList(w, r)
	case "/api/v1/tasks/detail":
		g.handleTaskDetail(w, r)
	case "/api/v1/tasks/poll":
		g.handleTaskPoll(w, r)
	default:
		http.NotFound(w, r)
	}
}

// ==================== Health and Status Endpoints ====================

// handleHealth is the health check endpoint for OpcGateway v1
func (g *OpcGateway) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	g.sendResponse(w, Response{
		ID:       "health-check",
		Success:  true,
		Data:     "ComputeHub System Healthy",
		Verified: false,
	})
}

// handleStatus is the system status endpoint for OpcGateway v1
func (g *OpcGateway) handleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	onlineCount := 0
	totalTasks := 0
	activeTasks := 0

	for _, node := range nodes {
		totalTasks += node.Metrics.TotalTasks
		activeTasks += node.Metrics.ActiveTasks
		if node.Register.Status == "online" {
			onlineCount++
		}
	}

	uptime := time.Since(g.startTime).String()

	status := SystemStatus{
		Pipeline: PipelineStatus{
			Status: "ACTIVE",
			PureLatency: "0s",
		},
		Executor: ExecutorStatus{
			Status:           "READY",
			VerificationRate: 100.0,
			SandboxPath:      "/tmp/opc-sandbox",
		},
		Kernel: KernelStatus{
			Status:         "RUNNING",
			ScheduleLatency: "5µs",
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

// ==================== Legacy Endpoints ====================

// handleDispatch is the main dispatch endpoint for OpcGateway v1
func (g *OpcGateway) handleDispatch(w http.ResponseWriter, r *http.Request) {
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

	var dispatchReq struct {
		ID      string `json:"id"`
		Command string `json:"command"`
		Payload interface{} `json:"payload"`
	}
	if err := json.Unmarshal(body, &dispatchReq); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if dispatchReq.Command == "" {
		g.sendResponse(w, Response{Success: false, Error: "command is required"})
		return
	}

	// Pure Layer 1-3: Input Validation
	filtered, err := g.Pipeline.Process(dispatchReq.Command)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Input failed Pure pipeline validation: %v", err)})
		return
	}

	// Type assert the filtered result to map[string]interface{}
	filteredMap, ok := filtered.(map[string]interface{})
	if !ok {
		g.sendResponse(w, Response{Success: false, Error: "Invalid command format after purification"})
		return
	}

	action, _ := filteredMap["action"].(string)
	payload, _ := filteredMap["payload"]

	respChan := g.Kernel.DispatchExtended(dispatchReq.ID, action, payload)
	resp := <-respChan

	g.sendResponse(w, Response{
		ID:       dispatchReq.ID,
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Verified: false,
		Duration: resp.Duration,
	})
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

func (g *OpcGateway) handleNodeUnregister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		NodeID string `json:"node_id"`
	}
	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.NodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required"})
		return
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeUnregister, req.NodeID)
	resp := <-respChan

	// If kernel didn't find it and we have a sim fallback, try that
	if !resp.Success && g.unregisterSimFallback != nil {
		if fbErr := g.unregisterSimFallback(req.NodeID); fbErr == nil {
			g.sendResponse(w, Response{
				Success: true,
				Data:    map[string]string{"message": "node removed", "node_id": req.NodeID},
			})
			return
		}
	}

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

func (g *OpcGateway) handleNodeHeartbeat(w http.ResponseWriter, r *http.Request) {
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

	var heartbeat map[string]interface{}
	if err := json.Unmarshal(body, &heartbeat); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	nodeID, _ := heartbeat["node_id"].(string)
	if nodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required for heartbeat"})
		return
	}

	// Check if node exists in kernel
	kernelRespChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeHeartbeat, heartbeat)
	kernelResp := <-kernelRespChan

	// Update Scheduler metrics
	if g.Scheduler != nil {
		g.Scheduler.UpdateNodeHeartbeat(nodeID, 15, 45.0, 62.0, 24.0)
	}

	g.sendResponse(w, Response{
		Success:  kernelResp.Success,
		Data:     kernelResp.Data,
		Error:    fmt.Sprintf("%v", kernelResp.Error),
		Duration: kernelResp.Duration,
	})
}

func (g *OpcGateway) handleNodeList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	nodeData := make([]map[string]interface{}, 0, len(nodes))

	for _, node := range nodes {
		nodeData = append(nodeData, map[string]interface{}{
			"node_id":    node.Register.NodeID,
			"region":     node.Register.Region,
			"gpu_type":   node.Register.GPUType,
			"status":     node.Register.Status,
			"active_tasks": node.Metrics.ActiveTasks,
			"cpu_utilization": node.Metrics.CPUUtilization,
			"gpu_utilization": node.Metrics.GPUUtilization,
			"temperature": node.Metrics.Temperature,
			"memory_used_gb": node.Metrics.MemoryUsedGB,
		})
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    nodeData,
	})
}

func (g *OpcGateway) handleNodeMetrics(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodeID := r.URL.Query().Get("node_id")
	if nodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required"})
		return
	}

	metrics, err := g.Kernel.NodeMgr.GetNodeMetrics(nodeID)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("%v", err)})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    metrics,
	})
}

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

	task.SubmittedAt = time.Now()
	if task.Priority == 0 {
		task.Priority = 5
	}
	if task.SourceType == "" {
		task.SourceType = "api"
	}
	if task.MaxRetries == 0 {
		task.MaxRetries = 3
	}

	// Record task submission in Prometheus metrics
	if g.Metrics != nil {
		g.MetricsCollector.RecordTaskSubmission()
	}

	// If composer is available, decompose complex tasks
	if g.Composer != nil {
		// In a real scenario, complex tasks would be decomposed here
		// For now, we just submit the task as-is
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

	// Record task completion in Prometheus metrics
	if g.Metrics != nil {
		duration, _ := time.ParseDuration(result.Duration)
		g.MetricsCollector.RecordTaskCompletion(result.Success, duration.Seconds())
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
	tasks := make(map[string][]map[string]interface{})

	for _, node := range nodes {
		tasks[node.Register.NodeID] = []map[string]interface{}{}
		for taskID, ts := range node.Tasks {
			tasks[node.Register.NodeID] = append(tasks[node.Register.NodeID], map[string]interface{}{
				"task_id":    taskID,
				"status":     ts.Status,
				"command":    ts.Task.Command,
				"source_type": ts.Task.SourceType,
				"priority":   ts.Task.Priority,
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
