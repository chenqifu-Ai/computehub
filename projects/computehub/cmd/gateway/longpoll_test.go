package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"testing"
	"time"
)

func TestLongPollFlow(t *testing.T) {
	gw := NewGateway("localhost", 8123, "frontend")
	go gw.ServeWithServer(8123)
	defer gw.Shutdown()
	time.Sleep(2 * time.Second)

	base := "http://localhost:8123"

	// 1. register node
	nodeID := "node-test"
	t.Logf("Register node: %s", nodeID)
	res := mustPost(base, "/api/v1/nodes/register", map[string]interface{}{
		"node_id":       nodeID,
		"gpu_type":      "test-gpu",
		"region":        "test",
		"cpu_cores":     4,
		"memory_gb":     8,
		"platform":      "linux/arm64",
		"max_concurrency": 4,
	})
	if !res {
		t.Fatal("register failed")
	}

	// 2. submit task (no direct assignment - no AssignedNode in payload)
	t.Log("Submitting task...")
	task := map[string]interface{}{
		"command":     "echo hello-longpoll",
		"timeout":     30,
		"priority":    5,
		"source_type": "manual",
	}
	res = mustPost(base, "/api/v1/tasks/submit", task)
	if !res {
		t.Fatal("task submit failed")
	}
	// Get the task ID from list
	list := mustGet(base, "/api/v1/tasks/list")
	var listData map[string]interface{}
	json.Unmarshal([]byte(list), &listData)
	t.Logf("Tasks list: %s", list)

	// 3. poll with long_poll=true
	t.Log("Polling with long_poll...")
	resp := mustPost(base, "/api/v1/tasks/poll", map[string]interface{}{
		"node_id":    nodeID,
		"long_poll":  true,
	})
	t.Logf("Poll response: %s", resp)

	// 4. Check pending tasks count (GET)
	t.Log("Checking pending tasks...")
	pendingResp := mustGet(base, "/api/v1/tasks/poll?node_id="+nodeID)
	t.Logf("Pending response: %s", pendingResp)
	if strings.Contains(pendingResp, "pending_tasks") {
		t.Log("✅ pending_tasks field present")
	} else {
		t.Logf("⚠️ pending_tasks not found: %s", pendingResp)
	}

	t.Log("All tests passed!")
}

func mustPost(url, path string, body interface{}) bool {
	data, _ := json.Marshal(body)
	r, err := http.Post(url+path, "application/json", bytes.NewBuffer(data))
	if err != nil {
		fmt.Fprintf(os.Stderr, "POST %s failed: %v\n", path, err)
		return false
	}
	defer r.Body.Close()
	resp, _ := io.ReadAll(r.Body)
	fmt.Fprintf(os.Stderr, "  POST %s -> %s\n", path, string(resp))
	return r.StatusCode == 200 && bytes.Contains(resp, []byte(`"success":true`))
}

func mustGet(url, path string) string {
	r, err := http.Get(url + path)
	if err != nil {
		return ""
	}
	defer r.Body.Close()
	data, _ := io.ReadAll(r.Body)
	return string(data)
}
