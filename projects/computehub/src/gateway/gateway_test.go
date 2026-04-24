package gateway

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
)

func setupTestGateway(t *testing.T) *httptest.Server {
	config := &GatewayConfig{
		GeneStorePath: "/tmp/test-genes.json",
		SandboxPath:   "/tmp/opc-sandbox",
		BufferSize:    100,
		MaxStates:     1000,
		MaxNodes:      50,
	}
	gw := NewOpcGateway(0, config) // port 0 = random
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gw.ServeHTTP(w, r)
	}))
	t.Cleanup(func() { ts.Close() })
	return ts
}

func TestHealthEndpoint(t *testing.T) {
	ts := setupTestGateway(t)
	resp, err := http.Get(ts.URL + "/api/health")
	if err != nil {
		t.Fatalf("Health check failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}
}

func TestStatusEndpoint(t *testing.T) {
	ts := setupTestGateway(t)
	resp, err := http.Get(ts.URL + "/api/status")
	if err != nil {
		t.Fatalf("Status check failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}

	var status map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&status); err != nil {
		t.Fatalf("Failed to decode status: %v", err)
	}

	// Check kernel status
	ks, ok := status["kernel"].(map[string]interface{})
	if !ok {
		t.Fatal("kernel status not found")
	}
	if ks["status"] != "RUNNING" {
		t.Errorf("Expected kernel status RUNNING, got %v", ks["status"])
	}

	// Check node manager
	nm, ok := status["nodeManager"].(map[string]interface{})
	if !ok {
		t.Fatal("nodeManager status not found")
	}
	if nm["total_nodes"] != float64(0) {
		t.Errorf("Expected 0 total nodes, got %v", nm["total_nodes"])
	}
}

func TestNodeRegisterEndpoint(t *testing.T) {
	ts := setupTestGateway(t)

	reg := map[string]interface{}{
		"node_id":        "api-test-node-001",
		"node_type":      "gpu",
		"gpu_type":       "A100",
		"region":         "us-east",
		"cpu_cores":      32,
		"memory_gb":      128,
		"gpu_memory_gb":  80,
		"max_concurrency": 10,
		"ip_address":     "10.0.0.1",
	}

	body, _ := json.Marshal(reg)
	resp, err := http.Post(ts.URL+"/api/v1/nodes/register", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Node register failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	if result["success"] != true {
		t.Errorf("Expected success=true, got %v", result["success"])
	}
}

func TestNodeListEndpoint(t *testing.T) {
	ts := setupTestGateway(t)

	// Register a node first
	reg := map[string]interface{}{
		"node_id":        "list-test-node",
		"node_type":      "gpu",
		"gpu_type":       "H100",
		"region":         "eu-west",
		"max_concurrency": 5,
	}
	body, _ := json.Marshal(reg)
	http.Post(ts.URL+"/api/v1/nodes/register", "application/json", bytes.NewBuffer(body))

	// List nodes
	resp, err := http.Get(ts.URL + "/api/v1/nodes/list")
	if err != nil {
		t.Fatalf("Node list failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	if result["success"] != true {
		t.Errorf("Expected success=true")
	}
}

func TestTaskSubmitEndpoint(t *testing.T) {
	ts := setupTestGateway(t)

	// Register node first
	reg := map[string]interface{}{
		"node_id":        "task-api-node",
		"node_type":      "gpu",
		"region":         "us-east",
		"max_concurrency": 10,
		"status":         "online",
	}
	body, _ := json.Marshal(reg)
	http.Post(ts.URL+"/api/v1/nodes/register", "application/json", bytes.NewBuffer(body))

	// Submit task
	task := map[string]interface{}{
		"task_id":   "api-task-001",
		"source_type": "direct",
		"priority":  8,
		"command":   "echo hello world",
		"timeout":   300,
	}
	body, _ = json.Marshal(task)
	resp, err := http.Post(ts.URL+"/api/v1/tasks/submit", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Task submit failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	if result["success"] != true {
		t.Errorf("Expected success=true, got %v", result["success"])
	}
}

func TestTaskResultEndpoint(t *testing.T) {
	ts := setupTestGateway(t)

	// Register node
	reg := map[string]interface{}{
		"node_id":        "result-api-node",
		"node_type":      "gpu",
		"region":         "us-east",
		"max_concurrency": 10,
		"status":         "online",
	}
	body, _ := json.Marshal(reg)
	http.Post(ts.URL+"/api/v1/nodes/register", "application/json", bytes.NewBuffer(body))

	// Submit task
	task := map[string]interface{}{
		"task_id":   "result-api-task",
		"command":   "echo done",
		"source_type": "direct",
		"priority":  5,
	}
	body, _ = json.Marshal(task)
	http.Post(ts.URL+"/api/v1/tasks/submit", "application/json", bytes.NewBuffer(body))

	// Submit result
	result := map[string]interface{}{
		"task_id":      "result-api-task",
		"success":      true,
		"exit_code":    0,
		"stdout":       "done",
		"duration":     "0.5s",
		"executed_on":  "result-api-node",
		"verified":     true,
	}
	body, _ = json.Marshal(result)
	resp, err := http.Post(ts.URL+"/api/v1/tasks/result", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Task result failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}
}

func TestNodeHeartbeatEndpoint(t *testing.T) {
	ts := setupTestGateway(t)

	// Register node
	reg := map[string]interface{}{
		"node_id":     "hb-api-node",
		"node_type":   "gpu",
		"gpu_type":    "A100",
		"region":      "us-east",
		"status":      "online",
	}
	body, _ := json.Marshal(reg)
	http.Post(ts.URL+"/api/v1/nodes/register", "application/json", bytes.NewBuffer(body))

	// Send heartbeat with GPU metrics
	hb := map[string]interface{}{
		"node_id":     "hb-api-node",
		"cpu_utilization": 65.0,
		"memory_used_gb":  48.0,
	}
	body, _ = json.Marshal(hb)
	resp, err := http.Post(ts.URL+"/api/v1/nodes/heartbeat", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Heartbeat failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}
}

func TestDispatchEndpointLegacy(t *testing.T) {
	ts := setupTestGateway(t)

	// Legacy dispatch
	reqBody := map[string]interface{}{
		"id":      "legacy-001",
		"command": "PING",
	}
	body, _ := json.Marshal(reqBody)
	resp, err := http.Post(ts.URL+"/api/dispatch", "application/json", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Legacy dispatch failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}
}

func TestMetricsEndpoint(t *testing.T) {
	ts := setupTestGateway(t)

	// Register a node
	reg := map[string]interface{}{
		"node_id":        "metrics-api-node",
		"node_type":      "gpu",
		"gpu_type":       "V100",
		"region":         "ap-southeast",
		"cpu_cores":      16,
		"max_concurrency": 8,
		"status":         "online",
	}
	body, _ := json.Marshal(reg)
	http.Post(ts.URL+"/api/v1/nodes/register", "application/json", bytes.NewBuffer(body))

	// Get node metrics
	resp, err := http.Get(ts.URL + "/api/v1/nodes/metrics?node_id=metrics-api-node")
	if err != nil {
		t.Fatalf("Metrics query failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	if result["success"] != true {
		t.Errorf("Expected success=true")
	}
}

func TestTaskListEndpoint(t *testing.T) {
	ts := setupTestGateway(t)

	// Register node and submit tasks
	reg := map[string]interface{}{
		"node_id":        "list-api-node",
		"node_type":      "gpu",
		"region":         "us-east",
		"max_concurrency": 10,
		"status":         "online",
	}
	body, _ := json.Marshal(reg)
	http.Post(ts.URL+"/api/v1/nodes/register", "application/json", bytes.NewBuffer(body))

	for i := 0; i < 3; i++ {
		task := map[string]interface{}{
			"task_id":   fmt.Sprintf("list-api-task-%d", i),
			"command":   fmt.Sprintf("echo task-%d", i),
			"priority":  5,
		}
		body, _ = json.Marshal(task)
		http.Post(ts.URL+"/api/v1/tasks/submit", "application/json", bytes.NewBuffer(body))
	}

	// List tasks
	resp, err := http.Get(ts.URL + "/api/v1/tasks/list")
	if err != nil {
		t.Fatalf("Task list failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected 200, got %d", resp.StatusCode)
	}

	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	if result["success"] != true {
		t.Errorf("Expected success=true")
	}
}
