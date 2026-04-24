package health

import (
	"net"
	"testing"
	"time"
)

func TestNewHealthMonitor(t *testing.T) {
	hm := NewHealthMonitor(DefaultHealthConfig())
	if hm.nodeHealth == nil {
		t.Fatal("nodeHealth is nil")
	}
}

func TestRegisterNode(t *testing.T) {
	hm := NewHealthMonitor(DefaultHealthConfig())
	hm.RegisterNode("node-001")

	health, err := hm.GetNodeHealth("node-001")
	if err != nil {
		t.Fatalf("GetNodeHealth failed: %v", err)
	}
	if health.NodeID != "node-001" {
		t.Errorf("Expected node-001, got %s", health.NodeID)
	}
}

func TestUnregisterNode(t *testing.T) {
	hm := NewHealthMonitor(DefaultHealthConfig())
	hm.RegisterNode("node-002")
	hm.UnregisterNode("node-002")

	_, err := hm.GetNodeHealth("node-002")
	if err == nil {
		t.Fatal("Expected error for unregistered node")
	}
}

func TestGetAllHealth(t *testing.T) {
	hm := NewHealthMonitor(DefaultHealthConfig())
	hm.RegisterNode("node-003")
	hm.RegisterNode("node-004")

	all := hm.GetAllHealth()
	if len(all) != 2 {
		t.Errorf("Expected 2 nodes, got %d", len(all))
	}
}

func TestCustomCheckFunc(t *testing.T) {
	hm := NewHealthMonitor(DefaultHealthConfig())
	hm.RegisterNode("custom-node")

	// 设置自定义检查函数 - 总是成功
	hm.SetCheckFunc(func(nodeID string) (HealthCheckResult, error) {
		return HealthCheckResult{
			NodeID:    nodeID,
			Success:   true,
			Latency:   10 * time.Millisecond,
			Timestamp: time.Now(),
		}, nil
	})

	result, err := hm.CheckNode("custom-node")
	if err != nil {
		t.Fatalf("CheckNode failed: %v", err)
	}
	if !result.Success {
		t.Error("Expected success")
	}
}

func TestMultipleChecks(t *testing.T) {
	hm := NewHealthMonitor(HealthMonitorConfig{
		HealthyThreshold:   3,
		UnhealthyThreshold: 3,
		MaxRecentChecks:    5,
	})
	hm.RegisterNode("multi-node")

	// 设置成功检查
	hm.SetCheckFunc(func(nodeID string) (HealthCheckResult, error) {
		return HealthCheckResult{
			NodeID:    nodeID,
			Success:   true,
			Latency:   10 * time.Millisecond,
			Timestamp: time.Now(),
		}, nil
	})

	// 执行 3 次成功检查
	for i := 0; i < 3; i++ {
		hm.CheckNode("multi-node")
	}

	health, _ := hm.GetNodeHealth("multi-node")
	if health.Status != "healthy" {
		t.Errorf("Expected healthy after 3 successes, got %s", health.Status)
	}
	if health.SuccessRate != 1.0 {
		t.Errorf("Expected 100%% success rate, got %.2f", health.SuccessRate)
	}
}

func TestUnhealthyAfterFailures(t *testing.T) {
	hm := NewHealthMonitor(HealthMonitorConfig{
		HealthyThreshold:   3,
		UnhealthyThreshold: 2, // 降低阈值以便测试
		MaxRecentChecks:    5,
	})
	hm.RegisterNode("fail-node")

	// 设置失败检查
	hm.SetCheckFunc(func(nodeID string) (HealthCheckResult, error) {
		return HealthCheckResult{
			NodeID:    nodeID,
			Success:   false,
			Error:     "connection refused",
			Timestamp: time.Now(),
		}, nil
	})

	// 执行 3 次失败检查
	for i := 0; i < 3; i++ {
		hm.CheckNode("fail-node")
	}

	health, _ := hm.GetNodeHealth("fail-node")
	if health.Status != "unhealthy" {
		t.Errorf("Expected unhealthy after 3 failures, got %s", health.Status)
	}
}

func TestDegradedState(t *testing.T) {
	hm := NewHealthMonitor(HealthMonitorConfig{
		HealthyThreshold:   3,
		UnhealthyThreshold: 3,
		MaxRecentChecks:    5,
	})
	hm.RegisterNode("degraded-node")

	// 先成功再失败
	hm.SetCheckFunc(func(nodeID string) (HealthCheckResult, error) {
		passed := hm.nodeHealth[nodeID].TotalChecks
		if passed < 2 {
			return HealthCheckResult{
				NodeID:    nodeID,
				Success:   true,
				Latency:   10 * time.Millisecond,
				Timestamp: time.Now(),
			}, nil
		}
		return HealthCheckResult{
			NodeID:    nodeID,
			Success:   false,
			Error:     "error",
			Timestamp: time.Now(),
		}, nil
	})

	// 2 次成功 + 2 次失败
	for i := 0; i < 4; i++ {
		hm.CheckNode("degraded-node")
	}

	health, _ := hm.GetNodeHealth("degraded-node")
	if health.Status != "degraded" {
		t.Errorf("Expected degraded, got %s", health.Status)
	}
}

func TestGetHealthyCount(t *testing.T) {
	hm := NewHealthMonitor(HealthMonitorConfig{
		HealthyThreshold:   2,
		UnhealthyThreshold: 2,
		MaxRecentChecks:    5,
	})

	hm.RegisterNode("healthy-1")
	hm.RegisterNode("unhealthy-1")

	hm.SetCheckFunc(func(nodeID string) (HealthCheckResult, error) {
		if nodeID == "healthy-1" {
			return HealthCheckResult{
				NodeID:    nodeID,
				Success:   true,
				Latency:   10 * time.Millisecond,
				Timestamp: time.Now(),
			}, nil
		}
		return HealthCheckResult{
			NodeID:    nodeID,
			Success:   false,
			Error:     "error",
			Timestamp: time.Now(),
		}, nil
	})

	// 2 次检查使 healthy-1 变为 healthy
	for i := 0; i < 2; i++ {
		hm.CheckNode("healthy-1")
	}
	for i := 0; i < 2; i++ {
		hm.CheckNode("unhealthy-1")
	}

	if hm.GetHealthyCount() != 1 {
		t.Errorf("Expected 1 healthy, got %d", hm.GetHealthyCount())
	}
	if hm.GetUnhealthyCount() != 1 {
		t.Errorf("Expected 1 unhealthy, got %d", hm.GetUnhealthyCount())
	}
}

func TestGetStats(t *testing.T) {
	hm := NewHealthMonitor(HealthMonitorConfig{
		CheckInterval: 30 * time.Second,
		Timeout:       5 * time.Second,
	})

	hm.RegisterNode("node-a")
	hm.RegisterNode("node-b")

	stats := hm.GetStats()
	if stats["total_nodes"] != 2 {
		t.Errorf("Expected 2 total nodes, got %v", stats["total_nodes"])
	}
}

func TestNoCheckFunc(t *testing.T) {
	hm := NewHealthMonitor(DefaultHealthConfig())
	hm.SetCheckFunc(nil)  // 显式设置为 nil
	hm.RegisterNode("no-func")

	_, err := hm.CheckNode("no-func")
	if err == nil {
		t.Fatal("Expected error when no check function")
	}
}

// 使用真实 TCP 连接的集成测试
func TestRealTCPCheck(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real TCP check in short mode")
	}

	// 启动一个临时 TCP 服务器
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Skip("could not start test listener")
	}
	defer listener.Close()

	addr := listener.Addr().String()

	hm := NewHealthMonitor(DefaultHealthConfig())
	hm.RegisterNode(addr)

	result, err := hm.CheckNode(addr)
	if err != nil {
		t.Fatalf("CheckNode failed: %v", err)
	}
	if !result.Success {
		t.Errorf("Expected success, error: %s", result.Error)
	}
	if !result.TCPConnected {
		t.Error("Expected TCP connected")
	}
	if result.Latency <= 0 {
		t.Error("Expected positive latency")
	}
}

func BenchmarkRegisterNodes(b *testing.B) {
	hm := NewHealthMonitor(DefaultHealthConfig())
	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		nodeID := "bench-node-" + string(rune('0'+i%10))
		hm.RegisterNode(nodeID)
	}
}
