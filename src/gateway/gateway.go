package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/computehub/opc/src/agent"
	"github.com/computehub/opc/src/composer"
	"github.com/computehub/opc/src/executor"
	"github.com/computehub/opc/src/gene"
	"github.com/computehub/opc/src/kernel"
	"github.com/computehub/opc/src/prometheus"
	"github.com/computehub/opc/src/pure"
	"github.com/computehub/opc/src/scheduler"
)

// initSlog 初始化结构化日志（JSON 格式，带级别和源位置）
func initSlog() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level:     slog.LevelInfo,
		AddSource: true,
	})))
}

// logWithTimestamp 向后兼容的日志函数，底层使用 slog
func logWithTimestamp(format string, args ...interface{}) {
	message := fmt.Sprintf(format, args...)
	slog.Info("gateway", "msg", message)
}

// extractClientIP extracts the real client IP from an HTTP request.
// Prefers X-Forwarded-For header (for reverse proxy setups), falls back to RemoteAddr.
func extractClientIP(r *http.Request) string {
	// Check X-Forwarded-For first (reverse proxy support)
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		// Take the first (original client) IP
		if idx := strings.Index(xff, ","); idx > 0 {
			return strings.TrimSpace(xff[:idx])
		}
		return strings.TrimSpace(xff)
	}
	// Fallback to RemoteAddr (strips port suffix)
	addr := r.RemoteAddr
	if idx := strings.LastIndex(addr, ":"); idx > 0 {
		// Handle IPv6: [::1]:port
		if strings.HasPrefix(addr, "[") {
			closeBracket := strings.Index(addr, "]")
			if closeBracket > 0 {
				return addr[1:closeBracket]
			}
		}
		return addr[:idx]
	}
	return addr
}

// Response is a standardized API response structure
type Response struct {
	ID       string      `json:"id"`
	Success  bool        `json:"success"`
	Data     interface{} `json:"data,omitempty"`
	Error    string      `json:"error,omitempty"`
	Verified bool        `json:"verified"`
	Duration string      `json:"duration"`
}

// ==================== Gateway Component Status ====================

// PipelineStatus represents pipeline component status
type PipelineStatus struct {
	Status        string `json:"status"`
	Interceptions int    `json:"interceptions"`
	PureLatency   string `json:"pure_latency"`
}

// ExecutorStatus represents executor component status
type ExecutorStatus struct {
	Status           string  `json:"status"`
	VerificationRate float64 `json:"verification_rate"`
	SandboxPath      string  `json:"sandbox_path"`
}

// KernelStatus represents kernel component status
type KernelStatus struct {
	Status         string `json:"status"`
	ScheduleLatency string `json:"schedule_latency"`
	QueueDepth     int    `json:"queue_depth"`
}

// GeneStoreStatus represents gene store component status
type GeneStoreStatus struct {
	Size       int     `json:"size"`
	RecallRate float64 `json:"recall_rate"`
}

// NodeStatus represents a single node's status
type NodeStatus struct {
	NodeID        string  `json:"node_id"`
	Region        string  `json:"region"`
	GPUType       string  `json:"gpu_type"`
	Status        string  `json:"status"`
	ActiveTasks   int     `json:"active_tasks"`
	CPUUtilization float64 `json:"cpu_utilization"`
}

// NodeManagerStatus represents the overall node manager status
type NodeManagerStatus struct {
	TotalNodes  int           `json:"total_nodes"`
	OnlineNodes int           `json:"online_nodes"`
	TotalTasks  int           `json:"total_tasks"`
	ActiveTasks int           `json:"active_tasks"`
	Nodes       []NodeStatus  `json:"nodes"`
}

// SystemStatus represents the overall system status
type SystemStatus struct {
	Pipeline    PipelineStatus    `json:"pipeline"`
	Executor    ExecutorStatus    `json:"executor"`
	Kernel      KernelStatus      `json:"kernel"`
	GeneStore   GeneStoreStatus   `json:"geneStore"`
	NodeManager NodeManagerStatus `json:"nodeManager"`
	Uptime      string            `json:"uptime"`
}

// OpcGateway provides a REST API for the ComputeHub System
type OpcGateway struct {
	Kernel                 *kernel.ExtendedKernel
	Pipeline               *pure.PurePipeline
	Executor               *executor.OpcExecutor
	GeneStore              *gene.GeneStore
	Composer               *composer.TaskComposer
	Agent                  *agent.Agent
	composerAPI            string // config.json → composer.api_url
	composerKey            string // config.json → composer.api_key
	startTime              time.Time
	mu                     sync.Mutex
	unregisterSimFallback  func(nodeID string) error
	TaskDispatcher         *kernel.TaskDispatcher
	Metrics                *prometheus.Metrics
	MetricsCollector       *prometheus.Collector
	Scheduler              *scheduler.Scheduler
	wsHub                  *WSHub // WebSocket Hub（SPEC-WS-001）
	shellRouter            *shellRouter // Shell 会话路由
	ExpertRegistry         *agent.ExpertRegistry // Phase 3: 专家 Agent 注册表
	HallRouter             *agent.HallRouter     // Phase 3: Hall 消息路由器

	// 银河计划 Phase 2 三大功能
	TaskTracker            *TaskTracker           // 任务进度跟踪
	AuditStore             *AuditStore            // 安全审计日志

	// 银河计划 Phase 1B: TriggerEngine
	TriggerEngine          *TriggerEngine         // YAML 驱动的事件触发引擎

	// Phase 3 事件缓冲（来自各 Worker 的遥测日志）
	Phase3EventBuffer      *Phase3EventBuffer

	// 圆桌讨论发起器
	RoundTable             *HallRoundTable
}

// SetSimUnregisterFallback sets a fallback for deleting simulated nodes
func (g *OpcGateway) SetSimUnregisterFallback(fn func(nodeID string) error) {
	g.unregisterSimFallback = fn
}

func NewOpcGateway(port int, config *GatewayConfig) *OpcGateway {
	// Use config values or fall back to defaults
	geneStorePath := "./genes.json"
	sandboxPath := "/tmp/opc-sandbox"
	bufferSize := 100
	maxStates := 1000
	maxNodes := 50

	if config != nil {
		if config.GeneStorePath != "" {
			geneStorePath = config.GeneStorePath
		}
		if config.SandboxPath != "" {
			sandboxPath = config.SandboxPath
		}
		if config.BufferSize > 0 {
			bufferSize = config.BufferSize
		}
		if config.MaxStates > 0 {
			maxStates = config.MaxStates
		}
		if config.MaxNodes > 0 {
			maxNodes = config.MaxNodes
		}
	}

	// Initialize Internal Components
	p := pure.NewPurePipeline()
	p.AddFilter(&pure.SyntaxFilter{})
	p.AddFilter(&pure.SemanticFilter{AllowedActions: []string{"EXEC", "PING", "STATUS", "NODE_REGISTER", "TASK_SUBMIT", "NODE_HEARTBEAT", "TASK_RESULT", "GPU_MONITOR"}})
	p.AddFilter(&pure.BoundaryFilter{Blacklist: []string{"/etc/passwd", "/root/.ssh"}})
	p.AddFilter(&pure.ContextFilter{DeviceFingerprint: "OPC-GATEWAY-API"})

	kernelObj := kernel.NewExtendedKernel(bufferSize, maxStates, maxNodes)
	kernelObj.Start() // Start kernel processing goroutine

	ex := executor.NewOpcExecutor(sandboxPath)
	gs := gene.NewGeneStore(geneStorePath)

	// Initialize TaskComposer with default config
	composerCfg := composer.DefaultConfig()
	if config != nil && config.ComposerModel != "" {
		composerCfg.DecomposeModel = config.ComposerModel
	}
	if config != nil && len(config.ComposerExecModels) > 0 {
		composerCfg.ExecuteModels = config.ComposerExecModels
	}
	if config != nil && config.ComposerMaxConcurrency > 0 {
		composerCfg.MaxConcurrency = config.ComposerMaxConcurrency
	}
	composerAPI := ""
	composerKey := ""
	if config != nil {
		composerAPI = config.ComposerAPIURL
		composerKey = config.ComposerKey
	}
	composerObj := composer.NewTaskComposer(composerCfg, composerAPI, composerKey)

	// Initialize Agent (Layer 2: natural language → plan → execute)
	llmClient := composer.NewLLMClient(composerAPI, composerKey, composerCfg.DecomposeModel)

	// Create tool registry with Gateway URL for real data access
	gwURL := fmt.Sprintf("http://localhost:%d", port)
	agentTools := agent.NewToolRegistry()
	agentTools.SetGatewayURL(gwURL)
	agentTools.SetLLMClient(llmClient)

	agentObj := agent.NewAgent(llmClient, agentTools, "")  // "" → 默认记忆路径 /home/computehub/opc-memory
	agentObj.SetKernel(kernelObj)
	agentObj.SetNodeProvider(kernelObj.NodeMgr)
	logWithTimestamp("🧠 Agent initialized: model=%s", composerCfg.DecomposeModel)

	// ── Phase 1: 共享记忆层持久化 ──
	memoryDir := "/home/computehub/ComputeHub/data"
	if config != nil && config.DataDir != "" {
		memoryDir = config.DataDir
	}
	memoryFile := filepath.Join(memoryDir, "cluster_memory.json")
	SetMemoryFilePath(memoryFile)
	SetKnowledgeDataDir(memoryDir)
	// 从文件恢复 KnowledgeStore 持久化知识
	globalKnowledgeStore.load(memoryDir)
	if err := clusterMem.loadFromFile(); err != nil {
		logWithTimestamp("⚠️ 共享记忆加载失败: %v", err)
	}
	logWithTimestamp("🧠 Shared memory persistence: %s", memoryFile)

	// ── 知识同步回调：ClusterMemory → GitMemory ──
	// 当知识通过 API 写入 ClusterMemory 时，同步到 Agent GitMemory 落盘
	if agentObj.GetMemory() != nil {
		clusterMem.SetKnowledgeCallback(func(topic, content string) {
			if err := agentObj.GetMemory().SaveKnowledge(topic, content); err != nil {
				logWithTimestamp("⚠️ 知识同步到 GitMemory 失败: %v", err)
			}
		})
		logWithTimestamp("🧠 Knowledge sync callback registered: ClusterMemory → GitMemory")
	}

	// ── 启动时从 Agent GitMemory 同步到 ClusterMemory ──
	// 解决 Gateway 重启后 ClusterMemory 清零的问题
	if agentObj.GetMemory() != nil {
		go func() {
			time.Sleep(3 * time.Second) // 等 Gateway 完全就绪
			epSynced := syncGitMemoryToCluster(agentObj.GetMemory(), clusterMem, "ecs-p2ph")
			knSynced := syncClusterKnowledgeToGitMemory(agentObj.GetMemory(), clusterMem)
			logWithTimestamp("🧠 GitMemory ↔ ClusterMemory 同步完成: %d 条经验, %d 条知识", epSynced, knSynced)
		}()
	}

	// ── Phase 3: 专家 Agent 注册表 + Hall 路由器 ──
	// 专家使用 qwen3.6-35b（支持图片分析）
	expertLLM := composer.NewLLMClient(composerAPI, composerKey, "qwen3.6-35b")
	expertRegistry := agent.NewExpertRegistry(expertLLM)
	hallRouter := agent.NewHallRouter(expertRegistry, agentObj)
	hallRouter.SetPostMessage(func(topic, from, fromName, to, content string) {
		PostHallMessage(topic, from, fromName, to, content)
	})
	agent.RegisterHallTools(agentTools, hallRouter)
	agent.SetGatewayURL(fmt.Sprintf("http://127.0.0.1:%d", port))
	logWithTimestamp("🏛️ Phase 3: Expert Registry initialized with %d experts", len(expertRegistry.List()))

	// Phase 2: 为每个专家注入共享记忆搜索回调
	for _, expert := range expertRegistry.List() {
		expert.SetMemorySearchFn(func(query string, limit int) (string, error) {
			episodes := clusterMem.searchEpisodes(query, limit)
			knowledge := clusterMem.searchKnowledge(query, limit)
			var b strings.Builder
			if len(episodes) > 0 {
				b.WriteString(fmt.Sprintf("📚 共享经验 (%d 条):\n", len(episodes)))
				for _, ep := range episodes {
					icon := "✅"
					if !ep.Success {
						icon = "❌"
					}
					b.WriteString(fmt.Sprintf("  %s [%s] %s\n", icon, ep.NodeID, truncateString(ep.Task, 80)))
				}
			}
			if len(knowledge) > 0 {
				b.WriteString(fmt.Sprintf("📖 共享知识 (%d 条):\n", len(knowledge)))
				for _, kn := range knowledge {
					b.WriteString(fmt.Sprintf("  📝 [%s] %s\n", kn.NodeID, kn.Topic))
				}
			}
			if b.Len() == 0 {
				return "", nil
			}
			return b.String(), nil
		})
	}
	logWithTimestamp("🧠 Phase 2: Expert memory search callbacks injected")

	// 注册交流大厅新消息回调 → 专家路由 + Agent 自动回复
	SetHallOnNewMessage(func(topic, from, to, content string, attachments []Attachment) {
		go func() {
			defer func() {
				if r := recover(); r != nil {
					logWithTimestamp("[HallRouter] ❌ panic in callback: %v", r)
				}
			}()

			logWithTimestamp("[HallRouter] 📨 callback triggered: from=%s to=%s topic=%s content=%s attachments=%d", from, to, topic, truncateString(content, 60), len(attachments))

			// 如果本条消息没有附件，往前找最近一条带附件的消息
			allAttachments := attachments
			if len(allAttachments) == 0 {
				allAttachments = findRecentAttachments(topic, from)
			}

			// 转换为 agent 包的类型
			var agentAttachments []agent.Attachment
			for _, a := range allAttachments {
				agentAttachments = append(agentAttachments, agent.Attachment{
					Name: a.Name,
					URL:  a.URL,
					Size: a.Size,
					Type: a.Type,
				})
			}

			// Step 1: 先让 Hall 路由器处理（专家匹配）
			if hallRouter.HandleMessage(topic, from, from, to, content, agentAttachments) {
				logWithTimestamp("[HallRouter] ✅ routed to expert")
				return // 已有专家回复
			}

			logWithTimestamp("[HallRouter] ⏩ no expert matched, checking @小智")

			// Step 2: 被 @小智 时才触发 Agent 自动回复
			if !strings.Contains(content, "@小智") {
				return
			}

			// 构建任务分解系统提示（含专家列表）
			expertList := expertRegistry.ListDescriptions()
			taskPrompt := fmt.Sprintf(`你是小智，ComputeHub集群的AI助手，也是集群的"任务分解调度员"。

交流大厅有人给你发消息：@%s 说："%s"

## 你的职责
1. 分析任务类型和复杂度
2. 如果是简单任务（打招呼、确认），直接回复
3. 如果是复杂任务（检查状态、分析数据、部署升级），需要分解为子任务

## 任务分解规则
当收到复杂任务时，你可以通过 hall_speak 工具 @ 其他 Agent 委派子任务：

%s

## 任务委派格式
使用 hall_speak 工具发送消息：
- topic: "general"
- to: "all"（或具体 Agent ID）
- content: "@目标Agent 任务描述"

## 回复要求
- 直接回答对方的问题
- 如果分解了任务，先发一条"收到，我来分解这个任务"再开始委派
- 委派完成后，等各 Agent 回复，然后汇总结果
- 不要说空话，不要提到你联系谁
- 用中文回复`,
				from, content, expertList)

			resp, err := agentObj.Think(context.Background(), &agent.AgentRequest{
				Task:       taskPrompt,
				SessionID:  "hall-auto",
				FastReply:  false,
			})
			if err == nil && resp != nil && resp.Result != "" {
				PostHallMessage(topic, "小智", "小智", "all", "@"+from+" "+resp.Result)
			}
		}()
	})
	logWithTimestamp("🏛️ AI Hall auto-reply registered (with expert routing + task decomposition)")

	// Create gateway instance before sim registration (needed for self-reference)
	gw := &OpcGateway{
		Kernel:    kernelObj,
		Pipeline:  p,
		Executor:  ex,
		GeneStore: gs,
		Composer:  composerObj,
		Agent:     agentObj,
		startTime: time.Now(),
		wsHub:     NewWSHub(), // WebSocket Hub（SPEC-WS-001）
		shellRouter: newShellRouter(), // Shell 会话路由
		ExpertRegistry: expertRegistry, // Phase 3: 专家 Agent 注册表
		HallRouter:     hallRouter,     // Phase 3: Hall 消息路由器
		TaskTracker:    NewTaskTracker(), // 银河计划 Phase 2: 任务进度跟踪
		AuditStore:     NewAuditStore(1000), // 银河计划 Phase 2: 安全审计日志
	}

	// 把 shellRouter 注入到 WS Hub（用于 routeShellOutputToTUI）
	gw.wsHub.shellRouter = gw.shellRouter

	// 把 config.json 的 composer 配置存到 gw 里（用于 LLM Proxy 等后续使用）
	if config != nil {
		gw.composerAPI = config.ComposerAPIURL
		gw.composerKey = config.ComposerKey
	}

	// Create Prometheus metrics and registerer
	metricsReg := prometheus.NewRegistry()
	gw.Metrics = metricsReg.CreateMetrics()
	gw.MetricsCollector = prometheus.NewCollector(gw.Metrics)

	// Connect collector to real NodeManager for live metrics
	gw.MetricsCollector.SetNodeMgr(kernelObj.NodeMgr)
	logWithTimestamp("🔗 Prometheus metrics collector connected to NodeManager")

	// Start metrics collector (updates every 5s from kernel state)
	gw.MetricsCollector.Start(5 * time.Second)
	logWithTimestamp("✅ Prometheus metrics collector started (interval=5s)")

	logWithTimestamp("✅ Gateway initialized, ready to serve")

	// Start task dispatcher (picks up pending tasks from kernel queue)
	runner := &kernel.LocalTaskRunner{SandboxPath: sandboxPath}
	dispatcher := kernel.NewTaskDispatcher(kernelObj, runner)
	dispatcher.Start(2 * time.Second)
	gw.TaskDispatcher = dispatcher
	logWithTimestamp("✅ Task dispatcher started (interval=2s)")

	// Initialize Scheduler connected to real NodeManager
	sched := scheduler.NewScheduler(scheduler.DefaultConfig())
	// Register real nodes into scheduler (from kernel's NodeMgr)
	nodes := kernelObj.NodeMgr.ListNodes()
	for _, state := range nodes {
		reg := state.Register
		sched.RegisterNode(&scheduler.NodeInfo{
			ID:           reg.NodeID,
			Region:       reg.Region,
			Status:       reg.Status,
			GPUType:      reg.GPUType,
			CPUCores:     reg.CPUCores,
			MemoryGB:     reg.MemoryGB,
			GPUMemoryGB:  reg.GPUMemoryGB,
			MaxTasks:     reg.MaxConcurrency,
			SuccessRate:  1.0,
		})
	}
	gw.Scheduler = sched
	logWithTimestamp("✅ Scheduler initialized with %d real nodes", len(nodes))

	// ── Phase 2: 记忆衰减定时器（每 6 小时执行一次） ──
	go func() {
		decayTicker := time.NewTicker(6 * time.Hour)
		defer decayTicker.Stop()
		// 启动时立即执行一次
		if agentObj.GetMemory() != nil {
			if err := agentObj.GetMemory().DailyDecay(); err != nil {
				logWithTimestamp("⚠️ 记忆衰减（启动）失败: %v", err)
			} else {
				logWithTimestamp("🧠 记忆衰减（启动）完成")
			}
		}
		for range decayTicker.C {
			if agentObj.GetMemory() != nil {
				if err := agentObj.GetMemory().DailyDecay(); err != nil {
					logWithTimestamp("⚠️ 记忆衰减失败: %v", err)
				} else {
					logWithTimestamp("🧠 记忆衰减完成")
				}
			}
		}
	}()
	logWithTimestamp("🧠 Memory decay scheduler started (interval=6h)")

	// ── 银河计划 Phase 1B: TriggerEngine 触发引擎初始化 ──
	triggerCfgPath := "data/trigger_rules.json"
	if config != nil && config.TriggerRulesPath != "" {
		triggerCfgPath = config.TriggerRulesPath
	}
	te := NewTriggerEngine(triggerCfgPath)
	if err := te.LoadRules(); err != nil {
		logWithTimestamp("⚠️ TriggerEngine 加载规则失败: %v, 使用默认规则", err)
	}
	// 启动系统指标采集（每 60 秒）
	cpuCores := 0
	if len(nodes) > 0 && nodes[0].Register != nil {
		cpuCores = nodes[0].Register.CPUCores
	}
	if cpuCores <= 0 {
		cpuCores = 4
	}
	te.StartSystemCollector(60*time.Second, cpuCores)
	gw.TriggerEngine = te
	logWithTimestamp("⚡ TriggerEngine initialized: %d rules, %d enabled", len(te.GetRules()), func() int {
		n := 0
		for _, r := range te.GetRules() {
			if r.Enabled {
				n++
			}
		}
		return n
	}())

	// 初始化 Phase 3 事件缓冲区
	gw.Phase3EventBuffer = NewPhase3EventBuffer(200)
	logWithTimestamp("🌌 Phase 3 event buffer initialized (max=200)")

	// 🌌 Phase 3b: 自主进化引擎 — 任务复盘、知识沉淀、自我反思
	// 在 Gateway 侧初始化 Agent.Phase3，事件写入 Phase3EventBuffer 供监控页面读取
	if gw.Agent != nil && gw.Agent.GetMemory() != nil {
		phase3 := agent.NewGalaxyPhase3Manager(gw.Agent, gw.ExpertRegistry, gw.Agent.GetMemory(), llmClient)
		// 注入事件回调 → Phase3EventBuffer（监控页面 & stats）
		phase3.SetEventSyncFn(func(evt agent.Phase3Event) {
			gw.Phase3EventBuffer.Push(Phase3Event{
				Time:      evt.Time,
				Source:    evt.Source,
				Action:    evt.Action,
				Detail:    evt.Detail,
				LLMCalled: evt.LLMCalled,
				Success:   evt.Success,
				NodeID:    "ecs-p2ph",
			})
		})
		gw.Agent.SetPhase3(phase3)
		logWithTimestamp("🌌 Phase 3b 自主进化引擎已激活 (Gateway)")
	} else {
		logWithTimestamp("⚠️ Phase 3b 初始化跳过: Agent 或 Memory 不可用")
	}

	// 初始化圆桌讨论发起器
	gw.RoundTable = NewHallRoundTable()
	logWithTimestamp("🎙️ Hall RoundTable initialized")

	// 启动 ARC-AI-NET 两阶段健康监控
	gw.Kernel.NodeMgr.StartHealthMonitor(BroadcastProbeInterval)
	gw.StartArcNetMonitor()
	logWithTimestamp("✅ ARC-AI-NET monitoring started (suspect=%s, offline=%s)", SuspectAfter, OfflineAfter)

	return gw
}

// GatewayConfig holds configuration for gateway components
type GatewayConfig struct {
	GeneStorePath      string
	SandboxPath        string
	BufferSize         int
	MaxStates          int
	MaxNodes           int
	ComposerModel      string
	ComposerExecModels []string
	ComposerAPIURL     string
	ComposerKey        string
	ComposerMaxConcurrency int
	DataDir            string // 数据目录（共享记忆持久化等）
	TriggerRulesPath   string // TriggerEngine 规则文件路径
}

// Validate 校验配置，返回所有缺失/错误项
func (c *GatewayConfig) Validate() []string {
	var errs []string
	if c.ComposerAPIURL == "" {
		errs = append(errs, "composer.api_url is required")
	}
	if c.ComposerKey == "" {
		errs = append(errs, "composer.api_key is required")
	}
	if c.SandboxPath == "" {
		errs = append(errs, "executor.sandbox_path is required")
	}
	if c.BufferSize <= 0 {
		errs = append(errs, "kernel.buffer_size must be > 0")
	}
	if c.MaxStates <= 0 {
		errs = append(errs, "kernel.max_states must be > 0")
	}
	if c.MaxNodes <= 0 {
		errs = append(errs, "kernel.max_nodes must be > 0")
	}
	if c.ComposerMaxConcurrency <= 0 {
		errs = append(errs, "composer.max_concurrency must be > 0")
	}
	return errs
}

// ApplyEnvOverrides 用环境变量覆盖配置字段
// 环境变量格式: CONFIG_<FIELD>，如 CONFIG_COMPOSER_API_URL
func (c *GatewayConfig) ApplyEnvOverrides() {
	if v := os.Getenv("CONFIG_COMPOSER_API_URL"); v != "" {
		c.ComposerAPIURL = v
	}
	if v := os.Getenv("CONFIG_COMPOSER_API_KEY"); v != "" {
		c.ComposerKey = v
	}
	if v := os.Getenv("CONFIG_COMPOSER_MODEL"); v != "" {
		c.ComposerModel = v
	}
	if v := os.Getenv("CONFIG_SANDBOX_PATH"); v != "" {
		c.SandboxPath = v
	}
	if v := os.Getenv("CONFIG_DATA_DIR"); v != "" {
		c.DataDir = v
	}
	if v := os.Getenv("CONFIG_GENE_STORE_PATH"); v != "" {
		c.GeneStorePath = v
	}
	if v := os.Getenv("CONFIG_TRIGGER_RULES_PATH"); v != "" {
		c.TriggerRulesPath = v
	}
}

func (g *OpcGateway) Serve(port int, dashboardDir ...string) {
	g.registerRoutes(port, dashboardDir...)
	srv := g.serveWithGracefulShutdown(port)
	<-g.waitForShutdown(srv)
}

// ServeWithServer is like Serve but returns *http.Server for graceful shutdown.
// This is the preferred method for production use.
func (g *OpcGateway) ServeWithServer(port int, dashboardDir ...string) *http.Server {
	g.registerRoutes(port, dashboardDir...)
	return g.serveWithGracefulShutdown(port)
}

// serveWithGracefulShutdown 启动 HTTP 服务并注册优雅关闭
func (g *OpcGateway) serveWithGracefulShutdown(port int) *http.Server {
	// Middleware 链: RequestID → Auth → DefaultServeMux
	handler := RequestIDMiddleware(AuthMiddleware(http.DefaultServeMux))

	srv := &http.Server{
		Addr:    fmt.Sprintf(":%d", port),
		Handler: handler,
	}

	go func() {
		logWithTimestamp("🌐 ComputeHub Gateway listening on :%d", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logWithTimestamp("Fatal Gateway Error: %v", err)
		}
	}()

	return srv
}

// waitForShutdown 等待 SIGINT/SIGTERM 并优雅关闭
func (g *OpcGateway) waitForShutdown(srv *http.Server) chan struct{} {
	done := make(chan struct{}, 1)
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		sig := <-sigCh
		logWithTimestamp("🛑 Received signal %v, shutting down gracefully...", sig)

		// 给正在处理的请求 30s 宽限期
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		// 关闭 HTTP 服务
		if err := srv.Shutdown(ctx); err != nil {
			logWithTimestamp("⚠️ Graceful shutdown error: %v", err)
		}

		// 关闭内部组件
		if g.MetricsCollector != nil {
			g.MetricsCollector.Stop()
		}
		if g.wsHub != nil {
			g.wsHub.Close()
		}

		logWithTimestamp("✅ Gateway shutdown complete")
		close(done)
	}()
	return done
}

// ServeHTTP implements http.Handler for test integration
func (g *OpcGateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	switch r.URL.Path {
	case "/api/dispatch":
		g.handleDispatch(w, r)
	case "/api/health":
		g.handleHealth(w, r)
	case "/api/status":
		g.handleStatus(w, r)
	case "/api/v1/nodes/register":
		g.handleNodeRegister(w, r)
	case "/api/v1/nodes/unregister":
		g.handleNodeUnregister(w, r)
	case "/api/v1/nodes/heartbeat":
		g.handleNodeHeartbeat(w, r)
	case "/api/v1/nodes/list":
		g.handleNodeList(w, r)
	case "/api/v1/nodes/metrics":
		g.handleNodeMetrics(w, r)
	case "/api/v1/nodes/stats":
		g.handleNodesStats(w, r)
	case "/api/v1/tasks/submit":
		g.handleTaskSubmit(w, r)
	case "/api/v1/tasks/result":
		g.handleTaskResult(w, r)
	case "/api/v1/tasks/cancel":
		g.handleTaskCancel(w, r)
	case "/api/v1/tasks/list":
		g.handleTaskList(w, r)
	case "/api/v1/tasks/detail":
		g.handleTaskDetail(w, r)
	case "/api/v1/tasks/poll":
		g.handleTaskPoll(w, r)
	case "/api/v1/tasks/progress":
		g.handleTaskProgress(w, r)
	case "/api/v1/download":
		g.handleFileDownload(w, r)
	case "/api/v1/upgrade/check":
		g.handleUpgradeCheck(w, r)
	case "/api/v1/upgrade/config":
		g.handleUpgradeConfig(w, r)
	case "/api/v1/upgrade/checksum":
		g.handleUpgradeChecksum(w, r)
	default:
		http.NotFound(w, r)
	}
}

// ==================== Health and Status Endpoints ====================

// handleHealth is the health check endpoint for OpcGateway v1
func (g *OpcGateway) handleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	g.sendResponse(w, Response{
		ID:       "health-check",
		Success:  true,
		Data:     "ComputeHub System Healthy",
		Verified: false,
	})
}

// handleWSHealth WS Hub 健康检查端点
func (g *OpcGateway) handleWSHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.wsHub == nil {
		g.sendResponse(w, Response{Success: false, Error: "WS Hub not initialized"})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"online_count": g.wsHub.OnlineCount(),
			"clients":      g.wsHub.ListClients(),
			"sent":         g.wsHub.MessagesSent,
			"received":     g.wsHub.MessagesReceived,
			"connects":     g.wsHub.ConnectCount,
			"disconnects":  g.wsHub.DisconnectCount,
		},
	})
}

// handleStatus is the system status endpoint for OpcGateway v1
func (g *OpcGateway) handleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	onlineCount := 0
	totalTasks := 0
	activeTasks := 0

	for _, node := range nodes {
		totalTasks += node.Metrics.TotalTasks
		activeTasks += node.Metrics.ActiveTasks
		if node.Register.Status == "online" {
			onlineCount++
		}
	}

	uptime := time.Since(g.startTime).String()

	status := SystemStatus{
		Pipeline: PipelineStatus{
			Status: "ACTIVE",
			PureLatency: "0s",
		},
		Executor: ExecutorStatus{
			Status:           "READY",
			VerificationRate: 100.0,
			SandboxPath:      "/tmp/opc-sandbox",
		},
		Kernel: KernelStatus{
			Status:         "RUNNING",
			ScheduleLatency: "5µs",
		},
		GeneStore: GeneStoreStatus{
			Size:       len(g.GeneStore.Genes),
			RecallRate: 0.0,
		},
		NodeManager: NodeManagerStatus{
			TotalNodes:  len(nodes),
			OnlineNodes: onlineCount,
			TotalTasks:  totalTasks,
			ActiveTasks: activeTasks,
		},
		Uptime: uptime,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

func (g *OpcGateway) sendResponse(w http.ResponseWriter, resp Response) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

// ==================== Legacy Endpoints ====================

// handleDispatch is the main dispatch endpoint for OpcGateway v1
func (g *OpcGateway) handleDispatch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	var dispatchReq struct {
		ID      string `json:"id"`
		Command string `json:"command"`
		Payload interface{} `json:"payload"`
	}
	if err := json.Unmarshal(body, &dispatchReq); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if dispatchReq.Command == "" {
		g.sendResponse(w, Response{Success: false, Error: "command is required"})
		return
	}

	// 轻量验证（dispatch 是内部可信 API，跳过 SemanticFilter）
	cmd := strings.TrimSpace(dispatchReq.Command)
	for _, b := range []string{"/etc/passwd", "/root/.ssh"} {
		if strings.Contains(cmd, b) {
			g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("security violation: path %s is forbidden", b)})
			return
		}
	}

	respChan := g.Kernel.DispatchExtended(dispatchReq.ID, cmd, dispatchReq.Payload)
	resp := <-respChan

	g.sendResponse(w, Response{
		ID:       dispatchReq.ID,
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Verified: false,
		Duration: resp.Duration,
	})
}

// ==================== ComputeHub API v1 Endpoints ====================
// (Node handlers moved to handler_nodes.go, Task handlers moved to handler_tasks.go)

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// ==================== File Download Endpoint ====================

// findDeployDir finds the deploy directory relative to the binary location.
// It supports both flat (deploy/) and versioned (deploy/<version>/) layouts.
//
// Critical fix (2026-06-01): Walk up to find .git first, so the deploy/ is
// always under the project root — avoids stale deploy/ at parent levels.
func findDeployDir() string {
	// Determine where the running binary lives — that's the most reliable anchor
	exe, _ := os.Executable()
	exeDir := ""
	if exe != "" {
		if idx := strings.LastIndex(exe, "/"); idx >= 0 {
			exeDir = exe[:idx]
		}
	}

	// Strategy: find .git directory to locate the project root.
	// Priority:
	//   1. exeDir/deploy/ (binary in project root — most common for ComputeHub)
	//   2. Walk up to find .git → parent project deploy/
	//   3. Scan children for .git (binary may sit above multiple projects)
	//   4. Versioned deploy/ layouts
	//   5. Flat deploy/ fallback
	if exeDir != "" {
		// 1. FIRST: exeDir/deploy/ — binary is in project root, deploy is a sibling
		candidate := filepath.Join(exeDir, "deploy")
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}

		// 2. Walk up to find .git → project root deploy/
		dir := exeDir
		for {
			if _, err := os.Stat(filepath.Join(dir, ".git")); err == nil {
				candidate := filepath.Join(dir, "deploy")
				if _, err := os.Stat(candidate); err == nil {
					return candidate
				}
				break
			}
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}

		// 3. Check exeDir children for .git (binary sits above project root)
		//    When multiple children have .git, prefer the project whose deploy/
		//    contains files matching the request, or the alphabetically first one.
		if entries, err := os.ReadDir(exeDir); err == nil {
			for _, e := range entries {
				if e.IsDir() {
					gitPath := filepath.Join(exeDir, e.Name(), ".git")
					if _, err := os.Stat(gitPath); err == nil {
						candidate := filepath.Join(exeDir, e.Name(), "deploy")
						if _, err := os.Stat(candidate); err == nil {
							return candidate
						}
					}
				}
			}
		}
	}

	// Search versioned directory first (binary may live in deploy/0.7.4/linux-arm64/)
	versionCandidates := []string{
		"deploy/0.7.7",
		"deploy/0.7.6",
		"deploy/0.7.5",
		"deploy/0.7.4",
	}
	for _, c := range versionCandidates {
		// Try relative to binary directory (e.g. exe=/deploy/0.7.4/linux-arm64/gw → ../../deploy/0.7.4)
		if exeDir != "" {
			// Binary is in a platform subdirectory: ../.. = version dir
			// Binary is in deploy root: .. = parent dir (project root)
			// Try both relative paths
			for _, rel := range []string{"./" + c, "../" + c, "../../" + c} {
				candidate := exeDir + "/" + rel
				if _, err := os.Stat(candidate); err == nil {
					return candidate
				}
			}
			// Also try abs path from exeDir parent
			candidate := exeDir + "/" + c
			if _, err := os.Stat(candidate); err == nil {
				return candidate
			}
		}
		// Try relative to CWD
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}

	// Fall back to flat deploy/ directory
	flatCandidates := []string{"deploy"}
	for _, c := range flatCandidates {
		if exeDir != "" {
			for _, rel := range []string{"./" + c, "../" + c, "../../" + c} {
				candidate := exeDir + "/" + rel
				if _, err := os.Stat(candidate); err == nil {
					return candidate
				}
			}
			candidate := exeDir + "/" + c
			if _, err := os.Stat(candidate); err == nil {
				return candidate
			}
		}
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}
	return "deploy"
}

// handleFileDownload serves files for worker self-transport / bootstrap.
// Usage:
//   GET /api/v1/download?file=computehub                        → auto-detect (fallback chain)
//   GET /api/v1/download?file=computehub&platform=linux-amd64   → exact platform
//   GET /api/v1/download?file=computehub.exe&platform=windows-amd64
//
// Supported platforms: linux-amd64, linux-arm64, darwin-amd64, darwin-arm64, windows-amd64
// Serves from the deploy/ directory relative to the binary location.
// handleFileDownload serves files for worker self-transport / bootstrap.
// Usage:
//   GET /api/v1/download?file=computehub                        → auto-detect (fallback chain)
//   GET /api/v1/download?file=computehub&platform=linux-amd64   → exact platform
//   GET /api/v1/download?file=computehub.exe&platform=windows-amd64
//
// Supported platforms: linux-amd64, linux-arm64, darwin-amd64, darwin-arm64, windows-amd64
// Serves from the deploy/ directory relative to the binary location.
func (g *OpcGateway) handleFileDownload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}
	// HEAD is allowed; http.ServeFile handles it automatically with headers only

	fileName := r.URL.Query().Get("file")
	if fileName == "" {
		g.sendResponse(w, Response{Success: false, Error: "file parameter is required"})
		return
	}

	// Only serve binaries from known directory
	allowedPrefixes := []string{"compute-worker-", "compute-gateway-", "compute-tui-", "computehub", "computehub-", "opc-", "tunnel"}
	allowed := false
	for _, prefix := range allowedPrefixes {
		if strings.HasPrefix(fileName, prefix) {
			allowed = true
			break
		}
	}
	if !allowed {
		g.sendResponse(w, Response{Success: false, Error: "file not allowed"})
		return
	}

	deployDir := findDeployDir()
	platform := r.URL.Query().Get("platform")

	// Normalize android → linux (same kernel ABI, Termux uses android/arm64)
	if platform != "" {
		parts := strings.Split(platform, "/")
		if len(parts) == 2 && parts[0] == "android" {
			platform = "linux/" + parts[1]
		}
	}

	// 1. Platform-specific directory FIRST when platform is specified
	//    (e.g. deploy/linux-arm64/computehub for arm64 nodes)
	//    ⚠️ If platform specified but not found → fail loudly, no wrong-platform fallback!
	if platform != "" {
		platDir := strings.ReplaceAll(platform, "/", "-")
		subDir := deployDir + "/" + platDir
		for _, tryName := range []string{fileName, "computehub", "computehub.exe"} {
			tryPath := subDir + "/" + tryName
			if _, err := os.Stat(tryPath); err == nil {
				w.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, fileName))
				http.ServeFile(w, r, tryPath)
				return
			}
		}
		// Platform specified but not found → 404 error
		http.Error(w, fmt.Sprintf(`{"error":"binary not found for platform: %s"}`, platform), http.StatusNotFound)
		return
	}

	// 2. Try deploy/ root (fallback for no-platform or generic requests)
	filePath := deployDir + "/" + fileName
	if _, err := os.Stat(filePath); err == nil {
		w.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, fileName))
		http.ServeFile(w, r, filePath)
		return
	}

	// 3. Fallback: try all known platform directories.
	//    🐛 Fix: when fileName ends with .exe, only search windows directories
	//    to avoid matching computehub (Linux binary) from linux-*/ or darwin-*/ subdirs.
	isWindowsRequest := strings.HasSuffix(fileName, ".exe")
	for _, platDir := range []string{"linux-amd64", "linux-arm64", "windows-amd64", "darwin-amd64", "darwin-arm64"} {
		// Skip non-Windows directories for .exe requests
		if isWindowsRequest && !strings.HasPrefix(platDir, "windows") {
			continue
		}
		platPath := deployDir + "/" + platDir + "/" + fileName
		if _, err := os.Stat(platPath); err == nil {
			w.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, fileName))
			http.ServeFile(w, r, platPath)
			return
		}
		noExt := strings.TrimSuffix(fileName, ".exe")
		for _, tryName := range []string{noExt, noExt + ".exe"} {
			tryPath := deployDir + "/" + platDir + "/" + tryName
			if _, err := os.Stat(tryPath); err == nil {
				w.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, fileName))
				http.ServeFile(w, r, tryPath)
				return
			}
		}
	}

	http.NotFound(w, r)
}

// isSimpleTask 判断命令是否为简单命令
// 简单命令直接调度，复杂命令（自然语言）走 Composer
func isSimpleTask(cmd string) bool {
	simplePatterns := []string{
		"ls", "df", "echo", "hostname", "uptime", "uname", "whoami",
		"date", "pwd", "ver", "dir", "type", "free", "ps",
		"cat", "head", "tail", "wc", "id", "env",
		"python", "python3", "node", "git", "go",
		"nvidia-smi", "wmic", "systeminfo",
	}

	cmd = strings.TrimSpace(cmd)

	// 包含中文 → 一定是自然语言（复杂任务）
	for _, r := range cmd {
		if r >= 0x4E00 && r <= 0x9FFF { // CJK Unified Ideographs
			return false
		}
	}

	firstWord := strings.Split(cmd, " ")[0]
	firstWord = strings.Split(firstWord, "\t")[0]

	for _, pattern := range simplePatterns {
		if strings.EqualFold(firstWord, pattern) {
			return true
		}
	}

	// 如果包含管道、重定向、引号套叠，也视为简单 shell 命令
	if strings.ContainsAny(cmd, "|<>;&") {
		return true
	}

	// 自然语言检测：超过 5 个词且不含 shell 关键字 → 复杂任务
	words := strings.Fields(cmd)
	shellKeywords := []string{"ls", "cat", "echo", "cd", "rm", "cp", "mv", "grep", "find", "sed", "awk"}
	hasShell := false
	for _, w := range words {
		for _, sk := range shellKeywords {
			if strings.EqualFold(w, sk) {
				hasShell = true
				break
			}
		}
		if hasShell {
			break
		}
	}

	if len(words) >= 5 && !hasShell && !strings.ContainsAny(cmd, "|&;<>\"'$") {
		return false
	}

	return true
}

// ====== LLM 代理端点、Agent Think/Stream、Expert List ======
// (Moved to handler_llm.go)

// findRecentAttachments 在话题中查找指定用户最近一条带附件的消息
func findRecentAttachments(topic, from string) []Attachment {
	msgs := GetHallMessages(topic, 0, 20)
	for i := len(msgs) - 1; i >= 0; i-- {
		m := msgs[i]
		if m.From == from && len(m.Attachments) > 0 {
			return m.Attachments
		}
	}
	return nil
}

// syncGitMemoryToCluster 从 Agent GitMemory 同步经验和知识到 ClusterMemory
// 解决 Gateway 重启后 ClusterMemory 清零的问题
func syncGitMemoryToCluster(mem agent.Memory, cm *ClusterMemory, nodeID string) int {
	synced := 0

	// 1. 同步经验
	episodes, err := mem.ListRecentEpisodes(1000)
	if err != nil {
		logWithTimestamp("⚠️ GitMemory 经验读取失败: %v", err)
	} else {
		for _, ep := range episodes {
			key := nodeID + ":" + ep.Task
			cm.mu.Lock()
			cm.episodes[key] = &SharedEpisode{
				NodeID:    nodeID,
				Task:      ep.Task,
				Result:    "",
				Success:   ep.Success,
				Learned:   ep.Learned,
				Timestamp: time.Now(),
				Strength:  ep.Strength,
			}
			cm.lastSync[nodeID] = time.Now()
			cm.indexEpisode(ep.Task, key)
			cm.indexEpisode(ep.Learned, key)
			cm.mu.Unlock()
			synced++
		}
	}

	// 2. 同步知识（新增：修复知识丢失根因）
	knowledge, err := mem.ListRecentKnowledge(1000)
	if err != nil {
		logWithTimestamp("⚠️ GitMemory 知识读取失败: %v", err)
	} else {
		for _, kn := range knowledge {
			key := kn.Topic + ":" + nodeID
			// 从文件读取完整内容
			content := kn.Topic // fallback: topic 本身
			kmPath := filepath.Join("/home/computehub/ComputeHub/data", "knowledge", kn.File)
			if data, readErr := os.ReadFile(kmPath); readErr == nil {
				if idx := strings.Index(string(data), "## Content\n\n"); idx >= 0 {
					content = strings.TrimSpace(string(data)[idx+12:])
				} else if idx := strings.Index(string(data), "## Solution\n"); idx >= 0 {
					content = strings.TrimSpace(string(data)[idx+len("## Solution\n"):])
				} else {
					content = strings.TrimSpace(string(data)[:min(500, len(string(data)))])
				}
			}
			cm.mu.Lock()
			cm.knowledge[key] = &SharedKnowledge{
				NodeID:  nodeID,
				Topic:   kn.Topic,
				Content: content,
				Author:  nodeID,
				Tags:    []string{kn.Topic, kn.Problem},
				Timestamp: time.Now(),
			}
			cm.lastSync[nodeID] = time.Now()
			cm.indexKnowledge(kn.Topic, key)
			cm.mu.Unlock()
			synced++
		}
	}

	// 一次性持久化（sync 完成后写一次，避免 95+ 次重复写入）
	if err := cm.saveToFile(); err != nil {
		logWithTimestamp("⚠️ ClusterMemory 持久化失败: %v", err)
	}

	return synced
}

// syncClusterKnowledgeToGitMemory 从 ClusterMemory 同步知识到 GitMemory
// 解决知识只存在 ClusterMemory 但 GitMemory 没有落盘的问题
func syncClusterKnowledgeToGitMemory(mem agent.Memory, cm *ClusterMemory) int {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	synced := 0
	for _, kn := range cm.knowledge {
		if err := mem.SaveKnowledge(kn.Topic, kn.Content); err != nil {
			logWithTimestamp("⚠️ 知识同步到 GitMemory 失败: %s: %v", kn.Topic[:min(len(kn.Topic), 40)], err)
			continue
		}
		synced++
	}

	return synced
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}


