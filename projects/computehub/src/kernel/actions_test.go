package kernel

import (
	"fmt"
	"testing"
)

func TestNewNodeManager(t *testing.T) {
	nm := NewNodeManager(10)
	if nm.nodes == nil {
		t.Fatal("NodeManager nodes map is nil")
	}
	if len(nm.nodes) != 0 {
		t.Errorf("Expected 0 nodes, got %d", len(nm.nodes))
	}
}

func TestRegisterNode(t *testing.T) {
	nm := NewNodeManager(5)

	reg := &NodeRegister{
		NodeID:        "test-node-001",
		NodeType:      "gpu",
		GPUType:       "A100",
		Region:        "us-east",
		CPUCores:      32,
		MemoryGB:      128,
		GPUMemoryGB:   80,
		MaxConcurrency: 10,
		IPAddress:     "10.0.0.1",
		Status:        "online",
	}

	if err := nm.RegisterNode(reg); err != nil {
		t.Fatalf("Failed to register node: %v", err)
	}

	if len(nm.nodes) != 1 {
		t.Errorf("Expected 1 node, got %d", len(nm.nodes))
	}

	state := nm.nodes["test-node-001"]
	if state == nil {
		t.Fatal("Node state not found")
	}
	if state.Register.Region != "us-east" {
		t.Errorf("Expected region us-east, got %s", state.Register.Region)
	}
}

func TestRegisterDuplicateNode(t *testing.T) {
	nm := NewNodeManager(5)

	reg := &NodeRegister{
		NodeID:     "test-node-dup",
		NodeType:   "gpu",
		Region:     "us-west",
		Status:     "online",
	}

	if err := nm.RegisterNode(reg); err != nil {
		t.Fatalf("First registration failed: %v", err)
	}

	if err := nm.RegisterNode(reg); err == nil {
		t.Fatal("Expected error for duplicate node registration")
	}
}

func TestRegisterMaxNodes(t *testing.T) {
	nm := NewNodeManager(2)

	for i := 0; i < 2; i++ {
		reg := &NodeRegister{
			NodeID:     fmt.Sprintf("test-node-%03d", i),
			NodeType:   "gpu",
			Region:     "us-east",
			Status:     "online",
		}
		if err := nm.RegisterNode(reg); err != nil {
			t.Fatalf("Registration %d failed: %v", i, err)
		}
	}

	// Third should fail
	reg := &NodeRegister{
		NodeID:   "test-node-003",
		NodeType: "gpu",
		Region:   "us-east",
		Status:   "online",
	}
	if err := nm.RegisterNode(reg); err == nil {
		t.Fatal("Expected error when max nodes reached")
	}
}

func TestHeartbeat(t *testing.T) {
	nm := NewNodeManager(5)

	reg := &NodeRegister{
		NodeID: "test-hb-001",
		NodeType: "gpu",
		GPUType:  "H100",
		Region:   "eu-west",
		Status:   "online",
	}
	if err := nm.RegisterNode(reg); err != nil {
		t.Fatalf("Failed to register node: %v", err)
	}

	metrics := &GPUMetrics{
		NodeID:     "test-hb-001",
		Utilization: 75.5,
		Temperature: 65.0,
		MemoryUsedGB: 32.0,
		MemoryTotalGB: 80.0,
	}

	if err := nm.Heartbeat("test-hb-001", metrics); err != nil {
		t.Fatalf("Heartbeat failed: %v", err)
	}

	state := nm.nodes["test-hb-001"]
	if state.Heartbeat.IsZero() {
		t.Error("Heartbeat timestamp not updated")
	}
}

func TestHeartbeatUnknownNode(t *testing.T) {
	nm := NewNodeManager(5)

	metrics := &GPUMetrics{
		NodeID: "unknown-node",
	}

	if err := nm.Heartbeat("unknown-node", metrics); err == nil {
		t.Fatal("Expected error for unknown node heartbeat")
	}
}

func TestSubmitTask(t *testing.T) {
	nm := NewNodeManager(5)

	// Register a node first
	reg := &NodeRegister{
		NodeID:        "test-task-001",
		NodeType:      "gpu",
		GPUType:       "A100",
		Region:        "us-east",
		MaxConcurrency: 5,
		Status:        "online",
	}
	if err := nm.RegisterNode(reg); err != nil {
		t.Fatalf("Failed to register node: %v", err)
	}

	task := &TaskSubmit{
		TaskID:       "task-001",
		SourceType:   "direct",
		Priority:     8,
		Timeout:      300,
		Command:      "nvidia-smi",
		MaxRetries:   3,
	}

	if err := nm.SubmitTask(task); err != nil {
		t.Fatalf("Failed to submit task: %v", err)
	}

	state := nm.nodes["test-task-001"]
	if state.Tasks["task-001"] == nil {
		t.Fatal("Task not found in node tasks")
	}
	if state.Metrics.ActiveTasks != 1 {
		t.Errorf("Expected 1 active task, got %d", state.Metrics.ActiveTasks)
	}
}

func TestSubmitTaskNoAvailableNodes(t *testing.T) {
	nm := NewNodeManager(5)

	task := &TaskSubmit{
		TaskID:   "task-no-node",
		Command:  "echo test",
	}

	if err := nm.SubmitTask(task); err == nil {
		t.Fatal("Expected error when no nodes available")
	}
}

func TestCompleteTask(t *testing.T) {
	nm := NewNodeManager(5)

	reg := &NodeRegister{
		NodeID:        "test-complete-001",
		NodeType:      "gpu",
		Region:        "us-east",
		MaxConcurrency: 5,
		Status:        "online",
	}
	nm.RegisterNode(reg)

	task := &TaskSubmit{
		TaskID:   "task-complete-001",
		Command:  "echo hello",
	}
	nm.SubmitTask(task)

	result := &TaskResult{
		TaskID:     "task-complete-001",
		Success:    true,
		ExitCode:   0,
		Stdout:     "hello",
		Duration:   "1.2s",
		ExecutedOn: "test-complete-001",
		Verified:   true,
	}

	if err := nm.CompleteTask("task-complete-001", "test-complete-001", result); err != nil {
		t.Fatalf("Failed to complete task: %v", err)
	}

	state := nm.nodes["test-complete-001"]
	ts := state.Tasks["task-complete-001"]
	if ts.Status != "completed" {
		t.Errorf("Expected status 'completed', got '%s'", ts.Status)
	}
	if state.Metrics.ActiveTasks != 0 {
		t.Errorf("Expected 0 active tasks, got %d", state.Metrics.ActiveTasks)
	}
}

func TestGetNodeMetrics(t *testing.T) {
	nm := NewNodeManager(5)

	reg := &NodeRegister{
		NodeID:        "test-metrics-001",
		NodeType:      "gpu",
		Region:        "us-east",
		MaxConcurrency: 5,
		Status:        "online",
	}
	nm.RegisterNode(reg)

	metrics, err := nm.GetNodeMetrics("test-metrics-001")
	if err != nil {
		t.Fatalf("Failed to get metrics: %v", err)
	}
	if metrics.NodeID != "test-metrics-001" {
		t.Errorf("Expected node_id test-metrics-001, got %s", metrics.NodeID)
	}
}

func TestGetNodeMetricsUnknown(t *testing.T) {
	nm := NewNodeManager(5)

	_, err := nm.GetNodeMetrics("unknown-node")
	if err == nil {
		t.Fatal("Expected error for unknown node metrics")
	}
}

func TestListNodes(t *testing.T) {
	nm := NewNodeManager(10)

	reg1 := &NodeRegister{
		NodeID:   "node-001",
		NodeType: "gpu",
		Region:   "us-east",
		Status:   "online",
	}
	reg2 := &NodeRegister{
		NodeID:   "node-002",
		NodeType: "cpu",
		Region:   "eu-west",
		Status:   "draining",
	}

	nm.RegisterNode(reg1)
	nm.RegisterNode(reg2)

	nodes := nm.ListNodes()
	if len(nodes) != 2 {
		t.Errorf("Expected 2 nodes, got %d", len(nodes))
	}
}

func TestExtendedKernelDispatch(t *testing.T) {
	ek := NewExtendedKernel(100, 1000, 50)

	// Register a node
	reg := &NodeRegister{
		NodeID:     "ek-node-001",
		NodeType:   "gpu",
		GPUType:    "A100",
		Region:     "us-east",
		Status:     "online",
	}

	respChan := ek.DispatchExtended("ek-test-001", ActionNodeRegister, reg)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("Node registration failed: %v", resp.Error)
	}
	if resp.Data.(map[string]string)["node_id"] != "ek-node-001" {
		t.Errorf("Expected node_id ek-node-001, got %s", resp.Data)
	}

	// Verify node is actually registered
	nodes := ek.NodeMgr.ListNodes()
	if len(nodes) != 1 {
		t.Errorf("Expected 1 node, got %d", len(nodes))
	}
}

func TestExtendedKernelTaskSubmit(t *testing.T) {
	ek := NewExtendedKernel(100, 1000, 50)

	// Register node first (sync - wait for response)
	reg := &NodeRegister{
		NodeID:        "ek-node-submit",
		NodeType:      "gpu",
		Region:        "us-east",
		MaxConcurrency: 5,
		Status:        "online",
	}
	respChan := ek.DispatchExtended("reg", ActionNodeRegister, reg)
	<-respChan // wait for registration

	// Submit task
	task := &TaskSubmit{
		TaskID:   "ek-task-001",
		Command:  "echo hello",
		Priority: 7,
	}

	respChan = ek.DispatchExtended("task-submit", ActionTaskSubmit, task)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("Task submission failed: %v", resp.Error)
	}
}

func TestExtendedKernelGPUMonitor(t *testing.T) {
	ek := NewExtendedKernel(100, 1000, 50)

	// Register node
	reg := &NodeRegister{
		NodeID:   "ek-monitor-001",
		NodeType: "gpu",
		Region:   "us-east",
		Status:   "online",
	}
	respChan := ek.DispatchExtended("reg", ActionNodeRegister, reg)
	<-respChan

	// Send GPU metrics
	metrics := &GPUMetrics{
		NodeID:       "ek-monitor-001",
		Utilization:  85.5,
		Temperature:  72.0,
		MemoryUsedGB: 58.0,
		MemoryTotalGB: 80.0,
	}

	respChan = ek.DispatchExtended("gpu-mon", ActionGPUMonitor, metrics)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("GPU monitor failed: %v", resp.Error)
	}
}

func TestExtendedKernelTaskResult(t *testing.T) {
	ek := NewExtendedKernel(100, 1000, 50)

	// Register node
	reg := &NodeRegister{
		NodeID:        "ek-result-001",
		NodeType:      "gpu",
		Region:        "us-east",
		MaxConcurrency: 5,
		Status:        "online",
	}
	respChan := ek.DispatchExtended("reg", ActionNodeRegister, reg)
	<-respChan

	// Submit task
	task := &TaskSubmit{
		TaskID:   "ek-result-task-001",
		Command:  "echo done",
	}
	respChan = ek.DispatchExtended("task-sub", ActionTaskSubmit, task)
	<-respChan

	// Submit result
	result := &TaskResult{
		TaskID:     "ek-result-task-001",
		Success:    true,
		ExitCode:   0,
		Stdout:     "done",
		Duration:   "0.5s",
		ExecutedOn: "ek-result-001",
		Verified:   true,
	}

	respChan = ek.DispatchExtended("task-res", ActionTaskResult, result)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("Task result failed: %v", resp.Error)
	}
}

func TestNodeOffline(t *testing.T) {
	nm := NewNodeManager(5)

	reg := &NodeRegister{
		NodeID:   "offline-node",
		NodeType: "gpu",
		Region:   "us-east",
		Status:   "online",
	}
	nm.RegisterNode(reg)

	// Submit task should work
	task := &TaskSubmit{
		TaskID: "offline-task",
	}
	if err := nm.SubmitTask(task); err != nil {
		t.Fatalf("Task submit should succeed for online node: %v", err)
	}

	// Change node to draining
	nm.mu.Lock()
	nm.nodes["offline-node"].Register.Status = "draining"
	nm.mu.Unlock()

	// New task should NOT be assigned to draining node
	task2 := &TaskSubmit{
		TaskID: "offline-task-2",
	}
	if err := nm.SubmitTask(task2); err == nil {
		// No other nodes, so this is expected to fail
		// Check if the draining node was NOT selected
		if nm.nodes["offline-node"].Metrics.ActiveTasks > 1 {
			t.Error("Draining node should not receive new tasks")
		}
	}
}

func BenchmarkRegisterNode(b *testing.B) {
	nm := NewNodeManager(1000)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		reg := &NodeRegister{
			NodeID:     "bench-node-" + string(rune('0'+i%10)),
			NodeType:   "gpu",
			Region:     "us-east",
			Status:     "online",
		}
		nm.RegisterNode(reg)
	}
}

func BenchmarkSubmitTask(b *testing.B) {
	nm := NewNodeManager(100)
	reg := &NodeRegister{
		NodeID:        "bench-node-submit",
		NodeType:      "gpu",
		Region:        "us-east",
		MaxConcurrency: 100,
		Status:        "online",
	}
	nm.RegisterNode(reg)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		task := &TaskSubmit{
			TaskID:   "bench-task-" + string(rune('0'+i%10)),
			Command:  "echo test",
			Priority: 5,
		}
		nm.SubmitTask(task)
	}
}
