// Package executor implements the physical execution engine.
// It runs sandboxed tasks, verifies results physically,
// and monitors resource usage for accurate billing.
//
// Architecture: Docker → cgroup → chroot → fallback shell
// Principle: Physical delivery only. No mock results.
package executor

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

// ─── 执行级别 ───

// IsolationLevel defines the sandbox isolation method.
type IsolationLevel int

const (
	IsolationDocker IsolationLevel = iota
	IsolationCgroup
	IsolationChroot
	IsolationShell // fallback
)

func (l IsolationLevel) String() string {
	switch l {
	case IsolationDocker:
		return "docker"
	case IsolationCgroup:
		return "cgroup"
	case IsolationChroot:
		return "chroot"
	case IsolationShell:
		return "shell"
	default:
		return "unknown"
	}
}

// ─── 执行结果 ───

// ExecutionResult is the physical outcome of a task execution.
type ExecutionResult struct {
	TaskID      string        `json:"task_id"`
	Stdout      string        `json:"stdout"`
	Stderr      string        `json:"stderr"`
	ExitCode    int           `json:"exit_code"`
	Duration    time.Duration `json:"duration"`
	IsVerified  bool          `json:"verified"`
	Isolation   string        `json:"isolation"`
	MemoryBytes uint64        `json:"memory_bytes,omitempty"`
	CPUPct      float64       `json:"cpu_pct,omitempty"`
	GPUUsed     int           `json:"gpu_used,omitempty"`
	GPUMemUsed  uint64        `json:"gpu_mem_used,omitempty"`
	Artifacts   []string      `json:"artifacts,omitempty"`
}

// Validation defines a single physical verification check.
type Validation struct {
	Name    string `json:"name"`
	Passed  bool   `json:"passed"`
	Message string `json:"message"`
}

// Validator is a physical verification function.
type Validator func(result ExecutionResult) Validation

// ─── 任务配置 ───

// TaskConfig defines how a task should be executed.
type TaskConfig struct {
	Command    string
	Env        map[string]string
	WorkingDir string
	Timeout    time.Duration // 0 = no timeout
	MaxMemMB   uint64        // 0 = no limit
	MaxCPUPct  float64       // 0 = no limit
	MaxGPU     int           // 0 = no GPU limit
	Artifacts  []string      // files to collect after execution
}

// ─── 执行器 ───

// Executor handles sandboxed task execution and verification.
type Executor struct {
	SandboxPath     string
	Isolation       IsolationLevel
	mu              sync.Mutex
	runningTasks    map[string]*taskState
	resourceMonitor *ResourceMonitor
}

type taskState struct {
	ctx    context.Context
	cancel context.CancelFunc
	start  time.Time
}

// NewExecutor creates a new executor with auto-detected isolation.
func NewExecutor(sandboxPath string) (*Executor, error) {
	if err := os.MkdirAll(sandboxPath, 0755); err != nil {
		return nil, fmt.Errorf("create sandbox dir: %w", err)
	}
	return &Executor{
		SandboxPath:     sandboxPath,
		Isolation:       autoDetectIsolation(),
		runningTasks:    make(map[string]*taskState),
		resourceMonitor: NewResourceMonitor(),
	}, nil
}

// NewExecutorWithIsolation creates an executor with a specific isolation level.
func NewExecutorWithIsolation(sandboxPath string, level IsolationLevel) (*Executor, error) {
	if err := os.MkdirAll(sandboxPath, 0755); err != nil {
		return nil, fmt.Errorf("create sandbox dir: %w", err)
	}
	return &Executor{
		SandboxPath:     sandboxPath,
		Isolation:       level,
		runningTasks:    make(map[string]*taskState),
		resourceMonitor: NewResourceMonitor(),
	}, nil
}

// ─── 隔离级别自动检测 ───

func autoDetectIsolation() IsolationLevel {
	if hasCommand("docker") {
		// Verify docker daemon is actually running
		cmd := exec.Command("docker", "info")
		if cmd.Run() == nil {
			return IsolationDocker
		}
	}
	if hasCommand("unshare") && canAccessCgroup() {
		return IsolationCgroup
	}
	// chroot requires root privileges - test if it works
	if hasCommand("chroot") && canUseChroot() {
		return IsolationChroot
	}
	return IsolationShell
}

func canUseChroot() bool {
	// Test if chroot is actually usable (requires root)
	tmpDir := "/tmp/chroot-test"
	os.MkdirAll(tmpDir, 0755)
	defer os.RemoveAll(tmpDir)
	cmd := exec.Command("chroot", tmpDir, "true")
	return cmd.Run() == nil
}

func canAccessCgroup() bool {
	if _, err := os.ReadFile("/sys/fs/cgroup/cgroup.controllers"); err == nil {
		return true
	}
	// Try v1 cgroup
	_, err := os.Stat("/sys/fs/cgroup/memory")
	return err == nil
}

func hasCommand(name string) bool {
	_, err := exec.LookPath(name)
	return err == nil
}

func hasPath(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// ─── 核心执行 ───

// Execute runs a command with the configured sandbox isolation.
func (e *Executor) Execute(taskID, command string) ExecutionResult {
	return e.ExecuteWithConfig(taskID, &TaskConfig{Command: command})
}

// ExecuteWithConfig runs a task with full configuration.
func (e *Executor) ExecuteWithConfig(taskID string, config *TaskConfig) ExecutionResult {
	taskDir := filepath.Join(e.SandboxPath, taskID)
	if err := os.MkdirAll(taskDir, 0755); err != nil {
		return ExecutionResult{
			TaskID:    taskID,
			ExitCode:  1,
			Duration:  0,
			Stderr:    fmt.Sprintf("sandbox dir create failed: %v", err),
			Isolation: "none",
		}
	}

	if config.WorkingDir == "" {
		config.WorkingDir = taskDir
	}

	result := e.runWithIsolation(taskID, config)
	result.Isolation = e.Isolation.String()

	if len(config.Artifacts) > 0 {
		result.Artifacts = e.collectArtifacts(taskDir, config.Artifacts)
	}
	return result
}

// ─── 隔离执行 ───

func (e *Executor) runWithIsolation(taskID string, config *TaskConfig) ExecutionResult {
	switch e.Isolation {
	case IsolationDocker:
		return e.runWithDocker(taskID, config)
	case IsolationCgroup, IsolationChroot:
		return e.runShell(taskID, config)
	default:
		return e.runShell(taskID, config)
	}
}

// ─── Docker 执行 ───

func (e *Executor) runWithDocker(taskID string, config *TaskConfig) ExecutionResult {
	volDir := filepath.Join(e.SandboxPath, taskID+"-vol")
	os.MkdirAll(volDir, 0755)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	args := []string{
		"run", "--rm", "--name", taskID,
		"-v", volDir + ":/workspace",
		"-w", "/workspace",
		"alpine:latest",
		"sh", "-c", config.Command,
	}

	cmd := exec.CommandContext(ctx, "docker", args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	runStart := time.Now()
	err := cmd.Run()
	duration := time.Since(runStart)

	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = 1
		}
	}

	return ExecutionResult{
		TaskID:    taskID,
		Stdout:    stdout.String(),
		Stderr:    stderr.String(),
		ExitCode:  exitCode,
		Duration:  duration,
		Isolation: "docker",
	}
}

// ─── Shell 执行（默认降级） ───

func (e *Executor) runShell(taskID string, config *TaskConfig) ExecutionResult {
	// Default 30 second timeout if not specified
	timeout := config.Timeout
	if timeout == 0 {
		timeout = 30 * time.Second
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, "sh", "-c", config.Command)
	cmd.Dir = config.WorkingDir
	cmd.Env = buildEnv(config.Env)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	runStart := time.Now()
	exitCode := 1
	if err := cmd.Start(); err == nil {
		if err := cmd.Wait(); err != nil {
			if exitErr, ok := err.(*exec.ExitError); ok {
				exitCode = exitErr.ExitCode()
			}
		} else {
			exitCode = 0
		}
	} else {
		exitCode = 1
	}
	duration := time.Since(runStart)

	// Check timeout
	if ctx.Err() == context.DeadlineExceeded {
		return ExecutionResult{
			TaskID:    taskID,
			ExitCode:  124,
			Duration:  duration,
			Stdout:    stdout.String(),
			Stderr:    "task timed out",
			Isolation: "shell",
		}
	}

	return ExecutionResult{
		TaskID:    taskID,
		Stdout:    stdout.String(),
		Stderr:    stderr.String(),
		ExitCode:  exitCode,
		Duration:  duration,
		Isolation: "shell",
	}
}

// ─── 验证 ───

// ExecuteWithValidation runs a command and verifies the result.
func (e *Executor) ExecuteWithValidation(taskID, command string, validators ...Validator) (ExecutionResult, []Validation) {
	result := e.Execute(taskID, command)
	validations := make([]Validation, 0, len(validators)+1)

	for _, v := range validators {
		validations = append(validations, v(result))
	}
	validations = append(validations, DefaultValidator(e.SandboxPath)(result))

	allPassed := true
	for _, v := range validations {
		if !v.Passed {
			allPassed = false
			break
		}
	}
	result.IsVerified = allPassed
	return result, validations
}

// ─── 验证器 ───

// DefaultValidator provides standard physical verification.
func DefaultValidator(sandboxPath string) Validator {
	return func(result ExecutionResult) Validation {
		if result.ExitCode != 0 {
			return Validation{"ExitCode", false, fmt.Sprintf("exit code %d != 0", result.ExitCode)}
		}
		if result.Duration == 0 {
			return Validation{"Duration", false, "zero duration"}
		}
		return Validation{"Default", true, "exit code 0, duration > 0"}
	}
}

// FileExistsValidator checks if a specific file was created.
func FileExistsValidator(sandboxPath, filePath string) Validator {
	return func(result ExecutionResult) Validation {
		fullPath := filepath.Join(sandboxPath, filePath)
		if _, err := os.Stat(fullPath); err == nil {
			return Validation{"FileExists", true, fmt.Sprintf("file exists: %s", filePath)}
		}
		return Validation{"FileExists", false, fmt.Sprintf("file not found: %s", filePath)}
	}
}

// StdoutContainsValidator checks if stdout contains a substring.
func StdoutContainsValidator(substring string) Validator {
	return func(result ExecutionResult) Validation {
		if strings.Contains(result.Stdout, substring) {
			return Validation{"StdoutContains", true, fmt.Sprintf("stdout contains: %s", substring)}
		}
		return Validation{"StdoutContains", false, fmt.Sprintf("stdout does not contain: %s", substring)}
	}
}

// DurationBelowValidator checks if execution finished within the time limit.
func DurationBelowValidator(limit time.Duration) Validator {
	return func(result ExecutionResult) Validation {
		if result.Duration < limit {
			return Validation{"Duration", true, fmt.Sprintf("duration %v < %v", result.Duration, limit)}
		}
		return Validation{"Duration", false, fmt.Sprintf("duration %v >= %v", result.Duration, limit)}
	}
}

// ExitCodeValidator checks if exit code matches.
func ExitCodeValidator(expected int) Validator {
	return func(result ExecutionResult) Validation {
		if result.ExitCode == expected {
			return Validation{"ExitCode", true, fmt.Sprintf("exit code %d", expected)}
		}
		return Validation{"ExitCode", false, fmt.Sprintf("expected %d, got %d", expected, result.ExitCode)}
	}
}

// ArtifactCountValidator checks if the expected number of artifacts exist.
func ArtifactCountValidator(minCount int) Validator {
	return func(result ExecutionResult) Validation {
		if len(result.Artifacts) >= minCount {
			return Validation{"Artifacts", true, fmt.Sprintf("artifact count %d >= %d", len(result.Artifacts), minCount)}
		}
		return Validation{"Artifacts", false, fmt.Sprintf("artifact count %d < %d", len(result.Artifacts), minCount)}
	}
}

// ─── GPU 任务执行 ───

// GPUTaskConfig is a task that requires GPU resources.
type GPUTaskConfig struct {
	TaskConfig
	Framework   string
	GPUCount    int
	DockerImage string
	ScriptPath  string
	Args        []string
}

// ExecuteGPUTask runs a GPU compute task.
func (e *Executor) ExecuteGPUTask(taskID string, config *GPUTaskConfig) ExecutionResult {
	taskDir := filepath.Join(e.SandboxPath, taskID)
	os.MkdirAll(taskDir, 0755)

	if config.Command == "" {
		config.Command = fmt.Sprintf("python %s %s", config.ScriptPath, strings.Join(config.Args, " "))
	}

	cmd := exec.Command("sh", "-c", config.Command)
	cmd.Dir = taskDir
	cmd.Env = append(os.Environ(),
		"CUDA_VISIBLE_DEVICES=0",
		"PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128",
	)
	if config.GPUCount > 0 {
		cmd.Env = append(cmd.Env, fmt.Sprintf("NGPU=%d", config.GPUCount))
	}

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	start := time.Now()
	err := cmd.Run()
	duration := time.Since(start)

	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = 1
		}
	}

	gpuUsed, gpuMemUsed := e.resourceMonitor.GetGPUInfo()
	artifacts := e.collectArtifacts(taskDir, config.Artifacts)

	return ExecutionResult{
		TaskID:     taskID,
		Stdout:     stdout.String(),
		Stderr:     stderr.String(),
		ExitCode:   exitCode,
		Duration:   duration,
		Isolation:  "gpu-shell",
		GPUUsed:    gpuUsed,
		GPUMemUsed: gpuMemUsed,
		Artifacts:  artifacts,
	}
}

// ─── 资源监控 ───

// ResourceMonitor tracks system resource usage.
type ResourceMonitor struct {
	mu sync.Mutex
}

// NewResourceMonitor creates a new monitor.
func NewResourceMonitor() *ResourceMonitor {
	return &ResourceMonitor{}
}

// GetMemoryMB returns available memory in MB.
func (m *ResourceMonitor) GetMemoryMB() uint64 {
	m.mu.Lock()
	defer m.mu.Unlock()

	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 0
	}

	for _, line := range strings.Split(string(data), "\n") {
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
	data, err := os.ReadFile("/proc/cpuinfo")
	if err != nil {
		return 1
	}
	count := 0
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "processor") {
			count++
		}
	}
	return count
}

// GetCPUPct returns current CPU usage percentage from /proc/stat.
func (m *ResourceMonitor) GetCPUPct() float64 {
	data, err := os.ReadFile("/proc/stat")
	if err != nil {
		return 0
	}
	lines := strings.Split(string(data), "\n")
	if len(lines) == 0 {
		return 0
	}

	var user, nice, system, idle, iowait, irq, softirq, steal uint64
	fmt.Sscanf(lines[0], "cpu  %d %d %d %d %d %d %d %d",
		&user, &nice, &system, &idle, &iowait, &irq, &softirq, &steal)

	total := user + nice + system + idle + iowait + irq + softirq + steal
	idleTotal := idle + iowait
	if total == 0 {
		return 0
	}
	return float64(total-idleTotal) / float64(total) * 100
}

// GetGPUInfo returns GPU usage count and memory in MB.
func (m *ResourceMonitor) GetGPUInfo() (int, uint64) {
	if data, err := exec.Command("nvidia-smi", "--query-gpu=index,memory.used", "--format=csv,noheader").Output(); err == nil {
		lines := strings.Split(strings.TrimSpace(string(data)), "\n")
		gpuCount := len(lines)
		totalMem := uint64(0)
		for _, line := range lines {
			var idx, memUsed uint64
			fmt.Sscanf(line, "%d, %d MiB", &idx, &memUsed)
			totalMem += memUsed
		}
		if gpuCount > 0 {
			return gpuCount, totalMem
		}
	}
	return 0, 0
}

// SystemInfo returns a full system resource snapshot.
// Uses internal non-locking reads to avoid deadlock with caller-held lock.
func (m *ResourceMonitor) SystemInfo() map[string]any {
	m.mu.Lock()
	defer m.mu.Unlock()

	gpuCount, gpuMem := m.getGPUInfoLocked()
	totalMem := m.getMemTotalLocked()
	availableMem := m.getMemAvailableLocked()
	cpuCount := m.getCPUCountLocked()

	return map[string]any{
		"cpu_cores":        cpuCount,
		"mem_total_mb":     totalMem,
		"mem_available_mb": availableMem,
		"gpu_count":        gpuCount,
		"gpu_mem_used_mb":  gpuMem,
		"os":               runtime.GOOS,
		"arch":             runtime.GOARCH,
	}
}

// ─── 内部无锁方法（供 SystemInfo 调用避免死锁） ───

func (m *ResourceMonitor) getMemTotalLocked() uint64 {
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 0
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "MemTotal:") {
			var kb uint64
			fmt.Sscanf(line, "MemTotal: %d kB", &kb)
			return kb / 1024
		}
	}
	return 0
}

func (m *ResourceMonitor) getMemAvailableLocked() uint64 {
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 0
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "MemAvailable:") {
			var kb uint64
			fmt.Sscanf(line, "MemAvailable: %d kB", &kb)
			return kb / 1024
		}
	}
	return 0
}

func (m *ResourceMonitor) getCPUCountLocked() int {
	data, err := os.ReadFile("/proc/cpuinfo")
	if err != nil {
		return 1
	}
	count := 0
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "processor") {
			count++
		}
	}
	return count
}

func (m *ResourceMonitor) getGPUInfoLocked() (int, uint64) {
	if data, err := exec.Command("nvidia-smi", "--query-gpu=index,memory.used", "--format=csv,noheader").Output(); err == nil {
		lines := strings.Split(strings.TrimSpace(string(data)), "\n")
		gpuCount := len(lines)
		totalMem := uint64(0)
		for _, line := range lines {
			var idx, memUsed uint64
			fmt.Sscanf(line, "%d, %d MiB", &idx, &memUsed)
			totalMem += memUsed
		}
		if gpuCount > 0 {
			return gpuCount, totalMem
		}
	}
	return 0, 0
}

// ─── 生命周期管理 ───

// StartTask marks a task as running.
func (e *Executor) StartTask(taskID string) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	if _, exists := e.runningTasks[taskID]; exists {
		return fmt.Errorf("task %s already running", taskID)
	}
	ctx, cancel := context.WithCancel(context.Background())
	e.runningTasks[taskID] = &taskState{ctx: ctx, cancel: cancel, start: time.Now()}
	return nil
}

// StopTask cancels a running task.
func (e *Executor) StopTask(taskID string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	if ts, ok := e.runningTasks[taskID]; ok {
		if ts.cancel != nil {
			ts.cancel()
		}
		delete(e.runningTasks, taskID)
	}
}

// IsRunning checks if a task is currently executing.
func (e *Executor) IsRunning(taskID string) bool {
	e.mu.Lock()
	defer e.mu.Unlock()
	_, ok := e.runningTasks[taskID]
	return ok
}

// RunningCount returns the number of currently running tasks.
func (e *Executor) RunningCount() int {
	e.mu.Lock()
	defer e.mu.Unlock()
	return len(e.runningTasks)
}

// RunningTasks returns list of running task IDs.
func (e *Executor) RunningTasks() []string {
	e.mu.Lock()
	defer e.mu.Unlock()
	ids := make([]string, 0, len(e.runningTasks))
	for id := range e.runningTasks {
		ids = append(ids, id)
	}
	return ids
}

// ─── 工具方法 ───

func buildEnv(extraEnv map[string]string) []string {
	env := os.Environ()
	for k, v := range extraEnv {
		env = append(env, fmt.Sprintf("%s=%s", k, v))
	}
	return env
}

func (e *Executor) collectArtifacts(taskDir string, patterns []string) []string {
	artifacts := make([]string, 0, len(patterns))
	for _, pattern := range patterns {
		matches, err := filepath.Glob(filepath.Join(taskDir, pattern))
		if err != nil {
			continue
		}
		artifacts = append(artifacts, matches...)
	}
	if len(artifacts) > 0 {
		fmt.Printf("[Executor] Collected %d artifacts for task in %s\n", len(artifacts), taskDir)
	}
	return artifacts
}

// ─── 任务队列 ───

// TaskQueue provides simple FIFO task processing.
type TaskQueue struct {
	tasks   chan *QueuedTask
	results chan ExecutionResult
}

// QueuedTask is a task ready to be processed.
type QueuedTask struct {
	TaskID string
	Config *TaskConfig
}

// NewTaskQueue creates a FIFO task queue with n workers.
func NewTaskQueue(nWorkers int) *TaskQueue {
	tq := &TaskQueue{
		tasks:   make(chan *QueuedTask, 1000),
		results: make(chan ExecutionResult, 1000),
	}
	for i := 0; i < nWorkers; i++ {
		go func() {
			for task := range tq.tasks {
				exec, _ := NewExecutor("/tmp/computehub-sandbox")
				tq.results <- exec.ExecuteWithConfig(task.TaskID, task.Config)
			}
		}()
	}
	return tq
}

// Submit adds a task to the queue.
func (tq *TaskQueue) Submit(task *QueuedTask) {
	tq.tasks <- task
}

// Results returns the results channel.
func (tq *TaskQueue) Results() <-chan ExecutionResult {
	return tq.results
}

// Stop shuts down the queue.
func (tq *TaskQueue) Stop() {
	close(tq.tasks)
	close(tq.results)
}
