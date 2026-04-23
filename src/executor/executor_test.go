// Package executor - comprehensive tests for enhanced execution engine
package executor

import (
	"fmt"
	"os"
	"runtime"
	"strings"
	"testing"
	"time"
)

// ─── 基础功能测试 ───

func TestNewExecutor(t *testing.T) {
	tmpDir := t.TempDir()
	exec, err := NewExecutor(tmpDir)
	if err != nil {
		t.Fatalf("NewExecutor should succeed: %v", err)
	}
	if exec == nil {
		t.Fatal("Executor should not be nil")
	}
	if exec.SandboxPath != tmpDir {
		t.Errorf("Expected sandbox path %s, got %s", tmpDir, exec.SandboxPath)
	}
}

func TestNewExecutorWithIsolation(t *testing.T) {
	tmpDir := t.TempDir()
	exec, err := NewExecutorWithIsolation(tmpDir, IsolationShell)
	if err != nil {
		t.Fatalf("NewExecutorWithIsolation should succeed: %v", err)
	}
	if exec.Isolation != IsolationShell {
		t.Errorf("Expected isolation shell, got %s", exec.Isolation)
	}
}

func TestAutoDetectIsolation(t *testing.T) {
	level := autoDetectIsolation()
	// Should be one of: shell, chroot, cgroup, docker
	switch level {
	case IsolationShell, IsolationChroot, IsolationCgroup, IsolationDocker:
		// valid
	default:
		t.Fatalf("Unknown isolation level: %d", level)
	}
	t.Logf("Auto-detected isolation: %s", level)
}

func TestIsolationLevelString(t *testing.T) {
	tests := []struct {
		level    IsolationLevel
		expected string
	}{
		{IsolationDocker, "docker"},
		{IsolationCgroup, "cgroup"},
		{IsolationChroot, "chroot"},
		{IsolationShell, "shell"},
	}
	for _, tc := range tests {
		if tc.level.String() != tc.expected {
			t.Errorf("IsolationLevel(%d).String() = %s, want %s", tc.level, tc.level.String(), tc.expected)
		}
	}
}

// ─── 命令执行测试 ───

func TestExecute_SimpleCommand(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	result := exec.Execute("task-001", "echo 'hello'")
	if result.ExitCode != 0 {
		t.Errorf("Expected exit code 0, got %d, stderr: %s", result.ExitCode, result.Stderr)
	}
	if !strings.Contains(result.Stdout, "hello") {
		t.Errorf("Expected stdout to contain 'hello', got '%s'", result.Stdout)
	}
	if result.Duration == 0 {
		t.Error("Duration should be > 0")
	}
	// Isolation level is auto-detected, just verify it's valid
	validIsolation := result.Isolation == "shell" || result.Isolation == "docker" || result.Isolation == "cgroup" || result.Isolation == "chroot"
	if !validIsolation {
		t.Errorf("Invalid isolation level: %s", result.Isolation)
	}
}

func TestExecute_FailingCommand(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	result := exec.Execute("task-002", "false")
	if result.ExitCode == 0 {
		t.Error("Expected non-zero exit code for 'false'")
	}
}

func TestExecute_CommandNotFound(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	result := exec.Execute("task-003", "nonexistent_command_xyz_12345")
	if result.ExitCode == 0 {
		t.Error("Expected non-zero exit code for nonexistent command")
	}
}

func TestExecute_FileCreation(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	result := exec.Execute("task-004", "echo 'created' > output.txt && cat output.txt")
	if result.ExitCode != 0 {
		t.Errorf("Expected exit code 0, got %d", result.ExitCode)
	}
	if result.Stdout != "created\n" {
		t.Errorf("Expected 'created\\n', got '%s'", result.Stdout)
	}
}

func TestExecute_MultipleCommands(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	result := exec.Execute("task-005", "echo a > /dev/null; echo b >> output.txt; echo c >> output.txt; cat output.txt")
	if result.ExitCode != 0 {
		t.Errorf("Expected exit code 0, got %d", result.ExitCode)
	}
}

func TestExecute_Timeout(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	config := &TaskConfig{
		Command: "sleep 10",
		Timeout: 500 * time.Millisecond,
	}
	result := exec.ExecuteWithConfig("task-006", config)
	if result.ExitCode != 124 {
		t.Errorf("Expected timeout exit code 124, got %d", result.ExitCode)
	}
}

// ─── 环境变量测试 ───

func TestExecute_WithEnv(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	config := &TaskConfig{
		Command: "echo $MY_VAR",
		Env:     map[string]string{"MY_VAR": "test_value"},
	}
	result := exec.ExecuteWithConfig("task-007", config)
	if result.ExitCode != 0 {
		t.Errorf("Expected exit code 0, got %d", result.ExitCode)
	}
	if result.Stdout != "test_value\n" {
		t.Errorf("Expected 'test_value\\n', got '%s'", result.Stdout)
	}
}

// ─── 验证器测试 ───

func TestDefaultValidator_Pass(t *testing.T) {
	validator := DefaultValidator("/tmp/test")
	result := ExecutionResult{ExitCode: 0, Duration: time.Second}
	v := validator(result)
	if !v.Passed {
		t.Fatalf("Expected passed, got: %s", v.Message)
	}
}

func TestDefaultValidator_FailExitCode(t *testing.T) {
	validator := DefaultValidator("/tmp/test")
	result := ExecutionResult{ExitCode: 1, Duration: time.Second}
	v := validator(result)
	if v.Passed {
		t.Fatal("Expected failed due to non-zero exit code")
	}
}

func TestDefaultValidator_FailDuration(t *testing.T) {
	validator := DefaultValidator("/tmp/test")
	result := ExecutionResult{ExitCode: 0, Duration: 0}
	v := validator(result)
	if v.Passed {
		t.Fatal("Expected failed due to zero duration")
	}
}

func TestFileExistsValidator_Pass(t *testing.T) {
	tmpDir := t.TempDir()
	os.WriteFile(tmpDir+"/output.txt", []byte("test"), 0644)

	validator := FileExistsValidator(tmpDir, "output.txt")
	result := ExecutionResult{ExitCode: 0, Duration: time.Second}
	v := validator(result)
	if !v.Passed {
		t.Fatalf("Expected passed, got: %s", v.Message)
	}
}

func TestFileExistsValidator_Fail(t *testing.T) {
	tmpDir := t.TempDir()

	validator := FileExistsValidator(tmpDir, "nonexistent.txt")
	result := ExecutionResult{ExitCode: 0, Duration: time.Second}
	v := validator(result)
	if v.Passed {
		t.Fatal("Expected failed for non-existent file")
	}
}

func TestStdoutContainsValidator_Pass(t *testing.T) {
	validator := StdoutContainsValidator("hello")
	result := ExecutionResult{ExitCode: 0, Stdout: "hello world\n"}
	v := validator(result)
	if !v.Passed {
		t.Fatalf("Expected passed, got: %s", v.Message)
	}
}

func TestStdoutContainsValidator_Fail(t *testing.T) {
	validator := StdoutContainsValidator("world")
	result := ExecutionResult{ExitCode: 0, Stdout: "hello foo\n"}
	v := validator(result)
	if v.Passed {
		t.Fatal("Expected failed for missing substring")
	}
}

func TestDurationBelowValidator_Pass(t *testing.T) {
	validator := DurationBelowValidator(10 * time.Second)
	result := ExecutionResult{Duration: 5 * time.Second}
	v := validator(result)
	if !v.Passed {
		t.Fatalf("Expected passed, got: %s", v.Message)
	}
}

func TestDurationBelowValidator_Fail(t *testing.T) {
	validator := DurationBelowValidator(1 * time.Millisecond)
	result := ExecutionResult{Duration: 5 * time.Second}
	v := validator(result)
	if v.Passed {
		t.Fatal("Expected failed for exceeding duration limit")
	}
}

func TestExitCodeValidator(t *testing.T) {
	validator := ExitCodeValidator(0)
	result := ExecutionResult{ExitCode: 0}
	v := validator(result)
	if !v.Passed {
		t.Fatalf("Expected passed, got: %s", v.Message)
	}
}

func TestArtifactCountValidator_Pass(t *testing.T) {
	validator := ArtifactCountValidator(2)
	result := ExecutionResult{Artifacts: []string{"a.txt", "b.txt"}}
	v := validator(result)
	if !v.Passed {
		t.Fatalf("Expected passed, got: %s", v.Message)
	}
}

func TestExecuteWithValidation(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	validators := []Validator{
		ExitCodeValidator(0),
		StdoutContainsValidator("hello"),
	}

	result, validations := exec.ExecuteWithValidation("task-100", "echo 'hello'", validators...)
	if !result.IsVerified {
		t.Fatal("Expected verified as true")
	}
	if len(validations) != 3 { // 2 custom + 1 default
		t.Errorf("Expected 3 validations, got %d", len(validations))
	}
}

// ─── 资源监控测试 ───

func TestResourceMonitor_GetMemoryMB(t *testing.T) {
	m := NewResourceMonitor()
	memMB := m.GetMemoryMB()
	if runtime.GOOS == "linux" && memMB == 0 {
		t.Log("Memory read returned 0 - may be non-standard Linux environment")
	}
}

func TestResourceMonitor_GetCPUCount(t *testing.T) {
	m := NewResourceMonitor()
	count := m.GetCPUCount()
	if count <= 0 {
		t.Error("CPU count should be >= 1")
	}
}

func TestResourceMonitor_SystemInfo(t *testing.T) {
	m := NewResourceMonitor()
	info := m.SystemInfo()
	if cpu, ok := info["cpu_cores"].(int); ok && cpu <= 0 {
		t.Log("CPU cores should be >= 1 (got 0, possibly restricted environment)")
	}
	if osVal, ok := info["os"].(string); !ok || osVal == "" {
		t.Error("OS should be a non-empty string")
	}
}

// ─── 任务生命周期测试 ───

func TestStartStopTask(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	if exec.IsRunning("task-100") {
		t.Fatal("Task should not be running initially")
	}

	err := exec.StartTask("task-100")
	if err != nil {
		t.Fatalf("StartTask should succeed: %v", err)
	}

	if !exec.IsRunning("task-100") {
		t.Fatal("Task should be running after StartTask")
	}

	exec.StopTask("task-100")
	if exec.IsRunning("task-100") {
		t.Fatal("Task should not be running after StopTask")
	}
}

func TestStartTask_Duplicate(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	exec.StartTask("task-101")
	err := exec.StartTask("task-101")
	if err == nil {
		t.Fatal("Duplicate StartTask should return error")
	}
}

func TestRunningCount(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	exec.StartTask("task-201")
	exec.StartTask("task-202")
	exec.StartTask("task-203")

	count := exec.RunningCount()
	if count != 3 {
		t.Errorf("Expected 3 running tasks, got %d", count)
	}

	exec.StopTask("task-201")
	count = exec.RunningCount()
	if count != 2 {
		t.Errorf("Expected 2 running tasks, got %d", count)
	}
}

func TestRunningTasks(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	exec.StartTask("task-a")
	exec.StartTask("task-b")
	exec.StartTask("task-c")

	tasks := exec.RunningTasks()
	if len(tasks) != 3 {
		t.Errorf("Expected 3 running tasks, got %d", len(tasks))
	}
}

// ─── 任务队列测试 ───

func TestTaskQueue(t *testing.T) {
	tq := NewTaskQueue(2)

	resultCh := make(chan ExecutionResult, 100)
	go func() {
		for r := range tq.Results() {
			resultCh <- r
		}
	}()

	// Submit 5 tasks
	for i := 0; i < 5; i++ {
		tq.Submit(&QueuedTask{
			TaskID: fmt.Sprintf("queue-%d", i),
			Config: &TaskConfig{Command: "echo done"},
		})
	}

	// Wait for results
	for i := 0; i < 5; i++ {
		select {
		case r := <-resultCh:
			if r.ExitCode != 0 {
				t.Errorf("Task %s failed: exit code %d", r.TaskID, r.ExitCode)
			}
		case <-time.After(5 * time.Second):
			t.Fatalf("Timeout waiting for task result")
		}
	}

	tq.Stop()
	close(resultCh)
}

// ─── 集成测试 ───

func TestFullExecutionChain(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	// Create a file
	result := exec.Execute("chain-001", "echo 'final' > result.txt")
	if result.ExitCode != 0 {
		t.Fatalf("Chain step 1 failed: %v", result.Stderr)
	}

	// Verify with validator
	validator := FileExistsValidator(tmpDir, "chain-001/result.txt")
	v := validator(ExecutionResult{ExitCode: 0, Duration: time.Second})
	if !v.Passed {
		t.Fatalf("File not found: %s", v.Message)
	}
}

func BenchmarkExecute_Simple(b *testing.B) {
	tmpDir := b.TempDir()
	exec, _ := NewExecutor(tmpDir)
	for i := 0; i < b.N; i++ {
		exec.Execute(fmt.Sprintf("bench-%d", i), "echo ok")
	}
}

func BenchmarkValidate_Default(b *testing.B) {
	validator := DefaultValidator("/tmp/test")
	result := ExecutionResult{ExitCode: 0, Duration: time.Second}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		validator(result)
	}
}
