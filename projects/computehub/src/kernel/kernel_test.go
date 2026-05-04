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

	// Give goroutine time to start
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
	time.Sleep(50 * time.Millisecond)

	// Dispatch 5 commands - state mirror should be capped at 3
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
	time.Sleep(50 * time.Millisecond)

	results := make([]string, 0, 5)
	done := make(chan string, 5)

	// Dispatch 5 commands
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
	time.Sleep(50 * time.Millisecond)

	// Dispatch more than buffer can hold at once
	responses := make([]chan Response, 5)
	for i := 0; i < 5; i++ {
		respChan := k.Dispatch("test", "PING", nil)
		responses[i] = respChan
	}

	// All should complete
	for i, respChan := range responses {
		resp := <-respChan
		if !resp.Success {
			t.Errorf("Command %d failed: %v", i, resp.Error)
		}
	}
}

func TestKernelSnapshotState(t *testing.T) {
	k := NewKernel(10, 100)

	// Snapshot without starting
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
	ek.Start() // Must start the kernel goroutine for PING/STATUS dispatching
	time.Sleep(50 * time.Millisecond)

	respChan := ek.DispatchExtended("ext-test", "PING", nil)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("PING via ExtendedKernel should succeed: %v", resp.Error)
	}
}

func TestExtendedKernelNodeOffline(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)

	respChan := ek.DispatchExtended("off-test", "NODE_OFFLINE", nil)
	resp := <-respChan

	if resp.Success {
		t.Fatal("NODE_OFFLINE should return not implemented")
	}
}

func TestExtendedKernelTaskCancel(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)

	respChan := ek.DispatchExtended("cancel-test", "TASK_CANCEL", nil)
	resp := <-respChan

	if resp.Success {
		t.Fatal("TASK_CANCEL should return not implemented")
	}
}

func TestExtendedKernelRegionQuery(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)

	respChan := ek.DispatchExtended("region-test", "REGION_QUERY", nil)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("REGION_QUERY should succeed: %v", resp.Error)
	}
}

func TestExtendedKernelMetricsReport(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)

	respChan := ek.DispatchExtended("metrics-test", "METRICS_REPORT", nil)
	resp := <-respChan

	if !resp.Success {
		t.Fatalf("METRICS_REPORT should succeed: %v", resp.Error)
	}
}

func TestExtendedKernelInvalidPayload(t *testing.T) {
	ek := NewExtendedKernel(10, 100, 10)

	// Pass invalid payload type for NodeRegister
	respChan := ek.DispatchExtended("invalid", ActionNodeRegister, "not a NodeRegister")
	resp := <-respChan

	if resp.Success {
		t.Fatal("Invalid payload should fail")
	}
}

func BenchmarkKernelDispatch(b *testing.B) {
	k := NewKernel(1000, 1000)
	k.Start()
	time.Sleep(50 * time.Millisecond)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		respChan := k.Dispatch("bench", "PING", nil)
		<-respChan
	}
}
