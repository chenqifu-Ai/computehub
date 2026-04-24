package gateway

import (
	"encoding/json"
	"fmt"
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

// Request represents the incoming API call
type Request struct {
	ID      string `json:"id"`
	Command string `json:"command"`
}

// Response represents the physical system response
type Response struct {
	ID        string      `json:"id"`
	Success   bool        `json:"success"`
	Data      interface{} `json:"data,omitempty"`
	Error     string      `json:"error,omitempty"`
	Duration  string      `json:"duration,omitempty"`
	Verified  bool        `json:"verified"`
}

type SystemStatus struct {
	Kernel    KernelStatus    `json:"kernel"`
	Pipeline  PipelineStatus  `json:"pipeline"`
	Executor  ExecutorStatus  `json:"executor"`
	GeneStore GeneStoreStatus `json:"geneStore"`
	Uptime    string          `json:"uptime"`
}

type KernelStatus struct {
	Status       string `json:"status"`
	ScheduleLatency string `json:"schedule_latency"`
	QueueDepth   int    `json:"queue_depth"`
}

type PipelineStatus struct {
	Status       string `json:"status"`
	Interceptions int    `json:"interceptions"`
	PureLatency   string `json:"pure_latency"`
}

type ExecutorStatus struct {
	Status        string  `json:"status"`
	VerificationRate float64 `json:"verification_rate"`
	SandboxPath   string  `json:"sandbox_path"`
}

type GeneStoreStatus struct {
	Size       int    `json:"size"`
	RecallRate float64 `json:"recall_rate"`
}

// OpcGateway provides a REST API for the OpenPC System
type OpcGateway struct {
	Kernel    *kernel.OpcKernel
	Pipeline  *pure.PurePipeline
	Executor  *executor.OpcExecutor
	GeneStore *gene.GeneStore
	mu        sync.Mutex
}

func NewOpcGateway(port int, config *GatewayConfig) *OpcGateway {
	// Use config values or fall back to defaults
	geneStorePath := "/root/downloads/opcsystem/genes.json"
	sandboxPath := "/tmp/opc-sandbox"
	bufferSize := 100
	maxStates := 1000

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
	p.AddFilter(&pure.SemanticFilter{AllowedActions: []string{"EXEC", "PING", "STATUS"}})
	p.AddFilter(&pure.BoundaryFilter{Blacklist: []string{"/etc/passwd", "/root/.ssh"}})
	p.AddFilter(&pure.ContextFilter{DeviceFingerprint: "OPC-GATEWAY-API"})

	k := kernel.NewKernel(bufferSize, maxStates)
	k.Start()

	ex := executor.NewOpcExecutor(sandboxPath)
	gs := gene.NewGeneStore(geneStorePath)

	return &OpcGateway{
		Kernel:    k,
		Pipeline:  p,
		Executor:  ex,
		GeneStore: gs,
	}
}

// GatewayConfig holds configuration for gateway components
type GatewayConfig struct {
	GeneStorePath string
	SandboxPath   string
	BufferSize    int
	MaxStates     int
}

func (g *OpcGateway) Serve(port int) {
	http.HandleFunc("/api/dispatch", g.handleDispatch)
	http.HandleFunc("/api/health", g.handleHealth)
	http.HandleFunc("/api/status", g.handleStatus)
	
	logWithTimestamp("🌐 OpenPC Gateway listening on :%d", port)
	if err := http.ListenAndServe(fmt.Sprintf(":%d", port), nil); err != nil {
		logWithTimestamp("Fatal Gateway Error: %v", err)
	}
}

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

	// 3. Kernel Dispatch
	action := "UNKNOWN"
	if strings.Contains(strings.ToUpper(finalCmd), "PING") {
		action = "PING"
	} else if strings.Contains(strings.ToUpper(finalCmd), "EXEC") {
		action = "EXEC"
	} else if strings.Contains(strings.ToUpper(finalCmd), "STATUS") {
		action = "STATUS"
	}

	respChan := g.Kernel.Dispatch(req.ID, action, finalCmd)
	kResp := <-respChan

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
	g.sendResponse(w, Response{Success: true, Data: "OpenPC System Healthy"})
}

func (g *OpcGateway) handleStatus(w http.ResponseWriter, r *http.Request) {
	// Collect physical metrics from internal components
	
	g.Kernel.Mu.RLock()
	kLatency := g.Kernel.LastLatency.String()
	g.Kernel.Mu.RUnlock()

	status := SystemStatus{
		Kernel: KernelStatus{
			Status:          "RUNNING",
			ScheduleLatency: kLatency,
			QueueDepth:      len(g.Kernel.LinearQueue),
		},
		Pipeline: PipelineStatus{
			Status:        "ACTIVE",
			Interceptions: 0, // To be implemented in Pipeline stats
			PureLatency:   g.Pipeline.LastLatency.String(),
		},
		Executor: ExecutorStatus{
			Status:           "READY",
			VerificationRate: 100.0,
			SandboxPath:      "/tmp/opc-sandbox",
		},
		GeneStore: GeneStoreStatus{
			Size:       0, // To be implemented in GeneStore.Count()
			RecallRate: 0.0,
		},
		Uptime: "Running",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

func (g *OpcGateway) sendResponse(w http.ResponseWriter, resp Response) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
