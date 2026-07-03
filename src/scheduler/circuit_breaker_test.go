package scheduler

import (
	"testing"
	"time"
)

func TestNewCircuitBreaker(t *testing.T) {
	cb := NewCircuitBreaker(DefaultCircuitBreakerConfig())
	if cb.regions == nil {
		t.Fatal("regions map is nil")
	}
}

func TestRecordSuccess(t *testing.T) {
	cb := NewCircuitBreaker(DefaultCircuitBreakerConfig())
	cb.EnsureRegion("us-east")

	cb.RecordSuccess("us-east")
	cb.RecordSuccess("us-east")

	stats := cb.GetAllCircuits()
	circuit := stats["us-east"]

	if circuit.SuccessCount != 2 {
		t.Errorf("Expected 2 successes, got %d", circuit.SuccessCount)
	}
	if circuit.TotalAttempts != 2 {
		t.Errorf("Expected 2 total attempts, got %d", circuit.TotalAttempts)
	}
	if circuit.SuccessRate != 1.0 {
		t.Errorf("Expected 100%% success rate, got %.2f", circuit.SuccessRate)
	}
}

func TestRecordFailure(t *testing.T) {
	cb := NewCircuitBreaker(DefaultCircuitBreakerConfig())
	cb.EnsureRegion("us-east")

	// 记录失败
	cb.RecordFailure("us-east")

	stats := cb.GetAllCircuits()
	circuit := stats["us-east"]

	if circuit.FailureCount != 1 {
		t.Errorf("Expected 1 failure, got %d", circuit.FailureCount)
	}
	if circuit.LastFailure.IsZero() {
		t.Error("Expected non-zero last failure time")
	}
}

func TestCircuitOpen(t *testing.T) {
	cb := NewCircuitBreaker(CircuitBreakerConfig{
		SuccessThreshold: 0.7,
		OpenDuration:     1 * time.Minute,
	})

	cb.EnsureRegion("us-east")

	// 模拟高失败率
	for i := 0; i < 10; i++ {
		if i < 3 {
			cb.RecordSuccess("us-east")
		} else {
			cb.RecordFailure("us-east")
		}
	}

	state, err := cb.CheckRegion("us-east")
	if err != nil {
		t.Fatalf("CheckRegion failed: %v", err)
	}
	if state != CircuitOpen {
		t.Errorf("Expected CircuitOpen, got %v", state)
	}

	if !cb.IsOpen("us-east") {
		t.Error("Expected region to be open")
	}
}

func TestCircuitRecovery(t *testing.T) {
	cb := NewCircuitBreaker(CircuitBreakerConfig{
		SuccessThreshold: 0.7,
		OpenDuration:     100 * time.Millisecond, // 短超时用于测试
		HalfOpenMax:      3,
		HalfOpenWindow:   1 * time.Second,
	})

	cb.EnsureRegion("us-east")

	// 触发熔断
	for i := 0; i < 10; i++ {
		if i < 2 {
			cb.RecordSuccess("us-east")
		} else {
			cb.RecordFailure("us-east")
		}
	}

	// 等待熔断过期
	time.Sleep(150 * time.Millisecond)

	// 检查状态 - 应该进入半开
	state, _ := cb.CheckRegion("us-east")
	if state != CircuitHalfOpen {
		t.Errorf("Expected CircuitHalfOpen, got %v", state)
	}

	// 半开期间记录成功
	cb.RecordSuccess("us-east")
	cb.RecordSuccess("us-east")
	cb.RecordSuccess("us-east")

	// 应该恢复正常
	state, _ = cb.CheckRegion("us-east")
	if state != CircuitClosed {
		t.Errorf("Expected CircuitClosed after recovery, got %v", state)
	}
}

func TestCircuitFailureInHalfOpen(t *testing.T) {
	cb := NewCircuitBreaker(CircuitBreakerConfig{
		SuccessThreshold: 0.7,
		OpenDuration:     100 * time.Millisecond,
		HalfOpenMax:      3,
	})

	cb.EnsureRegion("us-east")

	// 触发熔断
	for i := 0; i < 10; i++ {
		if i < 2 {
			cb.RecordSuccess("us-east")
		} else {
			cb.RecordFailure("us-east")
		}
	}

	// 等待进入半开
	time.Sleep(150 * time.Millisecond)

	// 半开期间记录失败
	cb.RecordFailure("us-east")
	cb.RecordFailure("us-east")
	cb.RecordFailure("us-east")

	// 应该重新熔断
	state, _ := cb.CheckRegion("us-east")
	if state != CircuitOpen {
		t.Errorf("Expected CircuitOpen after half-open failure, got %v", state)
	}
}

func TestForceOpen(t *testing.T) {
	cb := NewCircuitBreaker(DefaultCircuitBreakerConfig())
	cb.ForceOpen("us-east")

	if !cb.IsOpen("us-east") {
		t.Error("Expected region to be force-opened")
	}
}

func TestForceClose(t *testing.T) {
	cb := NewCircuitBreaker(DefaultCircuitBreakerConfig())
	cb.ForceOpen("us-east")
	cb.ForceClose("us-east")

	if cb.IsOpen("us-east") {
		t.Error("Expected region to be force-closed")
	}
}

func TestResetRegion(t *testing.T) {
	cb := NewCircuitBreaker(DefaultCircuitBreakerConfig())
	cb.EnsureRegion("us-east")

	cb.RecordFailure("us-east")
	cb.RecordFailure("us-east")

	cb.ResetRegion("us-east")

	stats := cb.GetAllCircuits()
	circuit := stats["us-east"]

	if circuit.SuccessCount != 0 {
		t.Errorf("Expected 0 successes after reset, got %d", circuit.SuccessCount)
	}
	if circuit.State != CircuitClosed {
		t.Errorf("Expected closed after reset, got %v", circuit.State)
	}
}

func TestCircuitBreakerGetStats(t *testing.T) {
	cb := NewCircuitBreaker(DefaultCircuitBreakerConfig())

	cb.EnsureRegion("us-east")
	cb.EnsureRegion("eu-west")
	cb.EnsureRegion("ap-southeast")

	cb.ForceOpen("us-east")

	stats := cb.GetStats()
	if stats["total_regions"] != 3 {
		t.Errorf("Expected 3 total regions, got %v", stats["total_regions"])
	}
	if stats["open_regions"] != 1 {
		t.Errorf("Expected 1 open region, got %v", stats["open_regions"])
	}
	if stats["success_threshold"] != 0.7 {
		t.Errorf("Expected threshold 0.7, got %v", stats["success_threshold"])
	}
}

func TestTrackTaskResult(t *testing.T) {
	cb := NewCircuitBreaker(CircuitBreakerConfig{
		SuccessThreshold: 0.7,
		OpenDuration:     1 * time.Minute,
	})

	cb.EnsureRegion("us-east")

	// 成功任务
	task := &ScheduledTask{
		TaskID:     "task-001",
		Region:     "us-east",
		MaxRetries: 3,
	}
	cb.TrackTaskResult(task, true)

	if task.RetryCount != 0 {
		t.Errorf("Expected 0 retries for success, got %d", task.RetryCount)
	}
}

func TestTrackTaskResultFailure(t *testing.T) {
	cb := NewCircuitBreaker(CircuitBreakerConfig{
		SuccessThreshold: 0.7,
		OpenDuration:     1 * time.Minute,
	})

	cb.EnsureRegion("us-east")

	task := &ScheduledTask{
		TaskID:     "task-002",
		Region:     "us-east",
		MaxRetries: 3,
	}
	cb.TrackTaskResult(task, false)

	if task.RetryCount != 1 {
		t.Errorf("Expected 1 retry, got %d", task.RetryCount)
	}
}

func TestRetryTask(t *testing.T) {
	cb := NewCircuitBreaker(CircuitBreakerConfig{
		SuccessThreshold: 0.7,
		OpenDuration:     1 * time.Hour,
	})

	cb.EnsureRegion("us-east")
	cb.ForceOpen("us-east")

	task := &ScheduledTask{
		TaskID:     "task-003",
		Region:     "us-east",
		MaxRetries: 3,
	}

	// 应该切换到 eu-west
	result := cb.RetryTask(task, []string{"us-east", "eu-west"})

	if result == nil {
		t.Fatal("Expected non-nil retry result")
	}
	if result.Region != "eu-west" {
		t.Errorf("Expected eu-west, got %s", result.Region)
	}
}

func TestCircuitStateString(t *testing.T) {
	tests := []struct {
		state  CircuitState
		expect string
	}{
		{CircuitClosed, "closed"},
		{CircuitOpen, "open"},
		{CircuitHalfOpen, "half-open"},
	}

	for _, tt := range tests {
		if tt.state.String() != tt.expect {
			t.Errorf("Expected %s, got %s", tt.expect, tt.state.String())
		}
	}
}

func BenchmarkRecordSuccess(b *testing.B) {
	cb := NewCircuitBreaker(DefaultCircuitBreakerConfig())
	cb.EnsureRegion("us-east")

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cb.RecordSuccess("us-east")
	}
}
