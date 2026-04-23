// Package scheduler - comprehensive tests for distributed scheduler
package scheduler

import (
	"testing"

	"github.com/chenqifu-Ai/computehub/src/node"
)

// ─── 调度器基础测试 ───

func createTestScheduler() (*Scheduler, *node.NodeManager) {
	localNode := node.NewNode("test-local", "test-local-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"
	localNode.Capability.CPUCores = 4
	localNode.Capability.MemTotalMB = 8192
	localNode.Capability.GPUEnabled = true
	localNode.Capability.GPUs = []node.GPUInfo{
		{Index: 0, Name: "TestGPU", MemMB: 8192},
	}

	nm := node.NewNodeManager(localNode)
	sc := NewScheduler(nm, StrategyBalanced)
	return sc, nm
}

func TestNewScheduler(t *testing.T) {
	sc, _ := createTestScheduler()
	if sc == nil {
		t.Fatal("Scheduler should not be nil")
	}
	if sc.primary != StrategyBalanced {
		t.Errorf("Expected balanced strategy, got %s", sc.primary)
	}
}

func TestScheduler_ScheduleNoCandidates(t *testing.T) {
	sc, _ := createTestScheduler()

	_, err := sc.Schedule("task-001", TaskRequirement{
		ResourceType: "gpu",
		GPUCount:     100, // No node has 100 GPUs
	})
	if err == nil {
		t.Error("Expected error when no candidates available")
	}
}

func TestScheduler_ScheduleLocalNode(t *testing.T) {
	sc, _ := createTestScheduler()

	node, err := sc.Schedule("task-002", TaskRequirement{
		ResourceType: "cpu",
		CPUCount:     2,
		MemoryGB:     4,
	})
	if err != nil {
		t.Fatalf("Schedule should succeed: %v", err)
	}
	if node == nil {
		t.Error("Node should not be nil")
	}
	if node.ID != "test-local" {
		t.Errorf("Expected local node, got %s", node.ID)
	}
}

func TestScheduler_ScheduleGPU(t *testing.T) {
	sc, _ := createTestScheduler()

	node, err := sc.Schedule("task-003", TaskRequirement{
		ResourceType: "gpu",
		GPUCount:     1,
	})
	if err != nil {
		t.Fatalf("GPU schedule should succeed: %v", err)
	}
	if !node.Capability.GPUEnabled {
		t.Error("Selected node should have GPU enabled")
	}
}

func TestScheduler_MultipleSchedules(t *testing.T) {
	sc, _ := createTestScheduler()

	for i := 0; i < 3; i++ {
		_, err := sc.Schedule("task-multi", TaskRequirement{
			ResourceType: "cpu",
			CPUCount:     1,
		})
		if err != nil {
			t.Errorf("Schedule %d failed: %v", i, err)
		}
	}

	stats := sc.Stats()
	if stats["total_scheduled"] != int64(3) {
		t.Errorf("Expected 3 scheduled, got %v", stats["total_scheduled"])
	}
}

// ─── 节点筛选测试 ───

func TestFilterByResourceGPU(t *testing.T) {
	sc, nm := createTestScheduler()

	// Add a CPU-only node
	cpuNode := node.NewNode("cpu-001", "cpu-node")
	cpuNode.IP = "10.0.0.1"
	cpuNode.Region = "local"
	cpuNode.Capability.GPUEnabled = false
	cpuNode.Capability.CPUCores = 8
	cpuNode.Capability.MemTotalMB = 16384
	nm.RegisterNode(cpuNode)

	// GPU task should pick GPU node
	node, err := sc.Schedule("gpu-task", TaskRequirement{
		ResourceType: "gpu",
		GPUCount:     1,
	})
	if err != nil {
		t.Fatalf("GPU task should succeed: %v", err)
	}
	if !node.Capability.GPUEnabled {
		t.Error("Should pick GPU node for GPU task")
	}
}

func TestFilterByResourceCPU(t *testing.T) {
	sc, _ := createTestScheduler()

	_, err := sc.Schedule("cpu-task", TaskRequirement{
		ResourceType: "cpu",
		CPUCount:     4,
	})
	if err != nil {
		t.Fatalf("CPU task should succeed: %v", err)
	}
}

func TestFilterByMemory(t *testing.T) {
	sc, _ := createTestScheduler()

	_, err := sc.Schedule("mem-task", TaskRequirement{
		ResourceType: "cpu",
		MemoryGB:     8,
	})
	if err != nil {
		t.Fatalf("Memory task should succeed: %v", err)
	}
}

// ─── 调度策略测试 ───

func TestStrategyGPUFirst(t *testing.T) {
	localNode := node.NewNode("gpu-first-001", "gpu-first")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"
	localNode.Capability.GPUEnabled = true
	localNode.Capability.CPUCores = 8
	localNode.Capability.MemTotalMB = 16384
	localNode.Capability.GPUs = []node.GPUInfo{
		{Index: 0, Name: "A100", MemMB: 40960},
	}

	nm := node.NewNodeManager(localNode)
	sc := NewScheduler(nm, StrategyGPUFirst)

	_, err := sc.Schedule("gpu-first-task", TaskRequirement{
		ResourceType: "gpu",
		GPUCount:     1,
	})
	if err != nil {
		t.Fatalf("GPU-first should succeed: %v", err)
	}
}

func TestStrategyRoundRobin(t *testing.T) {
	localNode := node.NewNode("rr-001", "rr-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"
	localNode.Capability.CPUCores = 4
	localNode.Capability.MemTotalMB = 8192

	nm := node.NewNodeManager(localNode)
	sc := NewScheduler(nm, StrategyRoundRobin)

	for i := 0; i < 3; i++ {
		node, err := sc.Schedule("rr-task", TaskRequirement{
			ResourceType: "cpu",
			CPUCount:     1,
		})
		if err != nil {
			t.Fatalf("Round-robin task %d failed: %v", i, err)
		}
		_ = node
	}
}

func TestStrategyLeastLoad(t *testing.T) {
	localNode := node.NewNode("load-001", "load-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"
	localNode.Capability.CPUCores = 4
	localNode.Capability.MemTotalMB = 8192

	nm := node.NewNodeManager(localNode)
	sc := NewScheduler(nm, StrategyLeastLoad)

	_, err := sc.Schedule("least-load-task", TaskRequirement{
		ResourceType: "cpu",
		CPUCount:     1,
	})
	if err != nil {
		t.Fatalf("Least-load should succeed: %v", err)
	}
}

// ─── 策略列表测试 ───

func TestAvailableStrategies(t *testing.T) {
	strategies := AvailableStrategies()
	if len(strategies) != 6 {
		t.Errorf("Expected 6 strategies, got %d", len(strategies))
	}

	expected := []Strategy{
		StrategyLeastLoad,
		StrategyGPUFirst,
		StrategyLatency,
		StrategyGeoProximity,
		StrategyRoundRobin,
		StrategyBalanced,
	}

	for i, expected := range expected {
		if i >= len(strategies) || strategies[i] != expected {
			t.Errorf("Strategy mismatch at %d: got %v, want %v", i, strategies, expected)
		}
	}
}

// ─── 批量调度测试 ───

func TestScheduler_BatchSchedule(t *testing.T) {
	sc, _ := createTestScheduler()

	tasks := []scheduledTask{
		{TaskID: "batch-001", Requirement: TaskRequirement{ResourceType: "cpu", CPUCount: 1}},
		{TaskID: "batch-002", Requirement: TaskRequirement{ResourceType: "cpu", CPUCount: 2}},
	}

	results := sc.ScheduleBatch(tasks)
	if len(results) != 2 {
		t.Errorf("Expected 2 results, got %d", len(results))
	}

	for i, r := range results {
		if r.Error != nil {
			t.Errorf("Batch task %d failed: %v", i, r.Error)
		}
	}
}

// ─── 统计测试 ───

func TestScheduler_Stats(t *testing.T) {
	sc, _ := createTestScheduler()

	_, _ = sc.Schedule("stat-001", TaskRequirement{ResourceType: "cpu", CPUCount: 1})
	_, _ = sc.Schedule("stat-002", TaskRequirement{ResourceType: "cpu", CPUCount: 1})

	stats := sc.Stats()
	if stats["total_scheduled"] != int64(2) {
		t.Errorf("Expected 2 scheduled, got %v", stats["total_scheduled"])
	}
}

func TestScheduler_QueueSubmit(t *testing.T) {
	sc, _ := createTestScheduler()

	// Submit to queue
	sc.SubmitToQueue("queue-001", TaskRequirement{ResourceType: "cpu", CPUCount: 1})
}

func TestMeetsRequirements(t *testing.T) {
	sc, _ := createTestScheduler()

	localNode, _ := sc.nodeMgr.GetNode("test-local")

	// CPU task on CPU node
	if !sc.meetsRequirements(localNode, TaskRequirement{
		ResourceType: "cpu",
		CPUCount:     2,
	}) {
		t.Error("CPU task should be met by CPU node")
	}

	// GPU task on GPU node
	if !sc.meetsRequirements(localNode, TaskRequirement{
		ResourceType: "gpu",
		GPUCount:     1,
	}) {
		t.Error("GPU task should be met by GPU node")
	}
}

// ─── 超时测试 ───

func TestScheduler_NoNodesOnline(t *testing.T) {
	localNode := node.NewNode("empty-001", "empty-node")
	localNode.IP = "127.0.0.1"
	localNode.Port = 8282
	localNode.Region = "local"

	nm := node.NewNodeManager(localNode)
	// Force offline
	localNode.Status = node.NodeStatusOffline

	sc := NewScheduler(nm, StrategyBalanced)

	_, err := sc.Schedule("no-node-task", TaskRequirement{
		ResourceType: "cpu",
		CPUCount:     1,
	})
	if err == nil {
		t.Error("Expected error when no nodes are online")
	}
}
