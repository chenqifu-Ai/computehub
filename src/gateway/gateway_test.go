// Package gateway_test - API 网关测试
package gateway

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func setupTestGateway(t *testing.T) *Gateway {
	t.Helper()
	tmpDir := t.TempDir()
	genesPath := filepath.Join(tmpDir, "genes.json")
	sandboxPath := filepath.Join(tmpDir, "sandbox")

	gw, err := NewGateway(0, sandboxPath, genesPath)
	if err != nil {
		t.Fatalf("NewGateway should succeed: %v", err)
	}
	// Store genes path so we can clean up
	_ = genesPath
	return gw
}

func TestNewGateway(t *testing.T) {
	gw := setupTestGateway(t)
	if gw == nil {
		t.Fatal("Gateway should not be nil")
	}
	if gw.Kernel == nil {
		t.Error("Kernel should be initialized")
	}
	if gw.Pipeline == nil {
		t.Error("Pipeline should be initialized")
	}
	if gw.Executor == nil {
		t.Error("Executor should be initialized")
	}
	if gw.GeneStore == nil {
		t.Error("GeneStore should be initialized")
	}
}

func TestHandleHealth(t *testing.T) {
	gw := setupTestGateway(t)

	req := httptest.NewRequest("GET", "/api/health", nil)
	w := httptest.NewRecorder()

	gw.handleHealth(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var body map[string]any
	json.NewDecoder(w.Body).Decode(&body)
	if body["success"] != true {
		t.Error("Response should have success=true")
	}
	
	data, ok := body["data"].(map[string]any)
	if !ok {
		t.Fatal("Response should have data as map")
	}
	if data["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got %v", data["status"])
	}
}

func TestHandleHealth_MethodNotAllowed(t *testing.T) {
	gw := setupTestGateway(t)

	req := httptest.NewRequest("POST", "/api/health", nil)
	w := httptest.NewRecorder()

	gw.handleHealth(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("Expected status 405, got %d", w.Code)
	}
}

func TestHandleStatus(t *testing.T) {
	gw := setupTestGateway(t)

	req := httptest.NewRequest("GET", "/api/status", nil)
	w := httptest.NewRecorder()

	gw.handleStatus(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var body map[string]any
	json.NewDecoder(w.Body).Decode(&body)
	if body["success"] != true {
		t.Error("Response should have success=true")
	}

	data, ok := body["data"].(map[string]any)
	if !ok {
		t.Fatal("Response should have data as map")
	}

	kernel, ok := data["kernel"].(map[string]any)
	if !ok {
		t.Fatal("Response should contain kernel data")
	}
	if kernel["status"] != "RUNNING" {
		t.Errorf("Expected kernel status RUNNING, got %v", kernel["status"])
	}
}

func TestHandleStatus_MethodNotAllowed(t *testing.T) {
	gw := setupTestGateway(t)

	req := httptest.NewRequest("POST", "/api/status", nil)
	w := httptest.NewRecorder()

	gw.handleStatus(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("Expected status 405, got %d", w.Code)
	}
}

func TestHandleDispatch_ValidSubmit(t *testing.T) {
	gw := setupTestGateway(t)

	payload := map[string]any{
		"id":           "test-001",
		"action":       "SUBMIT",
		"framework":    "pytorch",
		"resource_type": "gpu",
		"gpu_count":    1,
		"memory_gb":    8,
		"source":       "test",
	}
	body, _ := json.Marshal(payload)

	req := httptest.NewRequest("POST", "/api/dispatch", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	gw.handleDispatch(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d. Body: %s", w.Code, w.Body.String())
	}

	var resp map[string]any
	json.NewDecoder(w.Body).Decode(&resp)
	if resp["success"] != true {
		t.Errorf("Expected success=true, got: %s", w.Body.String())
	}
	if resp["task_id"] == "" {
		t.Error("Should return a task_id")
	}
}

func TestHandleDispatch_ValidExecute(t *testing.T) {
	gw := setupTestGateway(t)

	// First submit a task
	submitPayload := map[string]any{
		"id":           "test-002",
		"action":       "SUBMIT",
		"framework":    "tensorflow",
		"resource_type": "cpu",
		"cpu_count":    2,
		"memory_gb":    4,
		"source":       "test",
	}
	submitBody, _ := json.Marshal(submitPayload)
	req1 := httptest.NewRequest("POST", "/api/dispatch", bytes.NewBuffer(submitBody))
	req1.Header.Set("Content-Type", "application/json")
	w1 := httptest.NewRecorder()
	gw.handleDispatch(w1, req1)

	var submitResp map[string]any
	json.NewDecoder(w1.Body).Decode(&submitResp)
	taskID := submitResp["task_id"].(string)

	// Then execute it
	execPayload := map[string]any{
		"id":     taskID,
		"action": "EXECUTE",
	}
	execBody, _ := json.Marshal(execPayload)
	req2 := httptest.NewRequest("POST", "/api/dispatch", bytes.NewBuffer(execBody))
	req2.Header.Set("Content-Type", "application/json")
	w2 := httptest.NewRecorder()

	gw.handleDispatch(w2, req2)

	// Should succeed (execution runs in sandbox)
	if w2.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d. Body: %s", w2.Code, w2.Body.String())
	}
}

func TestHandleDispatch_InvalidJSON(t *testing.T) {
	gw := setupTestGateway(t)

	req := httptest.NewRequest("POST", "/api/dispatch", bytes.NewBuffer([]byte("not-json")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	gw.handleDispatch(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d", w.Code)
	}
}

func TestHandleDispatch_BlockedByPipeline(t *testing.T) {
	gw := setupTestGateway(t)

	payload := map[string]any{
		"id":        "test-003",
		"action":    "SUBMIT",
		"framework": "pytorch",
		"gpu_count": 100, // Exceeds limit
		"source":    "test",
	}
	body, _ := json.Marshal(payload)

	req := httptest.NewRequest("POST", "/api/dispatch", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	gw.handleDispatch(w, req)

	if w.Code != http.StatusUnprocessableEntity {
		t.Errorf("Expected status 422 (pipeline blocked), got %d. Body: %s", w.Code, w.Body.String())
	}
}

func TestHandleJobs_List(t *testing.T) {
	gw := setupTestGateway(t)

	req := httptest.NewRequest("GET", "/api/jobs", nil)
	w := httptest.NewRecorder()

	gw.handleJobs(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var body map[string]any
	json.NewDecoder(w.Body).Decode(&body)
	if body["success"] != true {
		t.Error("Response should have success=true")
	}
}

func TestHandleJobDetail(t *testing.T) {
	gw := setupTestGateway(t)

	// First submit a task
	submitPayload := map[string]any{
		"id":           "test-004",
		"action":       "SUBMIT",
		"framework":    "pytorch",
		"resource_type": "gpu",
		"gpu_count":    1,
		"source":       "test",
	}
	submitBody, _ := json.Marshal(submitPayload)
	req1 := httptest.NewRequest("POST", "/api/dispatch", bytes.NewBuffer(submitBody))
	req1.Header.Set("Content-Type", "application/json")
	w1 := httptest.NewRecorder()
	gw.handleDispatch(w1, req1)

	var submitResp map[string]any
	json.NewDecoder(w1.Body).Decode(&submitResp)
	taskID := submitResp["task_id"].(string)

	// Get job detail
	req2 := httptest.NewRequest("GET", "/api/jobs/"+taskID, nil)
	w2 := httptest.NewRecorder()

	gw.handleJobDetail(w2, req2)

	if w2.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d. Body: %s", w2.Code, w2.Body.String())
	}
}

func TestHandleJobDetail_NotFound(t *testing.T) {
	gw := setupTestGateway(t)

	req := httptest.NewRequest("GET", "/api/jobs/nonexistent", nil)
	w := httptest.NewRecorder()

	gw.handleJobDetail(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", w.Code)
	}
}

func TestHandleNodes(t *testing.T) {
	gw := setupTestGateway(t)

	req := httptest.NewRequest("GET", "/api/nodes", nil)
	w := httptest.NewRecorder()

	gw.handleNodes(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var body map[string]any
	json.NewDecoder(w.Body).Decode(&body)
	if body["success"] != true {
		t.Error("Response should have success=true")
	}
}

func TestGatewayServe(t *testing.T) {
	gw := setupTestGateway(t)

	// Start server on random port
	go func() {
		_ = gw.Serve(0)
	}()

	// Give it time to start
	time.Sleep(100 * time.Millisecond)

	// Stop it
	gw.Stop()
}

func TestLoadPredefinedGenes(t *testing.T) {
	gw := setupTestGateway(t)

	// Gene store should have predefined genes loaded
	stats := gw.GeneStore.Stats()
	if stats["total"] != 3 {
		t.Errorf("Expected 3 predefined genes, got %v", stats["total"])
	}
}

func TestGatewayConcurrentRequests(t *testing.T) {
	gw := setupTestGateway(t)

	// Fire 10 concurrent requests directly to handler (no server start)
	done := make(chan bool, 10)
	for i := 0; i < 10; i++ {
		go func() {
			req := httptest.NewRequest("GET", "/api/health", nil)
			w := httptest.NewRecorder()
			gw.handleHealth(w, req)
			if w.Code == http.StatusOK {
				done <- true
			} else {
				done <- false
			}
		}()
	}

	// All should succeed
	successCount := 0
	for i := 0; i < 10; i++ {
		if <-done {
			successCount++
		}
	}

	gw.Stop()

	if successCount != 10 {
		t.Errorf("Expected 10/10 concurrent requests to succeed, got %d", successCount)
	}
}

func TestMain(m *testing.M) {
	// Cleanup temp dirs after tests
	code := m.Run()
	os.Exit(code)
}
