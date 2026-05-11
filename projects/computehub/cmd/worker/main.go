// ComputeHub Worker Agent
// 部署在 GPU 机器上，负责：
//   1. 注册节点到 Gateway
//   2. 定期心跳（GPU 利用率/温度/显存）
//   3. 轮询待执行任务
//   4. 执行命令并回传结果
//
// 用法:
//   ./compute-worker --gw http://gateway:8282 \
//     --node-id gpu-01 \
//     --gpu-type H100 \
//     --region cn-east

package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/computehub/opc/src/version"
)

// ── 配置 ──
type Config struct {
	GatewayURL  string
	NodeID      string
	GPUType     string
	Region      string
	CPUCores    int
	MemoryGB    float64
	PollInterval time.Duration
	HeartbeatInterval time.Duration
	MaxConcurrent int
	ReportDir   string
}

var defaultConfig = Config{
	GatewayURL:        "http://localhost:8282",
	NodeID:            "",
	GPUType:           "",
	Region:            "cn-east",
	CPUCores:          0,
	MemoryGB:          0,
	PollInterval:      500 * time.Millisecond,
	HeartbeatInterval: 10 * time.Second,
	MaxConcurrent:     4,
	ReportDir:         "/tmp/computehub-worker",
}

// ── API 类型 ──
type RegisterReq struct {
	NodeID         string  `json:"node_id"`
	GPUType        string  `json:"gpu_type"`
	Region         string  `json:"region"`
	CPUCores       int     `json:"cpu_cores"`
	MemoryGB       float64 `json:"memory_gb"`
	Status         string  `json:"status"`
	IPAddress      string  `json:"ip_address"`
	MaxConcurrency int     `json:"max_concurrency"`
}

type HeartbeatReq struct {
	NodeID        string     `json:"node_id"`
	GPUUtilization float64   `json:"gpu_utilization"`
	GPUTemperature float64   `json:"gpu_temperature"`
	MemoryUsedGB  float64    `json:"memory_used_gb"`
	MemoryTotalGB float64    `json:"memory_total_gb"`
	CPULoad       float64    `json:"cpu_load"`
}

// PollReq is the request body for the polling endpoint
type PollReq struct {
	NodeID          string `json:"node_id"`
	GPUType         string `json:"gpu_type,omitempty"`
	Region          string `json:"region,omitempty"`
	RunningTaskCount int   `json:"running_task_count,omitempty"`
}

// PollResp is the response from the polling endpoint
type PollResp struct {
	Success bool                   `json:"success"`
	Data    *PollRespData          `json:"data"`
	Error   string                 `json:"error,omitempty"`
}

type PollRespData struct {
	Task    *PolledTask `json:"task"`
	Message string      `json:"message,omitempty"`
}

type PolledTask struct {
	TaskID     string `json:"task_id"`
	Command    string `json:"command"`
	Timeout    int    `json:"timeout"`
	Priority   int    `json:"priority"`
	NodeID     string `json:"node_id,omitempty"`
	SourceType string `json:"source_type,omitempty"`
}

type TaskInfo struct {
	TaskID    string `json:"task_id"`
	Source    string `json:"source"`
	Priority  int    `json:"priority"`
	Status    string `json:"status"`
	Retries   int    `json:"retries"`
	CreatedAt string `json:"created_at"`
}

type TaskSubmit struct {
	TaskID       string `json:"task_id"`
	NodeID       string `json:"node_id"`
	Command      string `json:"command"`
	Timeout      int    `json:"timeout"`
}

type TaskResult struct {
	TaskID     string `json:"task_id"`
	Success    bool   `json:"success"`
	ExitCode   int    `json:"exit_code"`
	Stdout     string `json:"stdout"`
	Stderr     string `json:"stderr"`
	Duration   string `json:"duration"`
	ExecutedOn string `json:"executed_on"`
	Verified   bool   `json:"verified"`
}

// ── 状态 ──
type WorkerState struct {
	mu           sync.Mutex
	nodeID       string
	config       Config
	client       *http.Client
	runningTasks map[string]*exec.Cmd
	taskCount    int64
	lastGPUStats GPUStats
}

type GPUStats struct {
	Utilization  float64
	Temperature  float64
	MemoryUsedGB float64
	MemoryTotalGB float64
	Count        int
}

func main() {
	runWorker()
	// 单次执行，退出后不自动重启
	fmt.Printf("\n %s⚠️ Worker 已退出%s\n", yellow(bold("")), reset())
}

func runWorker() {
	cfg := parseConfig()

	if cfg.NodeID == "" {
		cfg.NodeID = fmt.Sprintf("worker-%s", hostname())
	}
	if cfg.CPUCores == 0 {
		cfg.CPUCores = runtime.NumCPU()
	}
	if cfg.MemoryGB == 0 {
		cfg.MemoryGB = detectMemoryGB()
	}
	if cfg.GPUType == "" {
		// Try to detect GPU type
		if gpuType, _ := detectGPUType(); gpuType != "" {
			cfg.GPUType = gpuType
		} else {
			cfg.GPUType = "CPU"
		}
	}

	state := &WorkerState{
		config:       cfg,
		client:       &http.Client{Timeout: 30 * time.Second},
		runningTasks: make(map[string]*exec.Cmd),
		lastGPUStats: GPUStats{Count: countGPUs()},
	}
	state.nodeID = cfg.NodeID

	fmt.Printf("%s ComputeHub Worker Agent v%s%s\n", green(bold("╔══════════════════════════════════════╗")), version.Short(), reset())
	fmt.Printf("%s  Node:     %s%s", green(bold("║")), cyan(cfg.NodeID), reset())
	fmt.Println()
	fmt.Printf("%s  Gateway:  %s%s", green(bold("║")), cyan(cfg.GatewayURL), reset())
	fmt.Println()
	fmt.Printf("%s  GPU:      %s%s", green(bold("║")), cyan(fmt.Sprintf("%s (%dx)", cfg.GPUType, state.lastGPUStats.Count)), reset())
	fmt.Println()
	fmt.Printf("%s  Region:   %s%s", green(bold("║")), cyan(cfg.Region), reset())
	fmt.Println()
	fmt.Printf("%s  CPU:      %s%s", green(bold("║")), cyan(fmt.Sprintf("%d cores", cfg.CPUCores)), reset())
	fmt.Println()
	fmt.Printf("%s  Memory:   %s%s", green(bold("║")), cyan(fmt.Sprintf("%.0f GB", cfg.MemoryGB)), reset())
	fmt.Println()
	fmt.Printf("%s╚══════════════════════════════════════╝%s\n", green(bold("")), reset())

	// Step 1: Register
	if err := state.register(); err != nil {
		fmt.Printf("%s ❌ 注册失败: %v%s\n", red(bold("")), err, reset())
		fmt.Printf("  %s重试中...%s\n", yellow(""), reset())
		go func() {
			for {
				time.Sleep(10 * time.Second)
				if err := state.register(); err == nil {
					break
				}
			}
		}()
	}

	// Step 2: Start heartbeat loop
	go state.heartbeatLoop()

	// Step 3: Start auto-upgrade loop (checks every 5 min)
	go state.upgradeLoop()

	// Step 4: Start task poller
	go state.taskPollLoop()

	// Step 4: Graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	fmt.Printf("\n%s ⚠️ 收到终止信号，正在关闭...%s\n", yellow(bold("")), reset())
	state.unregister()
	// Use return instead of os.Exit(0) so the auto-restart loop can continue
	return
}

// ── 注册 ──

func (s *WorkerState) register() error {
	ip := getLocalIP()
	req := RegisterReq{
		NodeID:         s.nodeID,
		GPUType:        s.config.GPUType,
		Region:         s.config.Region,
		CPUCores:       s.config.CPUCores,
		MemoryGB:       s.config.MemoryGB,
		Status:         "online",
		IPAddress:      ip,
		MaxConcurrency: s.config.MaxConcurrent,
	}

	body, _ := json.Marshal(req)
	resp, err := s.client.Post(
		s.config.GatewayURL+"/api/v1/nodes/register",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		return fmt.Errorf("无法连接 gateway: %w", err)
	}
	defer resp.Body.Close()

	var result struct {
		Success bool   `json:"success"`
		Error   string `json:"error"`
	}
	json.NewDecoder(resp.Body).Decode(&result)

	if !result.Success && result.Error != "" && !strings.Contains(result.Error, "already registered") {
		return fmt.Errorf("注册被拒: %s", result.Error)
	}

	fmt.Printf("\n %s✅ 节点已注册: %s (%s | %s | %dc/%dGB)%s\n",
		green(bold("")), cyan(s.nodeID), cyan(s.config.GPUType), cyan(s.config.Region),
		s.config.CPUCores, int(s.config.MemoryGB), reset())
	return nil
}

func (s *WorkerState) unregister() {
	body, _ := json.Marshal(map[string]string{"node_id": s.nodeID})
	resp, err := s.client.Post(
		s.config.GatewayURL+"/api/v1/nodes/unregister",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		fmt.Printf(" %s注销失败: %v%s\n", red(""), err, reset())
		return
	}
	resp.Body.Close()
	fmt.Printf(" %s✅ 节点已注销%s\n", green(""), reset())
}

// ── 心跳 ──

func (s *WorkerState) heartbeatLoop() {
	for {
		stats := s.collectGPUStats()
		s.mu.Lock()
		s.lastGPUStats = stats
		s.mu.Unlock()

		body, _ := json.Marshal(HeartbeatReq{
			NodeID:         s.nodeID,
			GPUUtilization: stats.Utilization,
			GPUTemperature: stats.Temperature,
			MemoryUsedGB:   stats.MemoryUsedGB,
			MemoryTotalGB:  stats.MemoryTotalGB,
			CPULoad:        getCPULoad(),
		})

		resp, err := s.client.Post(
			s.config.GatewayURL+"/api/v1/nodes/heartbeat",
			"application/json",
			bytes.NewBuffer(body),
		)
		if err != nil || resp.StatusCode != 200 {
			fmt.Printf(" %s心跳失败: %v%s\n", red(""), err, reset())
		} else {
			resp.Body.Close()
		}

		// Log GPU status
		if stats.Count > 0 {
			fmt.Printf("\r %s[心跳] GPU: %s%%  %s°C  Mem: %s%s%s   ",
				dim(""),
				pctColor(stats.Utilization),
				tempColor(stats.Temperature),
				cyan(fmt.Sprintf("%.0f", stats.MemoryUsedGB)),
				cyan(fmt.Sprintf("/%.0fGB", stats.MemoryTotalGB)),
				reset(),
			)
		}

		time.Sleep(s.config.HeartbeatInterval)
	}
}

// ── 任务轮询 ──

func (s *WorkerState) taskPollLoop() {
	for {
		// Count running tasks
		s.mu.Lock()
		runningCount := len(s.runningTasks)
		s.mu.Unlock()

		if runningCount >= s.config.MaxConcurrent {
			time.Sleep(s.config.PollInterval)
			continue
		}

		// Poll Gateway for a pending task
		task, err := s.pollTask()
		if err != nil {
			fmt.Printf(" %s⚠️ poll 失败: %v%s\n", yellow(""), err, reset())
			time.Sleep(s.config.PollInterval)
			continue
		}

		if task == nil {
			// No pending tasks, sleep and retry
			time.Sleep(s.config.PollInterval)
			continue
		}

		fmt.Printf("\n %s📋 认领到任务: %s%s\n", yellow(bold("")), cyan(task.TaskID), reset())
		fmt.Printf("   命令: %s%s%s\n", dim(""), task.Command, reset())

		// Execute in background
		go s.executeTask(&TaskDetail{
			TaskID:     task.TaskID,
			Command:    task.Command,
			NodeID:     task.NodeID,
			Timeout:    task.Timeout,
			Priority:   task.Priority,
			SourceType: task.SourceType,
		})

		time.Sleep(s.config.PollInterval)
	}
}

// pollTask 轮询 Gateway 获取待处理任务
func (s *WorkerState) pollTask() (*PolledTask, error) {
	req := PollReq{
		NodeID:          s.nodeID,
		GPUType:         s.config.GPUType,
		Region:          s.config.Region,
		RunningTaskCount: len(s.runningTasks),
	}

	body, _ := json.Marshal(req)
	resp, err := s.client.Post(
		s.config.GatewayURL+"/api/v1/tasks/poll",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		return nil, fmt.Errorf("连接失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	var wrapper struct {
		Success bool          `json:"success"`
		Data    *PollRespData `json:"data"`
		Error   string        `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&wrapper); err != nil {
		return nil, fmt.Errorf("JSON 解析失败: %w", err)
	}
	if !wrapper.Success {
		return nil, fmt.Errorf("API 错误: %s", wrapper.Error)
	}
	if wrapper.Data == nil || wrapper.Data.Task == nil {
		return nil, nil // 没有待处理任务
	}
	return wrapper.Data.Task, nil
}

// ── GPU 采集 ──

func (s *WorkerState) collectGPUStats() GPUStats {
	stats := s.collectNvidiaSMI()
	if stats.Count > 0 {
		return stats
	}

	// Fallback: try collecting via other methods
	stats.Count = countGPUs()
	if stats.Count > 0 {
		stats.MemoryTotalGB = float64(stats.Count) * 80 // rough estimate for H100
	}
	return stats
}

// collectNvidiaSMI is implemented in worker_util_linux.go / worker_util_windows.go

// ── 任务执行 ──

type TaskDetail struct {
	TaskID       string `json:"task_id"`
	Command      string `json:"command"`
	NodeID       string `json:"node_id"`
	Timeout      int    `json:"timeout"`
	Priority     int    `json:"priority"`
	SourceType   string `json:"source_type"`
	Status       string `json:"status"`
}

func (s *WorkerState) executeTask(task *TaskDetail) {
	if task.Command == "" {
		fmt.Printf(" %s⚠️ 任务 %s 没有命令，回传错误结果%s\n", yellow(""), task.TaskID, reset())
		s.submitTaskError(task.TaskID, "empty command")
		return
	}

	fmt.Printf("\n %s⚡ 执行任务: %s (超时: %ds)%s\n", green(bold("")), cyan(task.TaskID), task.Timeout, reset())
	fmt.Printf("   命令: %s%s%s\n", dim(""), task.Command, reset())

	start := time.Now()

	cmd := runCommand(task.Command)

	// Get stdout pipe for streaming
	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		fmt.Printf(" %s❌ stdout pipe 创建失败: %v%s\n", red(bold("")), err, reset())
		s.submitTaskError(task.TaskID, err.Error())
		return
	}
	stderrPipe, err := cmd.StderrPipe()
	if err != nil {
		fmt.Printf(" %s❌ stderr pipe 创建失败: %v%s\n", red(bold("")), err, reset())
		s.submitTaskError(task.TaskID, err.Error())
		return
	}

	// Set timeout
	if task.Timeout > 0 {
		timer := time.AfterFunc(time.Duration(task.Timeout)*time.Second, func() {
			if cmd.Process != nil {
				killProcess(cmd.Process)
				time.Sleep(3 * time.Second)
				if cmd.Process != nil {
					cmd.Process.Kill()
				}
			}
		})
		defer timer.Stop()
	}

	// Mark as running
	s.mu.Lock()
	s.runningTasks[task.TaskID] = cmd
	s.taskCount++
	s.mu.Unlock()

	// Start the command
	if err := cmd.Start(); err != nil {
		fmt.Printf(" %s❌ 启动命令失败: %v%s\n", red(bold("")), err, reset())
		s.mu.Lock()
		delete(s.runningTasks, task.TaskID)
		s.mu.Unlock()
		s.submitTaskError(task.TaskID, err.Error())
		return
	}

	// Read stdout and stderr asynchronously with streaming
	var stdoutBuf, stderrBuf bytes.Buffer
	var stdoutDone, stderrDone bool
	var mu sync.Mutex

	// Streaming ticker — pushes incremental output every 500ms
	streamTicker := time.NewTicker(500 * time.Millisecond)
	stopStream := make(chan struct{})

	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		for scanner.Scan() {
			line := scanner.Text() + "\n"
			mu.Lock()
			stdoutBuf.WriteString(line)
			mu.Unlock()
		}
		mu.Lock()
		stdoutDone = true
		mu.Unlock()
	}()

	go func() {
		scanner := bufio.NewScanner(stderrPipe)
		for scanner.Scan() {
			line := scanner.Text() + "\n"
			mu.Lock()
			stderrBuf.WriteString(line)
			mu.Unlock()
		}
		mu.Lock()
		stderrDone = true
		mu.Unlock()
	}()

	// Background streaming to Gateway
	go func() {
		var lastStdout, lastStderr int
		for {
			select {
			case <-streamTicker.C:
				mu.Lock()
				currentStdout := stdoutBuf.String()
				currentStderr := stderrBuf.String()
				mu.Unlock()

				// Compute increment
				newStdout := ""
				if len(currentStdout) > lastStdout {
					newStdout = currentStdout[lastStdout:]
				}
				newStderr := ""
				if len(currentStderr) > lastStderr {
					newStderr = currentStderr[lastStderr:]
				}

				if newStdout != "" || newStderr != "" {
					s.sendStreamProgress(task.TaskID, newStdout, newStderr)
					lastStdout = len(currentStdout)
					lastStderr = len(currentStderr)
				}

				if stdoutDone && stderrDone {
					// Send remaining buffer
					remainingStdout := ""
					if len(currentStdout) > lastStdout {
						remainingStdout = currentStdout[lastStdout:]
					}
					remainingStderr := ""
					if len(currentStderr) > lastStderr {
						remainingStderr = currentStderr[lastStderr:]
					}
					if remainingStdout != "" || remainingStderr != "" {
						s.sendStreamProgress(task.TaskID, remainingStdout, remainingStderr)
					}
					close(stopStream)
					return
				}
			case <-stopStream:
				streamTicker.Stop()
				return
			}
		}
	}()

	// Wait for command completion
	err = cmd.Wait()
	duration := time.Since(start)

	// Wait for streaming goroutine to finish
	select {
	case <-stopStream:
	case <-time.After(2 * time.Second):
	}

	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = -1
		}
	}

	// Clean up
	s.mu.Lock()
	delete(s.runningTasks, task.TaskID)
	s.mu.Unlock()

	success := exitCode == 0

	mu.Lock()
	finalStdout := stdoutBuf.String()
	finalStderr := stderrBuf.String()
	mu.Unlock()

	result := TaskResult{
		TaskID:     task.TaskID,
		Success:    success,
		ExitCode:   exitCode,
		Stdout:     truncateString(finalStdout, 100*1024),
		Stderr:     truncateString(finalStderr, 100*1024),
		Duration:   duration.Round(time.Millisecond).String(),
		ExecutedOn: s.nodeID,
		Verified:   true,
	}

	// Submit result
	s.submitTaskResult(result)

	statusIcon := "✅"
	statusColor := green
	if !success {
		statusIcon = "❌"
		statusColor = red
	}

	fmt.Printf(" %s%s 任务 %s 完成 [%s] %s (%s)%s\n",
		statusColor(bold("")), statusIcon, cyan(task.TaskID),
		statusColor(fmt.Sprintf("exit=%d", exitCode)),
		duration.Round(time.Millisecond), reset(), reset())

	// Save report
	s.saveTaskReport(task.TaskID, result)
}

// sendStreamProgress sends incremental output to Gateway
func (s *WorkerState) sendStreamProgress(taskID, stdout, stderr string) {
	body, _ := json.Marshal(map[string]string{
		"task_id": taskID,
		"node_id": s.nodeID,
		"stdout":  stdout,
		"stderr":  stderr,
	})
	resp, err := s.client.Post(
		s.config.GatewayURL+"/api/v1/tasks/progress",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		// Silently ignore stream errors — don't disrupt execution
		return
	}
	resp.Body.Close()
}

// submitTaskError submits a task error result
func (s *WorkerState) submitTaskError(taskID, errMsg string) {
	result := TaskResult{
		TaskID:     taskID,
		Success:    false,
		ExitCode:   -1,
		Stderr:     errMsg,
		Duration:   "0s",
		ExecutedOn: s.nodeID,
		Verified:   false,
	}
	s.submitTaskResult(result)
}

// submitTaskResult submits the final task result to Gateway
func (s *WorkerState) submitTaskResult(result TaskResult) {
	body, _ := json.Marshal(result)
	resp, err := s.client.Post(
		s.config.GatewayURL+"/api/v1/tasks/result",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		fmt.Printf(" %s❌ 结果回传失败: %v%s\n", red(bold("")), err, reset())
		return
	}
	resp.Body.Close()
}

func (s *WorkerState) saveTaskReport(taskID string, result TaskResult) {
	os.MkdirAll(s.config.ReportDir, 0755)
	report := struct {
		TaskID   string    `json:"task_id"`
		NodeID   string    `json:"node_id"`
		Result   TaskResult `json:"result"`
		FinishedAt time.Time `json:"finished_at"`
	}{
		TaskID:   taskID,
		NodeID:   s.nodeID,
		Result:   result,
		FinishedAt: time.Now(),
	}
	data, _ := json.MarshalIndent(report, "", "  ")
	filename := fmt.Sprintf("%s/task-%s-%d.json", s.config.ReportDir, taskID, time.Now().Unix())
	os.WriteFile(filename, data, 0644)
}

// ═══════════════════════════════════════════
// ── 工具函数 ──
// ═══════════════════════════════════════════

func hostname() string {
	h, err := os.Hostname()
	if err != nil {
		return "unknown"
	}
	return h
}

func getLocalIP() string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return "0.0.0.0"
	}
	for _, addr := range addrs {
		if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
			return ipnet.IP.String()
		}
	}
	return "0.0.0.0"
	// We need net - add it
}

func truncateString(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max] + "\n... [truncated]"
}

// ── CLI 参数 ──

func parseConfig() Config {
	cfg := defaultConfig
	args := os.Args[1:]

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--gw", "--gateway":
			if i+1 < len(args) {
				cfg.GatewayURL = args[i+1]
				i++
			}
		case "--node-id", "--id":
			if i+1 < len(args) {
				cfg.NodeID = args[i+1]
				i++
			}
		case "--gpu-type", "--gpu":
			if i+1 < len(args) {
				cfg.GPUType = args[i+1]
				i++
			}
		case "--region":
			if i+1 < len(args) {
				cfg.Region = args[i+1]
				i++
			}
		case "--interval", "--poll":
			if i+1 < len(args) {
				d, _ := time.ParseDuration(args[i+1] + "s")
				if d > 0 {
					cfg.PollInterval = d
				}
				i++
			}
		case "--heartbeat":
			if i+1 < len(args) {
				d, _ := time.ParseDuration(args[i+1] + "s")
				if d > 0 {
					cfg.HeartbeatInterval = d
				}
				i++
			}
		case "--concurrent":
			if i+1 < len(args) {
				n, _ := strconv.Atoi(args[i+1])
				if n > 0 {
					cfg.MaxConcurrent = n
				}
				i++
			}
		case "--help", "-h":
			printWorkerHelp()
			os.Exit(0)
		}
	}
	return cfg
}

func printWorkerHelp() {
	fmt.Println("")
	fmt.Println(yellow(bold("")), "ComputeHub Worker Agent v"+version.Short(), reset())
	fmt.Println("")
	fmt.Println(bold(""), "用法:", reset())
	fmt.Println("  ./compute-worker --flags [options]")
	fmt.Println("")
	fmt.Println(bold(""), "参数:", reset())
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--gw <url>"), dim("Gateway 地址 (默认: http://localhost:8282)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--node-id <id>"), dim("节点 ID (默认: worker-<hostname>)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--gpu-type <type>"), dim("GPU 型号 (默认: 自动检测)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--region <region>"), dim("区域 (默认: cn-east)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--interval <sec>"), dim("任务轮询间隔秒 (默认: 5)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--heartbeat <sec>"), dim("心跳间隔秒 (默认: 10)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--concurrent <n>"), dim("最大并发任务数 (默认: 4)")))
	fmt.Println("")
	fmt.Println(green(bold("")), "示例:", reset())
	fmt.Println("  ./compute-worker --gw http://192.168.1.17:8282 --node-id gpu-01 --gpu-type H100 --region cn-east")
	fmt.Println("  ./compute-worker --node-id worker-2 --interval 3 --concurrent 8")
}

// ── ANSI 颜色 ──

func reset() string   { return "\033[0m" }
func bold(s string) string  { return "\033[1m" + s }
func dim(s string) string   { return "\033[2m" + s }
func red(s string) string   { return "\033[31m" + s }
func green(s string) string { return "\033[32m" + s }
func yellow(s string) string { return "\033[33m" + s }
func cyan(s string) string  { return "\033[36m" + s }

func pctColor(v float64) string {
	if v > 90 { return fmt.Sprintf("\033[31m\033[1m%.1f%%\033[0m", v) }
	if v > 70 { return fmt.Sprintf("\033[33m%.1f%%\033[0m", v) }
	return fmt.Sprintf("\033[32m%.1f%%\033[0m", v)
}

func tempColor(t float64) string {
	if t > 85 { return fmt.Sprintf("\033[31m\033[1m%.0f°C\033[0m", t) }
	if t > 70 { return fmt.Sprintf("\033[33m%.0f°C\033[0m", t) }
	return fmt.Sprintf("\033[32m%.0f°C\033[0m", t)
}
