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

package workercmd

import (
	"bufio"
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"

	"github.com/computehub/opc/src/agent"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/computehub/opc/src/version"
)

// ═══════════════════════════════════════════
// Worker Agent — 本地 AI 大脑
// ═══════════════════════════════════════════
var workerAgentServer *WorkerAgentServer

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
	IPOverride  string
	ReportDir   string
	ConfirmConnect bool // --confirm-connect: register+heartbeat only, no agent/poller
	NoUpgrade      bool // --no-upgrade: 禁用自动升级循环
	// LLM 配置（从 config.json → composer 读取）
	ComposerAPIURL string `json:"api_url"`
	ComposerAPIKey string `json:"api_key"`
	ComposerModel  string `json:"model"`
	// OpenClaw 管理配置
	OpenClawPort   int    `json:"openclaw_port"`   // OpenClaw Gateway 端口（默认 18789）
	OpenClawRemote string `json:"openclaw_remote"` // 远程 Gateway URL（配对用）
	OpenClawToken  string `json:"openclaw_token"`  // 配对 token
}

var defaultConfig = Config{
	GatewayURL:        "http://localhost:8282",
	NodeID:            "",
	GPUType:           "",
	Region:            "cn-east",
	CPUCores:          0,
	MemoryGB:          0,
	PollInterval:      10 * time.Second,
	HeartbeatInterval: 25 * time.Second,
	MaxConcurrent:     16,
	ReportDir:         "/tmp/computehub-worker",
}

// ── API 类型 ──
type RegisterReq struct {
	NodeID         string  `json:"node_id"`
	NodeType       string  `json:"node_type"`     // "gpu" | "cpu" | "mixed"
	Platform       string  `json:"platform"`      // "linux/amd64" | "windows/amd64" | "linux/arm64" | "darwin/arm64"
	GPUType        string  `json:"gpu_type"`
	Region         string  `json:"region"`
	CPUCores       int     `json:"cpu_cores"`
	MemoryGB       float64 `json:"memory_gb"`
	Status         string  `json:"status"`
	IPAddress      string  `json:"ip_address"`
	MaxConcurrency int     `json:"max_concurrency"`
	Version        string  `json:"version"`
}

// detectNodeType determines node_type from GPU/CPU info.
func detectNodeType(gpuType string, cpuCores int) string {
	if gpuType != "" && gpuType != "CPU" {
		return "gpu"
	}
	if cpuCores > 0 {
		return "cpu"
	}
	return "mixed"
}

type HeartbeatReq struct {
	NodeID        string     `json:"node_id"`
	GPUUtilization float64   `json:"gpu_utilization"`
	GPUTemperature float64   `json:"gpu_temperature"`
	MemoryUsedGB  float64    `json:"memory_used_gb"`
	MemoryTotalGB float64    `json:"memory_total_gb"`
	CPULoad       float64    `json:"cpu_load"`
	Version       string     `json:"version,omitempty"`
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
	um           *UpgradeManager // intelligent upgrade manager (Phase 1+)

	// WS 感知：WS 在线时轮询降频
	isWSConnected int32 // atomic: 1=online, 0=offline
}

type GPUStats struct {
	Utilization  float64
	Temperature  float64
	MemoryUsedGB float64
	MemoryTotalGB float64
	Count        int
}

func Run(args []string) {
	// Check for --test-register first (upgrade executor mode)
	testRegister := false
	for _, a := range args {
		if a == "--test-register" {
			testRegister = true
			break
		}
	}
	if testRegister {
		exitCode := RunTestRegister(args)
		os.Exit(exitCode)
	}

	// Check for --confirm-connect (light mode: connect test only)
	confirmConnect := false
	for _, a := range args {
		if a == "--confirm-connect" {
			confirmConnect = true
			break
		}
	}
	if confirmConnect {
		exitCode := RunConfirmConnect(args)
		os.Exit(exitCode)
	}

	runWorker(args)
	fmt.Printf("\n %s⚠️ Worker 已退出%s\n", yellow(bold("")), reset())
}

// ── 连接确认 ──

// RunConfirmConnect 注册节点到 Gateway 并发送一次心跳，验证连通性后立即退出。
// 升级脚本在替换 binary 前调用此模式测试新版本能否连上 Gateway。
// 用法: 和 worker 使用完全相同的参数，仅加 --confirm-connect
//
// 返回: 0 = 连接正常, 1 = 连接失败
func RunConfirmConnect(args []string) int {
	cfg, ok := parseConfigWithArgs(args)
	if !ok {
		return 1
	}

	if cfg.NodeID == "" {
		cfg.NodeID = sanitizeNodeID(hostname())
	}
	if cfg.CPUCores == 0 {
		cfg.CPUCores = runtime.NumCPU()
	}
	if cfg.MemoryGB == 0 {
		cfg.MemoryGB = detectMemoryGB()
	}
	if cfg.GPUType == "" {
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
	}
	state.nodeID = cfg.NodeID

	fmt.Printf("%s %s🔌 连接确认: %s → %s%s\n",
		tscolor(), green(bold("")), cyan(cfg.NodeID), cyan(cfg.GatewayURL), reset())

	// Step 1: Register
	if err := state.register(); err != nil {
		fmt.Printf("%s %s❌ 注册失败: %v%s\n", tscolor(), red(bold("")), err, reset())
		return 1
	}

	// Step 2: Send one heartbeat to verify ongoing connectivity
	fmt.Printf("%s %s💓 发送心跳...%s", tscolor(), dim(""), reset())
	stats := state.collectGPUStats()
	state.mu.Lock()
	state.lastGPUStats = stats
	state.mu.Unlock()

	body, _ := json.Marshal(HeartbeatReq{
		NodeID:         state.nodeID,
		GPUUtilization: stats.Utilization,
		GPUTemperature: stats.Temperature,
		MemoryUsedGB:   stats.MemoryUsedGB,
		MemoryTotalGB:  stats.MemoryTotalGB,
		CPULoad:        getCPULoad(),
	})

	resp, err := state.client.Post(
		cfg.GatewayURL+"/api/v1/nodes/heartbeat",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		fmt.Printf("\n%s %s❌ 心跳失败: %v%s\n", tscolor(), red(bold("")), err, reset())
		return 1
	}
	resp.Body.Close()
	fmt.Printf(" %s✅%s\n", green(""), reset())

	// Step 3: Unregister to clean up (confirmation mode)
	state.unregister()

	fmt.Printf("%s %s✅ 连接确认成功: %s → %s%s\n",
		tscolor(), green(bold("")), cyan(cfg.NodeID), cyan(cfg.GatewayURL), reset())
	return 0
}

func runWorker(args []string) {
	cfg, ok := parseConfigWithArgs(args)
	if !ok {
		return
	}

	if cfg.NodeID == "" {
		cfg.NodeID = sanitizeNodeID(hostname())
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

	fmt.Printf("%s %s ComputeHub Worker Agent v%s%s\n", tscolor(), green(bold("╔══════════════════════════════════════╗")), version.Short(), reset())
	fmt.Printf("%s %s  Node:     %s%s", tscolor(), green(bold("║")), cyan(cfg.NodeID), reset())
	fmt.Println()
	fmt.Printf("%s %s  Gateway:  %s%s", tscolor(), green(bold("║")), cyan(cfg.GatewayURL), reset())
	fmt.Println()
	fmt.Printf("%s %s  GPU:      %s%s", tscolor(), green(bold("║")), cyan(fmt.Sprintf("%s (%dx)", cfg.GPUType, state.lastGPUStats.Count)), reset())
	fmt.Println()
	fmt.Printf("%s %s  Region:   %s%s", tscolor(), green(bold("║")), cyan(cfg.Region), reset())
	fmt.Println()
	fmt.Printf("%s %s  CPU:      %s%s", tscolor(), green(bold("║")), cyan(fmt.Sprintf("%d cores", cfg.CPUCores)), reset())
	fmt.Println()
	fmt.Printf("%s %s  Memory:   %s%s", tscolor(), green(bold("║")), cyan(fmt.Sprintf("%.0f GB", cfg.MemoryGB)), reset())
	fmt.Println()
	fmt.Printf("%s %s╚══════════════════════════════════════╝%s\n", tscolor(), green(bold("")), reset())

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

	// Step 3: Create UpgradeManager (intelligent upgrade, Phase 1+)
	state.um = NewUpgradeManager(state)

	// Step 3b: Start upgrade main loop — uses UpgradeManager with intelligent decisions
	// 默认启用自动升级；--no-upgrade 标志用于开发/测试模式避免 auto-upgrade 杀死进程
	if !cfg.NoUpgrade {
		go state.upgradeLoop()
	}

	// Step 4: Start task poller
	go state.taskPollLoop()

	// Step 5: Start Worker Agent (Phase 1: local AI brain)
	agentPort := 8383
	// Allow override via WORKER_AGENT_PORT env
	if p := os.Getenv("WORKER_AGENT_PORT"); p != "" {
		if port, err := strconv.Atoi(p); err == nil && port > 0 {
			agentPort = port
		}
	}
	workerAgentServer = startWorkerAgent(state, state.um, agentPort)

	// Step 6: Graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	fmt.Printf("\n%s ⚠️ 收到终止信号，正在关闭...%s\n", yellow(bold("")), reset())
	if workerAgentServer != nil {
		workerAgentServer.Stop()
	}
	state.unregister()
	// Use return instead of os.Exit(0) so the auto-restart loop can continue
	return
}

// ── 注册 ──

func (s *WorkerState) register() error {
	ip := s.config.IPOverride
	if ip == "" {
		ip = getLocalIP()
	}
	req := RegisterReq{
		NodeID:         s.nodeID,
		NodeType:       detectNodeType(s.config.GPUType, s.config.CPUCores),
		Platform:       runtime.GOOS + "/" + runtime.GOARCH,
		GPUType:        s.config.GPUType,
		Region:         s.config.Region,
		CPUCores:       s.config.CPUCores,
		MemoryGB:       s.config.MemoryGB,
		Status:         "online",
		IPAddress:      ip,
		MaxConcurrency: s.config.MaxConcurrent,
		Version:        version.Short(),
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

	fmt.Printf("\n%s %s✅ 节点已注册: %s (%s | %s | %dc/%dGB)%s\n",
		tscolor(), green(bold("")), cyan(s.nodeID), cyan(s.config.GPUType), cyan(s.config.Region),
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
			Version:        version.Short(),
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
	// WS 感知动态间隔：
	//   WS 在线 (isWSConnected=1) → 60s 兜底，任务走 WS 推送
	//   WS 断线 (isWSConnected=0) → 10s 主动轮询
	//   出错退避 → 上限 10s
	baseInterval := s.config.PollInterval // 默认 10s
	wsFallback := 60 * time.Second
	pollInterval := baseInterval
	maxBackoff := 10 * time.Second

	for {
		// Count running tasks
		s.mu.Lock()
		runningCount := len(s.runningTasks)
		s.mu.Unlock()

		if runningCount >= s.config.MaxConcurrent {
			time.Sleep(pollInterval)
			continue
		}

		// WS 在线 → 用 60s 长间隔兜底（任务已被 WS 实时推送）
		// WS 断线 → 用配置的 10s 主动轮询
		if atomic.LoadInt32(&s.isWSConnected) == 1 {
			pollInterval = wsFallback
		} else {
			pollInterval = baseInterval
		}

		// Poll Gateway for a pending task
		task, err := s.pollTask()
		if err != nil {
			fmt.Printf("%s %s⚠️ poll 失败: %v%s\n", tscolor(), yellow(""), err, reset())
			// 退避：每次失败翻倍，上限 10s
			pollInterval *= 2
			if pollInterval > maxBackoff {
				pollInterval = maxBackoff
			}
			time.Sleep(pollInterval)
			continue
		}

		if task == nil {
			// No pending tasks, sleep and retry
			time.Sleep(pollInterval)
			continue
		}

		fmt.Printf("\n%s %s📋 认领到任务: %s%s\n", tscolor(), yellow(bold("")), cyan(task.TaskID), reset())
		fmt.Printf("%s   命令: %s%s%s\n", tscolor(), dim(""), task.Command, reset())

		// Execute in background
		go s.executeTask(&TaskDetail{
			TaskID:     task.TaskID,
			Command:    task.Command,
			NodeID:     task.NodeID,
			Timeout:    task.Timeout,
			Priority:   task.Priority,
			SourceType: task.SourceType,
		})

		// 认领成功 → 恢复默认
		time.Sleep(pollInterval)
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
		fmt.Printf(" %s⚠️ 任务 %s 没有命令，回传错误结果%s\n", tscolor(), yellow(task.TaskID), reset())
		s.submitTaskError(task.TaskID, "empty command")
		return
	}

	fmt.Printf("\n%s %s⚡ 执行任务: %s (超时: %ds)%s\n", tscolor(), green(bold("")), cyan(task.TaskID), task.Timeout, reset())
	fmt.Printf("%s   命令: %s%s%s\n", tscolor(), dim(""), task.Command, reset())

	// ── 安全检查：拦截 SSH 自连接攻击 ──
	if err := agent.DetectSSHSelfAttack(task.Command); err != nil {
		fmt.Printf(" %s❌ 安全拦截: %v%s\n", red(bold("")), err, reset())
		s.submitTaskError(task.TaskID, fmt.Sprintf("❌ 安全拦截: %v", err))
		return
	}

	// ── ARC-AI-NET-001 自动消费 ──
	// 如果命令是 Base64 编码的 AI 间协议消息，自动写入队列并通知
	if decodedMsg, isAiMsg := decodeAIMessage(task.Command); isAiMsg {
		fmt.Printf(" %s🤖 AI消息自动消费: %s → %s%s\n", tscolor(), green(decodedMsg.From), cyan(decodedMsg.To), reset())
		fmt.Printf(" %s   内容: %s%s\n", tscolor(), dim(""), decodedMsg.Content)

		// 写入本地 AI 消息队列文件
		queueDir := aiQueueDir()
		queueFile := filepath.Join(queueDir, "msgs.json")
		os.MkdirAll(queueDir, 0755)

		queueEntry := map[string]interface{}{
			"msg_id":    decodedMsg.MsgID,
			"from":      decodedMsg.From,
			"to":        decodedMsg.To,
			"content":   decodedMsg.Content,
			"timestamp": time.Now().Format(time.RFC3339),
			"task_id":   task.TaskID,
			"processed": false,
		}

		// 追加到队列文件
		var entries []map[string]interface{}
		if data, err := os.ReadFile(queueFile); err == nil {
			json.Unmarshal(data, &entries)
		}
		entries = append(entries, queueEntry)
		entryData, _ := json.MarshalIndent(entries, "", "  ")
		os.WriteFile(queueFile, entryData, 0644)

		// 返回成功（消息已入队列）
		stdout := fmt.Sprintf("✅ AI 消息已入队列: msg_id=%s from=%s to=%s",
			decodedMsg.MsgID, decodedMsg.From, decodedMsg.To)
		s.submitTaskResult(TaskResult{
			TaskID:     task.TaskID,
			Success:    true,
			ExitCode:   0,
			Stdout:     stdout,
			Duration:   time.Since(time.Now()).String(),
			ExecutedOn: s.nodeID,
			Verified:   true,
		})
		return
	}

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

	// ── Start 超时隔离（WIN-CMDHANG-001）──
	// 确保 cmd.Start() 不卡死 Worker（Windows 上 cmd /c chcp 65001 >nul 可能挂）
	startCh := make(chan error, 1)
	go func() {
		startCh <- cmd.Start()
	}()

	var startErr error
	select {
	case startErr = <-startCh:
	case <-time.After(10 * time.Second):
		startErr = fmt.Errorf("启动命令超时 (10s)")
	}

	if startErr != nil {
		fmt.Printf(" %s❌ 启动命令失败: %v%s\n", red(bold("")), startErr, reset())
		s.submitTaskError(task.TaskID, startErr.Error())
		return
	}

	// Start 成功后注册到 runningTasks（决不在 Start 前注册）
	s.mu.Lock()
	s.runningTasks[task.TaskID] = cmd
	s.taskCount++
	s.mu.Unlock()

	// Set timeout (cmd.Process 此时已不为 nil)
	if task.Timeout > 0 {
		timer := time.AfterFunc(time.Duration(task.Timeout)*time.Second, func() {
			killProcess(cmd.Process)
			time.Sleep(3 * time.Second)
			if cmd.Process != nil {
				cmd.Process.Kill()
			}
		})
		defer timer.Stop()
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

	fmt.Printf("%s %s%s 任务 %s 完成 [%s] %s (%s)%s\n",
		tscolor(), statusColor(bold("")), statusIcon, cyan(task.TaskID),
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

// ── 工具函数 ──

// sanitizeNodeID sanitizes a node ID for cross-platform compatibility.
// Windows NetBIOS limits hostnames to 15 chars, so we enforce a safe limit.
// If user-provided, it's passed in directly — only auto-generated names are truncated.
// This function is only called for auto-generated names, so truncation is safe.
func sanitizeNodeID(name string) string {
	const maxLen = 15
	s := strings.ToLower(name)
	// Remove invalid chars for Windows NetBIOS
	result := make([]byte, 0, len(s))
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' {
			result = append(result, byte(r))
		}
	}
	s = string(result)
	if len(s) > maxLen {
		s = s[:maxLen]
	}
	if s == "" {
		s = "worker"
	}
	return s
}

func hostname() string {
	h, err := os.Hostname()
	if err != nil {
		return "unknown"
	}
	return h
}

func getLocalIP() string {
	// First try: UDP dial to determine the outbound interface IP
	// Works in most environments including proot/Termux
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err == nil {
		defer conn.Close()
		localAddr := conn.LocalAddr().(*net.UDPAddr)
		if localAddr != nil && localAddr.IP != nil && !localAddr.IP.IsLoopback() {
			return localAddr.IP.String()
		}
	}

	// Second try: enumerate interfaces
	addrs, err := net.InterfaceAddrs()
	if err == nil {
		for _, addr := range addrs {
			if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
				return ipnet.IP.String()
			}
		}
	}

	return "0.0.0.0"
}

func truncateString(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max] + "\n... [truncated]"
}

// ── CLI 参数 ──

func parseConfigWithArgs(args []string) (Config, bool) {
	cfg := defaultConfig

	// 尝试从 config.json 加载 LLM 配置
	configPaths := []string{"config.json"}
	if home, err := os.UserHomeDir(); err == nil {
		configPaths = append(configPaths, filepath.Join(home, "config.json"))
	}
	for _, p := range configPaths {
		if data, err := os.ReadFile(p); err == nil {
			var fileCfg struct {
				Composer struct {
					APIURL string `json:"api_url"`
					APIKey string `json:"api_key"`
					Model  string `json:"model"`
				} `json:"composer"`
			}
			if json.Unmarshal(data, &fileCfg) == nil {
				cfg.ComposerAPIURL = fileCfg.Composer.APIURL
				cfg.ComposerAPIKey = fileCfg.Composer.APIKey
				cfg.ComposerModel = fileCfg.Composer.Model
			}
			break
		}
	}

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
		case "--ip", "--address":
			if i+1 < len(args) {
				cfg.IPOverride = args[i+1]
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
		case "--confirm-connect":
			cfg.ConfirmConnect = true
		case "--no-upgrade":
			cfg.NoUpgrade = true
		case "--help", "-h":
			printWorkerHelpInternal()
			return cfg, false
		}
	}
	return cfg, true
}

func printWorkerHelpInternal() {
	fmt.Println("")
	fmt.Println(yellow(bold("")), "ComputeHub Worker Agent v"+version.Short(), reset())
	fmt.Println("")
	fmt.Println(bold(""), "用法:", reset())
	fmt.Println("  ./compute-worker --flags [options]")
	fmt.Println("")
	fmt.Println(bold(""), "参数:", reset())
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--gw <url>"), dim("Gateway 地址 (默认: http://localhost:8282)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--node-id <id>"), dim("节点 ID (默认: worker-<hostname>)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--ip <address>"), dim("手动指定 IP (默认: 自动检测)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--gpu-type <type>"), dim("GPU 型号 (默认: 自动检测)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--region <region>"), dim("区域 (默认: cn-east)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--interval <sec>"), dim("任务轮询间隔秒 (默认: 3)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--heartbeat <sec>"), dim("心跳间隔秒 (默认: 25)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--concurrent <n>"), dim("最大并发任务数 (默认: 4)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--confirm-connect"), dim("只做连接验证 (注册+心跳)，升级脚本用")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--no-upgrade"), dim("禁用自动升级循环 (开发/测试模式)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--test-register"), dim("升级模式: 注册验证后替换binary再正式运行 (自动使用)")))
	fmt.Println(fmt.Sprintf("  %-28s %s", bold("--parent-ctrl <addr>"), dim("与父进程 IPC 的 TCP 地址 (自动使用)")))
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

func ts() string {
	return time.Now().Format("15:04:05")
}
func tscolor() string {
	return dim("[" + ts() + "]")
}

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

// ────────────────────────────────────────────
// ARC-AI-NET-001 自动消费（AI间通信协议）
// ────────────────────────────────────────────

// aiMessage 是 ARC-AI-NET-001 协议的消息结构
type aiMessage struct {
	Protocol string `json:"protocol"`
	Version  string `json:"version"`
	MsgID    string `json:"msg_id"`
	MsgType  string `json:"msg_type"`
	From     string `json:"from"`
	FromNode string `json:"from_node"`
	To       string `json:"to"`
	ToNode   string `json:"to_node"`
	Content  string `json:"content"`
}

// decodeAIMessage 尝试 Base64 解码命令并判断是否为 AI 间协议消息。
// 如果是，返回解析后的消息结构和 true。
func decodeAIMessage(cmd string) (*aiMessage, bool) {
	if len(cmd) < 20 {
		return nil, false
	}

	// 尝试 Base64 解码
	decoded, err := base64.StdEncoding.DecodeString(cmd)
	if err != nil {
		// 尝试 Base64URL 编码
		decoded, err = base64.RawURLEncoding.DecodeString(cmd)
		if err != nil {
			return nil, false
		}
	}

	var msg aiMessage
	if err := json.Unmarshal(decoded, &msg); err != nil {
		return nil, false
	}

	// 验证协议标识
	if msg.Protocol != "arc-ai-net-001" {
		return nil, false
	}

	return &msg, true
}

// aiQueueDir 返回本节点的 AI 消息队列目录
func aiQueueDir() string {
	home, _ := os.UserHomeDir()
	if home == "" {
		home = "/tmp"
	}
	dir := filepath.Join(home, ".computehub", "ai_queue")
	os.MkdirAll(dir, 0755)
	return dir
}
