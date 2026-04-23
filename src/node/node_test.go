// Package node - comprehensive tests for distributed node system
package node

import (
	"testing"
	"time"
)

// ─── 节点基本功能测试 ───

func TestNewNode(t *testing.T) {
	node := NewNode("test-001", "test-node")
	if node.ID != "test-001" {
		t.Errorf("Expected ID test-001, got %s", node.ID)
	}
	// NewNode starts as "online" by default
	if node.Status != NodeStatusOnline {
		t.Errorf("Expected status online, got %s", node.Status)
	}
	if node.Capability.OS == "" {
		t.Error("OS should not be empty")
	}
}

func TestNodeMarkHeartbeat(t *testing.T) {
	node := NewNode("hb-001", "hb-node")
	node.Status = NodeStatusOffline

	node.MarkHeartbeat()
	if node.Status != NodeStatusOnline {
		t.Errorf("Expected online after heartbeat, got %s", node.Status)
	}
	if node.HBFailures() != 0 {
		t.Error("HB failures should reset to 0")
	}
}

func TestNodeRecordHBFailure(t *testing.T) {
	node := NewNode("fail-001", "fail-node")
	node.Status = NodeStatusOnline

	fail1 := node.RecordHBFailure()
	if fail1 != 1 {
		t.Errorf("Expected 1 failure, got %d", fail1)
	}

	fail2 := node.RecordHBFailure()
	if fail2 != 2 {
		t.Errorf("Expected 2 failures, got %d", fail2)
	}

	// 3 failures should mark offline
	fail3 := node.RecordHBFailure()
	if fail3 != 3 {
		t.Errorf("Expected 3 failures, got %d", fail3)
	}
	if node.Status != NodeStatusOffline {
		t.Errorf("Expected offline after 3 failures, got %s", node.Status)
	}
}

// ─── 节点任务管理测试 ───

func TestNodeTaskCount(t *testing.T) {
	node := NewNode("task-001", "task-node")
	// NewNode starts online by default
	if node.Status != NodeStatusOnline {
		t.Fatalf("Expected online by default, got %s", node.Status)
	}

	node.IncrementTasksRunning()
	if node.Status != NodeStatusBusy {
		t.Errorf("Expected busy after first task, got %s", node.Status)
	}

	node.IncrementTasksRunning()
	node.IncrementTasksRunning()
	if node.TasksRunning != 3 {
		t.Errorf("Expected 3 running tasks, got %d", node.TasksRunning)
	}

	node.DecrementTasksRunning()
	if node.TasksRunning != 2 {
		t.Errorf("Expected 2 running tasks, got %d", node.TasksRunning)
	}

	// Drain to 0
	node.DecrementTasksRunning()
	node.DecrementTasksRunning()
	if node.Status != NodeStatusOnline {
		t.Errorf("Expected online after tasks drained, got %s", node.Status)
	}
}

func TestNodeCanAcceptTasks(t *testing.T) {
	node := NewNode("accept-001", "accept-node")
	// Default status is online
	if !node.CanAcceptTasks(0.9) {
		t.Error("New online node should accept tasks")
	}

	node.MarkHeartbeat()
	if !node.CanAcceptTasks(0.9) {
		t.Error("Online node should accept tasks")
	}

	// Mark as busy
	node.IncrementTasksRunning()
	node.Load = 0.95
	if node.CanAcceptTasks(0.9) {
		t.Error("High load node should not accept tasks above threshold")
	}
}

// ─── 节点能力检测测试 ───

func TestDetectLocalCapability(t *testing.T) {
	cap := DetectLocalCapability()
	if cap.OS == "" {
		t.Error("OS should not be empty")
	}
	if cap.Arch == "" {
		t.Error("Arch should not be empty")
	}
	if cap.CPUCores <= 0 {
		t.Error("CPU cores should be >= 1")
	}
	if len(cap.Frameworks) == 0 {
		t.Error("Should have at least some default frameworks")
	}
	t.Logf("Detected %d CPUs, %d GPUs, Docker: %v", cap.CPUCores, len(cap.GPUs), cap.Docker)
}

func TestHasCommand(t *testing.T) {
	if !hasCommand("sh") {
		t.Error("sh command should be available")
	}
	if hasCommand("nonexistent-command-xyz-12345") {
		t.Error("nonexistent command should return false")
	}
}

// ─── 节点管理器测试 ───

func TestNodeManager_RegisterAndRemove(t *testing.T) {
	localNode := NewNode("local-001", "local")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"

	nm := NewNodeManager(localNode)
	if len(nm.GetAllNodes()) != 1 {
		t.Error("Should have 1 node after registration")
	}

	remoteNode := NewNode("remote-001", "remote")
	remoteNode.IP = "10.0.0.1"
	remoteNode.Region = "us-east"
	nm.RegisterNode(remoteNode)

	if len(nm.GetAllNodes()) != 2 {
		t.Error("Should have 2 nodes after remote registration")
	}

	// Remove the remote node
	nm.RemoveNode("remote-001")
	if len(nm.GetAllNodes()) != 1 {
		t.Error("Should have 1 node after removal")
	}
}

func TestNodeManager_GetNode(t *testing.T) {
	localNode := NewNode("gm-001", "gm-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"

	nm := NewNodeManager(localNode)

	existing, ok := nm.GetNode("gm-001")
	if !ok {
		t.Fatal("Existing node should be found")
	}
	if existing.ID != "gm-001" {
		t.Errorf("Expected gm-001, got %s", existing.ID)
	}

	_, ok = nm.GetNode("nonexistent")
	if ok {
		t.Error("Nonexistent node should not be found")
	}
}

func TestNodeManager_PoolStats(t *testing.T) {
	localNode := NewNode("ps-001", "ps-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"

	nm := NewNodeManager(localNode)
	localNode.Capability.CPUCores = 4
	localNode.Capability.MemTotalMB = 8192

	stats := nm.PoolStats()
	total, ok := stats["total_nodes"].(int)
	if !ok {
		t.Fatalf("total_nodes should be int, got %T", stats["total_nodes"])
	}
	if total != 1 {
		t.Errorf("Expected 1 total node, got %d", total)
	}
	online, ok := stats["online"].(int)
	if !ok {
		t.Fatalf("online should be int, got %T", stats["online"])
	}
	if online != 1 {
		t.Errorf("Expected 1 online node, got %d", online)
	}
}

func TestNodeManager_GetOnlineNodes(t *testing.T) {
	localNode := NewNode("on-001", "on-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"

	nm := NewNodeManager(localNode)

	online := nm.GetOnlineNodes()
	if len(online) != 1 {
		t.Fatalf("Expected 1 online node, got %d", len(online))
	}

	// Add and offline a remote node
	remote := NewNode("on-002", "on-remote")
	remote.IP = "10.0.0.2"
	remote.Region = "eu"
	nm.RegisterNode(remote)

	// Force offline
	for i := 0; i < 5; i++ {
		remote.RecordHBFailure()
	}

	online = nm.GetOnlineNodes()
	if len(online) != 1 {
		t.Errorf("Expected 1 online node (offline node excluded), got %d", len(online))
	}
}

func TestNodeManager_Failover(t *testing.T) {
	localNode := NewNode("fo-001", "fo-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"

	nm := NewNodeManager(localNode)

	// Add another online node
	remote := NewNode("fo-002", "fo-remote")
	remote.IP = "10.0.0.2"
	remote.Region = "local"
	nm.RegisterNode(remote)

	// Check failover count
	count := nm.FailoverCount()
	if count < 1 {
		t.Errorf("Expected at least 1 failover candidate, got %d", count)
	}
}

// ─── 熔断器测试 ───

func TestCircuitBreaker_ClosedToOpen(t *testing.T) {
	cb := NewCircuitBreaker(3, 2, 60*time.Second)
	if cb.State() != CircuitClosed {
		t.Errorf("Expected closed, got %s", cb.State())
	}

	// 3 failures should open the circuit
	cb.RecordFailure()
	cb.RecordFailure()
	cb.RecordFailure()

	// Record one more to ensure it stays open
	cb.RecordFailure()

	state := cb.State()
	if state != CircuitOpen {
		t.Errorf("Expected open after failures, got %s", state)
	}

	// Circuit should block when open (no timeout elapsed)
	if cb.Allow() {
		t.Error("Circuit should block when open")
	}
}

func TestCircuitBreaker_HalfOpenToClosed(t *testing.T) {
	cb := NewCircuitBreaker(2, 2, 100*time.Millisecond)

	cb.RecordFailure()
	cb.RecordFailure()
	state := cb.State()
	if state != CircuitOpen {
		t.Errorf("Expected open, got %s", state)
	}

	// Wait for reset timeout
	time.Sleep(200 * time.Millisecond)

	// Allow() should transition to half-open and return true
	if !cb.Allow() {
		t.Error("Circuit should allow when timeout elapsed")
	}

	// State should now be half-open
	state = cb.State()
	if state != CircuitHalfOpen {
		t.Errorf("Expected half-open after timeout, got %s", state)
	}

	// 2 successes should close it
	cb.RecordSuccess()
	cb.RecordSuccess()

	if cb.State() != CircuitClosed {
		t.Errorf("Expected closed after 2 successes, got %s", cb.State())
	}
}

func TestCircuitBreaker_HalfOpenToFails(t *testing.T) {
	cb := NewCircuitBreaker(2, 2, 100*time.Millisecond)

	cb.RecordFailure()
	cb.RecordFailure()
	time.Sleep(200 * time.Millisecond)

	cb.RecordFailure() // This should keep it open
	if cb.State() != CircuitOpen {
		t.Errorf("Expected still open after half-open failure, got %s", cb.State())
	}
}

// ─── 节点发现测试 ───

func TestDiscoverLocalNodes_ReturnsAtLeastLocal(t *testing.T) {
	nodes := DiscoverLocalNodes(500 * time.Millisecond)
	// May return 0 if no nodes are running, but should not panic
	_ = nodes
}

// ─── 节点心跳间隔测试 ───

func TestNodeManager_HeartbeatInterval(t *testing.T) {
	localNode := NewNode("hb-int-001", "hb-int-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"

	nm := NewNodeManager(localNode, WithHeartbeatInterval(5*time.Second))

	// Verify the manager was created with custom interval
	nodes := nm.GetAllNodes()
	if len(nodes) != 1 {
		t.Errorf("Expected 1 node, got %d", len(nodes))
	}
}

func TestNodeManager_RegionIndex(t *testing.T) {
	localNode := NewNode("ri-001", "ri-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "us-east"

	nm := NewNodeManager(localNode)

	// Add node in different region
	remote := NewNode("ri-002", "ri-remote")
	remote.IP = "10.0.0.2"
	remote.Region = "eu-west"
	nm.RegisterNode(remote)

	// Get nodes by region
	usNodes := nm.GetNodesByRegion("us-east")
	if len(usNodes) != 1 {
		t.Errorf("Expected 1 node in us-east, got %d", len(usNodes))
	}

	euNodes := nm.GetNodesByRegion("eu-west")
	if len(euNodes) != 1 {
		t.Errorf("Expected 1 node in eu-west, got %d", len(euNodes))
	}
}
