package scheduler

import (
	"fmt"
	"testing"
	"time"
)

func TestNewScheduler(t *testing.T) {
	s := NewScheduler(DefaultConfig())
	if s.regionIndex == nil {
		t.Fatal("regionIndex is nil")
	}
	if s.nodeIndex == nil {
		t.Fatal("nodeIndex is nil")
	}
}

func TestRegisterNode(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	node := &NodeInfo{
		ID:         "node-us-east-001",
		Region:     "us-east",
		Status:     "online",
		GPUType:    "A100",
		CPUCores:   32,
		MemoryGB:   128,
		GPUMemoryGB: 80,
		MaxTasks:   10,
		SuccessRate: 1.0,
	}

	if err := s.RegisterNode(node); err != nil {
		t.Fatalf("RegisterNode failed: %v", err)
	}

	// Verify node is registered
	if _, exists := s.nodeIndex["node-us-east-001"]; !exists {
		t.Fatal("Node not found in index")
	}

	// Verify region is created
	if _, exists := s.regionIndex["us-east"]; !exists {
		t.Fatal("Region not created")
	}

	// Verify duplicate registration fails
	if err := s.RegisterNode(node); err == nil {
		t.Fatal("Expected error for duplicate node")
	}
}

func TestRegisterMultipleNodes(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	regions := []string{"us-east", "us-west", "eu-west"}
	for _, region := range regions {
		for j := 0; j < 3; j++ {
			node := &NodeInfo{
				ID:          fmt.Sprintf("%s-%03d", region, j),
				Region:      region,
				Status:      "online",
				GPUType:     "A100",
				CPUCores:    32,
				MemoryGB:    128,
				GPUMemoryGB: 80,
				MaxTasks:    10,
				SuccessRate: 0.95,
			}
			if err := s.RegisterNode(node); err != nil {
				t.Fatalf("Failed to register %s: %v", node.ID, err)
			}
		}
	}

	// Check total nodes
	if len(s.nodeIndex) != 9 {
		t.Errorf("Expected 9 nodes, got %d", len(s.nodeIndex))
	}

	// Check region distribution
	if len(s.regionIndex["us-east"].Nodes) != 3 {
		t.Errorf("Expected 3 us-east nodes, got %d", len(s.regionIndex["us-east"].Nodes))
	}
}

func TestScheduleTaskBasic(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	// Register a node
	node := &NodeInfo{
		ID:          "node-sched-001",
		Region:      "us-east",
		Status:      "online",
		GPUType:     "A100",
		MaxTasks:    5,
		SuccessRate: 1.0,
		NetworkLatency: 50,
	}
	s.RegisterNode(node)

	// Schedule a task
	result := s.ScheduleTask("task-001", "us-east", 5)

	if result == nil {
		t.Fatal("Schedule result is nil")
	}
	if result.NodeID != "node-sched-001" {
		t.Errorf("Expected node-sched-001, got %s", result.NodeID)
	}
	if result.Reason == "" {
		t.Error("Expected non-empty reason")
	}

	// Verify task was assigned
	if node.ActiveTasks != 1 {
		t.Errorf("Expected 1 active task, got %d", node.ActiveTasks)
	}
}

func TestScheduleTaskNoCandidates(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	result := s.ScheduleTask("task-no-node", "", 5)
	if result.Reason != "no available nodes" {
		t.Errorf("Expected 'no available nodes', got '%s'", result.Reason)
	}
}

func TestScheduleTaskCapacityExhausted(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	// Register a node with capacity 2
	node := &NodeInfo{
		ID:          "node-cap-001",
		Region:      "us-east",
		Status:      "online",
		MaxTasks:    2,
		SuccessRate: 1.0,
		NetworkLatency: 50,
	}
	s.RegisterNode(node)

	// Fill capacity
	s.ScheduleTask("task-cap-001", "", 5)
	s.ScheduleTask("task-cap-002", "", 5)

	// Third should fail
	result := s.ScheduleTask("task-cap-003", "", 5)
	if result.NodeID != "" {
		t.Errorf("Expected no node, got %s", result.NodeID)
	}

	// Verify capacity is full
	if node.ActiveTasks != 2 {
		t.Errorf("Expected 2 active tasks, got %d", node.ActiveTasks)
	}
}

func TestScheduleTaskOfflineNode(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	// Register online and offline nodes
	onlineNode := &NodeInfo{
		ID:           "node-online-001",
		Region:       "us-east",
		Status:       "online",
		MaxTasks:     10,
		SuccessRate:  1.0,
		NetworkLatency: 50,
		LastHeartbeat: time.Now(),
	}
	offlineNode := &NodeInfo{
		ID:           "node-offline-001",
		Region:       "us-east",
		Status:       "offline",
		MaxTasks:     10,
		SuccessRate:  1.0,
		NetworkLatency: 50,
	}
	s.RegisterNode(onlineNode)
	s.RegisterNode(offlineNode)

	result := s.ScheduleTask("task-001", "", 5)
	if result.NodeID != "node-online-001" {
		t.Errorf("Expected online node, got %s", result.NodeID)
	}
}

func TestScheduleTaskTimeoutNode(t *testing.T) {
	s := NewScheduler(SchedulerConfig{
		NodeTimeout: 60,
	})

	// Register node with old heartbeat
	node := &NodeInfo{
		ID:            "node-timeout-001",
		Region:        "us-east",
		Status:        "online",
		MaxTasks:      10,
		SuccessRate:   1.0,
		NetworkLatency: 50,
		LastHeartbeat: time.Now().Add(-2 * time.Hour), // 2 hours ago
	}
	s.RegisterNode(node)

	result := s.ScheduleTask("task-001", "", 5)
	if result.NodeID == "node-timeout-001" {
		t.Error("Should not schedule to timed-out node")
	}

	// Verify node was marked offline
	if node.Status != "offline" {
		t.Errorf("Expected offline, got %s", node.Status)
	}
}

func TestScheduleTaskRegionAffinity(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	// Register nodes in different regions
	for _, region := range []string{"us-east", "eu-west", "ap-southeast"} {
		node := &NodeInfo{
			ID:          fmt.Sprintf("node-%s-001", region),
			Region:      region,
			Status:      "online",
			MaxTasks:    10,
			SuccessRate: 1.0,
			NetworkLatency: 50,
		}
		s.RegisterNode(node)
	}

	// Schedule with region affinity
	result := s.ScheduleTask("task-001", "eu-west", 5)
	if result.NodeID != "node-eu-west-001" {
		t.Errorf("Expected eu-west node, got %s", result.NodeID)
	}
}

func TestUpdateNodeHeartbeat(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	node := &NodeInfo{
		ID:           "node-hb-001",
		Region:       "us-east",
		Status:       "online",
		MaxTasks:     10,
		SuccessRate:  1.0,
		NetworkLatency: 50,
	}
	s.RegisterNode(node)

	// Update heartbeat
	err := s.UpdateNodeHeartbeat("node-hb-001", 75, 85.5, 65.0, 60.0)
	if err != nil {
		t.Fatalf("UpdateNodeHeartbeat failed: %v", err)
	}

	// Verify update
	if node.NetworkLatency != 75 {
		t.Errorf("Expected latency 75, got %d", node.NetworkLatency)
	}
	if node.GPUUtil != 85.5 {
		t.Errorf("Expected GPU util 85.5, got %f", node.GPUUtil)
	}
}

func TestUpdateNodeHeartbeatUnknown(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	err := s.UpdateNodeHeartbeat("unknown-node", 50, 50.0, 50.0, 40.0)
	if err == nil {
		t.Fatal("Expected error for unknown node")
	}
}

func TestHealthCheck(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	// Register healthy node
	healthyNode := &NodeInfo{
		ID:            "node-healthy-001",
		Region:        "us-east",
		Status:        "online",
		LastHeartbeat: time.Now(),
		Temperature:   65.0,
		GPUUtil:       75.0,
	}
	s.RegisterNode(healthyNode)

	// Register high-temp node
	hotNode := &NodeInfo{
		ID:            "node-hot-001",
		Region:        "us-east",
		Status:        "online",
		LastHeartbeat: time.Now(),
		Temperature:   92.0,
	}
	s.RegisterNode(hotNode)

	results := s.HealthCheck()

	if results["node-healthy-001"] != "healthy" {
		t.Errorf("Expected healthy, got %s", results["node-healthy-001"])
	}

	if results["node-hot-001"] != "warning (high temp)" {
		t.Errorf("Expected high temp warning, got %s", results["node-hot-001"])
	}
}

func TestCircuitBreakerTrigger(t *testing.T) {
	s := NewScheduler(SchedulerConfig{
		FailureRateThreshold: 0.3,
	})

	// Register node
	node := &NodeInfo{
		ID:          "node-cb-001",
		Region:      "us-east",
		Status:      "online",
		SuccessRate: 0.6,
	}
	s.RegisterNode(node)

	// Simulate failures (failure rate > 30%)
	s.CheckCircuitBreaker("us-east", false)

	// Check if circuit breaker is triggered
	if !s.circuitBreaker["us-east"] {
		t.Error("Expected circuit breaker to be triggered")
	}

	// Verify node is marked as circuit_breaking
	if node.Status != "circuit_breaking" {
		t.Errorf("Expected circuit_breaking, got %s", node.Status)
	}
}

func TestCircuitBreakerClear(t *testing.T) {
	s := NewScheduler(SchedulerConfig{
		FailureRateThreshold: 0.3,
	})

	node := &NodeInfo{
		ID:          "node-cb-clear-001",
		Region:      "us-east",
		Status:      "online",
	}
	s.RegisterNode(node)

	// Trigger circuit breaker
	s.CheckCircuitBreaker("us-east", false)

	// Clear it
	s.ClearCircuitBreaker("us-east")

	// Verify cleared
	if s.circuitBreaker["us-east"] {
		t.Error("Expected circuit breaker to be cleared")
	}

	// Verify node status restored
	if node.Status != "online" {
		t.Errorf("Expected online, got %s", node.Status)
	}
}

func TestCircuitBreakerSkipped(t *testing.T) {
	s := NewScheduler(SchedulerConfig{
		FailureRateThreshold: 0.3,
	})

	// Register nodes in different regions
	for _, region := range []string{"us-east", "eu-west"} {
		node := &NodeInfo{
			ID:          fmt.Sprintf("node-cb-%s-001", region),
			Region:      region,
			Status:      "online",
			MaxTasks:    10,
			SuccessRate: 1.0,
			NetworkLatency: 50,
		}
		s.RegisterNode(node)
	}

	// Trigger circuit breaker on us-east only
	s.CheckCircuitBreaker("us-east", false)

	// eu-west should still be available
	result := s.ScheduleTask("task-001", "", 5)
	if result.NodeID != "node-cb-eu-west-001" {
		t.Errorf("Expected eu-west node, got %s", result.NodeID)
	}
}

func TestMarkNodeOffline(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	node := &NodeInfo{
		ID:          "node-offline-001",
		Region:      "us-east",
		Status:      "online",
		MaxTasks:    10,
	}
	s.RegisterNode(node)

	s.MarkNodeOffline("node-offline-001")
	if node.Status != "offline" {
		t.Errorf("Expected offline, got %s", node.Status)
	}
}

func TestGetStats(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	// Register some nodes
	for i := 0; i < 3; i++ {
		node := &NodeInfo{
			ID:          fmt.Sprintf("node-stats-%03d", i),
			Region:      "us-east",
			Status:      "online",
			MaxTasks:    10,
			SuccessRate: 0.95,
			NetworkLatency: 50,
		}
		s.RegisterNode(node)
	}

	// Schedule a task
	s.ScheduleTask("task-stats-001", "", 5)

	stats := s.GetStats()

	if stats["total_nodes"] != 3 {
		t.Errorf("Expected 3 total nodes, got %v", stats["total_nodes"])
	}
	if stats["online_nodes"] != 3 {
		t.Errorf("Expected 3 online nodes, got %v", stats["online_nodes"])
	}
	if stats["total_tasks"] != 1 {
		t.Errorf("Expected 1 total task, got %v", stats["total_tasks"])
	}
}

func TestGetCandidates(t *testing.T) {
	s := NewScheduler(DefaultConfig())

	// Register various nodes
	nodes := []*NodeInfo{
		{ID: "cand-online", Region: "us-east", Status: "online", MaxTasks: 10, NetworkLatency: 50},
		{ID: "cand-offline", Region: "us-east", Status: "offline", MaxTasks: 10, NetworkLatency: 50},
		{ID: "cand-draining", Region: "us-east", Status: "draining", MaxTasks: 10, NetworkLatency: 50},
		{ID: "cand-full", Region: "us-east", Status: "online", MaxTasks: 1, NetworkLatency: 50},
	}

	for _, n := range nodes {
		s.RegisterNode(n)
	}
	// Fill up cand-full
	s.nodeIndex["cand-full"].ActiveTasks = 1

	candidates := s.getCandidates("")
	candidateIDs := make(map[string]bool)
	for _, c := range candidates {
		candidateIDs[c.ID] = true
	}

	if !candidateIDs["cand-online"] {
		t.Error("Expected cand-online in candidates")
	}
	if candidateIDs["cand-offline"] {
		t.Error("Should not include offline node")
	}
	if candidateIDs["cand-draining"] {
		t.Error("Should not include draining node")
	}
	if candidateIDs["cand-full"] {
		t.Error("Should not include full node")
	}
}

func BenchmarkScheduleTask(b *testing.B) {
	s := NewScheduler(DefaultConfig())

	// Pre-register 100 nodes
	for i := 0; i < 100; i++ {
		region := []string{"us-east", "us-west", "eu-west", "ap-southeast"}[i%4]
		node := &NodeInfo{
			ID:             fmt.Sprintf("bench-node-%03d", i),
			Region:         region,
			Status:         "online",
			MaxTasks:       100,
			SuccessRate:    0.95,
			NetworkLatency: 50,
		}
		s.RegisterNode(node)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		s.ScheduleTask(fmt.Sprintf("bench-task-%d", i), "", 5)
	}
}
