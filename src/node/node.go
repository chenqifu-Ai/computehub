// Package node implements distributed compute node management.
// Nodes register themselves, report capabilities, heartbeat health,
// and receive distributed tasks from the scheduler.
//
// Protocol: HTTP/JSON over gRPC-like RPC channels.
package node

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"sync"
	"time"
)

// ─── 节点状态常量 ───

const (
	NodeStatusOnline   = "online"
	NodeStatusOffline  = "offline"
	NodeStatusBusy     = "busy"
	NodeStatusDraining = "draining"
	NodeStatusNew      = "new"
)

// ─── 节点能力 ───

// NodeCapability describes what a node can execute.
type NodeCapability struct {
	Frameworks    []string          `json:"frameworks"`
	ResourceTypes []string          `json:"resource_types"`
	OS            string            `json:"os"`
	Arch          string            `json:"arch"`
	GPUs          []GPUInfo         `json:"gpus,omitempty"`
	CPUCores      int               `json:"cpu_cores"`
	MemTotalMB    uint64            `json:"mem_total_mb"`
	Docker        bool              `json:"docker"`
	GPUEnabled    bool              `json:"gpu_enabled"`
	Tags          map[string]string `json:"tags,omitempty"`
}

// GPUInfo holds GPU hardware details.
type GPUInfo struct {
	Index   int    `json:"index"`
	Name    string `json:"name"`
	MemMB   uint64 `json:"mem_mb"`
	MemUsed uint64 `json:"mem_used"`
	Temp    uint8  `json:"temp"`
	UtilPct float64 `json:"util_pct"`
}

// ─── 节点信息 ───

// Node represents a distributed compute node (local or remote).
type Node struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	IP          string            `json:"ip"`
	Port        int               `json:"port"`
	Status      string            `json:"status"`
	Capability  NodeCapability    `json:"capability"`
	Load        float64           `json:"load"`
	Region      string            `json:"region"`
	Registered  time.Time         `json:"registered_at"`
	LastHB      time.Time         `json:"last_heartbeat"`
	TasksRunning int              `json:"tasks_running"`
	Tags        map[string]string `json:"tags,omitempty"`

	// Internal (not serialized)
	mu     sync.RWMutex
	hbFail int // consecutive heartbeat failures
}

// NewNode creates a node with auto-detected capabilities.
func NewNode(id, name string) *Node {
	return &Node{
		ID:          id,
		Name:        name,
		Status:      NodeStatusOnline,
		Registered:  time.Now(),
		LastHB:      time.Now(),
		Tags:        make(map[string]string),
		Capability:  NodeCapability{
			Tags:          make(map[string]string),
			Frameworks:    []string{"pytorch", "tensorflow", "jax", "onnx", "custom"},
			ResourceTypes: []string{"gpu", "cpu"},
			OS:            runtime.GOOS,
			Arch:          runtime.GOARCH,
			CPUCores:      runtime.NumCPU(),
		},
	}
}

// SetCapability sets the node's detected capabilities.
func (n *Node) SetCapability(cap NodeCapability) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.Capability = cap
}

// GetCapability returns a copy of the node's capabilities.
func (n *Node) GetCapability() NodeCapability {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return n.Capability
}

// MarkHeartbeat records a successful heartbeat.
func (n *Node) MarkHeartbeat() {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.LastHB = time.Now()
	n.hbFail = 0
	if n.Status == NodeStatusOffline {
		n.Status = NodeStatusOnline
	}
}

// RecordHBFailure increments heartbeat failure count.
func (n *Node) RecordHBFailure() int {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.hbFail++
	if n.hbFail >= 3 && n.Status != NodeStatusOffline {
		n.Status = NodeStatusOffline
	}
	return n.hbFail
}

// HBFailures returns consecutive heartbeat failure count.
func (n *Node) HBFailures() int {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return n.hbFail
}

// CanAcceptTasks returns true if the node is online and not too loaded.
func (n *Node) CanAcceptTasks(maxLoad float64) bool {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return n.Status == NodeStatusOnline && n.Load < maxLoad
}

// IncrementTasksRunning adds to the running task count.
func (n *Node) IncrementTasksRunning() {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.TasksRunning++
	if n.TasksRunning > 0 && n.Status == NodeStatusOnline {
		n.Status = NodeStatusBusy
	}
}

// DecrementTasksRunning removes from the running task count.
func (n *Node) DecrementTasksRunning() {
	n.mu.Lock()
	defer n.mu.Unlock()
	if n.TasksRunning > 0 {
		n.TasksRunning--
	}
	if n.TasksRunning == 0 && n.Status == NodeStatusBusy {
		n.Status = NodeStatusOnline
	}
}

// ─── 心跳消息 ───

// HeartbeatRequest is sent by a node to the gateway.
type HeartbeatRequest struct {
	NodeID     string            `json:"node_id"`
	Capability *NodeCapability   `json:"capability,omitempty"`
	Metrics    *NodeMetrics      `json:"metrics,omitempty"`
	Signature  string            `json:"signature,omitempty"`
}

// HeartbeatResponse is returned by the gateway.
type HeartbeatResponse struct {
	Accepted   bool              `json:"accepted"`
	NodeID     string            `json:"node_id"`
	Assignments []TaskAssignment  `json:"assignments,omitempty"`
	Message    string            `json:"message,omitempty"`
}

// ─── 节点注册 ───

// RegisterRequest is sent during node registration.
type RegisterRequest struct {
	NodeID     string           `json:"node_id"`
	Name       string           `json:"name"`
	IP         string           `json:"ip"`
	Port       int              `json:"port"`
	Capability NodeCapability   `json:"capability"`
	Region     string           `json:"region"`
}

// RegisterResponse is returned after registration.
type RegisterResponse struct {
	Success bool   `json:"success"`
	NodeID  string `json:"node_id"`
	Message string `json:"message"`
}

// ─── 任务分配 ───

// TaskAssignment tells a node what to execute.
type TaskAssignment struct {
	TaskID string `json:"task_id"`
	Action string `json:"action"`
}

// ─── 任务结果回传 ───

// TaskResultReport is sent by a node after task completion.
type TaskResultReport struct {
	TaskID   string          `json:"task_id"`
	NodeID   string          `json:"node_id"`
	ExitCode int             `json:"exit_code"`
	Stdout   string          `json:"stdout"`
	Stderr   string          `json:"stderr"`
	Duration string          `json:"duration"`
	Metrics  *NodeMetrics    `json:"metrics,omitempty"`
	Artifacts []string       `json:"artifacts,omitempty"`
}

// ─── 节点指标 ───

// NodeMetrics reports runtime resource usage.
type NodeMetrics struct {
	CPUPct    float64 `json:"cpu_pct"`
	MemUsedMB uint64  `json:"mem_used_mb"`
	MemTotalMB uint64 `json:"mem_total_mb"`
	GPUs      []GPUInfo `json:"gpus,omitempty"`
	TasksRunning int   `json:"tasks_running"`
	Load      float64 `json:"load"`
}

// ─── 自动检测系统能力 ───

// DetectLocalCapability auto-detects this machine's capabilities.
func DetectLocalCapability() NodeCapability {
	cap := NodeCapability{
		OS:   runtime.GOOS,
		Arch: runtime.GOARCH,
		Frameworks: []string{
			"pytorch", "tensorflow", "jax", "onnx", "huggingface", "custom",
		},
		ResourceTypes: []string{"gpu", "cpu"},
		CPUCores:      runtime.NumCPU(),
		Docker:        hasCommand("docker"),
		Tags:          make(map[string]string),
	}

	// Memory
	if data, err := os.ReadFile("/proc/meminfo"); err == nil {
		for _, line := range strings.Split(string(data), "\n") {
			if strings.HasPrefix(line, "MemTotal:") {
				var kb uint64
				fmt.Sscanf(line, "MemTotal: %d kB", &kb)
				cap.MemTotalMB = kb / 1024
			}
		}
	}

	// GPU detection
	gpus := detectGPUs()
	if len(gpus) > 0 {
		cap.GPUs = gpus
		cap.GPUEnabled = true
	}

	// Region tag
	cap.Tags["region"] = os.Getenv("NODE_REGION")
	if cap.Tags["region"] == "" {
		cap.Tags["region"] = "default"
	}

	// GPU framework support tags
	if cap.GPUEnabled {
		cap.Frameworks = append(cap.Frameworks, "triton", "vllm")
		cap.Tags["gpu_compute"] = detectGPUCompute()
	}

	return cap
}

// ─── GPU 检测 ───

func detectGPUs() []GPUInfo {
	var gpus []GPUInfo

	// Try nvidia-smi first
	if hasCommand("nvidia-smi") {
		if data, err := exec.Command("nvidia-smi",
			"--query-gpu=index,name,memory.total,memory.used,temperature.gpu,utilization.gpu",
			"--format=csv,noheader,nounits").Output(); err == nil {
			lines := strings.Split(strings.TrimSpace(string(data)), "\n")
			for _, line := range lines {
				parts := strings.Split(line, ",")
				if len(parts) < 6 {
					continue
				}
				var idx, total, used, temp, util uint64
				fmt.Sscanf(parts[0], "%d", &idx)
				fmt.Sscanf(parts[2], "%d", &total)
				fmt.Sscanf(parts[3], "%d", &used)
				fmt.Sscanf(parts[4], "%d", &temp)
				fmt.Sscanf(parts[5], "%d", &util)
				gpus = append(gpus, GPUInfo{
					Index:   int(idx),
					Name:    strings.TrimSpace(parts[1]),
					MemMB:   total * 1024, // MB from GB
					MemUsed: used * 1024,
					Temp:    uint8(temp),
					UtilPct: float64(util),
				})
			}
		}
	}

	// Fallback: check /sys/class/drm for AMD GPUs
	if len(gpus) == 0 && hasCommand("rocminfo") {
		// Could parse rocminfo output
	}

	// Last fallback: assume no GPUs
	if len(gpus) == 0 {
		// Check if CUDA is available
		if hasPath("/usr/local/cuda") {
			gpus = append(gpus, GPUInfo{
				Index:  0,
				Name:   "CUDA (unavailable)",
				MemMB:  0,
			})
		}
	}

	return gpus
}

func detectGPUCompute() string {
	// Return CUDA compute capability or "N/A"
	if data, err := exec.Command("nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader").Output(); err == nil {
		return strings.TrimSpace(string(data))
	}
	return "N/A"
}

func hasCommand(name string) bool {
	_, err := exec.LookPath(name)
	return err == nil
}

func hasPath(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// ─── 节点发现 ───

// DiscoverLocalNodes scans the local network for ComputeHub nodes.
func DiscoverLocalNodes(timeout time.Duration) []*Node {
	// Scan common ports on local subnet
	var nodes []*Node
	port := 8282

	// Get local subnet (simplified: last octet scan)
	localIP := getLocalIP()
	if localIP == "" {
		return nodes
	}

	prefix := extractPrefix(localIP)
	for i := 1; i <= 30; i++ { // Scan first 30 hosts
		host := prefix + fmt.Sprintf("%d", i)
		addr := host + fmt.Sprintf(":%d", port)

		client := &http.Client{Timeout: timeout}
		conn, err := client.Get(fmt.Sprintf("http://%s/api/health", addr))
		if err == nil {
			conn.Body.Close()
			node := NewNode(
				fmt.Sprintf("local-%s-%d", host, port),
				fmt.Sprintf("Node-%s", host),
			)
			node.IP = host
			node.Port = port
			node.Status = NodeStatusOnline
			node.Region = "local"
			nodes = append(nodes, node)
		}
	}

	return nodes
}

func getLocalIP() string {
	// Try to get the primary interface IP
	if data, err := exec.Command("hostname", "-I").Output(); err == nil {
		return strings.TrimSpace(string(data))
	}
	return "192.168.1"
}

func extractPrefix(ip string) string {
	parts := strings.Split(ip, ".")
	if len(parts) >= 3 {
		return strings.Join(parts[:3], ".") + "."
	}
	return "192.168.1."
}
