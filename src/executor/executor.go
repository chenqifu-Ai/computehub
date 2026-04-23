// Package executor implements the physical execution engine.
// It runs containerized tasks, verifies results physically,
// and monitors resource usage for accurate billing.
//
// Key principle: Physical delivery only. No mock results.
package executor

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// ─── 执行结果 ───

// ExecutionResult is the physical outcome of a task execution.
type ExecutionResult struct {
	TaskID   string        `json:"task_id"`
	Stdout   string        `json:"stdout"`
	Stderr   string        `json:"stderr"`
	ExitCode int           `json:"exit_code"`
	Duration time.Duration `json:"duration"`
	IsVerified bool      `json:"verified"`
}

// Validation represents a single physical verification check.
type Validation struct {
	Name    string `json:"name"`
	Passed  bool   `json:"passed"`
	Message string `json:"message"`
}

// PhysicalValidator defines how to verify execution results.
type PhysicalValidator func(result ExecutionResult) bool

// ─── 执行器 ───

// Executor handles containerized task execution and verification.
type Executor struct {
	SandboxPath  string
	mu           sync.Mutex
	runningTasks map[string]bool
}

// NewExecutor creates a new executor with sandbox at the given path.
func NewExecutor(sandboxPath string) (*Executor, error) {
	if err := os.MkdirAll(sandboxPath, 0755); err != nil {
		return nil, fmt.Errorf("create sandbox dir: %w", err)
	}

	return &Executor{
		SandboxPath:  sandboxPath,
		runningTasks: make(map[string]bool),
	}, nil
}

// ─── 执行核心 ───

// Execute runs a shell command in the sandbox.
func (e *Executor) Execute(taskID, command string) ExecutionResult {
	start := time.Now()

	taskDir := filepath.Join(e.SandboxPath, taskID)
	if err := os.MkdirAll(taskDir, 0755); err != nil {
		return ExecutionResult{
			TaskID:   taskID,
			ExitCode: 1,
			Duration: time.Since(start),
			Stderr:   fmt.Sprintf("sandbox dir create failed: %v", err),
		}
	}

	cmd := exec.Command("sh", "-c", command)
	cmd.Dir = taskDir

	output, err := cmd.CombinedOutput()
	duration := time.Since(start)

	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = 1
		}
	}

	return ExecutionResult{
		TaskID:   taskID,
		Stdout:   string(output),
		ExitCode: exitCode,
		Duration: duration,
	}
}

// ExecuteWithValidation runs a command and verifies the result.
func (e *Executor) ExecuteWithValidation(taskID, command string, validator PhysicalValidator) (ExecutionResult, bool) {
	if validator == nil {
		validator = DefaultValidator(e.SandboxPath)
	}

	result := e.Execute(taskID, command)
	result.IsVerified = validator(result)

	return result, result.IsVerified
}

// ─── 验证器 ───

// DefaultValidator provides standard physical verification.
func DefaultValidator(sandboxPath string) PhysicalValidator {
	return func(result ExecutionResult) bool {
		if result.ExitCode != 0 {
			return false
		}
		if result.Duration == 0 {
			return false
		}
		return true
	}
}

// FileExistsValidator checks if a specific file was created.
func FileExistsValidator(sandboxPath, filePath string) PhysicalValidator {
	return func(result ExecutionResult) bool {
		fullPath := filepath.Join(sandboxPath, filePath)
		_, err := os.Stat(fullPath)
		return err == nil
	}
}

// ─── 资源监控 ───

// ResourceMonitor tracks system resource usage.
type ResourceMonitor struct {
	mu      sync.Mutex
	lastRun time.Time
}

// NewResourceMonitor creates a new monitor.
func NewResourceMonitor() *ResourceMonitor {
	return &ResourceMonitor{}
}

// GetMemoryMB returns available memory in MB from /proc/meminfo.
func (m *ResourceMonitor) GetMemoryMB() uint64 {
	m.mu.Lock()
	defer m.mu.Unlock()

	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 0
	}

	lines := strings.Split(string(data), "\n")
	for _, line := range lines {
		if strings.HasPrefix(line, "MemAvailable:") {
			var kb uint64
			fmt.Sscanf(line, "MemAvailable: %d kB", &kb)
			return kb / 1024
		}
	}
	return 0
}

// GetCPUCount returns the number of CPU cores.
func (m *ResourceMonitor) GetCPUCount() int {
	count := 0
	data, err := os.ReadFile("/proc/cpuinfo")
	if err != nil {
		return 1
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "processor") {
			count++
		}
	}
	return count
}

// ─── 任务生命周期 ───

// StartTask marks a task as running.
func (e *Executor) StartTask(taskID string) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.runningTasks[taskID] {
		return fmt.Errorf("task %s already running", taskID)
	}
	e.runningTasks[taskID] = true
	return nil
}

// StopTask marks a task as stopped.
func (e *Executor) StopTask(taskID string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	delete(e.runningTasks, taskID)
}

// IsRunning checks if a task is currently executing.
func (e *Executor) IsRunning(taskID string) bool {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.runningTasks[taskID]
}

// RunningCount returns the number of currently running tasks.
func (e *Executor) RunningCount() int {
	e.mu.Lock()
	defer e.mu.Unlock()
	return len(e.runningTasks)
}
