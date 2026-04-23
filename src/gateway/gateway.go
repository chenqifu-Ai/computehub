// Package gateway provides the REST API layer.
// It connects clients to the deterministic kernel through
// the purification pipeline and gene store, with distributed
// node scheduling for multi-node compute.
package gateway

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/chenqifu-Ai/computehub/src/executor"
	"github.com/chenqifu-Ai/computehub/src/gene"
	"github.com/chenqifu-Ai/computehub/src/kernel"
	"github.com/chenqifu-Ai/computehub/src/node"
	"github.com/chenqifu-Ai/computehub/src/pure"
	"github.com/chenqifu-Ai/computehub/src/scheduler"
)

// ─── API 请求/响应结构 ───

// DispatchRequest is an API task dispatch request.
type DispatchRequest struct {
	ID           string            `json:"id,omitempty"`
	Action       string            `json:"action"`
	Framework    string            `json:"framework,omitempty"`
	ResourceType string            `json:"resource_type,omitempty"`
	GPUCount     int               `json:"gpu_count,omitempty"`
	CPUCount     int               `json:"cpu_count,omitempty"`
	MemoryGB     int               `json:"memory_gb,omitempty"`
	DurationSecs int               `json:"duration_secs,omitempty"`
	Requirements map[string]string `json:"requirements,omitempty"`
	Source       string            `json:"source"`
	Region       string            `json:"region,omitempty"` // preferred region
	Priority     int               `json:"priority,omitempty"`
}

// DispatchResponse is the API task dispatch response.
type DispatchResponse struct {
	Success  bool        `json:"success"`
	TaskID   string      `json:"task_id,omitempty"`
	Status   string      `json:"status,omitempty"`
	NodeID   string      `json:"node_id,omitempty"` // which node handles it
	Message  string      `json:"message,omitempty"`
	Error    string      `json:"error,omitempty"`
	Data     any         `json:"data,omitempty"`
	Duration string      `json:"duration,omitempty"`
	Verified bool        `json:"verified,omitempty"`
}

// ─── Gateway 结构 ───

// Gateway is the REST API gateway.
// It connects clients to the deterministic kernel through
// the purification pipeline and gene store.
type Gateway struct {
	Kernel      *kernel.Kernel
	Pipeline    *pure.Pipeline
	Executor    *executor.Executor
	GeneStore   *gene.Store
	NodeMgr     *node.NodeManager
	Scheduler   *scheduler.Scheduler
	mu          sync.Mutex
	startTime   time.Time
	Port        int
}

// ─── 初始化 ───

// NewGateway creates a fully initialized gateway with distributed node support.
func NewGateway(port int, sandboxPath string, genesPath string) (*Gateway, error) {
	// Initialize gene store
	gs := gene.NewStore(genesPath)
	gs.LoadPredefined()

	// Initialize executor
	ex, err := executor.NewExecutor(sandboxPath)
	if err != nil {
		return nil, fmt.Errorf("create executor: %w", err)
	}

	// Initialize kernel
	k := kernel.NewKernelDefaults()
	k.Start()

	// Initialize pipeline
	p := pure.ProductionPipeline()

	// Initialize local node
	localNode := node.NewNode("local-gateway", "gateway-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = port
	localNode.Region = "local"
	localNode.SetCapability(node.DetectLocalCapability())

	// Initialize node manager with local node
	nm := node.NewNodeManager(localNode)

	// Initialize scheduler with balanced strategy
	sc := scheduler.NewScheduler(nm, scheduler.StrategyBalanced)

	gw := &Gateway{
		Kernel:    k,
		Pipeline:  p,
		Executor:  ex,
		GeneStore: gs,
		NodeMgr:   nm,
		Scheduler: sc,
		startTime: time.Now(),
		Port:      port,
	}

	return gw, nil
}

// ─── HTTP 路由 ───

// Serve starts the HTTP server.
func (g *Gateway) Serve(port int) error {
	http.HandleFunc("/api/health", g.handleHealth)
	http.HandleFunc("/api/status", g.handleStatus)
	http.HandleFunc("/api/dispatch", g.handleDispatch)
	http.HandleFunc("/api/jobs", g.handleJobs)
	http.HandleFunc("/api/jobs/", g.handleJobDetail)
	http.HandleFunc("/api/nodes", g.handleNodes)
	// Distributed node endpoints (for node-to-gateway communication)
	http.HandleFunc("/api/node/register", g.handleNodeRegister)
	http.HandleFunc("/api/node/heartbeat", g.handleNodeHeartbeat)
	http.HandleFunc("/api/node/assign", g.handleNodeAssign)
	http.HandleFunc("/api/node/result", g.handleNodeResult)
	http.HandleFunc("/api/node/capability", g.handleNodeCapability)

	addr := fmt.Sprintf(":%d", port)
	fmt.Printf("[Gateway] 🌐 ComputeHub Gateway listening on %s\n", addr)
	fmt.Printf("[Gateway] 📡 Distributed nodes enabled\n")
	return http.ListenAndServe(addr, nil)
}

// Stop gracefully shuts down the gateway.
func (g *Gateway) Stop() {
	g.Kernel.Stop()
}

// ─── 健康检查 ───

func (g *Gateway) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		jsonError(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	jsonOK(w, map[string]any{
		"status":    "healthy",
		"service":   "computehub-gateway",
		"version":   "2.1.0",
		"uptime":    time.Since(g.startTime).String(),
		"timestamp": time.Now().Format(time.RFC3339),
	})
}

// ─── 系统状态 ───

func (g *Gateway) handleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		jsonError(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	status := map[string]any{
		"kernel":    g.Kernel.Info(),
		"pipeline":  g.Pipeline.Stats(),
		"executor": map[string]any{
			"status":        "ready",
			"running_tasks": g.Executor.RunningCount(),
			"sandbox_path":  g.Executor.SandboxPath,
		},
		"gene_store":  g.GeneStore.Stats(),
		"scheduler":   g.Scheduler.Stats(),
		"node_pool":   g.NodeMgr.PoolStats(),
	}

	jsonOK(w, status)
}

// ─── 任务分发 ───

func (g *Gateway) handleDispatch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		jsonError(w, "only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var req DispatchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, fmt.Sprintf("invalid JSON: %v", err), http.StatusBadRequest)
		return
	}

	start := time.Now()

	// Create compute task
	task := &kernel.ComputeTask{
		ID:           req.ID,
		Action:       kernel.TaskAction(req.Action),
		Framework:    req.Framework,
		ResourceType: req.ResourceType,
		GPUCount:     req.GPUCount,
		CPUCount:     req.CPUCount,
		MemoryGB:     req.MemoryGB,
		DurationSecs: req.DurationSecs,
		Requirements: req.Requirements,
		Source:       req.Source,
	}

	// Stage 1: Gene Recall (before purification)
	if task.Action == kernel.TaskActionExecute {
		if pattern := task.Framework + "_" + task.ResourceType; pattern != "" {
			if correctPath, found := g.GeneStore.Recall(pattern); found {
				task.Requirements["_gene_reuse"] = correctPath
			}
		}
	}

	// Stage 2: Purification Pipeline
	cleaned, err := g.Pipeline.Process(task)
	if err != nil {
		resp := DispatchResponse{
			Success:  false,
			Error:    fmt.Sprintf("pipeline blocked: %v", err),
			Duration: time.Since(start).String(),
		}
		jsonResponse(w, resp, http.StatusUnprocessableEntity)
		return
	}

	purifiedTask := cleaned.(*kernel.ComputeTask)

	// Stage 3: Distributed Scheduling
	var assignedNode *node.Node
	var dispatchError error

	// Try to schedule via distributed scheduler first
	if purifiedTask.Action == kernel.TaskActionSubmit || purifiedTask.Action == kernel.TaskActionExecute {
		taskReq := scheduler.TaskRequirement{
			Framework:    purifiedTask.Framework,
			ResourceType: purifiedTask.ResourceType,
			GPUCount:     purifiedTask.GPUCount,
			CPUCount:     purifiedTask.CPUCount,
			MemoryGB:     purifiedTask.MemoryGB,
			Region:       req.Region,
			Priority:     req.Priority,
		}

		// Try distributed scheduling
		assignedNode, dispatchError = g.Scheduler.Schedule(purifiedTask.ID, taskReq)

		// If no remote node available, fall back to local execution
		if dispatchError != nil {
			// Fall back: dispatch directly to local kernel
			localResult := g.Kernel.Dispatch(purifiedTask)
			switch v := localResult.Data.(type) {
			case *kernel.ComputeTask:
				purifiedTask.Status = v.Status
			case map[string]any:
				if s, ok := v["status"]; ok {
					purifiedTask.Status = fmt.Sprint(s)
				}
			}
		}
	}

	// Stage 4: Kernel Dispatch
	result := g.Kernel.Dispatch(purifiedTask)

	// Stage 5: Execute (if EXECUTE action)
	var execResult *executor.ExecutionResult
	if result.Success && purifiedTask.Action == kernel.TaskActionExecute && dispatchError == nil {
		// Build the execution command
		cmd := fmt.Sprintf(
			"echo '{\"task\":\"%s\",\"framework\":\"%s\",\"gpus\":%d,\"cpus\":%d,\"mem\":%d}'",
			purifiedTask.ID, purifiedTask.Framework,
			purifiedTask.GPUCount, purifiedTask.CPUCount, purifiedTask.MemoryGB,
		)
		res := g.Executor.Execute(purifiedTask.ID, cmd)
		execResult = &res

		// Stage 6: Verify
		validator := executor.DefaultValidator(g.Executor.SandboxPath)
		v := validator(res)

		if !v.Passed {
			// Evolution: learn from failure
			g.GeneStore.Evolve(
				fmt.Sprintf("exec_fail_%s", purifiedTask.ID),
				"retry_with_adjusted_params",
				"Task execution failed verification",
				"auto_learn",
			)
		}
	}

	// Build response
	taskStatus := ""
	if result.Data != nil {
		switch v := result.Data.(type) {
		case *kernel.ComputeTask:
			taskStatus = v.Status
		case map[string]any:
			if s, has := v["status"]; has {
				taskStatus = fmt.Sprint(s)
			}
		default:
			taskStatus = fmt.Sprint(v)
		}
	}

	resp := DispatchResponse{
		Success:  result.Success,
		TaskID:   purifiedTask.ID,
		Status:   taskStatus,
		NodeID:   func() string {
			if assignedNode != nil {
				return assignedNode.ID
			}
			return ""
		}(),
		Error:    func() string {
			if result.Error != nil {
				return result.Error.Error()
			}
			if dispatchError != nil {
				return dispatchError.Error()
			}
			return ""
		}(),
		Duration: time.Since(start).String(),
		Verified: execResult != nil && execResult.ExitCode == 0,
	}

	if result.Success && execResult != nil {
		resp.Data = map[string]any{
			"exit_code":   execResult.ExitCode,
			"duration":    execResult.Duration.String(),
			"stdout":      execResult.Stdout,
			"verified":    execResult.ExitCode == 0,
			"isolation":   execResult.Isolation,
		}
	}

	statusCode := http.StatusOK
	if !result.Success {
		statusCode = http.StatusConflict
	}
	jsonResponse(w, resp, statusCode)
}

// ─── 任务管理 ───

func (g *Gateway) handleJobs(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		g.handleListJobs(w, r)
	default:
		jsonError(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func (g *Gateway) handleListJobs(w http.ResponseWriter, r *http.Request) {
	stats := g.Kernel.GetTaskStats()
	quota := g.Kernel.GetQuota()

	jsonOK(w, map[string]any{
		"tasks": stats,
		"quota": map[string]any{
			"max_gpu":       quota.MaxGPUs,
			"max_cpu":       quota.MaxCPUs,
			"max_memory_gb": quota.MaxMemoryGB,
			"max_concurrent": quota.MaxConcurrent,
		},
		"scheduler": g.Scheduler.Stats(),
	})
}

func (g *Gateway) handleJobDetail(w http.ResponseWriter, r *http.Request) {
	// Extract task ID from path: /api/jobs/<id>
	id := strings.TrimPrefix(r.URL.Path, "/api/jobs/")
	if id == "" {
		jsonError(w, "task ID required", http.StatusBadRequest)
		return
	}

	result := g.Kernel.Dispatch(&kernel.ComputeTask{
		ID:     id,
		Action: kernel.TaskActionStatus,
	})

	if result.Success {
		jsonOK(w, result.Data)
	} else {
		jsonError(w, result.Error.Error(), http.StatusNotFound)
	}
}

// ─── 节点管理 ───

func (g *Gateway) handleNodes(w http.ResponseWriter, r *http.Request) {
	allNodes := g.NodeMgr.GetAllNodes()

	// Build node list with serialized info
	nodeInfos := make([]map[string]any, 0, len(allNodes))
	for _, n := range allNodes {
		nodeInfos = append(nodeInfos, map[string]any{
			"id":             n.ID,
			"name":           n.Name,
			"ip":             n.IP,
			"port":           n.Port,
			"status":         n.Status,
			"resource_type":  n.Capability.ResourceTypes,
			"gpu_count":      len(n.Capability.GPUs),
			"cpu_count":      n.Capability.CPUCores,
			"memory_gb":      n.Capability.MemTotalMB / 1024,
			"load":           n.Load,
			"region":         n.Region,
			"tasks_running":  n.TasksRunning,
			"gpu_enabled":    n.Capability.GPUEnabled,
			"registered_at":  n.Registered.Format(time.RFC3339),
		})
	}

	jsonOK(w, map[string]any{
		"nodes":  nodeInfos,
		"local":  map[string]any{"status": "online"},
		"pool":   g.NodeMgr.PoolStats(),
	})
}

// ─── 节点注册 (for remote nodes) ───

func (g *Gateway) handleNodeRegister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		jsonError(w, "only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var req node.RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "invalid JSON", http.StatusBadRequest)
		return
	}

	// Create and register the node
	regNode := node.NewNode(req.NodeID, req.Name)
	regNode.IP = req.IP
	regNode.Port = req.Port
	regNode.Region = req.Region
	regNode.SetCapability(req.Capability)
	regNode.Status = node.NodeStatusOnline

	g.NodeMgr.RegisterNode(regNode)

	jsonResponse(w, node.RegisterResponse{
		Success: true,
		NodeID:  req.NodeID,
		Message: fmt.Sprintf("Node %s registered successfully", req.NodeID),
	}, http.StatusOK)
}

// ─── 节点心跳 (for remote nodes) ───

func (g *Gateway) handleNodeHeartbeat(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		jsonError(w, "only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var req node.HeartbeatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, "invalid JSON", http.StatusBadRequest)
		return
	}

	// Update node state
	targetNode, exists := g.NodeMgr.GetNode(req.NodeID)
	if exists {
		targetNode.MarkHeartbeat()
		if req.Capability != nil {
			targetNode.SetCapability(*req.Capability)
		}
		if req.Metrics != nil {
			targetNode.Load = req.Metrics.Load
		}

		jsonResponse(w, &node.HeartbeatResponse{
			Accepted:  true,
			NodeID:    req.NodeID,
			Message:   "heartbeat accepted",
		}, http.StatusOK)
		return
	}

	jsonResponse(w, node.HeartbeatResponse{
		Accepted: false,
		Message:  fmt.Sprintf("unknown node: %s", req.NodeID),
	}, http.StatusNotFound)
}

// ─── 节点任务分配 (for remote nodes) ───

func (g *Gateway) handleNodeAssign(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		jsonError(w, "only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var assignment node.TaskAssignment
	if err := json.NewDecoder(r.Body).Decode(&assignment); err != nil {
		jsonError(w, "invalid JSON", http.StatusBadRequest)
		return
	}

	jsonResponse(w, assignment, http.StatusOK)
}

// ─── 节点结果回传 (for remote nodes) ───

func (g *Gateway) handleNodeResult(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		jsonError(w, "only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var report node.TaskResultReport
	if err := json.NewDecoder(r.Body).Decode(&report); err != nil {
		jsonError(w, "invalid JSON", http.StatusBadRequest)
		return
	}

	// Decrement task count on the node
	if node, exists := g.NodeMgr.GetNode(report.NodeID); exists {
		node.DecrementTasksRunning()
	}

	jsonOK(w, map[string]any{
		"accepted":  true,
		"task_id":   report.TaskID,
		"node_id":   report.NodeID,
		"exit_code": report.ExitCode,
	})
}

// ─── 节点能力查询 ───

func (g *Gateway) handleNodeCapability(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		jsonError(w, "only GET allowed", http.StatusMethodNotAllowed)
		return
	}

	// Return local node's capability
	localNode, _ := g.NodeMgr.GetNode("local-gateway")
	if localNode == nil {
		jsonError(w, "local node not found", http.StatusNotFound)
		return
	}

	jsonOK(w, localNode.GetCapability())
}

// ─── HTTP 辅助函数 ───

func jsonResponse(w http.ResponseWriter, resp any, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(resp)
}

func jsonOK(w http.ResponseWriter, data any) {
	jsonResponse(w, map[string]any{
		"success": true,
		"data":    data,
	}, http.StatusOK)
}

func jsonError(w http.ResponseWriter, msg string, status int) {
	jsonResponse(w, map[string]any{
		"success": false,
		"error":   msg,
	}, status)
}
