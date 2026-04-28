package web

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/chenqifu-Ai/computehub/src/blockchain"
	"github.com/chenqifu-Ai/computehub/src/node"
)

// ─── Fake Providers for Dashboard Test ─────────────────────────────

type fakeNodeProvider struct{}
func (f *fakeNodeProvider) GetOnlineNodes() []*node.Node {
	return []*node.Node{
		{ID: "n1", Name: "node-alpha", Status: "online", Load: 0.45,
			Capability: node.NodeCapability{GPUEnabled: true, GPUs: []node.GPUInfo{{Name: "A100", MemMB: 40960}}}},
		{ID: "n2", Name: "node-beta", Status: "busy", Load: 0.82,
			Capability: node.NodeCapability{GPUEnabled: false}},
	}
}
func (f *fakeNodeProvider) GetTotalNodes() int { return 2 }

type fakeBCProvider struct{}
func (f *fakeBCProvider) GetChainInfo() map[string]any {
	return map[string]any{"height": int64(42), "total_settlements": 156, "mempool_size": 3}
}
func (f *fakeBCProvider) GetStakingStats() map[string]interface{} {
	return map[string]interface{}{"total_staked": 5000.0, "total_rewards": 250.0, "active_stakers": 3, "block_counter": int64(128)}
}
func (f *fakeBCProvider) GetEscrowStats() map[string]int {
	return map[string]int{"total": 10, "locked": 6, "released": 4, "refunded": 0}
}
func (f *fakeBCProvider) GetDisputeStats() map[string]int {
	return map[string]int{"total": 2}
}
func (f *fakeBCProvider) GetTokenSymbol() string { return "CHB" }

type fakeTaskProvider struct{}
func (f *fakeTaskProvider) GetAllTasks() []*blockchain.TaskRecord {
	return []*blockchain.TaskRecord{
		{ID: "t1", Status: "running", NodeAddr: "node-alpha", GPUCount: 2},
		{ID: "t2", Status: "completed", NodeAddr: "node-beta", GPUCount: 1},
	}
}
func (f *fakeTaskProvider) GetTaskStats() map[string]int {
	return map[string]int{"total": 2, "running": 1, "completed": 1}
}

// ─── Tests ─────────────────────────────────────────────────────────

func TestNewDashboardServer(t *testing.T) {
	ds := NewDashboardServer()
	if ds == nil {
		t.Fatal("DashboardServer should not be nil")
	}
}

func TestCollectDataWithProviders(t *testing.T) {
	ds := NewDashboardServer()
	ds.SetProviders(&fakeNodeProvider{}, &fakeBCProvider{}, &fakeTaskProvider{})

	data := ds.CollectData()

	if data.NodeCount != 2 {
		t.Errorf("Expected 2 nodes, got %d", data.NodeCount)
	}
	if data.ActiveTasks != 1 {
		t.Errorf("Expected 1 active task, got %d", data.ActiveTasks)
	}
	if data.BlockHeight != 42 {
		t.Errorf("Expected block height 42, got %d", data.BlockHeight)
	}
	if data.TxCount != 156 {
		t.Errorf("Expected 156 tx, got %d", data.TxCount)
	}
	if data.MempoolSize != 3 {
		t.Errorf("Expected 3 mempool, got %d", data.MempoolSize)
	}
	if data.TotalStaked != 5000.0 {
		t.Errorf("Expected 5000 staked, got %.1f", data.TotalStaked)
	}
	if data.TotalEscrows != 10 {
		t.Errorf("Expected 10 escrows, got %d", data.TotalEscrows)
	}
}

func TestServeDashboard_HTTP(t *testing.T) {
	ds := NewDashboardServer()
	ds.SetProviders(&fakeNodeProvider{}, &fakeBCProvider{}, &fakeTaskProvider{})

	req := httptest.NewRequest("GET", "/web/dashboard", nil)
	w := httptest.NewRecorder()

	ds.ServeDashboard(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}
	body := w.Body.String()
	if len(body) < 100 {
		t.Errorf("Dashboard HTML too short: %d bytes", len(body))
	}
	// Should contain key elements
	checks := []string{"ComputeHub", "node-alpha", "node-beta", "5000", "42", "156"}
	for _, c := range checks {
		if !contains(body, c) {
			t.Errorf("Dashboard should contain '%s'", c)
		}
	}
}

func TestServeMetrics_JSON(t *testing.T) {
	ds := NewDashboardServer()
	ds.SetProviders(&fakeNodeProvider{}, &fakeBCProvider{}, &fakeTaskProvider{})

	req := httptest.NewRequest("GET", "/web/api/metrics", nil)
	w := httptest.NewRecorder()

	ds.ServeMetrics(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}
	contentType := w.Header().Get("Content-Type")
	if contentType != "application/json" {
		t.Errorf("Expected application/json, got %s", contentType)
	}
	body := w.Body.String()
	if len(body) < 50 {
		t.Errorf("Metrics JSON too short: %d bytes", len(body))
	}
}

func TestDashboard_Uptime(t *testing.T) {
	ds := NewDashboardServer()
	data := ds.CollectData()
	if data.Uptime == "" {
		t.Error("Uptime should not be empty")
	}
}

func TestFormatDuration(t *testing.T) {
	tests := []struct {
		seconds  int
		expected string
	}{
		{30, "0h 0m 30s"},
		{60, "0h 1m 0s"},
		{3600, "1h 0m 0s"},
		{3661, "1h 1m 1s"},
	}
	for _, tt := range tests {
		result := formatDuration(time.Duration(tt.seconds) * time.Second)
		if result != tt.expected {
			t.Errorf("formatDuration(%d) = %s, want %s", tt.seconds, result, tt.expected)
		}
	}
}

func TestToIntToFloat(t *testing.T) {
	if toInt(42) != 42 { t.Error("toInt(42) failed") }
	if toInt(int64(42)) != 42 { t.Error("toInt(int64(42)) failed") }
	if toInt(float64(42.5)) != 42 { t.Error("toInt(float64(42.5)) failed") }
	if toFloat(42.5) != 42.5 { t.Error("toFloat(42.5) failed") }
	if toFloat(42) != 42.0 { t.Error("toFloat(42) failed") }
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && strings.Contains(s, substr)
}
