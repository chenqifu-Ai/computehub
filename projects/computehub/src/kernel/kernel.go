package kernel

import (
	"fmt"
	"sync"
	"time"
)

// logWithTimestamp 添加时间戳的日志函数
func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
}

// State represents the physical state of the system at a given timestamp
type State struct {
	Timestamp int64
	Payload   map[string]interface{}
}

// OpcKernel is the deterministic scheduler kernel
type OpcKernel struct {
	Mu            sync.RWMutex
	stateMirror   []State
	maxStates     int
	LinearQueue   chan Command
	LastLatency   time.Duration
	NodeMgr       *NodeManager // node management for extended actions
	done          chan struct{}
}

// Command represents a linearized system instruction
type Command struct {
	ID       string
	Action   string
	Payload  interface{}
	Response chan Response
}

type Response struct {
	Success  bool
	Data     interface{}
	Error    error
	Duration string
}

// NewKernel initializes a new deterministic kernel
func NewKernel(bufferSize int, maxStates int) *OpcKernel {
	return &OpcKernel{
		stateMirror: make([]State, 0),
		maxStates:   maxStates,
		LinearQueue: make(chan Command, bufferSize),
		done:        make(chan struct{}),
	}
}

// Start begins the linearized command processing loop
func (k *OpcKernel) Start() {
	go func() {
		for cmd := range k.LinearQueue {
			k.processCommand(cmd)
		}
		close(k.done)
	}()
}

// processCommand executes commands linearly to eliminate race conditions
func (k *OpcKernel) processCommand(cmd Command) {
	start := time.Now()

	// Snapshot state before execution
	k.snapshotState()

	logWithTimestamp("[Kernel] Processing Command %s: %s", cmd.ID, cmd.Action)

	// Execute based on action type
	resp := k.executeAction(cmd)

	duration := time.Since(start)
	k.Mu.Lock()
	k.LastLatency = duration
	k.Mu.Unlock()

	logWithTimestamp("[Kernel] Command %s completed in %v (success=%v)", cmd.ID, duration, resp.Success)
	cmd.Response <- resp
}

// executeAction dispatches to the appropriate handler
func (k *OpcKernel) executeAction(cmd Command) Response {
	switch cmd.Action {
	case "PING":
		return Response{Success: true, Data: "PONG", Duration: "0s"}
	case "STATUS":
		return Response{Success: true, Data: "System Healthy | Kernel: Deterministic", Duration: "0s"}
	case ActionNodeRegister:
		return k.handleNodeRegister(cmd)
	case ActionNodeUnregister:
		return k.handleNodeUnregister(cmd)
	case ActionNodeHeartbeat:
		return k.handleNodeHeartbeat(cmd)
	case ActionTaskSubmit:
		return k.handleTaskSubmit(cmd)
	case ActionTaskResult:
		return k.handleTaskResult(cmd)
	case ActionTaskCancel:
		return k.handleTaskCancel(cmd)
	case ActionNodeOffline:
		return k.handleNodeOffline(cmd)
	case ActionGPUMonitor:
		return k.handleGPUMonitor(cmd)
	case ActionRegionQuery:
		return k.handleRegionQuery(cmd)
	case ActionMetricsReport:
		return k.handleMetricsReport(cmd)
	default:
		return Response{Success: false, Error: fmt.Errorf("unknown action: %s", cmd.Action)}
	}
}

// ====== Action Handlers ======

func (k *OpcKernel) handleNodeRegister(cmd Command) Response {
	start := time.Now()

	reg, ok := cmd.Payload.(*NodeRegister)
	if !ok {
		return Response{Success: false, Error: fmt.Errorf("invalid NodeRegister payload")}
	}

	if k.NodeMgr == nil {
		return Response{Success: false, Error: fmt.Errorf("NodeManager not initialized")}
	}

	if err := k.NodeMgr.RegisterNode(reg); err != nil {
		return Response{Success: false, Error: err, Duration: time.Since(start).String()}
	}

	return Response{
		Success:  true,
		Data:     map[string]string{"message": "node registered", "node_id": reg.NodeID},
		Duration: time.Since(start).String(),
	}
}

func (k *OpcKernel) handleNodeUnregister(cmd Command) Response {
	start := time.Now()

	nodeID, ok := cmd.Payload.(string)
	if !ok {
		return Response{Success: false, Error: fmt.Errorf("invalid node_id payload")}
	}

	if k.NodeMgr == nil {
		return Response{Success: false, Error: fmt.Errorf("NodeManager not initialized")}
	}

	if err := k.NodeMgr.UnregisterNode(nodeID); err != nil {
		return Response{Success: false, Error: err, Duration: time.Since(start).String()}
	}

	return Response{
		Success:  true,
		Data:     map[string]string{"message": "node removed", "node_id": nodeID},
		Duration: time.Since(start).String(),
	}
}

func (k *OpcKernel) handleNodeHeartbeat(cmd Command) Response {
	start := time.Now()

	if k.NodeMgr == nil {
		return Response{Success: false, Error: fmt.Errorf("NodeManager not initialized")}
	}

	// payload can be GPUMetrics, string (nodeID), or map
	switch p := cmd.Payload.(type) {
	case *GPUMetrics:
		if p == nil {
			return Response{Success: false, Error: fmt.Errorf("nil GPUMetrics payload")}
		}
		// Auto-register node if not found (recover from Gateway restart)
		if err := k.maybeAutoRegisterNode(p.NodeID, func() {
			k.NodeMgr.RegisterNode(&NodeRegister{
				NodeID: p.NodeID, NodeType: "gpu", GPUType: p.NodeID,
				Status: "online", RegisteredAt: time.Now(),
			})
		}); err != nil {
			return Response{Success: false, Error: err, Duration: time.Since(start).String()}
		}
		if err := k.NodeMgr.Heartbeat(p.NodeID, p); err != nil {
			return Response{Success: false, Error: err, Duration: time.Since(start).String()}
		}
	case string:
		// heartbeat with just nodeID
		nodeID := p
		if err := k.maybeAutoRegisterNode(nodeID, func() {
			k.NodeMgr.RegisterNode(&NodeRegister{
				NodeID: nodeID, NodeType: "gpu", Status: "online", RegisteredAt: time.Now(),
			})
		}); err != nil {
			return Response{Success: false, Error: err, Duration: time.Since(start).String()}
		}
		if err := k.NodeMgr.Heartbeat(nodeID, nil); err != nil {
			return Response{Success: false, Error: err, Duration: time.Since(start).String()}
		}
	case map[string]interface{}:
		nodeID, _ := p["node_id"].(string)
		if nodeID == "" {
			return Response{Success: false, Error: fmt.Errorf("heartbeat payload missing node_id")}
		}
		// Auto-register node if not found (recover from Gateway restart)
		if err := k.maybeAutoRegisterNode(nodeID, func() {
			k.NodeMgr.RegisterNode(&NodeRegister{
				NodeID: nodeID, NodeType: "gpu", Status: "online", RegisteredAt: time.Now(),
			})
		}); err != nil {
			return Response{Success: false, Error: err, Duration: time.Since(start).String()}
		}
		// Update IP from Gateway-observed connection (injected by handleNodeHeartbeat)
		if ip, ok := p["ip_address"].(string); ok && ip != "" && ip != "0.0.0.0" {
			if state, err := k.NodeMgr.GetNodeState(nodeID); err == nil && state.Register.IPAddress != ip {
				state.Register.IPAddress = ip
				logWithTimestamp("[Kernel] 📍 Updated node %s IP → %s", nodeID, ip)
			}
		}

		// Extract GPU metrics from heartbeat payload
		var metrics *GPUMetrics
		if gpuUtil, ok := p["gpu_utilization"].(float64); ok {
			metrics = &GPUMetrics{
				NodeID:        nodeID,
				Utilization:   gpuUtil,
				Temperature:   extractFloat64(p["gpu_temperature"]),
				MemoryUsedGB:  extractFloat64(p["memory_used_gb"]),
				MemoryTotalGB: extractFloat64(p["memory_total_gb"]),
			}
			logWithTimestamp("[Kernel] 💓 Heartbeat metrics for %s: util=%.1f temp=%.1f mem=%.1f", nodeID, metrics.Utilization, metrics.Temperature, metrics.MemoryUsedGB)
		} else {
			logWithTimestamp("[Kernel] ⚠️ No GPU metrics in heartbeat for %s, keys=%v", nodeID, p)
		}
		if err := k.NodeMgr.Heartbeat(nodeID, metrics); err != nil {
			return Response{Success: false, Error: err, Duration: time.Since(start).String()}
		}
	default:
		return Response{Success: false, Error: fmt.Errorf("invalid heartbeat payload type")}
	}

	return Response{
		Success:  true,
		Data:     map[string]string{"message": "heartbeat acknowledged"},
		Duration: time.Since(start).String(),
	}
}

// blockedNodes is a permanent blocklist — these nodes can NEVER auto-register.
var blockedNodes = map[string]bool{
	// "cqf-test-worker02": true,  // unblocked 2026-05-10 for testing
}

// maybeAutoRegisterNode checks if node exists; if not, calls fn to register it.
// Returns error only if registration itself fails (e.g., max nodes reached).
func (k *OpcKernel) maybeAutoRegisterNode(nodeID string, registerFn func()) error {
	// Block known problematic nodes from auto-registering
	if blockedNodes[nodeID] {
		logWithTimestamp("[Kernel] 🚫 Blocked node %s from auto-registration", nodeID)
		return fmt.Errorf("node %s is permanently blocked", nodeID)
	}

	k.NodeMgr.mu.Lock()
	_, exists := k.NodeMgr.nodes[nodeID]
	k.NodeMgr.mu.Unlock()

	if !exists {
		logWithTimestamp("[Kernel] 🔁 Auto-registering node %s (heartbeat recovery)", nodeID)
		registerFn()
	}
	return nil
}

// extractFloat64 safely extracts a float64 from an interface{} value
func extractFloat64(v interface{}) float64 {
	if f, ok := v.(float64); ok {
		return f
	}
	return 0
}

func (k *OpcKernel) handleTaskSubmit(cmd Command) Response {
	start := time.Now()

	task, ok := cmd.Payload.(*TaskSubmit)
	if !ok {
		return Response{Success: false, Error: fmt.Errorf("invalid TaskSubmit payload")}
	}

	if k.NodeMgr == nil {
		return Response{Success: false, Error: fmt.Errorf("NodeManager not initialized")}
	}

	if err := k.NodeMgr.SubmitTask(task); err != nil {
		return Response{Success: false, Error: err, Duration: time.Since(start).String()}
	}

	return Response{
		Success:  true,
		Data:     map[string]string{"message": "task submitted", "task_id": task.TaskID},
		Duration: time.Since(start).String(),
	}
}

func (k *OpcKernel) handleTaskResult(cmd Command) Response {
	start := time.Now()

	result, ok := cmd.Payload.(*TaskResult)
	if !ok {
		return Response{Success: false, Error: fmt.Errorf("invalid TaskResult payload")}
	}

	if k.NodeMgr == nil {
		return Response{Success: false, Error: fmt.Errorf("NodeManager not initialized")}
	}

	if err := k.NodeMgr.CompleteTask(result.TaskID, result.ExecutedOn, result); err != nil {
		return Response{Success: false, Error: err, Duration: time.Since(start).String()}
	}

	return Response{
		Success:  true,
		Data: map[string]interface{}{
			"task_id":  result.TaskID,
			"verified": result.Verified,
		},
		Duration: time.Since(start).String(),
	}
}

func (k *OpcKernel) handleTaskCancel(cmd Command) Response {
	start := time.Now()

	taskID, ok := cmd.Payload.(string)
	if !ok {
		return Response{Success: false, Error: fmt.Errorf("invalid task_id payload")}
	}

	if k.NodeMgr == nil {
		return Response{Success: false, Error: fmt.Errorf("NodeManager not initialized")}
	}

	// Find and cancel task on any node
	k.NodeMgr.mu.Lock()
	cancelled := false
	for _, state := range k.NodeMgr.nodes {
		if ts, exists := state.Tasks[taskID]; exists {
			ts.Status = "cancelled"
			state.Metrics.ActiveTasks--
			cancelled = true
			break
		}
	}
	k.NodeMgr.mu.Unlock()

	if !cancelled {
		return Response{Success: false, Error: fmt.Errorf("task %s not found", taskID), Duration: time.Since(start).String()}
	}

	return Response{
		Success:  true,
		Data:     map[string]string{"message": "task cancelled", "task_id": taskID},
		Duration: time.Since(start).String(),
	}
}

func (k *OpcKernel) handleNodeOffline(cmd Command) Response {
	start := time.Now()

	nodeID, ok := cmd.Payload.(string)
	if !ok {
		return Response{Success: false, Error: fmt.Errorf("invalid node_id payload")}
	}

	if k.NodeMgr == nil {
		return Response{Success: false, Error: fmt.Errorf("NodeManager not initialized")}
	}

	k.NodeMgr.mu.Lock()
	if state, exists := k.NodeMgr.nodes[nodeID]; exists {
		state.Register.Status = "offline"
	}
	k.NodeMgr.mu.Unlock()

	return Response{
		Success:  true,
		Data:     map[string]string{"message": "node marked offline", "node_id": nodeID},
		Duration: time.Since(start).String(),
	}
}

func (k *OpcKernel) handleGPUMonitor(cmd Command) Response {
	start := time.Now()

	metrics, ok := cmd.Payload.(*GPUMetrics)
	if !ok {
		return Response{Success: false, Error: fmt.Errorf("invalid GPUMetrics payload")}
	}

	if k.NodeMgr == nil {
		return Response{Success: false, Error: fmt.Errorf("NodeManager not initialized")}
	}

	if err := k.NodeMgr.Heartbeat(metrics.NodeID, metrics); err != nil {
		return Response{Success: false, Error: err, Duration: time.Since(start).String()}
	}

	return Response{
		Success:  true,
		Data:     metrics,
		Duration: time.Since(start).String(),
	}
}

func (k *OpcKernel) handleRegionQuery(cmd Command) Response {
	start := time.Now()

	if k.NodeMgr == nil {
		return Response{Success: false, Error: fmt.Errorf("NodeManager not initialized")}
	}

	nodes := k.NodeMgr.ListNodes()
	return Response{
		Success:  true,
		Data:     nodes,
		Duration: time.Since(start).String(),
	}
}

func (k *OpcKernel) handleMetricsReport(cmd Command) Response {
	// Alias for region query — returns all node metrics
	return k.handleRegionQuery(cmd)
}

// snapshotState saves the current physical state to the mirror for rollback
func (k *OpcKernel) snapshotState() {
	k.Mu.Lock()
	defer k.Mu.Unlock()

	state := State{
		Timestamp: time.Now().UnixNano(),
		Payload:   make(map[string]interface{}),
	}

	k.stateMirror = append(k.stateMirror, state)
	if len(k.stateMirror) > k.maxStates {
		k.stateMirror = k.stateMirror[1:]
	}
}

// Dispatch sends a command to the linear queue
func (k *OpcKernel) Dispatch(id, action string, payload interface{}) chan Response {
	respChan := make(chan Response, 1)
	k.LinearQueue <- Command{
		ID:       id,
		Action:   action,
		Payload:  payload,
		Response: respChan,
	}
	return respChan
}

// GetNodeManager returns the NodeManager (for testing/introspection)
func (k *OpcKernel) GetNodeManager() *NodeManager {
	return k.NodeMgr
}

// Stop closes the LinearQueue channel, stopping the processing goroutine.
// Call this in test cleanup or when shutting down the kernel.
func (k *OpcKernel) Stop() {
	close(k.LinearQueue)
}

// GetKernel returns the underlying OpcKernel from ExtendedKernel
func (ek *ExtendedKernel) GetKernel() *OpcKernel {
	return ek.OpcKernel
}
