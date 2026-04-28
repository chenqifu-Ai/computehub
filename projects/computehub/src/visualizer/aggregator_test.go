package visualizer

import (
	"testing"
	"time"

	"github.com/computehub/opc/src/discover"
	"github.com/computehub/opc/src/health"
	"github.com/computehub/opc/src/monitor"
	"github.com/computehub/opc/src/scheduler"
)

func TestNewGlobalPowerMap(t *testing.T) {
	gpm := NewGlobalPowerMap(false)
	if gpm == nil {
		t.Fatal("GlobalPowerMap should not be nil")
	}
	if len(gpm.regions) != 0 {
		t.Errorf("Expected 0 regions, got %d", len(gpm.regions))
	}
	if len(gpm.gpuSnapshots) != 0 {
		t.Errorf("Expected 0 GPU snapshots, got %d", len(gpm.gpuSnapshots))
	}
}

func TestNewGlobalPowerMapSimulate(t *testing.T) {
	gpm := NewGlobalPowerMap(true)
	if !gpm.simulate {
		t.Error("Expected simulate mode to be true")
	}
}

func TestGetGlobalSnapshotNoData(t *testing.T) {
	gpm := NewGlobalPowerMap(false)
	snapshot := gpm.GetGlobalSnapshot()

	if snapshot == nil {
		t.Fatal("Snapshot should not be nil")
	}
	if snapshot.TotalNodes != 0 {
		t.Errorf("Expected 0 total nodes, got %d", snapshot.TotalNodes)
	}
}

func TestRegisterNode(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	node := &scheduler.NodeInfo{
		ID:          "node-reg-test-001",
		Region:      "region-reg-test",
		GPUType:     "A100",
		Status:      "online",
		CPUCores:    32,
		MemoryGB:    128,
		GPUMemoryGB: 80,
		GPUUtil:     50.0,
		Temperature: 60.0,
		CPUUtil:     45.0,
		ActiveTasks: 3,
		MaxTasks:    10,
		SuccessRate: 0.98,
		AssignedAt:  time.Now(),
	}
	gpm.RegisterNode(node)

	snapshot := gpm.GetGlobalSnapshot()
	if snapshot.TotalNodes != 1 {
		t.Errorf("Expected 1 node, got %d", snapshot.TotalNodes)
	}
	if snapshot.OnlineNodes != 1 {
		t.Errorf("Expected 1 online node, got %d", snapshot.OnlineNodes)
	}

	region := gpm.GetRegionData("region-reg-test")
	if region == nil {
		t.Fatal("Region should exist")
	}
	if len(region.Nodes) != 1 {
		t.Errorf("Expected 1 node in region, got %d", len(region.Nodes))
	}
}

func TestRegisterNodeOnline(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	onlineNode := &scheduler.NodeInfo{
		ID:     "node-online",
		Region: "us-west",
		GPUType: "H100",
		Status: "online",
	}
	offlineNode := &scheduler.NodeInfo{
		ID:     "node-offline",
		Region: "us-west",
		GPUType: "V100",
		Status: "offline",
	}

	gpm.RegisterNode(onlineNode)
	gpm.RegisterNode(offlineNode)

	snapshot := gpm.GetGlobalSnapshot()
	if snapshot.TotalNodes != 2 {
		t.Errorf("Expected 2 total nodes, got %d", snapshot.TotalNodes)
	}
	if snapshot.OnlineNodes != 1 {
		t.Errorf("Expected 1 online node, got %d", snapshot.OnlineNodes)
	}
}

func TestUpdateGPU(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	gpm.UpdateGPU(&monitor.GPUMetrics{
		DeviceID:     "gpu-001",
		Model:        "A100",
		Utilization:  75.5,
		Temperature:  65.0,
		MemoryUsedMB: 32768,
		MeasuredAt:   time.Now(),
	})

	snapshots := gpm.GetGPURadars(10)
	if len(snapshots) != 1 {
		t.Errorf("Expected 1 GPU snapshot, got %d", len(snapshots))
	}
	if snapshots[0].Model != "A100" {
		t.Errorf("Expected model 'A100', got '%s'", snapshots[0].Model)
	}
}

func TestGetGPURadarsLimit(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	for i := 0; i < 10; i++ {
		gpm.UpdateGPU(&monitor.GPUMetrics{
			DeviceID:     "gpu",
			Model:        "A100",
			Utilization:  float64(i * 10),
			Temperature:  50.0,
			MemoryUsedMB: 16384,
			MeasuredAt:   time.Now(),
		})
	}

	snapshots := gpm.GetGPURadars(3)
	if len(snapshots) > 3 {
		t.Errorf("Expected max 3 snapshots, got %d", len(snapshots))
	}
}

func TestGetGPURadarsNoLimit(t *testing.T) {
	gpm := NewGlobalPowerMap(false)
	snapshots := gpm.GetGPURadars(0)
	if snapshots != nil {
		t.Errorf("Expected nil for no data, got %d snapshots", len(snapshots))
	}
}

func TestUpdateHealth(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	node := &scheduler.NodeInfo{
		ID:     "node-health-test",
		Region: "region-health-test",
		GPUType: "A100",
		Status: "online",
	}
	gpm.RegisterNode(node)

	gpm.UpdateHealth(&health.NodeHealth{
		NodeID: "node-health-test",
		Status: "degraded",
	})

	region := gpm.GetRegionData("region-health-test")
	found := false
	for _, n := range region.Nodes {
		if n.ID == "node-health-test" {
			if n.HealthStatus != "degraded" {
				t.Errorf("Expected health status 'degraded', got '%s'", n.HealthStatus)
			}
			found = true
		}
	}
	if !found {
		t.Error("Node not found in region")
	}
}

func TestAddAlert(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	node := &scheduler.NodeInfo{
		ID:     "node-alert-test",
		Region: "region-alert-test",
		GPUType: "A100",
		Status: "online",
	}
	gpm.RegisterNode(node)

	alert := Alert{
		ID:        "alert-001",
		Type:      "temperature",
		Severity:  "critical",
		Message:   "GPU temperature exceeds 90C",
		Source:    "node-alert-test",
		Timestamp: time.Now(),
	}
	gpm.AddAlert(alert)

	region := gpm.GetRegionData("region-alert-test")
	if len(region.Alerts) != 1 {
		t.Errorf("Expected 1 alert, got %d", len(region.Alerts))
	}
	if region.Alerts[0].Type != "temperature" {
		t.Errorf("Expected alert type 'temperature', got '%s'", region.Alerts[0].Type)
	}
}

func TestRegisterNodeDiscovery(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	node := &discover.NodeInfo{
		NodeID:   "disc-node-uniq",
		Region:   "region-disc-test",
		GPUType:  "H100",
		IPAddress: "10.0.0.1",
	}
	gpm.RegisterNodeDiscovery(node)

	region := gpm.GetRegionData("region-disc-test")
	if region == nil {
		t.Fatal("Region should exist")
	}
	if len(region.Nodes) != 1 {
		t.Errorf("Expected 1 node, got %d", len(region.Nodes))
	}
}

func TestGetRegionDataNotExists(t *testing.T) {
	gpm := NewGlobalPowerMap(false)
	region := gpm.GetRegionData("non-existent")
	if region != nil {
		t.Error("Expected nil for non-existent region")
	}
}

func TestGetAllRegions(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	gpm.RegisterNode(&scheduler.NodeInfo{ID: "node-1", Region: "us-east", Status: "online"})
	gpm.RegisterNode(&scheduler.NodeInfo{ID: "node-2", Region: "eu-west", Status: "online"})

	regions := gpm.GetAllRegions()
	if len(regions) != 2 {
		t.Errorf("Expected 2 regions, got %d", len(regions))
	}
}

func TestSubscribeAndUnsubscribe(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	sub := gpm.Subscribe("test-sub", "")
	if sub == nil {
		t.Fatal("Subscriber should not be nil")
	}
	if sub.ID != "test-sub" {
		t.Errorf("Expected subscriber ID 'test-sub', got '%s'", sub.ID)
	}

	gpm.Unsubscribe("test-sub")

	// Verify channel is closed (Unsubscribe closes it)
	_, ok := <-sub.Chan
	if ok {
		t.Error("Expected channel to be closed after unsubscribe")
	}
}

func TestBroadcastToSubscribers(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	sub := gpm.Subscribe("broadcast-test", "")

	data := map[string]string{"message": "hello"}
	gpm.Broadcast(data)

	select {
	case msg := <-sub.Chan:
		if len(msg) == 0 {
			t.Error("Expected non-empty broadcast message")
		}
	default:
		t.Error("Expected to receive broadcast message")
	}

	gpm.Unsubscribe("broadcast-test")
}

func TestGenerateSimulationData(t *testing.T) {
	gpm := NewGlobalPowerMap(true)
	gpm.GenerateSimulationData()

	snapshot := gpm.GetGlobalSnapshot()
	if snapshot.TotalNodes == 0 {
		t.Error("Expected simulation data to have nodes")
	}

	regions := gpm.GetAllRegions()
	if len(regions) == 0 {
		t.Error("Expected simulation data to have regions")
	}
}

func TestGenerateSimulationDataNoSim(t *testing.T) {
	gpm := NewGlobalPowerMap(false)
	gpm.GenerateSimulationData()

	snapshot := gpm.GetGlobalSnapshot()
	if snapshot.TotalNodes != 0 {
		t.Error("Expected no nodes when simulation is disabled")
	}
}

func TestRegionToCountry(t *testing.T) {
	tests := []struct {
		region  string
		country string
	}{
		{"cn-east", "China"},
		{"cn-north", "China"},
		{"us-east", "USA"},
		{"us-west", "USA"},
		{"eu-west", "Germany"},
		{"eu-north", "UK"},
		{"ap-southeast", "Singapore"},
		{"ap-east", "Japan"},
		{"ap-south", "India"},
		{"unknown", "Unknown"},
	}

	for _, tt := range tests {
		country := regionToCountry(tt.region)
		if country != tt.country {
			t.Errorf("regionToCountry(%s) = '%s', expected '%s'", tt.region, country, tt.country)
		}
	}
}

func TestRegionToLatLng(t *testing.T) {
	tests := []struct {
		region string
		lat    float64
		lng    float64
	}{
		{"cn-east", 31.2304, 121.4737},
		{"us-east", 37.7749, -122.4194},
		{"eu-west", 52.5200, 13.4050},
	}

	for _, tt := range tests {
		lat := regionToLat(tt.region)
		lng := regionToLng(tt.region)
		if lat != tt.lat {
			t.Errorf("regionToLat(%s) = %f, expected %f", tt.region, lat, tt.lat)
		}
		if lng != tt.lng {
			t.Errorf("regionToLng(%s) = %f, expected %f", tt.region, lng, tt.lng)
		}
	}
}

func TestGpuStatus(t *testing.T) {
	tests := []struct {
		temp float64
		util float64
		want string
	}{
		{95, 50, "critical"},
		{85, 50, "degraded"},
		{50, 95, "busy"},
		{50, 50, "idle"},
		{50, 0, "offline"}, // util = 0 — offline check triggers first
	}

	for _, tt := range tests {
		got := gpuStatus(tt.temp, tt.util)
		if got != tt.want {
			t.Errorf("gpuStatus(temp=%.0f, util=%.0f) = '%s', expected '%s'", tt.temp, tt.util, got, tt.want)
		}
	}
}

func TestHealthStatus(t *testing.T) {
	tests := []struct {
		load float64
		temp float64
		want string
	}{
		{50, 95, "critical"},    // temp > 90
		{50, 50, "healthy"},     // normal
		{50, 85, "degraded"},    // temp > 80
		{90, 50, "degraded"},    // load > 80
		{98, 50, "critical"},    // load > 95
	}

	for _, tt := range tests {
		got := healthStatus(tt.load, tt.temp)
		if got != tt.want {
			t.Errorf("healthStatus(load=%.0f, temp=%.0f) = '%s', expected '%s'", tt.load, tt.temp, got, tt.want)
		}
	}
}

func TestGPUSnapshotHistoryLimit(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	for i := 0; i < 150; i++ {
		gpm.UpdateGPU(&monitor.GPUMetrics{
			DeviceID:     "gpu-limited",
			Model:        "A100",
			Utilization:  50.0,
			Temperature:  60.0,
			MemoryUsedMB: 16384,
			MeasuredAt:   time.Now(),
		})
	}

	gpm.gpuLock.RLock()
	snaps := gpm.gpuSnapshots["gpu-limited"]
	count := len(snaps)
	gpm.gpuLock.RUnlock()

	if count > 100 {
		t.Errorf("Expected max 100 snapshots, got %d", count)
	}
}

func TestGetGlobalSnapshotStructured(t *testing.T) {
	gpm := NewGlobalPowerMap(false)

	gpm.RegisterNode(&scheduler.NodeInfo{
		ID:     "n1",
		Region: "us-east",
		GPUType: "A100",
		Status: "online",
		GPUMemoryGB: 80,
		MemoryGB:    256,
		CPUCores:    64,
	})
	gpm.RegisterNode(&scheduler.NodeInfo{
		ID:     "n2",
		Region: "eu-west",
		GPUType: "H100",
		Status: "online",
		GPUMemoryGB: 80,
		MemoryGB:    256,
		CPUCores:    64,
	})

	snap := gpm.GetGlobalSnapshot()
	if snap.TotalNodes != 2 {
		t.Errorf("Expected 2 nodes, got %d", snap.TotalNodes)
	}
	if snap.OnlineNodes != 2 {
		t.Errorf("Expected 2 online nodes, got %d", snap.OnlineNodes)
	}
}
