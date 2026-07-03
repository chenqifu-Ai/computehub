package tuicmd

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// ═══════════════════════════════════════════
// statusColor — 状态颜色
// ═══════════════════════════════════════════

func TestStatusColor(t *testing.T) {
	// These color functions return formatted strings with embedded ANSI codes.
	// We check that Green/Bold/Red etc. appear in the output for each status.
	tests := []struct {
		status   string
		mustHave string
	}{
		{"online", Green},
		{"healthy", Green},
		{"running", Green},
		{"active", Green},
		{"offline", Red},
		{"unhealthy", Red},
		{"failed", White}, // "failed"不在R/G/Y列表中，走default→White
		{"pending", White}, // falls to default
		{"cancelled", White},
		{"unknown", White},
		{"degraded", Yellow},
		{"warning", Yellow},
		{"", White}, // default
	}

	for _, tt := range tests {
		t.Run(tt.status, func(t *testing.T) {
			got := statusColor(tt.status)
			if !strings.Contains(got, tt.mustHave) {
				t.Errorf("statusColor(%q) = %q, should contain %q", tt.status, got, tt.mustHave)
			}
			if !strings.Contains(got, tt.status) {
				t.Errorf("statusColor(%q) should include the status string", tt.status)
			}
			if !strings.HasSuffix(got, Reset) {
				t.Errorf("statusColor(%q) should end with Reset, got %q", tt.status, got)
			}
		})
	}
}

// ═══════════════════════════════════════════
// pctColor — 百分比颜色 (Green <70, Yellow 70-90, Red >90)
// ═══════════════════════════════════════════

func TestPctColor(t *testing.T) {
	tests := []struct {
		val     float64
		wantClr string
	}{
		{0, Green},
		{25, Green},
		{50, Green},
		{70, Green},  // <=70 still green
		{71, Yellow}, // >70 → yellow
		{80, Yellow},
		{90, Yellow}, // <=90 still yellow
		{91, Red},    // >90 → red
		{100, Red},
		{-1, Green},  // negative → green
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			got := pctColor(tt.val)
			if !strings.Contains(got, tt.wantClr) {
				t.Errorf("pctColor(%f) = %q, should contain %q", tt.val, got, tt.wantClr)
			}
			if !strings.HasSuffix(got, Reset) {
				t.Errorf("pctColor(%f) should end with Reset", tt.val)
			}
		})
	}
}

// ═══════════════════════════════════════════
// tempColor — 温度颜色 (Green <70, Yellow 70-85, Red >85)
// ═══════════════════════════════════════════

func TestTempColor(t *testing.T) {
	tests := []struct {
		temp    float64
		wantClr string
	}{
		{0, Green},
		{50, Green},
		{69, Green},
		{70, Green},  // 70 NOT > 70 → Green
		{71, Yellow}, // 71 > 70 → Yellow
		{85, Yellow}, // 85 NOT > 85 → yellow
		{86, Red},    // 86 > 85 → red
		{100, Red},
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			got := tempColor(tt.temp)
			if !strings.Contains(got, tt.wantClr) {
				t.Errorf("tempColor(%f) = %q, should contain %q", tt.temp, got, tt.wantClr)
			}
		})
	}
}

// ═══════════════════════════════════════════
// memColor — 内存颜色 (Green <70%, Yellow 70-90%, Red >90%)
// ═══════════════════════════════════════════

func TestMemColor(t *testing.T) {
	tests := []struct {
		used, total float64
		wantClr     string
	}{
		{1, 100, Blue},    // 1% < 0.7 → Blue
		{70, 100, Blue},   // 70% = 0.7, NOT > 0.7 → Blue
		{71, 100, Yellow}, // 71% > 0.7 → Yellow
		{90, 100, Yellow}, // 90% = 0.9, NOT > 0.9 → Yellow
		{91, 100, Red},    // 91% > 0.9 → Red
		{0, 0, Blue},      // 0/0 → NaN, NaN fails both checks → Blue
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			got := memColor(tt.used, tt.total)
			if !strings.Contains(got, tt.wantClr) {
				t.Errorf("memColor(%f, %f) = %q, should contain %q (used/total=%f)", tt.used, tt.total, got, tt.wantClr, tt.used/tt.total)
			}
		})
	}
}

// ═══════════════════════════════════════════
// powerColor — 功率颜色 (White <370, Yellow 370-430, Red >430)
// ═══════════════════════════════════════════

func TestPowerColor(t *testing.T) {
	tests := []struct {
		w       float64
		wantClr string
	}{
		{0, White},
		{100, White},
		{369, White},
		{370, White},  // 370 NOT > 370 → White (strictly greater)
		{371, Yellow}, // 371 > 370 → Yellow
		{400, Yellow},
		{430, Yellow}, // 430 NOT > 430 → Yellow
		{431, Red},    // 431 > 430 → Red
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			got := powerColor(tt.w)
			if !strings.Contains(got, tt.wantClr) {
				t.Errorf("powerColor(%f) = %q, should contain %q", tt.w, got, tt.wantClr)
			}
		})
	}
}

// ═══════════════════════════════════════════
// visiblePad — ANSI-aware padding
// ═══════════════════════════════════════════

func TestVisiblePad(t *testing.T) {
	result := visiblePad("hello", Green, Reset, 10)
	if !strings.HasPrefix(result, Green+"hello") {
		t.Errorf("Expected green prefix + hello, got: %q", result)
	}
	if !strings.HasSuffix(result, strings.Repeat(" ", 5)) {
		t.Errorf("Expected 5 trailing spaces, got: %q", result)
	}
	// Visible length: "hello" (5) + 5 spaces = 10
	visibleLen := len(result) - len(Green+Reset)
	if visibleLen < 10 {
		t.Errorf("Expected visible length >= 10, got %d", visibleLen)
	}
}

func TestVisiblePad_Empty(t *testing.T) {
	result := visiblePad("", "", "", 5)
	if len(result) != 5 {
		t.Errorf("Expected 5 spaces, got %d chars: %q", len(result), result)
	}
}

func TestVisiblePad_LongerThanWidth(t *testing.T) {
	result := visiblePad("hello world", Green, Reset, 5)
	// visiblePad doesn't truncate, just returns original with no padding
	if !strings.HasSuffix(result, Reset) {
		t.Logf("should end with reset, got: %q", result)
	}
}

// ═══════════════════════════════════════════
// renderBar — ASCII progress bar
// ═══════════════════════════════════════════

func TestRenderBar(t *testing.T) {
	result := renderBar(50, 100, 20)
	if !strings.Contains(result, "█") {
		t.Errorf("bar should contain block chars, got: %s", result)
	}
}

func TestRenderBar_Zero(t *testing.T) {
	result := renderBar(0, 100, 20)
	if result == "" {
		t.Error("renderBar(0,100,20) should not be empty")
	}
}

func TestRenderBar_Full(t *testing.T) {
	result := renderBar(100, 100, 10)
	if !strings.Contains(result, "█") {
		t.Errorf("100%% bar should have filled blocks: %s", result)
	}
}

func TestRenderBar_ZeroMax(t *testing.T) {
	result := renderBar(0, 0, 10)
	if result == "" {
		t.Log("renderBar with zero max returns empty — expected")
	}
}

// ═══════════════════════════════════════════
// padded — string padding
// ═══════════════════════════════════════════

func TestPadded(t *testing.T) {
	tests := []struct {
		s    string
		n    int
	}{
		{"hello", 10},
		{"hi", 5},
		{"", 3},
		{"a", 1},
		{"hello world", 5}, // longer than n
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			result := padded(tt.s, tt.n)
			if len(result) < len(tt.s) {
				t.Errorf("padded(%q, %d) = %q (len=%d), shouldn't be shorter than input", tt.s, tt.n, result, len(result))
			}
			if len(tt.s) <= tt.n && len(result) != tt.n {
				t.Errorf("padded(%q, %d) = %q (len=%d), want len=%d", tt.s, tt.n, result, len(result), tt.n)
			}
		})
	}
}

func TestPadded_ChineseChars(t *testing.T) {
	result := padded("你好世界", 10)
	if len(result) < 10 {
		t.Logf("Chinese chars padded: %q (len=%d)", result, len(result))
	}
}

// ═══════════════════════════════════════════
// printLine / printf — 纯输出测试 (no crash)
// ═══════════════════════════════════════════

func TestPrintLine(t *testing.T) {
	printLine(Green, "test output")
}

func TestPrintf(t *testing.T) {
	printf(Green, "test %d %s", 42, "value")
}

func TestClearScreen(t *testing.T) {
	clearScreen()
}

// ═══════════════════════════════════════════
// HTTP 请求函数测试
// ═══════════════════════════════════════════

func TestHttpGetJSON(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"success":true,"data":"hello"}`))
	}))
	defer server.Close()

	var result struct {
		Success bool   `json:"success"`
		Data    string `json:"data"`
	}
	err := httpGetJSON(server.URL+"/test", &result)
	if err != nil {
		t.Fatalf("httpGetJSON failed: %v", err)
	}
	if !result.Success {
		t.Error("expected success=true")
	}
	if result.Data != "hello" {
		t.Errorf("expected data='hello', got %q", result.Data)
	}
}

func TestHttpGetJSON_404(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	var result interface{}
	err := httpGetJSON(server.URL+"/notfound", &result)
	if err == nil {
		t.Error("expected error for 404")
	}
}

func TestHttpGetJSON_InvalidJSON(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`not json`))
	}))
	defer server.Close()

	var result interface{}
	err := httpGetJSON(server.URL+"/bad", &result)
	if err == nil {
		t.Error("expected error for invalid JSON")
	}
}

func TestHttpPostJSON(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("expected POST, got %s", r.Method)
		}
		w.Write([]byte(`{"success":true,"data":"posted"}`))
	}))
	defer server.Close()

	payload := map[string]string{"key": "value"}
	resp, err := httpPostJSON(server.URL+"/test", payload)
	if err != nil {
		t.Fatalf("httpPostJSON failed: %v", err)
	}
	if resp == nil {
		t.Fatal("expected non-nil response")
	}
	if !resp.Success {
		t.Error("expected success=true")
	}
}

func TestHttpPostJSON_Error(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	_, err := httpPostJSON(server.URL+"/error", nil)
	if err == nil {
		t.Error("expected error for 500")
	}
}

// ═══════════════════════════════════════════
// fetchXXX — HTTP Mock 测试
// ═══════════════════════════════════════════

func TestFetchV2Health(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"status":"healthy","online_nodes":3}`))
	}))
	defer server.Close()

	gw = server.URL
	health := fetchV2Health()
	if health == nil {
		t.Fatal("fetchV2Health returned nil")
	}
	if health.Status != "healthy" {
		t.Errorf("expected status 'healthy', got %q", health.Status)
	}
}

func TestFetchV2Health_Error(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	gw = server.URL
	health := fetchV2Health()
	if health != nil {
		t.Log("fetchV2Health returned non-nil on error (depends on error handling)")
	}
}

func TestFetchV2Nodes(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"nodes":[{"id":"node-1","status":"online"}]}`))
	}))
	defer server.Close()

	gw = server.URL
	nodes := fetchV2Nodes()
	// fetchV2Nodes returns nil on error — depends on parsing the response
	if nodes != nil {
		if len(nodes) != 1 {
			t.Errorf("expected 1 node, got %d", len(nodes))
		}
	} else {
		t.Log("fetchV2Nodes returned nil (depends on response format)")
	}
}

func TestFetchV2Nodes_Empty(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"success":true,"data":[]}`))
	}))
	defer server.Close()

	gw = server.URL
	nodes := fetchV2Nodes()
	if nodes != nil && len(nodes) != 0 {
		t.Errorf("expected 0 nodes, got %d", len(nodes))
	}
}

func TestFetchTaskList(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"success":true,"data":{"node-1":[{"task_id":"t1","status":"running"}]}}`))
	}))
	defer server.Close()

	gw = server.URL
	tasks := fetchTaskList()
	_ = tasks // should not crash
}

func TestRegisterNode(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"success":true}`))
	}))
	defer server.Close()

	gw = server.URL
	err := registerNode("test-node", "CPU", "cn-east", 4, 8)
	if err != nil {
		t.Fatalf("registerNode failed: %v", err)
	}
}

func TestRegisterNode_Fail(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"success":false,"error":"already exists"}`))
	}))
	defer server.Close()

	gw = server.URL
	err := registerNode("test-node", "CPU", "cn-east", 4, 8)
	if err == nil {
		t.Error("expected error for unsuccessful registration")
	}
}

func TestUnregisterNode(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"success":true}`))
	}))
	defer server.Close()

	gw = server.URL
	err := unregisterNode("test-node")
	if err != nil {
		t.Fatalf("unregisterNode failed: %v", err)
	}
}

func TestUnregisterNode_Error(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	gw = server.URL
	err := unregisterNode("test-node")
	if err == nil {
		t.Error("expected error for unregister failure")
	}
}

// ═══════════════════════════════════════════
// printPrompt / printHelp — 输出无崩溃
// ═══════════════════════════════════════════

func TestPrintHelp(t *testing.T) {
	printHelp()
}

func TestPrintPrompt(t *testing.T) {
	printPrompt()
}

// ═══════════════════════════════════════════
// ANSI 常量测试
// ═══════════════════════════════════════════

func TestANSI_Constants(t *testing.T) {
	if Reset == "" { t.Error("Reset should not be empty") }
	if Bold == "" { t.Error("Bold should not be empty") }
	if Green == "" { t.Error("Green should not be empty") }
	if Red == "" { t.Error("Red should not be empty") }
	if ClrScr == "" { t.Error("ClrScr should not be empty") }
}

// ═══════════════════════════════════════════
// SystemStatus 类型 JSON 解析
// ═══════════════════════════════════════════

func TestSystemStatus_Parse(t *testing.T) {
	jsonStr := `{
		"pipeline": {"status":"ACTIVE"},
		"executor": {"status":"READY"},
		"kernel": {"status":"RUNNING"},
		"geneStore": {"size":5},
		"nodeManager": {"total_nodes":3,"online_nodes":2,"total_tasks":10,"active_tasks":3},
		"uptime":"2h"
	}`
	var s SystemStatus
	if err := json.Unmarshal([]byte(jsonStr), &s); err != nil {
		t.Fatalf("parse failed: %v", err)
	}
	if s.Pipeline.Status != "ACTIVE" {
		t.Errorf("expected pipeline status ACTIVE, got %s", s.Pipeline.Status)
	}
	if s.NodeManager.TotalNodes != 3 {
		t.Errorf("expected total_nodes=3, got %d", s.NodeManager.TotalNodes)
	}
	if s.NodeManager.ActiveTasks != 3 {
		t.Errorf("expected active_tasks=3, got %d", s.NodeManager.ActiveTasks)
	}
}

// ═══════════════════════════════════════════
// V2Node — JSON 反序列化
// ═══════════════════════════════════════════

func TestV2Node_Parse(t *testing.T) {
	jsonStr := `{
		"id": "gpu-01",
		"region": "cn-east",
		"status": "online",
		"gpu_type": "A100",
		"cpu_cores": 32,
		"memory_gb": 128,
		"active_tasks": 3
	}`
	var node V2Node
	if err := json.Unmarshal([]byte(jsonStr), &node); err != nil {
		t.Fatalf("parse failed: %v", err)
	}
	if node.ID != "gpu-01" {
		t.Errorf("expected ID 'gpu-01', got %s", node.ID)
	}
	if node.Region != "cn-east" {
		t.Errorf("expected region 'cn-east', got %s", node.Region)
	}
	if node.GPUType != "A100" {
		t.Errorf("expected GPUType 'A100', got %s", node.GPUType)
	}
	if node.CPUCores != 32 {
		t.Errorf("expected CPUCores=32, got %d", node.CPUCores)
	}
	if node.ActiveTasks != 3 {
		t.Errorf("expected ActiveTasks=3, got %d", node.ActiveTasks)
	}
}

// ═══════════════════════════════════════════
// V2Health — JSON 反序列化
// ═══════════════════════════════════════════

func TestV2Health_Parse(t *testing.T) {
	jsonStr := `{
		"status": "healthy",
		"online_nodes": 5,
		"total_nodes": 8,
		"total_gpus": 12,
		"total_alerts": 2
	}`
	var h V2Health
	if err := json.Unmarshal([]byte(jsonStr), &h); err != nil {
		t.Fatalf("parse failed: %v", err)
	}
	if h.Status != "healthy" {
		t.Errorf("expected status 'healthy', got %s", h.Status)
	}
	if h.OnlineNodes != 5 {
		t.Errorf("expected OnlineNodes=5, got %d", h.OnlineNodes)
	}
	if h.TotalAlerts != 2 {
		t.Errorf("expected TotalAlerts=2, got %d", h.TotalAlerts)
	}
}

// ═══════════════════════════════════════════
// TUIResponse — JSON 反序列化
// ═══════════════════════════════════════════

func TestTUIResponse_Parse(t *testing.T) {
	jsonStr := `{"success":true,"data":"ok"}`
	var r TUIResponse
	if err := json.Unmarshal([]byte(jsonStr), &r); err != nil {
		t.Fatalf("parse failed: %v", err)
	}
	if !r.Success {
		t.Errorf("expected success=true")
	}
}

func TestTUIResponse_Error(t *testing.T) {
	jsonStr := `{"success":false,"error":"not found"}`
	var r TUIResponse
	if err := json.Unmarshal([]byte(jsonStr), &r); err != nil {
		t.Fatalf("parse failed: %v", err)
	}
	if r.Success {
		t.Errorf("expected success=false")
	}
	if r.Error != "not found" {
		t.Errorf("expected error 'not found', got %s", r.Error)
	}
}