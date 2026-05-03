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
	"bytes"
	"encoding/json"
	"fmt"
	"io"
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
	PollInterval:      5 * time.Second,
	HeartbeatInterval: 10 * time.Second,
	MaxConcurrent:     4,
	ReportDir:         "/tmp/computehub-worker",
}

// ── API 类型 ──
type RegisterReq struct {
	NodeID     string  `json:"node_id"`
	GPUType    string  `json:"gpu_type"`
	Region     string  `json:"region"`
	CPUCores   int     `json:"cpu_cores"`
	MemoryGB   float64 `json:"memory_gb"`
	Status     string  `json:"status"`
	IPAddress  string  `json:"ip_address"`
}

type HeartbeatReq struct {
	NodeID        string     `json:"node_id"`
	GPUUtilization float64   `json:"gpu_utilization"`
	GPUTemperature float64   `json:"gpu_temperature"`
	MemoryUsedGB  float64    `json:"memory_used_gb"`
	MemoryTotalGB float64    `json:"memory_total_gb"`
	CPULoad       float64    `json:"cpu_load"`
}

type TaskInfo struct {
	TaskID    string `json:"task_id"`
	Source    string `json:"source"`
	Priority  int    `json:"priority"`
	Status    string `json:"status"`
	Retries   int    `json:"retries"`
	CreatedAt string `json:"created_at"`
}

type TaskListResponse struct {
	Success bool                   `json:"success"`
	Data    map[string][]TaskInfo  `json:"data"`
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

	fmt.Printf("%s ComputeHub Worker Agent v0.1%s\n", green(bold("╔══════════════════════════════════════╗")), reset())
	fmt.Printf("%s  Node:     %s%s%s\n", green(bold("║")), cyan(cfg.NodeID), reset())
	fmt.Printf("%s  Gateway:  %s%s%s\n", green(bold("║")), cyan(cfg.GatewayURL), reset())
	fmt.Printf("%s  GPU:      %s%s%s\n", green(bold("║")), cyan(fmt.Sprintf("%s (%dx)", cfg.GPUType, state.lastGPUStats.Count)), reset())
	fmt.Printf("%s  Region:   %s%s%s\n", green(bold("║")), cyan(cfg.Region), reset())
	fmt.Printf("%s  CPU:      %s%s%s\n", green(bold("║")), cyan(fmt.Sprintf("%d cores", cfg.CPUCores)), reset())
	fmt.Printf("%s  Memory:   %s%s%s\n", green(bold("║")), cyan(fmt.Sprintf("%.0f GB", cfg.MemoryGB)), reset())
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

	// Step 3: Start task poller
	go state.taskPollLoop()

	// Step 4: Graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	fmt.Printf("\n%s ⚠️ 收到终止信号，正在关闭...%s\n", yellow(bold("")), reset())
	state.unregister()
	os.Exit(0)
}

// ── 注册 ──

func (s *WorkerState) register() error {
	ip := getLocalIP()
	req := RegisterReq{
		NodeID:   s.nodeID,
		GPUType:  s.config.GPUType,
		Region:   s.config.Region,
		CPUCores: s.config.CPUCores,
		MemoryGB: s.config.MemoryGB,
		Status:   "online",
		IPAddress: ip,
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

	if !result.Success && result.Error != "" && !strings.Contains(result.Error, "node already registered") {
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
			fmt.Printf("\r %s[心跳] GPU: %s%.1f%%%s  %s%.0f°C%s  Mem: %s%.0f/%.0fGB%s   ",
				dim(""), reset(),
				pctColor(stats.Utilization),
				reset(),
				tempColor(stats.Temperature),
				reset(),
				cyan(fmt.Sprintf("%.0f", stats.MemoryUsedGB)),
				reset(),
				cyan(fmt.Sprintf("%.0f", stats.MemoryTotalGB)),
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

		// Fetch task list
		tasks, err := s.fetchTasks()
		if err != nil {
			time.Sleep(s.config.PollInterval)
			continue
		}

		// Look for pending tasks assigned to us
		for _, task := range tasks {
			if task.Status == "pending" {
				s.mu.Lock()
				_, alreadyRunning := s.runningTasks[task.TaskID]
				s.mu.Unlock()
				if alreadyRunning {
					continue
				}

				fmt.Printf("\n %s📋 发现待处理任务: %s%s\n", yellow(bold("")), cyan(task.TaskID), reset())

				// Fetch full task detail (includes command)
				detail, err := s.fetchTaskDetail(task.TaskID)
				if err != nil {
					fmt.Printf(" %s⚠️ 无法获取任务详情: %v%s\n", yellow(""), err, reset())
					continue
				}

				// Execute in background
				go s.executeTask(detail)
			}
		}

		time.Sleep(s.config.PollInterval)
	}
}

func (s *WorkerState) fetchTasks() ([]TaskInfo, error) {
	resp, err := s.client.Get(s.config.GatewayURL + "/api/v1/tasks/list")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var listResp TaskListResponse
	if err := json.Unmarshal(body, &listResp); err != nil {
		return nil, err
	}

	tasks := listResp.Data[s.nodeID]
	if tasks == nil {
		return nil, nil
	}
	return tasks, nil
}

func (s *WorkerState) fetchTaskDetail(taskID string) (*TaskDetail, error) {
	url := fmt.Sprintf("%s/api/v1/tasks/detail?task_id=%s&node_id=%s",
		s.config.GatewayURL, taskID, s.nodeID)
	resp, err := s.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("connection failed: %w", err)
	}
	defer resp.Body.Close()

	var wrapper struct {
		Success bool        `json:"success"`
		Data    *TaskDetail `json:"data"`
		Error   string      `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&wrapper); err != nil {
		return nil, fmt.Errorf("parse error: %w", err)
	}
	if !wrapper.Success {
		return nil, fmt.Errorf("API error: %s", wrapper.Error)
	}
	return wrapper.Data, nil
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

func (s *WorkerState) collectNvidiaSMI() GPUStats {
	var stats GPUStats

	cmd := exec.Command("nvidia-smi",
		"--query-gpu=index,utilization.gpu,temperature.gpu,memory.used,memory.total",
		"--format=csv,noheader,nounits")
	output, err := cmd.Output()
	if err != nil {
		return stats
	}

	lines := strings.Split(strings.TrimSpace(string(output)), "\n")
	for _, line := range lines {
		parts := strings.Split(line, ",")
		if len(parts) < 5 {
			continue
		}
		stats.Count++

		util, _ := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
		temp, _ := strconv.ParseFloat(strings.TrimSpace(parts[2]), 64)
		memUsed, _ := strconv.ParseFloat(strings.TrimSpace(parts[3]), 64)
		memTotal, _ := strconv.ParseFloat(strings.TrimSpace(parts[4]), 64)

		stats.Utilization += util
		stats.Temperature += temp
		stats.MemoryUsedGB += memUsed / 1024
		stats.MemoryTotalGB += memTotal / 1024
	}

	if stats.Count > 0 {
		stats.Utilization /= float64(stats.Count)
		stats.Temperature /= float64(stats.Count)
	}

	return stats
}

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
		fmt.Printf(" %s⚠️ 任务 %s 没有命令，跳过%s\n", yellow(""), task.TaskID, reset())
		return
	}

	fmt.Printf("\n %s⚡ 执行任务: %s (超时: %ds)%s\n", green(bold("")), cyan(task.TaskID), task.Timeout, reset())
	fmt.Printf("   命令: %s%s%s\n", dim(""), task.Command, reset())

	start := time.Now()

	ctx := s.client
	_ = ctx

	cmd := exec.Command("sh", "-c", task.Command)

	// Set timeout
	if task.Timeout > 0 {
		timer := time.AfterFunc(time.Duration(task.Timeout)*time.Second, func() {
			cmd.Process.Signal(syscall.SIGTERM)
			time.Sleep(3 * time.Second)
			if cmd.Process != nil {
				cmd.Process.Kill()
			}
		})
		defer timer.Stop()
	}

	// Mark as running
	s.mu.Lock()
	s.runningTasks[task.TaskID] = cmd
	s.taskCount++
	s.mu.Unlock()

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	exitCode := 0
	err := cmd.Run()
	duration := time.Since(start)

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

	result := TaskResult{
		TaskID:     task.TaskID,
		Success:    success,
		ExitCode:   exitCode,
		Stdout:     truncateString(stdout.String(), 100*1024),
		Stderr:     truncateString(stderr.String(), 100*1024),
		Duration:   duration.Round(time.Millisecond).String(),
		ExecutedOn: s.nodeID,
		Verified:   true,
	}

	// Submit result
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

	statusIcon := "✅"
	statusColor := green
	if !success {
		statusIcon = "❌"
		statusColor = red
	}

	fmt.Printf(" %s%s 任务 %s 完成 [%s] %s (%s)%s\n",
		statusColor(bold("")), statusIcon, cyan(task.TaskID),
		statusColor(fmt.Sprintf("exit=%d", exitCode)),
		duration.Round(time.Millisecond), reset())

	// Save report
	s.saveTaskReport(task.TaskID, result)
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

func detectMemoryGB() float64 {
	// Try /proc/meminfo
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 32
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "MemTotal:") {
			parts := strings.Fields(line)
			if len(parts) >= 2 {
				kb, _ := strconv.ParseFloat(parts[1], 64)
				return kb / 1024 / 1024
			}
		}
	}
	return 32
}

func detectGPUType() (string, error) {
	cmd := exec.Command("nvidia-smi", "--query-gpu=name", "--format=csv,noheader")
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}
	lines := strings.Split(strings.TrimSpace(string(output)), "\n")
	if len(lines) > 0 {
		return strings.TrimSpace(lines[0]), nil
	}
	return "", fmt.Errorf("no GPU found")
}

func countGPUs() int {
	cmd := exec.Command("nvidia-smi", "-L")
	output, err := cmd.Output()
	if err != nil {
		return 0
	}
	return len(strings.Split(strings.TrimSpace(string(output)), "\n"))
}

func getCPULoad() float64 {
	// Quick load average
	data, err := os.ReadFile("/proc/loadavg")
	if err != nil {
		return 0
	}
	parts := strings.Fields(string(data))
	if len(parts) >= 1 {
		load, _ := strconv.ParseFloat(parts[0], 64)
		return load / float64(runtime.NumCPU()) * 100
	}
	return 0
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
	fmt.Printf(`
%sComputeHub Worker Agent v0.1%s

%s用法:%s
  ./compute-worker [flags]

%s参数:%s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s
  %-28s %s

%s示例:%s
  ./compute-worker --gw http://192.168.1.17:8282 --node-id gpu-01 --gpu-type H100 --region cn-east
  ./compute-worker --node-id worker-2 --interval 3 --concurrent 8
`,
		yellow(bold("")), reset(),
		bold(""), reset(),
		fmt.Sprintf("--gw <url>           %s", dim("Gateway 地址 (默认: http://localhost:8282)")),
		fmt.Sprintf("--node-id <id>       %s", dim("节点 ID (默认: worker-<hostname>)")),
		fmt.Sprintf("--gpu-type <type>    %s", dim("GPU 型号 (默认: 自动检测)")),
		fmt.Sprintf("--region <region>    %s", dim("区域 (默认: cn-east)")),
		fmt.Sprintf("--interval <sec>     %s", dim("任务轮询间隔秒 (默认: 5)")),
		fmt.Sprintf("--heartbeat <sec>    %s", dim("心跳间隔秒 (默认: 10)")),
		fmt.Sprintf("--concurrent <n>     %s", dim("最大并发任务数 (默认: 4)")),
		green(bold("")), reset())
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
