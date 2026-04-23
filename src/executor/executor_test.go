// Package executor_test - 执行器单元测试
package executor

import (
	"os"
	"testing"
	"time"
)

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

func TestExecute_SimpleCommand(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	result := exec.Execute("task-001", "echo 'hello'")
	if result.ExitCode != 0 {
		t.Errorf("Expected exit code 0, got %d", result.ExitCode)
	}
	if result.Stdout != "hello\n" {
		t.Errorf("Expected 'hello\\n', got '%s'", result.Stdout)
	}
	if result.Duration == 0 {
		t.Error("Duration should be > 0")
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

	result := exec.Execute("task-003", "nonexistent_command_xyz")
	if result.ExitCode == 0 {
		t.Error("Expected non-zero exit code for nonexistent command")
	}
}

func TestExecuteWithValidation(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	validator := func(result ExecutionResult) bool {
		return result.ExitCode == 0 && result.Duration > 0
	}

	result, verified := exec.ExecuteWithValidation("task-004", "echo 'test'", validator)
	if !verified {
		t.Fatal("Should be verified as true")
	}
	if result.ExitCode != 0 {
		t.Errorf("Expected exit code 0, got %d", result.ExitCode)
	}
}

func TestExecuteWithValidation_Failure(t *testing.T) {
	tmpDir := t.TempDir()
	exec, _ := NewExecutor(tmpDir)

	validator := func(result ExecutionResult) bool {
		return result.ExitCode == 0
	}

	_, verified := exec.ExecuteWithValidation("task-005", "false", validator)
	if verified {
		t.Fatal("Should be verified as false")
	}
}

func TestDefaultValidator(t *testing.T) {
	validator := DefaultValidator("/tmp/test")

	// Passing result
	passResult := ExecutionResult{ExitCode: 0, Duration: time.Second}
	if !validator(passResult) {
		t.Fatal("Default validator should accept exitCode=0, duration>0")
	}

	// Failing result - exit code
	failResult := ExecutionResult{ExitCode: 1, Duration: time.Second}
	if validator(failResult) {
		t.Fatal("Default validator should reject non-zero exit code")
	}

	// Failing result - zero duration
	failResult2 := ExecutionResult{ExitCode: 0, Duration: 0}
	if validator(failResult2) {
		t.Fatal("Default validator should reject zero duration")
	}
}

func TestFileExistsValidator(t *testing.T) {
	tmpDir := t.TempDir()

	// Create test file
	testFile := "test_output.txt"
	err := os.WriteFile(tmpDir+"/"+testFile, []byte("test"), 0644)
	if err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	validator := FileExistsValidator(tmpDir, testFile)
	result := ExecutionResult{ExitCode: 0, Duration: time.Second}
	if !validator(result) {
		t.Fatal("Validator should find existing file")
	}

	// Non-existent file
	nonExistentValidator := FileExistsValidator(tmpDir, "nonexistent.txt")
	if nonExistentValidator(result) {
		t.Fatal("Validator should not find non-existent file")
	}
}

func TestTaskStartStop(t *testing.T) {
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

func TestResourceMonitor_GetMemoryMB(t *testing.T) {
	m := NewResourceMonitor()
	memMB := m.GetMemoryMB()
	// Just check it doesn't crash; on Linux should return > 0
	if memMB == 0 {
		t.Log("Memory read returned 0 - may be non-Linux environment")
	}
}

func TestResourceMonitor_GetCPUCount(t *testing.T) {
	m := NewResourceMonitor()
	count := m.GetCPUCount()
	if count <= 0 {
		t.Error("CPU count should be >= 1")
	}
}
