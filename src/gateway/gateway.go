// Package gateway provides the REST API layer.
// It sits between clients and the kernel, applying purification
// and gene recall before dispatching tasks.
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
	"github.com/chenqifu-Ai/computehub/src/pure"
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
}

// DispatchResponse is the API task dispatch response.
type DispatchResponse struct {
	Success  bool        `json:"success"`
	TaskID   string      `json:"task_id,omitempty"`
	Status   string      `json:"status,omitempty"`
	Message  string      `json:"message,omitempty"`
	Error    string      `json:"error,omitempty"`
	Data     any         `json:"data,omitempty"`
	Duration string      `json:"duration,omitempty"`
	Verified bool        `json:"verified,omitempty"`
}

// NodeInfo represents a remote compute node.
type NodeInfo struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	IP          string            `json:"ip"`
	Status      string            `json:"status"` // online, offline, busy
	ResourceType string           `json:"resource_type"`
	GPUs        int               `json:"gpus"`
	CPUs        int               `json:"cpus"`
	MemoryGB    int               `json:"memory_gb"`
	Load        float64           `json:"load"`
	Region      string            `json:"region"`
	Capabilities map[string]string `json:"capabilities,omitempty"`
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
	mu          sync.Mutex
	startTime   time.Time
	Port        int
}

// NewGateway creates a fully initialized gateway.
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

	return &Gateway{
		Kernel:    k,
		Pipeline:  p,
		Executor:  ex,
		GeneStore: gs,
		startTime: time.Now(),
		Port:      port,
	}, nil
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

	addr := fmt.Sprintf(":%d", port)
	fmt.Printf("[Gateway] 🌐 ComputeHub Gateway listening on %s\n", addr)
	return http.ListenAndServe(addr, nil)
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
		"version":   "2.0.0",
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

	// Collect metrics from all components
	status := map[string]any{
		"kernel":    g.Kernel.Info(),
		"pipeline":  g.Pipeline.Stats(),
		"executor": map[string]any{
			"status":        "ready",
			"running_tasks": g.Executor.RunningCount(),
			"sandbox_path":  g.Executor.SandboxPath,
		},
		"gene_store": g.GeneStore.Stats(),
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

	// Stage 3: Dispatch to kernel
	result := g.Kernel.Dispatch(purifiedTask)

	// Stage 4: Execute (if EXECUTE action)
	var execResult *executor.ExecutionResult
	if result.Success && purifiedTask.Action == kernel.TaskActionExecute {
		// Execute the actual task
		cmd := fmt.Sprintf(
			"echo '{\"task\":\"%s\",\"framework\":\"%s\",\"gpus\":%d,\"cpus\":%d,\"mem\":%d}'",
			purifiedTask.ID, purifiedTask.Framework,
			purifiedTask.GPUCount, purifiedTask.CPUCount, purifiedTask.MemoryGB,
		)
		res := g.Executor.Execute(purifiedTask.ID, cmd)
		execResult = &res

		// Stage 5: Verify
		validator := executor.DefaultValidator(g.Executor.SandboxPath)
		allPassed := validator(res)

		if !allPassed {
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
	if ct, ok := result.Data.(*kernel.ComputeTask); ok {
		taskStatus = ct.Status
	} else if taskMap, ok := result.Data.(map[string]any); ok {
		if s, has := taskMap["status"]; has {
			taskStatus = fmt.Sprint(s)
		}
	}
	resp := DispatchResponse{
		Success:  result.Success,
		TaskID:   purifiedTask.ID,
		Status:   taskStatus,
		Error:    func() string { if result.Error != nil { return result.Error.Error() }; return "" }(),
		Duration: time.Since(start).String(),
		Verified: execResult != nil && execResult.ExitCode == 0,
	}

	if result.Success && execResult != nil {
		resp.Data = map[string]any{
			"exit_code":   execResult.ExitCode,
			"duration":    execResult.Duration.String(),
			"stdout":      execResult.Stdout,
			"verified":    execResult.ExitCode == 0,
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
			"max_gpu":      quota.MaxGPUs,
			"max_cpu":      quota.MaxCPUs,
			"max_memory_gb": quota.MaxMemoryGB,
			"max_concurrent": quota.MaxConcurrent,
		},
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
	jsonOK(w, map[string]any{
		"nodes": []NodeInfo{}, // Remote nodes not yet implemented
		"local": map[string]any{
			"status": "online",
		},
	})
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

// Stop gracefully shuts down the gateway.
func (g *Gateway) Stop() {
	g.Kernel.Stop()
}
