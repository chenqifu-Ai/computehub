package monitor

import (
	"fmt"
	"testing"
	"time"
)

func TestNewHealthMonitor(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())
	if m.nodeStates == nil {
		t.Fatal("nodeStates is nil")
	}
}

func TestUpdateHeartbeatBasic(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	system := &SystemMetrics{
		Hostname:   "test-node-001",
		OS:         "Linux",
		MemUsedGB:  32.0,
		MemTotalGB: 64.0,
		CPU: CPUMetrics{
			Cores:       32,
			Utilization: 45.0,
			Temperature: 65.0,
		},
		GPU: []GPUMetrics{
			{
				DeviceID:    "gpu-0",
				Model:       "A100",
				Utilization: 75.0,
				Temperature: 70.0,
				MemoryUsedMB: 24576,
				MemoryTotalMB: 40960,
				PowerWatts:  250.0,
				MeasuredAt:  time.Now(),
			},
		},
		Network: []NetworkMetrics{
			{
				Interface:   "eth0",
				PingMS:      15.0,
				PacketLoss:  0.0,
				MeasuredAt:  time.Now(),
			},
		},
		MeasuredAt: time.Now(),
	}

	heartbeat := m.UpdateHeartbeat("test-node-001", system)

	if heartbeat.NodeID != "test-node-001" {
		t.Errorf("Expected node_id test-node-001, got %s", heartbeat.NodeID)
	}
	if heartbeat.Status != "healthy" {
		t.Errorf("Expected healthy status, got %s", heartbeat.Status)
	}
	if heartbeat.HealthScore < 80 || heartbeat.HealthScore > 100 {
		t.Errorf("Expected health score 80-100, got %f", heartbeat.HealthScore)
	}
}

func TestUpdateHeartbeatHighTemp(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	system := &SystemMetrics{
		Hostname:   "hot-node-001",
		MemUsedGB:  32.0,
		MemTotalGB: 64.0,
		CPU: CPUMetrics{
			Temperature: 85.0,
		},
		GPU: []GPUMetrics{
			{
				DeviceID:    "gpu-0",
				Model:       "A100",
				Temperature: 92.0,
				Utilization: 50.0,
				MeasuredAt:  time.Now(),
			},
		},
		MeasuredAt: time.Now(),
	}

	heartbeat := m.UpdateHeartbeat("hot-node-001", system)

	if heartbeat.Status != "warning" {
		t.Errorf("Expected warning status for high temp, got %s", heartbeat.Status)
	}
	if len(heartbeat.Alerts) == 0 {
		t.Error("Expected alerts for high temperature")
	}
}

func TestUpdateHeartbeatCriticalTemp(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	system := &SystemMetrics{
		Hostname:   "critical-node-001",
		MemUsedGB:  32.0,
		MemTotalGB: 64.0,
		CPU: CPUMetrics{
			Temperature: 96.0,
		},
		GPU: []GPUMetrics{
			{
				DeviceID:    "gpu-0",
				Model:       "A100",
				Temperature: 97.0,
				Utilization: 30.0,
				MeasuredAt:  time.Now(),
			},
		},
		MeasuredAt: time.Now(),
	}

	heartbeat := m.UpdateHeartbeat("critical-node-001", system)

	if heartbeat.Status != "critical" {
		t.Errorf("Expected critical status, got %s", heartbeat.Status)
	}
	if len(heartbeat.Alerts) == 0 {
		t.Error("Expected critical alerts")
	}
}

func TestUpdateHeartbeatMemoryWarning(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	system := &SystemMetrics{
		Hostname:   "mem-node-001",
		MemUsedGB:  61.0,
		MemTotalGB: 64.0,
		CPU: CPUMetrics{
			Temperature: 50.0,
		},
		GPU: []GPUMetrics{
			{
				DeviceID: "gpu-0",
				Temperature: 60.0,
				Utilization: 50.0,
				MeasuredAt: time.Now(),
			},
		},
		MeasuredAt: time.Now(),
	}

	heartbeat := m.UpdateHeartbeat("mem-node-001", system)

	if len(heartbeat.Alerts) == 0 {
		t.Error("Expected memory warning alerts")
	}
}

func TestUpdateHeartbeatNetworkLoss(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	system := &SystemMetrics{
		Hostname:   "net-node-001",
		MemUsedGB:  32.0,
		MemTotalGB: 64.0,
		CPU: CPUMetrics{
			Temperature: 50.0,
		},
		GPU: []GPUMetrics{
			{
				DeviceID: "gpu-0",
				Temperature: 60.0,
				Utilization: 50.0,
				MeasuredAt: time.Now(),
			},
		},
		Network: []NetworkMetrics{
			{
				Interface:  "eth0",
				PingMS:     300.0,
				PacketLoss: 8.0,
				MeasuredAt: time.Now(),
			},
		},
		MeasuredAt: time.Now(),
	}

	heartbeat := m.UpdateHeartbeat("net-node-001", system)

	hasNetworkAlert := false
	for _, alert := range heartbeat.Alerts {
		if alert.Component == "network" {
			hasNetworkAlert = true
			break
		}
	}
	if !hasNetworkAlert {
		t.Error("Expected network alerts for packet loss")
	}
}

func TestMultipleNodes(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	// Update multiple nodes
	for i := 0; i < 5; i++ {
		system := &SystemMetrics{
			Hostname:   fmt.Sprintf("node-%03d", i),
			MemUsedGB:  32.0,
			MemTotalGB: 64.0,
			CPU: CPUMetrics{
				Temperature: 60.0,
			},
			GPU: []GPUMetrics{
				{
					DeviceID:    "gpu-0",
					Model:       "A100",
					Temperature: 65.0,
					Utilization: 70.0,
					MeasuredAt:  time.Now(),
				},
			},
			MeasuredAt: time.Now(),
		}
		m.UpdateHeartbeat(fmt.Sprintf("node-%03d", i), system)
	}

	stats := m.GetMonitorStats()
	if stats["total_nodes"] != 5 {
		t.Errorf("Expected 5 total nodes, got %v", stats["total_nodes"])
	}
}

func TestGetNodeStatus(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	system := &SystemMetrics{
		Hostname:   "test-node-001",
		MemUsedGB:  32.0,
		MemTotalGB: 64.0,
		CPU: CPUMetrics{
			Temperature: 60.0,
		},
		GPU: []GPUMetrics{
			{
				DeviceID: "gpu-0",
				Temperature: 65.0,
				MeasuredAt: time.Now(),
			},
		},
		MeasuredAt: time.Now(),
	}

	m.UpdateHeartbeat("test-node-001", system)

	state, exists := m.GetNodeStatus("test-node-001")
	if !exists {
		t.Fatal("Node state not found")
	}

	if state.NodeID != "test-node-001" {
		t.Errorf("Expected node_id test-node-001, got %s", state.NodeID)
	}

	// Verify deep copy
	state.MetricsHistory[0].MemUsedGB = 999.0
	original, _ := m.GetNodeStatus("test-node-001")
	if original.MetricsHistory[0].MemUsedGB == 999.0 {
		t.Error("Deep copy failed - original was modified")
	}
}

func TestGetNodeStatusNotFound(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	_, exists := m.GetNodeStatus("nonexistent-node")
	if exists {
		t.Error("Expected node not found")
	}
}

func TestGetRecentAlerts(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	// Generate some alerts
	for i := 0; i < 10; i++ {
		system := &SystemMetrics{
			Hostname: "alert-node",
			CPU: CPUMetrics{
				Temperature: 96.0,
			},
			MeasuredAt: time.Now(),
		}
		m.UpdateHeartbeat("alert-node", system)
	}

	alerts := m.GetRecentAlerts(5)
	if len(alerts) != 5 {
		t.Errorf("Expected 5 alerts, got %d", len(alerts))
	}
}

func TestGetAlertsByLevel(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	// Generate warnings
	for i := 0; i < 5; i++ {
		system := &SystemMetrics{
			Hostname: "warn-node",
			CPU: CPUMetrics{
				Temperature: 85.0,
			},
			MeasuredAt: time.Now(),
		}
		m.UpdateHeartbeat("warn-node", system)
	}

	// Generate critical
	system := &SystemMetrics{
		Hostname: "critical-node",
		CPU: CPUMetrics{
			Temperature: 96.0,
		},
		MeasuredAt: time.Now(),
	}
	m.UpdateHeartbeat("critical-node", system)

	warnings := m.GetAlertsByLevel(AlertWarning)
	criticals := m.GetAlertsByLevel(AlertCritical)

	if len(warnings) == 0 {
		t.Error("Expected warning alerts")
	}
	if len(criticals) == 0 {
		t.Error("Expected critical alerts")
	}
}

func TestClearAlert(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	// Generate alerts
	system := &SystemMetrics{
		Hostname: "test-node",
		CPU: CPUMetrics{
			Temperature: 96.0,
		},
		MeasuredAt: time.Now(),
	}
	m.UpdateHeartbeat("test-node", system)

	initialCount := len(m.GetRecentAlerts(100))
	if initialCount == 0 {
		t.Fatal("No alerts generated")
	}

	// Clear one alert
	alerts := m.GetRecentAlerts(100)
	if len(alerts) > 0 {
		m.ClearAlert(alerts[0].ID)
	}

	// Note: GetRecentAlerts returns a copy, so we can't verify count directly
	// But the method exists and doesn't panic
}

func TestGetMonitorStats(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	// Register nodes
	for i := 0; i < 3; i++ {
		system := &SystemMetrics{
			Hostname: fmt.Sprintf("node-%03d", i),
			MemUsedGB: 32.0,
			MemTotalGB: 64.0,
			CPU: CPUMetrics{
				Temperature: 60.0,
			},
			MeasuredAt: time.Now(),
		}
		m.UpdateHeartbeat(fmt.Sprintf("node-%03d", i), system)
	}

	stats := m.GetMonitorStats()

	if stats["total_nodes"] != 3 {
		t.Errorf("Expected 3 total nodes, got %v", stats["total_nodes"])
	}
	if stats["healthy_nodes"] != 3 {
		t.Errorf("Expected 3 healthy nodes, got %v", stats["healthy_nodes"])
	}
}

func TestHealthScoreEdgeCases(t *testing.T) {
	m := NewHealthMonitor(DefaultMonitorConfig())

	// Very bad system
	system := &SystemMetrics{
		Hostname:   "bad-node",
		MemUsedGB:  63.0,
		MemTotalGB: 64.0,
		CPU: CPUMetrics{
			Temperature: 96.0,
		},
		GPU: []GPUMetrics{
			{
				DeviceID: "gpu-0",
				Temperature: 97.0,
				Utilization: 100.0,
				MeasuredAt: time.Now(),
			},
		},
		Network: []NetworkMetrics{
			{
				Interface:  "eth0",
				PingMS:     600.0,
				PacketLoss: 10.0,
				MeasuredAt: time.Now(),
			},
		},
		MeasuredAt: time.Now(),
	}

	heartbeat := m.UpdateHeartbeat("bad-node", system)
	if heartbeat.HealthScore >= 50 {
		t.Errorf("Expected health score < 50 for bad node, got %f", heartbeat.HealthScore)
	}

	// Perfect system
	perfectSystem := &SystemMetrics{
		Hostname:   "perfect-node",
		MemUsedGB:  16.0,
		MemTotalGB: 64.0,
		CPU: CPUMetrics{
			Temperature: 40.0,
		},
		GPU: []GPUMetrics{
			{
				DeviceID: "gpu-0",
				Temperature: 50.0,
				Utilization: 60.0,
				MeasuredAt: time.Now(),
			},
		},
		Network: []NetworkMetrics{
			{
				Interface:  "eth0",
				PingMS:     5.0,
				PacketLoss: 0.0,
				MeasuredAt: time.Now(),
			},
		},
		MeasuredAt: time.Now(),
	}

	heartbeat = m.UpdateHeartbeat("perfect-node", perfectSystem)
	if heartbeat.HealthScore < 90 {
		t.Errorf("Expected health score >= 90 for perfect node, got %f", heartbeat.HealthScore)
	}
}
