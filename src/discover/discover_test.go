package discover

import (
	"testing"
	"time"
)

func TestNewDiscoverer(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())
	if d.nodes == nil {
		t.Fatal("nodes map is nil")
	}
}

func TestRegisterNode(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	node := &NodeInfo{
		NodeID:    "node-discover-001",
		IPAddress: "192.168.1.100",
		Port:      8282,
		GPUType:   "A100",
		Region:    "us-east",
	}

	d.RegisterNode(node)

	// Verify node is registered
	n, err := d.GetNode("node-discover-001")
	if err != nil {
		t.Fatalf("GetNode failed: %v", err)
	}
	if n.IPAddress != "192.168.1.100" {
		t.Errorf("Expected IP 192.168.1.100, got %s", n.IPAddress)
	}
}

func TestUnregisterNode(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	node := &NodeInfo{
		NodeID:    "node-discover-002",
		IPAddress: "192.168.1.101",
		Port:      8283,
	}
	d.RegisterNode(node)

	d.UnregisterNode("node-discover-002")

	_, err := d.GetNode("node-discover-002")
	if err == nil {
		t.Fatal("Expected error for unregistered node")
	}
}

func TestGetAllNodes(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	d.RegisterNode(&NodeInfo{NodeID: "node-001", IPAddress: "10.0.0.1", Port: 8282})
	d.RegisterNode(&NodeInfo{NodeID: "node-002", IPAddress: "10.0.0.2", Port: 8283})
	d.RegisterNode(&NodeInfo{NodeID: "node-003", IPAddress: "10.0.0.3", Port: 8284})

	nodes := d.GetAllNodes()
	if len(nodes) != 3 {
		t.Errorf("Expected 3 nodes, got %d", len(nodes))
	}
}

func TestHeartbeat(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	d.RegisterNode(&NodeInfo{
		NodeID:    "node-hb-001",
		IPAddress: "10.0.0.1",
		Port:      8282,
	})

	now := time.Now()
	err := d.Heartbeat("node-hb-001", now)
	if err != nil {
		t.Fatalf("Heartbeat failed: %v", err)
	}

	node, _ := d.GetNode("node-hb-001")
	if !node.LastSeen.Equal(now) {
		t.Errorf("Expected LastSeen to be updated")
	}
}

func TestHeartbeatUnknown(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	err := d.Heartbeat("unknown-node", time.Now())
	if err == nil {
		t.Fatal("Expected error for unknown node")
	}
}

func TestIsNodeAlive(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	d.RegisterNode(&NodeInfo{
		NodeID:    "node-alive-001",
		IPAddress: "10.0.0.1",
		Port:      8282,
	})

	// New node should be alive
	if !d.IsNodeAlive("node-alive-001", 5*time.Minute) {
		t.Error("Expected node to be alive")
	}
}

func TestIsNodeNotAlive(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	d.RegisterNode(&NodeInfo{
		NodeID:    "node-dead-001",
		IPAddress: "10.0.0.1",
		Port:      8282,
	})

	// Manually set old LastSeen
	d.mu.Lock()
	d.nodes["node-dead-001"].LastSeen = time.Now().Add(-10 * time.Minute)
	d.mu.Unlock()

	if d.IsNodeAlive("node-dead-001", 5*time.Minute) {
		t.Error("Expected node to be dead")
	}
}

func TestGetAliveNodes(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	d.RegisterNode(&NodeInfo{
		NodeID:    "node-alive-1",
		IPAddress: "10.0.0.1",
		Port:      8282,
	})

	d.RegisterNode(&NodeInfo{
		NodeID:    "node-dead-1",
		IPAddress: "10.0.0.2",
		Port:      8283,
	})

	// Manually set last node as dead
	d.mu.Lock()
	d.nodes["node-dead-1"].LastSeen = time.Now().Add(-10 * time.Minute)
	d.mu.Unlock()

	alive := d.GetAliveNodes(5 * time.Minute)
	if len(alive) != 1 {
		t.Errorf("Expected 1 alive node, got %d", len(alive))
	}
}

func TestDiscoverByManual(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	d.RegisterNode(&NodeInfo{
		NodeID:    "node-manual-001",
		IPAddress: "10.0.0.1",
		Port:      8282,
	})

	result := d.DiscoverByManual()
	if result.TotalFound != 1 {
		t.Errorf("Expected 1 node found, got %d", result.TotalFound)
	}
	if result.Method != "manual" {
		t.Errorf("Expected method 'manual', got %s", result.Method)
	}
}

func TestGetStats(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	d.RegisterNode(&NodeInfo{NodeID: "node-stats-001", IPAddress: "10.0.0.1", Port: 8282})
	d.RegisterNode(&NodeInfo{NodeID: "node-stats-002", IPAddress: "10.0.0.2", Port: 8283})

	stats := d.GetStats()
	if stats["total_nodes"] != 2 {
		t.Errorf("Expected 2 total nodes, got %v", stats["total_nodes"])
	}
}

func TestNodeLabels(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	d.RegisterNode(&NodeInfo{
		NodeID:    "node-labels-001",
		IPAddress: "10.0.0.1",
		Port:      8282,
		Labels: map[string]string{
			"datacenter": "dc1",
			"tier":       "gpu",
		},
	})

	node, _ := d.GetNode("node-labels-001")
	if node.Labels["datacenter"] != "dc1" {
		t.Errorf("Expected datacenter dc1, got %s", node.Labels["datacenter"])
	}
}

func TestNodeCapacity(t *testing.T) {
	d := NewDiscoverer(DefaultConfig())

	d.RegisterNode(&NodeInfo{
		NodeID:    "node-cap-001",
		IPAddress: "10.0.0.1",
		Port:      8282,
		Capacity: map[string]float64{
			"gpu_hours": 100.0,
			"cpu_hours": 200.0,
		},
	})

	node, _ := d.GetNode("node-cap-001")
	if node.Capacity["gpu_hours"] != 100.0 {
		t.Errorf("Expected 100 gpu_hours, got %f", node.Capacity["gpu_hours"])
	}
}

func TestGetLocalIP(t *testing.T) {
	ip, err := GetLocalIP()
	if err != nil {
		t.Skipf("GetLocalIP failed (expected in sandbox): %v", err)
	}

	if ip == "" {
		t.Error("Expected non-empty IP")
	}
}

func TestGetLocalPorts(t *testing.T) {
	ports, err := GetLocalPorts(20000, 5)
	if err != nil {
		t.Skipf("GetLocalPorts failed (expected in sandbox): %v", err)
	}

	// Should have some available ports
	if len(ports) < 1 {
		t.Error("Expected at least 1 available port")
	}
}

func BenchmarkRegisterNodes(b *testing.B) {
	d := NewDiscoverer(DefaultConfig())
	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		node := &NodeInfo{
			NodeID:    "bench-node-" + string(rune('0'+i%10)),
			IPAddress: "10.0.0.1",
			Port:      8282,
		}
		d.RegisterNode(node)
	}
}
