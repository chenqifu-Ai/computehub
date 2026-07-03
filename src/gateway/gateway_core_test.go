package gateway

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

// ============================================================
// Gateway Core API Tests — 覆盖未测试的关键端点
// ============================================================

// setupCoreTestGateway 创建测试用 Gateway 服务器（与 gateway_test.go 共享 helper）
// 如果已有 setupTestGateway 则复用
func setupCoreTestGateway(t *testing.T) *httptest.Server {
	config := &GatewayConfig{
		GeneStorePath: t.TempDir() + "/test-genes.json",
		SandboxPath:   t.TempDir() + "/sandbox",
		BufferSize:    50,
		MaxStates:     500,
		MaxNodes:      20,
	}
	gw := NewOpcGateway(0, config)
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gw.ServeHTTP(w, r)
	}))
	t.Cleanup(func() { ts.Close() })
	return ts
}

// helper: register a node for subsequent tests
func registerTestNode(t *testing.T, ts *httptest.Server, nodeID string) {
	t.Helper()
	reg := map[string]interface{}{
		"node_id":         nodeID,
		"node_type":       "gpu",
		"gpu_type":        "A100",
		"region":          "test-region",
		"cpu_cores":       16,
		"memory_gb":       64,
		"gpu_memory_gb":   40,
		"max_concurrency": 8,
		"ip_address":      "10.0.0.99",
	}
	body, _ := json.Marshal(reg)
	resp, err := http.Post(ts.URL+"/api/v1/nodes/register", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("registerTestNode: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		t.Fatalf("registerTestNode: status %d, body: %s", resp.StatusCode, string(b))
	}
}

// ---- Node Unregister ----

func TestNodeUnregister_Success(t *testing.T) {
	ts := setupCoreTestGateway(t)
	registerTestNode(t, ts, "unreg-node-001")

	payload := map[string]string{"node_id": "unreg-node-001"}
	body, _ := json.Marshal(payload)
	resp, err := http.Post(ts.URL+"/api/v1/nodes/unregister", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("unregister failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if !result.Success {
		t.Errorf("expected success=true, got error: %s", result.Error)
	}
}

func TestNodeUnregister_MissingNodeID(t *testing.T) {
	ts := setupCoreTestGateway(t)

	body, _ := json.Marshal(map[string]string{})
	resp, err := http.Post(ts.URL+"/api/v1/nodes/unregister", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("unregister failed: %v", err)
	}
	defer resp.Body.Close()

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if result.Success {
		t.Error("expected failure for missing node_id")
	}
	if result.Error == "" {
		t.Error("expected error message for missing node_id")
	}
}

func TestNodeUnregister_WrongMethod(t *testing.T) {
	ts := setupCoreTestGateway(t)
	resp, err := http.Get(ts.URL + "/api/v1/nodes/unregister")
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("expected 405, got %d", resp.StatusCode)
	}
}

// ---- Task Cancel ----

func TestTaskCancel_Success(t *testing.T) {
	ts := setupCoreTestGateway(t)
	registerTestNode(t, ts, "cancel-worker")

	// Submit a task first
	task := map[string]interface{}{
		"task_id":     "cancel-task-001",
		"source_type": "direct",
		"priority":    5,
		"command":     "sleep 60",
		"timeout":     300,
	}
	body, _ := json.Marshal(task)
	http.Post(ts.URL+"/api/v1/tasks/submit", "application/json", bytes.NewBuffer(body))

	// Cancel it
	cancel := map[string]string{"task_id": "cancel-task-001"}
	body, _ = json.Marshal(cancel)
	resp, err := http.Post(ts.URL+"/api/v1/tasks/cancel", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("cancel failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}

func TestTaskCancel_MissingTaskID(t *testing.T) {
	ts := setupCoreTestGateway(t)

	body, _ := json.Marshal(map[string]string{})
	resp, err := http.Post(ts.URL+"/api/v1/tasks/cancel", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("cancel failed: %v", err)
	}
	defer resp.Body.Close()

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if result.Success {
		t.Error("expected failure for missing task_id")
	}
}

func TestTaskCancel_WrongMethod(t *testing.T) {
	ts := setupCoreTestGateway(t)
	resp, err := http.Get(ts.URL + "/api/v1/tasks/cancel")
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("expected 405, got %d", resp.StatusCode)
	}
}

// ---- Task Detail ----

func TestTaskDetail_AfterSubmit(t *testing.T) {
	ts := setupCoreTestGateway(t)
	registerTestNode(t, ts, "detail-worker")

	// Submit
	task := map[string]interface{}{
		"task_id":     "detail-task-001",
		"source_type": "direct",
		"priority":    5,
		"command":     "echo detail-test",
	}
	body, _ := json.Marshal(task)
	http.Post(ts.URL+"/api/v1/tasks/submit", "application/json", bytes.NewBuffer(body))

	// Get detail
	resp, err := http.Get(ts.URL + "/api/v1/tasks/detail?task_id=detail-task-001")
	if err != nil {
		t.Fatalf("detail failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}

func TestTaskDetail_MissingTaskID(t *testing.T) {
	ts := setupCoreTestGateway(t)

	resp, err := http.Get(ts.URL + "/api/v1/tasks/detail")
	if err != nil {
		t.Fatalf("detail failed: %v", err)
	}
	defer resp.Body.Close()

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if result.Success {
		t.Error("expected failure for missing task_id")
	}
}

// ---- File Download ----

func TestFileDownload_MissingFileParam(t *testing.T) {
	ts := setupCoreTestGateway(t)

	resp, err := http.Get(ts.URL + "/api/v1/download")
	if err != nil {
		t.Fatalf("download failed: %v", err)
	}
	defer resp.Body.Close()

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if result.Success {
		t.Error("expected failure for missing file param")
	}
}

func TestFileDownload_DisallowedFile(t *testing.T) {
	ts := setupCoreTestGateway(t)

	resp, err := http.Get(ts.URL + "/api/v1/download?file=evil.sh")
	if err != nil {
		t.Fatalf("download failed: %v", err)
	}
	defer resp.Body.Close()

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if result.Success {
		t.Error("expected failure for disallowed file prefix")
	}
	if result.Error == "" {
		t.Error("expected error message for disallowed file")
	}
}

func TestFileDownload_WrongMethod(t *testing.T) {
	ts := setupCoreTestGateway(t)

	resp, err := http.Post(ts.URL+"/api/v1/download", "application/json", nil)
	if err != nil {
		t.Fatalf("download failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("expected 405, got %d", resp.StatusCode)
	}
}

// ---- Task Poll (long-poll endpoint) ----

func TestTaskPoll_RegisteredNode(t *testing.T) {
	ts := setupCoreTestGateway(t)
	registerTestNode(t, ts, "poll-worker")

	// Poll — POST with node_id, should return 200 with no pending tasks
	poll := map[string]interface{}{
		"node_id":            "poll-worker",
		"running_task_count": 0,
	}
	body, _ := json.Marshal(poll)
	resp, err := http.Post(ts.URL+"/api/v1/tasks/poll", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("poll failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if !result.Success {
		t.Errorf("expected success=true, got error: %s", result.Error)
	}
}

func TestTaskPoll_MissingNodeID(t *testing.T) {
	ts := setupCoreTestGateway(t)

	poll := map[string]interface{}{}
	body, _ := json.Marshal(poll)
	resp, err := http.Post(ts.URL+"/api/v1/tasks/poll", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("poll failed: %v", err)
	}
	defer resp.Body.Close()

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if result.Success {
		t.Error("expected failure for missing node_id")
	}
}

func TestTaskPoll_WrongMethod(t *testing.T) {
	ts := setupCoreTestGateway(t)
	resp, err := http.Get(ts.URL + "/api/v1/tasks/poll")
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("expected 405, got %d", resp.StatusCode)
	}
}

// ---- Invalid JSON Body ----

func TestNodeRegister_InvalidJSON(t *testing.T) {
	ts := setupCoreTestGateway(t)

	resp, err := http.Post(ts.URL+"/api/v1/nodes/register", "application/json",
		bytes.NewBufferString("{not valid json"))
	if err != nil {
		t.Fatalf("register failed: %v", err)
	}
	defer resp.Body.Close()

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if result.Success {
		t.Error("expected failure for invalid JSON")
	}
}

func TestTaskSubmit_InvalidJSON(t *testing.T) {
	ts := setupCoreTestGateway(t)

	resp, err := http.Post(ts.URL+"/api/v1/tasks/submit", "application/json",
		bytes.NewBufferString("garbage"))
	if err != nil {
		t.Fatalf("submit failed: %v", err)
	}
	defer resp.Body.Close()

	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	if result.Success {
		t.Error("expected failure for invalid JSON")
	}
}

// ---- Heartbeat with invalid node_id ----

func TestHeartbeat_UnregisteredNode(t *testing.T) {
	ts := setupCoreTestGateway(t)

	hb := map[string]interface{}{
		"node_id":         "nonexistent-node",
		"cpu_utilization": 50.0,
	}
	body, _ := json.Marshal(hb)
	resp, err := http.Post(ts.URL+"/api/v1/nodes/heartbeat", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("heartbeat failed: %v", err)
	}
	defer resp.Body.Close()

	// Should still return 200 (graceful handling) or an error
	var result Response
	json.NewDecoder(resp.Body).Decode(&result)
	// Log the behavior — we accept either success or error
	t.Logf("heartbeat to unregistered node: success=%v error=%s", result.Success, result.Error)
}

// ---- Multiple operations in sequence ----

func TestRegister_Submit_Result_Cancel_Sequence(t *testing.T) {
	ts := setupCoreTestGateway(t)

	// 1. Register
	registerTestNode(t, ts, "seq-node")

	// 2. Submit
	task := map[string]interface{}{
		"task_id":     "seq-task-001",
		"source_type": "direct",
		"priority":    7,
		"command":     "echo sequence",
		"timeout":     60,
	}
	body, _ := json.Marshal(task)
	resp, err := http.Post(ts.URL+"/api/v1/tasks/submit", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("submit failed: %v", err)
	}
	resp.Body.Close()

	// 3. Result
	result_payload := map[string]interface{}{
		"task_id":     "seq-task-001",
		"success":     true,
		"exit_code":   0,
		"stdout":      "sequence",
		"executed_on": "seq-node",
	}
	body, _ = json.Marshal(result_payload)
	resp, err = http.Post(ts.URL+"/api/v1/tasks/result", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("result failed: %v", err)
	}
	resp.Body.Close()

	// 4. Cancel (should handle gracefully even after completion)
	cancel := map[string]string{"task_id": "seq-task-001"}
	body, _ = json.Marshal(cancel)
	resp, err = http.Post(ts.URL+"/api/v1/tasks/cancel", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("cancel failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200 for cancel after result, got %d", resp.StatusCode)
	}
}

// ---- Node Metrics Query ----

func TestNodeMetrics_UnregisteredNode(t *testing.T) {
	ts := setupCoreTestGateway(t)

	resp, err := http.Get(ts.URL + "/api/v1/nodes/metrics?node_id=nonexistent")
	if err != nil {
		t.Fatalf("metrics failed: %v", err)
	}
	defer resp.Body.Close()

	// Should handle gracefully
	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)
	t.Logf("metrics for unregistered node: %v", result)
}

// ---- Upgrade Check ----

func TestUpgradeCheck_Get(t *testing.T) {
	ts := setupCoreTestGateway(t)

	resp, err := http.Get(ts.URL + "/api/v1/upgrade/check")
	if err != nil {
		t.Fatalf("upgrade check failed: %v", err)
	}
	defer resp.Body.Close()

	// Should return 200 with version info (even if no upgrade available)
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}
