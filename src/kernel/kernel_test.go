package kernel

import (
	"testing"
	"time"
)

func TestNewKernel(t *testing.T) {
	k := NewKernel(100, 1000)
	if k.maxStates != 1000 {
		t.Errorf("Expected maxStates 1000, got %d", k.maxStates)
	}
	if cap(k.LinearQueue) != 100 {
		t.Errorf("Expected buffer size 100, got %d", cap(k.LinearQueue))
	}
	if len(k.stateMirror) != 0 {
		t.Errorf("Expected empty state mirror, got %d states", len(k.stateMirror))
	}
}

func TestKernelStart(t *testing.T) {
	k := NewKernel(10, 100)
	k.Start()
	defer k.Stop()
	time.Sleep(50 * time.Millisecond)

	respChan := k.Dispatch("test-1", "PING", nil)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("PING should succeed, got error: %v", resp.Error)
	}
	data, ok := resp.Data.(string)
	if !ok || data != "PONG" {
		t.Errorf("Expected 'PONG', got '%v'", resp.Data)
	}
}

func TestKernelStatus(t *testing.T) {
	k := NewKernel(10, 100)
	k.Start()
	defer k.Stop()
	time.Sleep(50 * time.Millisecond)

	respChan := k.Dispatch("test-2", "STATUS", nil)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("STATUS should succeed, got error: %v", resp.Error)
	}
}

func TestKernelUnknownAction(t *testing.T) {
	k := NewKernel(10, 100)
	k.Start()
	defer k.Stop()
	time.Sleep(50 * time.Millisecond)

	respChan := k.Dispatch("test-3", "UNKNOWN_ACTION", nil)
	resp := <-respChan

	if resp.Success {
		t.Fatal("Unknown action should fail")
	}
	if resp.Error == nil {
		t.Fatal("Expected error for unknown action")
	}
}

func TestKernelStateMirrorLimit(t *testing.T) {
	k := NewKernel(10, 3)
	k.Start()
	defer k.Stop()
	time.Sleep(50 * time.Millisecond)

	for i := 0; i < 5; i++ {
		respChan := k.Dispatch("test", "PING", nil)
		<-respChan
	}

	k.Mu.RLock()
	stateCount := len(k.stateMirror)
	k.Mu.RUnlock()

	if stateCount > 3 {
		t.Errorf("Expected max 3 states in mirror, got %d", stateCount)
	}
}

func TestKernelDispatchOrder(t *testing.T) {
	k := NewKernel(100, 1000)
	k.Start()
	defer k.Stop()
	time.Sleep(50 * time.Millisecond)

	results := make([]string, 0, 5)
	done := make(chan string, 5)

	for i := 0; i < 5; i++ {
		go func(n int) {
			respChan := k.Dispatch("test", "PING", nil)
			resp := <-respChan
			if resp.Success {
				done <- "PONG"
			}
		}(i)
	}

	for i := 0; i < 5; i++ {
		results = append(results, <-done)
	}
}

func TestKernelLatencyRecorded(t *testing.T) {
	k := NewKernel(10, 100)
	k.Start()
	defer k.Stop()
	time.Sleep(50 * time.Millisecond)

	respChan := k.Dispatch("test", "PING", nil)
	<-respChan

	k.Mu.RLock()
	latency := k.LastLatency
	k.Mu.RUnlock()

	if latency <= 0 {
		t.Error("Kernel latency should be positive after command dispatch")
	}
}

func TestKernelBufferSize(t *testing.T) {
	k := NewKernel(2, 100)
	k.Start()
	defer k.Stop()
	time.Sleep(50 * time.Millisecond)

	responses := make([]chan Response, 5)
	for i := 0; i < 5; i++ {
		respChan := k.Dispatch("test", "PING", nil)
		responses[i] = respChan
	}

	for i, respChan := range responses {
		resp := <-respChan
		if !resp.Success {
			t.Errorf("Command %d failed: %v", i, resp.Error)
		}
	}
}

func TestKernelSnapshotState(t *testing.T) {
	k := NewKernel(10, 100)

	k.snapshotState()

	k.Mu.RLock()
	if len(k.stateMirror) != 1 {
		t.Errorf("Expected 1 state snapshot, got %d", len(k.stateMirror))
	}
	state := k.stateMirror[0]
	if state.Timestamp == 0 {
		t.Error("Expected non-zero timestamp in state")
	}
	k.Mu.RUnlock()
}

func TestNewExtendedKernel(t *testing.T) {
	ek := NewExtendedKernel(100, 1000, 50)
	if ek.NodeMgr == nil {
		t.Fatal("NodeManager should not be nil")
	}
	if ek.OpcKernel == nil {
		t.Fatal("OpcKernel should not be nil")
	}
}

func TestExtendedKernelPing(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)
	ek.Start()
	defer ek.GetKernel().Stop()
	time.Sleep(50 * time.Millisecond)

	respChan := ek.DispatchExtended("ext-test", "PING", nil)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("PING via ExtendedKernel should succeed: %v", resp.Error)
	}
}

func TestExtendedKernelNodeOffline(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)
	ek.Start()
	defer ek.GetKernel().Stop()
	time.Sleep(50 * time.Millisecond)

	reg := &NodeRegister{
		NodeID:   "test-offline",
		NodeType: "gpu",
		Region:   "us-east",
		Status:   "online",
	}
	respChan := ek.DispatchExtended("reg", ActionNodeRegister, reg)
	<-respChan

	respChan = ek.DispatchExtended("off-test", ActionNodeOffline, "test-offline")
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("NODE_OFFLINE failed: %v", resp.Error)
	}
}

func TestExtendedKernelTaskCancel(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)
	ek.Start()
	defer ek.GetKernel().Stop()
	time.Sleep(50 * time.Millisecond)

	reg := &NodeRegister{
		NodeID:        "test-cancel",
		NodeType:      "gpu",
		Region:        "us-east",
		MaxConcurrency: 5,
		Status:        "online",
	}
	respChan := ek.DispatchExtended("reg", ActionNodeRegister, reg)
	<-respChan

	task := &TaskSubmit{
		TaskID: "cancel-task",
	}
	respChan = ek.DispatchExtended("sub", ActionTaskSubmit, task)
	<-respChan

	respChan = ek.DispatchExtended("cancel-test", ActionTaskCancel, "cancel-task")
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("TASK_CANCEL failed: %v", resp.Error)
	}
}

func TestExtendedKernelRegionQuery(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)
	ek.Start()
	defer ek.GetKernel().Stop()
	time.Sleep(50 * time.Millisecond)

	respChan := ek.DispatchExtended("region-test", ActionRegionQuery, nil)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("REGION_QUERY should succeed: %v", resp.Error)
	}
}

func TestExtendedKernelMetricsReport(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)
	ek.Start()
	defer ek.GetKernel().Stop()
	time.Sleep(50 * time.Millisecond)

	respChan := ek.DispatchExtended("metrics-test", ActionMetricsReport, nil)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("METRICS_REPORT should succeed: %v", resp.Error)
	}
}

func TestExtendedKernelInvalidPayload(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)
	ek.Start()
	defer ek.GetKernel().Stop()
	time.Sleep(50 * time.Millisecond)

	respChan := ek.DispatchExtended("invalid", ActionNodeRegister, "not a NodeRegister")
	resp := <-respChan

	if resp.Success {
		t.Fatal("Invalid payload should fail")
	}
}

func BenchmarkKernelDispatch(b *testing.B) {
	k := NewKernel(1000, 1000)
	k.Start()
	defer k.Stop()
	time.Sleep(50 * time.Millisecond)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		respChan := k.Dispatch("bench", "PING", nil)
		<-respChan
	}
}
