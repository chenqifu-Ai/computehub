package gateway

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
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

// logWithTimestamp 添加时间戳的日志函数
func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
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

func (g *OpcGateway) Serve(port int, dashboardDir ...string) {
	// Legacy endpoints (backward compatible)
	http.HandleFunc("/api/dispatch", g.handleDispatch)
	http.HandleFunc("/api/health", g.handleHealth)
	http.HandleFunc("/api/status", g.handleStatus)

	// ComputeHub API endpoints
	http.HandleFunc("/api/v1/nodes/register", g.handleNodeRegister)
	http.HandleFunc("/api/v1/nodes/unregister", g.handleNodeUnregister)
	http.HandleFunc("/api/v1/nodes/heartbeat", g.handleNodeHeartbeat)
	http.HandleFunc("/api/v1/nodes/list", g.handleNodeList)
	http.HandleFunc("/api/v1/nodes/metrics", g.handleNodeMetrics)
	http.HandleFunc("/api/v1/nodes/stats", g.handleNodesStats)
	http.HandleFunc("/api/v1/tasks/submit", g.handleTaskSubmit)
	http.HandleFunc("/api/v1/tasks/result", g.handleTaskResult)
	http.HandleFunc("/api/v1/tasks/cancel", g.handleTaskCancel)
	http.HandleFunc("/api/v1/tasks/list", g.handleTaskList)
	http.HandleFunc("/api/v1/tasks/detail", g.handleTaskDetail)
	http.HandleFunc("/api/v1/tasks/poll", g.handleTaskPoll)
	http.HandleFunc("/api/v1/tasks/progress", g.handleTaskProgress) // streaming output

	// Agent Registry (AI agent discovery)
	http.HandleFunc("/api/v1/agents/register", g.handleAgentRegister)
	http.HandleFunc("/api/v1/agents/heartbeat", g.handleAgentHeartbeat)
	http.HandleFunc("/api/v1/agents/unregister", g.handleAgentUnregister)
	http.HandleFunc("/api/v1/agents/list", g.handleAgentList)
	http.HandleFunc("/api/v1/agents/get", g.handleAgentGet)
	logWithTimestamp("🤖 Agent Registry endpoints registered: /api/v1/agents/*")

	// OpenClaw 管理
	http.HandleFunc("/api/v1/openclaw/status", g.handleOpenClawStatus)
	logWithTimestamp("🩺 OpenClaw status endpoint registered: /api/v1/openclaw/status")

	// Prometheus metrics endpoint
	http.HandleFunc("/metrics", prometheus.MetricsHandler(g.Metrics.Registry))
	logWithTimestamp("📈 Prometheus /metrics endpoint registered")

	// Video generation endpoints (worker built-in video pipeline)
	http.HandleFunc("/api/v1/video/generate", g.handleVideoGenerate)
	http.HandleFunc("/api/v1/video/progress", g.handleVideoProgress)
	http.HandleFunc("/api/v1/video/list", g.handleVideoList)
	logWithTimestamp("🎬 Video endpoints registered: /api/v1/video/*")

	// File download endpoint (self-bootstrap transport for workers)
	http.HandleFunc("/api/v1/download", g.handleFileDownload)
	logWithTimestamp("📦 Download endpoint registered: /api/v1/download")

	// Upgrade check endpoint (worker auto-update)
	http.HandleFunc("/api/v1/upgrade/check", g.handleUpgradeCheck)
	http.HandleFunc("/api/v1/upgrade/config", g.handleUpgradeConfig)
	http.HandleFunc("/api/v1/upgrade/checksum", g.handleUpgradeChecksum)
	logWithTimestamp("🔄 Upgrade endpoints registered: /api/v1/upgrade/*")

	// WebSocket Hub endpoint（SPEC-WS-001）
	http.HandleFunc("/api/v1/ws", g.wsHub.HandleWSUpgrade)
	logWithTimestamp("📡 WebSocket Hub registered: /api/v1/ws")

	// WS Hub 健康检查
	http.HandleFunc("/api/v1/ws/health", g.handleWSHealth)
	logWithTimestamp("📡 WS Health endpoint registered: /api/v1/ws/health")

	// TUI Shell WS endpoint（交互式远程终端）
	http.HandleFunc("/api/v1/tui/shell", g.HandleTUIShellWS)
	logWithTimestamp("💻 TUI Shell endpoint registered: /api/v1/tui/shell")

	// AI Hall endpoints (多 Agent 群聊)
	http.HandleFunc("/api/v1/hall/post", g.handleHallPost)
	http.HandleFunc("/api/v1/hall/upload", g.handleHallUpload)
	http.HandleFunc("/api/v1/hall/files/", g.handleHallFileDownload)
	http.HandleFunc("/api/v1/hall/topics", g.handleHallTopics)
	http.HandleFunc("/api/v1/hall/messages", g.handleHallMessages)
	http.HandleFunc("/api/v1/hall/poll", g.handleHallPoll)
	http.HandleFunc("/api/v1/hall/clear", g.handleHallClear)
	http.HandleFunc("/api/v1/hall/rename-topic", g.handleHallRenameTopic)
	// Phase 4: 新功能
	http.HandleFunc("/api/v1/hall/react", g.handleHallReact)
	http.HandleFunc("/api/v1/hall/pin", g.handleHallPin)
	http.HandleFunc("/api/v1/hall/pinned", g.handleHallPinned)
	http.HandleFunc("/api/v1/hall/edit", g.handleHallEdit)
	http.HandleFunc("/api/v1/hall/delete", g.handleHallDelete)
	http.HandleFunc("/api/v1/hall/online", g.handleHallOnline)
	http.HandleFunc("/api/v1/hall/online-list", g.handleHallOnlineList)
	http.HandleFunc("/api/v1/hall/typing", g.handleHallTyping)
	http.HandleFunc("/api/v1/hall/typing-list", g.handleHallTypingList)
	http.HandleFunc("/api/v1/hall/stats", g.handleHallStats)
	logWithTimestamp("🏛️ AI Hall endpoints registered: /api/v1/hall/*")

	// Ollama 本地模型对话
	http.HandleFunc("/api/v1/ollama/status", g.handleOllamaStatus)
	http.HandleFunc("/api/v1/ollama/start", g.handleOllamaStart)
	http.HandleFunc("/api/v1/ollama/models", g.handleOllamaModels)
	http.HandleFunc("/api/v1/ollama/chat", g.handleOllamaChat)
	logWithTimestamp("🦙 Ollama endpoints registered: /api/v1/ollama/*")

	// OCR 文字识别
	http.HandleFunc("/api/v1/ocr", g.handleOCR)
	http.HandleFunc("/api/v1/ocr/stats", g.handleOCRStats)
	logWithTimestamp("📝 OCR endpoints registered: /api/v1/ocr/*")

	// 对话历史 Git 管理
	http.HandleFunc("/api/v1/chat/save", g.handleChatSave)
	http.HandleFunc("/api/v1/chat/history", g.handleChatHistory)
	http.HandleFunc("/api/v1/chat/sessions", g.handleChatSessions)
	logWithTimestamp("📝 Chat history endpoints registered: /api/v1/chat/*")

	// ARC-AI-NET 集群广播 + 全量拓扑
	http.HandleFunc("/api/v1/cluster/broadcast", g.handleBroadcast)
	logWithTimestamp("📡 ARC-AI-NET broadcast registered: /api/v1/cluster/broadcast")
	http.HandleFunc("/api/v1/cluster/topology", g.handleTopologySync)
	logWithTimestamp("📡 ARC-AI-NET topology sync registered: /api/v1/cluster/topology")

	// 分布式共享记忆层（SPEC-DMEM-001 Phase 1）
	http.HandleFunc("/api/v1/memory/sync", g.handleMemorySync)
	http.HandleFunc("/api/v1/memory/search", g.handleMemorySearch)
	http.HandleFunc("/api/v1/memory/recall", g.handleMemoryRecall)
	http.HandleFunc("/api/v1/memory/stats", g.handleMemoryStats)
	http.HandleFunc("/api/v1/memory/list", g.handleMemoryList)
	http.HandleFunc("/api/v1/memory/delete", g.handleMemoryDelete)
	http.HandleFunc("/api/v1/memory/tags", g.handleMemoryTags)
	http.HandleFunc("/memory", g.handleMemoryPage)
	logWithTimestamp("🧠 Distributed Memory endpoints registered: /api/v1/memory/*")

	// ── 知识共享 API (KSP-001) ──
	http.HandleFunc("/api/v1/knowledge/put", g.handleKnowledgePut)
	http.HandleFunc("/api/v1/knowledge/query", g.handleKnowledgeQuery)
	http.HandleFunc("/api/v1/knowledge/sync", g.handleKnowledgeSync)
	http.HandleFunc("/api/v1/knowledge/stats", g.handleKnowledgeStats)
	logWithTimestamp("📚 Knowledge Sharing API registered: /api/v1/knowledge/*")

	// Dashboard static files (if directory provided)
	if len(dashboardDir) > 0 && dashboardDir[0] != "" {
		fs := http.FileServer(http.Dir(dashboardDir[0]))
		http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			// Don't intercept API/WS paths
			if strings.HasPrefix(r.URL.Path, "/api/") || strings.HasPrefix(r.URL.Path, "/ws/") {
				http.NotFound(w, r)
				return
			}
			fs.ServeHTTP(w, r)
		})
		logWithTimestamp("📂 Dashboard static files: %s", dashboardDir[0])
	}

	logWithTimestamp("🌐 ComputeHub Gateway listening on :%d", port)
	if err := http.ListenAndServe(fmt.Sprintf(":%d", port), AuthMiddleware(http.DefaultServeMux)); err != nil {
		logWithTimestamp("Fatal Gateway Error: %v", err)
	}
}

// ServeWithServer is like Serve but returns *http.Server for graceful shutdown.
// This is the preferred method for production use.
func (g *OpcGateway) ServeWithServer(port int, dashboardDir ...string) *http.Server {
	// Register all routes (same logic as Serve)
	http.HandleFunc("/api/dispatch", g.handleDispatch)
	http.HandleFunc("/api/health", g.handleHealth)
	http.HandleFunc("/api/status", g.handleStatus)

	http.HandleFunc("/api/v1/nodes/register", g.handleNodeRegister)
	http.HandleFunc("/api/v1/nodes/unregister", g.handleNodeUnregister)
	http.HandleFunc("/api/v1/nodes/heartbeat", g.handleNodeHeartbeat)
	http.HandleFunc("/api/v1/nodes/list", g.handleNodeList)
	http.HandleFunc("/api/v1/nodes/metrics", g.handleNodeMetrics)
	http.HandleFunc("/api/v1/nodes/stats", g.handleNodesStats)
	// Agent Registry (AI agent discovery)
	http.HandleFunc("/api/v1/agents/register", g.handleAgentRegister)
	http.HandleFunc("/api/v1/agents/heartbeat", g.handleAgentHeartbeat)
	http.HandleFunc("/api/v1/agents/unregister", g.handleAgentUnregister)
	http.HandleFunc("/api/v1/agents/list", g.handleAgentList)
	http.HandleFunc("/api/v1/agents/get", g.handleAgentGet)
	http.HandleFunc("/api/v1/openclaw/status", g.handleOpenClawStatus)
	http.HandleFunc("/api/v1/tasks/submit", g.handleTaskSubmit)
	http.HandleFunc("/api/v1/tasks/result", g.handleTaskResult)
	http.HandleFunc("/api/v1/tasks/cancel", g.handleTaskCancel)
	http.HandleFunc("/api/v1/tasks/list", g.handleTaskList)
	http.HandleFunc("/api/v1/tasks/detail", g.handleTaskDetail)
	http.HandleFunc("/api/v1/tasks/poll", g.handleTaskPoll)
	http.HandleFunc("/api/v1/tasks/progress", g.handleTaskProgress)

	// Prometheus metrics endpoint
	http.HandleFunc("/metrics", prometheus.MetricsHandler(g.Metrics.Registry))

	// Video generation endpoints (worker built-in video pipeline)
	http.HandleFunc("/api/v1/video/generate", g.handleVideoGenerate)
	http.HandleFunc("/api/v1/video/progress", g.handleVideoProgress)
	http.HandleFunc("/api/v1/video/list", g.handleVideoList)
	logWithTimestamp("🎬 Video endpoints registered: /api/v1/video/*")

	// File download endpoint (self-bootstrap transport for workers)
	http.HandleFunc("/api/v1/download", g.handleFileDownload)
	logWithTimestamp("📦 Download endpoint registered: /api/v1/download")
	// Upgrade check endpoint (worker auto-update)
	http.HandleFunc("/api/v1/upgrade/check", g.handleUpgradeCheck)
	http.HandleFunc("/api/v1/upgrade/config", g.handleUpgradeConfig)
	http.HandleFunc("/api/v1/upgrade/checksum", g.handleUpgradeChecksum)
	logWithTimestamp("🔄 Upgrade endpoints registered: /api/v1/upgrade/*")

	// ── 银河计划 Phase 2: 任务智能分配 ──
	http.HandleFunc("/api/v1/scheduler/schedule", g.handleSchedule)
	http.HandleFunc("/api/v1/scheduler/stats", g.handleSchedulerStats)
	logWithTimestamp("🎯 Scheduler endpoints registered: /api/v1/scheduler/*")

	// ── 银河计划 Phase 2: 进度跟踪系统 ──
	http.HandleFunc("/api/v1/tracker/track", g.handleTaskTrack)
	http.HandleFunc("/api/v1/tracker/query", g.handleTaskTrackerQuery)
	logWithTimestamp("📊 Task tracker endpoints registered: /api/v1/tracker/*")

	// ── 银河计划 Phase 2: 安全审计 ──
	http.HandleFunc("/api/v1/audit/log", g.handleAuditLog)
	http.HandleFunc("/api/v1/audit/query", g.handleAuditQuery)
	http.HandleFunc("/api/v1/audit/stats", g.handleAuditStats)
	logWithTimestamp("🔒 Audit endpoints registered: /api/v1/audit/*")

	// ── 银河计划 Phase 1B: TriggerEngine 触发引擎 ──
	http.HandleFunc("/api/v1/trigger/rules", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			if r.URL.Query().Get("id") != "" {
				g.handleTriggerGet(w, r)
			} else {
				g.handleTriggerList(w, r)
			}
		case http.MethodPost:
			g.handleTriggerAdd(w, r)
		case http.MethodPut:
			g.handleTriggerUpdate(w, r)
		case http.MethodDelete:
			g.handleTriggerDelete(w, r)
		default:
			http.Error(w, `{"error":"Method not allowed"}`, http.StatusMethodNotAllowed)
		}
	})
	http.HandleFunc("/api/v1/trigger/rules/toggle", g.handleTriggerToggle)
	http.HandleFunc("/api/v1/trigger/event", g.handleTriggerEvent)
	http.HandleFunc("/api/v1/trigger/stats", g.handleTriggerStats)
	http.HandleFunc("/trigger", g.handleTriggerPage)
	logWithTimestamp("⚡ TriggerEngine endpoints registered: /api/v1/trigger/*")

	// ── 银河计划 Phase 3: 自主进化 ──
	http.HandleFunc("/api/v1/galaxy/phase3/stats", g.handlePhase3Stats)
	http.HandleFunc("/api/v1/galaxy/phase3/self-learning", g.handlePhase3SelfLearning)
	http.HandleFunc("/api/v1/galaxy/phase3/innovation", g.handlePhase3Innovation)
	http.HandleFunc("/api/v1/galaxy/phase3/cross-domain", g.handlePhase3CrossDomain)
	http.HandleFunc("/api/v1/galaxy/phase3/delegate", g.handlePhase3SelfOrg)
	http.HandleFunc("/api/v1/galaxy/phase3/summary", g.handlePhase3Summary)
	// ── Phase 3 事件流 + 控制 ──
	http.HandleFunc("/api/v1/galaxy/phase3/event", g.handlePhase3Event)    // POST — Worker 推送事件
	http.HandleFunc("/api/v1/galaxy/phase3/events", g.handlePhase3Events)  // GET — 获取事件列表
	http.HandleFunc("/api/v1/galaxy/phase3/control", g.handlePhase3Control) // POST — 控制模式/间隔
	http.HandleFunc("/phase3", g.handlePhase3Page)                         // GET — 监控页面
	logWithTimestamp("🌌 Galaxy Phase 3 endpoints registered: /api/v1/galaxy/phase3/*")

	// WebSocket Hub endpoint（SPEC-WS-001）
	http.HandleFunc("/api/v1/ws", g.wsHub.HandleWSUpgrade)
	logWithTimestamp("📡 WebSocket Hub registered: /api/v1/ws")

	// WS Hub 健康检查
	http.HandleFunc("/api/v1/ws/health", g.handleWSHealth)
	logWithTimestamp("📡 WS Health endpoint registered: /api/v1/ws/health")

	// TUI Shell WS endpoint（交互式远程终端）
	http.HandleFunc("/api/v1/tui/shell", g.HandleTUIShellWS)
	logWithTimestamp("💻 TUI Shell endpoint registered: /api/v1/tui/shell")

	// AI Hall endpoints (多 Agent 群聊)
	http.HandleFunc("/api/v1/hall/post", g.handleHallPost)
	http.HandleFunc("/api/v1/hall/upload", g.handleHallUpload)
	http.HandleFunc("/api/v1/hall/files/", g.handleHallFileDownload)
	http.HandleFunc("/api/v1/hall/topics", g.handleHallTopics)
	http.HandleFunc("/api/v1/hall/messages", g.handleHallMessages)
	http.HandleFunc("/api/v1/hall/poll", g.handleHallPoll)
	http.HandleFunc("/api/v1/hall/clear", g.handleHallClear)
	http.HandleFunc("/api/v1/hall/rename-topic", g.handleHallRenameTopic)
	// Phase 4: 新功能
	http.HandleFunc("/api/v1/hall/react", g.handleHallReact)
	http.HandleFunc("/api/v1/hall/pin", g.handleHallPin)
	http.HandleFunc("/api/v1/hall/pinned", g.handleHallPinned)
	http.HandleFunc("/api/v1/hall/edit", g.handleHallEdit)
	http.HandleFunc("/api/v1/hall/delete", g.handleHallDelete)
	http.HandleFunc("/api/v1/hall/online", g.handleHallOnline)
	http.HandleFunc("/api/v1/hall/online-list", g.handleHallOnlineList)
	http.HandleFunc("/api/v1/hall/typing", g.handleHallTyping)
	http.HandleFunc("/api/v1/hall/typing-list", g.handleHallTypingList)
	http.HandleFunc("/api/v1/hall/stats", g.handleHallStats)
	// 圆桌讨论
	http.HandleFunc("/api/v1/hall/roundtable/start", g.handleRoundTableStart)
	http.HandleFunc("/api/v1/hall/roundtable/stop", g.handleRoundTableStop)
	http.HandleFunc("/api/v1/hall/roundtable/status", g.handleRoundTableStatus)
	http.HandleFunc("/api/v1/hall/roundtable/history", g.handleRoundTableHistory)
	http.HandleFunc("/api/v1/hall/roundtable/interval", g.handleRoundTableInterval)
	http.HandleFunc("/api/v1/hall/roundtable/now", g.handleRoundTableNow)
	logWithTimestamp("🏛️ AI Hall endpoints registered: /api/v1/hall/*")

	// Phase 3: 专家 Agent 端点
	http.HandleFunc("/api/v1/experts/list", g.handleExpertList)
	logWithTimestamp("🏛️ Phase 3: Expert endpoints registered: /api/v1/experts/*")

	// Agent Direct Message（银河计划 Phase 2 — 2026-06-30）
	http.HandleFunc("/api/v1/agent/send", g.handleAgentSend)
	http.HandleFunc("/api/v1/agent/send/result", g.handleAgentSendResult)
	logWithTimestamp("📡 Agent DM endpoints registered: /api/v1/agent/send*")

	// 初始化交流大厅持久化
	exeDir := filepath.Dir(os.Args[0])
	InitHallData(exeDir)
	logWithTimestamp("🏛️ AI Hall data persistence: %s", hallDataFile)

	// Ollama 本地模型对话
	http.HandleFunc("/api/v1/ollama/status", g.handleOllamaStatus)
	http.HandleFunc("/api/v1/ollama/start", g.handleOllamaStart)
	http.HandleFunc("/api/v1/ollama/models", g.handleOllamaModels)
	http.HandleFunc("/api/v1/ollama/chat", g.handleOllamaChat)
	logWithTimestamp("🦙 Ollama endpoints registered: /api/v1/ollama/*")

	// OCR 文字识别
	http.HandleFunc("/api/v1/ocr", g.handleOCR)
	http.HandleFunc("/api/v1/ocr/stats", g.handleOCRStats)
	logWithTimestamp("📝 OCR endpoints registered: /api/v1/ocr/*")

	// 对话历史 Git 管理
	http.HandleFunc("/api/v1/chat/save", g.handleChatSave)
	http.HandleFunc("/api/v1/chat/history", g.handleChatHistory)
	http.HandleFunc("/api/v1/chat/sessions", g.handleChatSessions)
	logWithTimestamp("📝 Chat history endpoints registered: /api/v1/chat/*")

	// ARC-AI-NET 集群广播 + 全量拓扑
	http.HandleFunc("/api/v1/cluster/broadcast", g.handleBroadcast)
	logWithTimestamp("📡 ARC-AI-NET broadcast registered: /api/v1/cluster/broadcast")
	http.HandleFunc("/api/v1/cluster/topology", g.handleTopologySync)
	logWithTimestamp("📡 ARC-AI-NET topology sync registered: /api/v1/cluster/topology")

	// 分布式共享记忆层（SPEC-DMEM-001 Phase 1）
	http.HandleFunc("/api/v1/memory/sync", g.handleMemorySync)
	http.HandleFunc("/api/v1/memory/search", g.handleMemorySearch)
	http.HandleFunc("/api/v1/memory/recall", g.handleMemoryRecall)
	http.HandleFunc("/api/v1/memory/stats", g.handleMemoryStats)
	http.HandleFunc("/api/v1/memory/list", g.handleMemoryList)
	http.HandleFunc("/api/v1/memory/delete", g.handleMemoryDelete)
	http.HandleFunc("/api/v1/memory/tags", g.handleMemoryTags)
	http.HandleFunc("/memory", g.handleMemoryPage)
	logWithTimestamp("🧠 Distributed Memory endpoints registered: /api/v1/memory/*")

	// ── 知识共享 API (KSP-001) ──
	http.HandleFunc("/api/v1/knowledge/put", g.handleKnowledgePut)
	http.HandleFunc("/api/v1/knowledge/query", g.handleKnowledgeQuery)
	http.HandleFunc("/api/v1/knowledge/sync", g.handleKnowledgeSync)
	http.HandleFunc("/api/v1/knowledge/stats", g.handleKnowledgeStats)
	logWithTimestamp("📚 Knowledge Sharing API registered: /api/v1/knowledge/*")

	// LLM Proxy endpoint (for workers without internet access)
	http.HandleFunc("/api/v1/llm/chat/completions", g.handleLlmProxy)
	logWithTimestamp("🌉 LLM Proxy endpoint registered: /api/v1/llm/chat/completions")

	// Agent Think endpoint (Layer 2: natural language task execution)
	if g.Agent != nil {
		http.HandleFunc("/api/v1/agent/think", g.handleAgentThink)
		http.HandleFunc("/api/v1/agent/stream", g.handleAgentStream)
		http.HandleFunc("/ai", g.handleAIPage)
		logWithTimestamp("🧠 Agent Think endpoint registered: /api/v1/agent/think")
		logWithTimestamp("🌊 Agent Stream endpoint registered: /api/v1/agent/stream")
		logWithTimestamp("🤖 AI Chat page: /ai")
	}

	// Dashboard static files (if directory provided)
	if len(dashboardDir) > 0 && dashboardDir[0] != "" {
		fs := http.FileServer(http.Dir(dashboardDir[0]))
		http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			if strings.HasPrefix(r.URL.Path, "/api/") || strings.HasPrefix(r.URL.Path, "/ws/") {
				http.NotFound(w, r)
				return
			}
			fs.ServeHTTP(w, r)
		})
		logWithTimestamp("📂 Dashboard static files: %s", dashboardDir[0])
	}

	srv := &http.Server{
		Addr:    fmt.Sprintf(":%d", port),
		Handler: nil, // use DefaultServeMux
	}

	go func() {
		logWithTimestamp("🌐 ComputeHub Gateway listening on :%d", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logWithTimestamp("Fatal Gateway Error: %v", err)
		}
	}()

	return srv
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

func (g *OpcGateway) handleNodeRegister(w http.ResponseWriter, r *http.Request) {
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

	var reg kernel.NodeRegister
	if err := json.Unmarshal(body, &reg); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	// Use Gateway-observed IP (from TCP connection) instead of worker self-report,
	// which would be a NAT-private IP for remote workers.
	reg.IPAddress = extractClientIP(r)

	reg.RegisteredAt = time.Now()
	if reg.Status == "" {
		reg.Status = "online"
	}
	if reg.Region == "" {
		reg.Region = "unknown"
	}

	// Warn on node ID length — Windows NetBIOS limits hostnames to 15 chars
	if len(reg.NodeID) > 15 {
		logWithTimestamp("⚠️ Node ID too long (%d chars): %q — may be truncated on Windows. Use --node-id with ≤15 chars",
			len(reg.NodeID), reg.NodeID)
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeRegister, &reg)
	resp := <-respChan

	// ARC-NET: 广播节点上线事件
	if resp.Success {
		regCopy := reg // copy to avoid race
		go g.BroadcastNodeEvent(EventTypeNodeJoin, &regCopy)
	}

	// 审计日志：节点注册
	g.auditLog(reg.NodeID, AuditNodeRegister, "node", reg.NodeID,
		fmt.Sprintf("region=%s gpu=%s", reg.Region, reg.GPUType), resp.Success)

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleNodeUnregister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		NodeID string `json:"node_id"`
	}
	body, err := io.ReadAll(r.Body)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: "Failed to read request body"})
		return
	}
	defer r.Body.Close()

	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.NodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required"})
		return
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeUnregister, req.NodeID)
	resp := <-respChan

	// ⚠️ 同步清理 visualizer GlobalPowerMap — 无论 kernel 找没找到
	// 因为 kernel 和 visualizer 是独立的节点存储，删除必须同步
	if g.unregisterSimFallback != nil {
		if fbErr := g.unregisterSimFallback(req.NodeID); fbErr == nil {
			logWithTimestamp("[Gateway] 🗑️ Visualizer data cleaned for node %s", req.NodeID)
		}
	}

	errStr := ""
	if resp.Error != nil {
		errStr = resp.Error.Error()
	}

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    errStr,
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleNodeHeartbeat(w http.ResponseWriter, r *http.Request) {
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

	var heartbeat map[string]interface{}
	if err := json.Unmarshal(body, &heartbeat); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	nodeID, _ := heartbeat["node_id"].(string)
	if nodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required for heartbeat"})
		return
	}

	// Inject the Gateway-observed IP into heartbeat payload so kernel can
	// update it even for nodes that were registered before the IP-fix was deployed.
	heartbeat["ip_address"] = extractClientIP(r)

	// Check if node exists in kernel
	kernelRespChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionNodeHeartbeat, heartbeat)
	kernelResp := <-kernelRespChan

	// Update Scheduler metrics
	if g.Scheduler != nil {
		g.Scheduler.UpdateNodeHeartbeat(nodeID, 15, 45.0, 62.0, 24.0)
	}

	g.sendResponse(w, Response{
		Success:  kernelResp.Success,
		Data:     kernelResp.Data,
		Error:    fmt.Sprintf("%v", kernelResp.Error),
		Duration: kernelResp.Duration,
	})
}

func (g *OpcGateway) handleNodeList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	nodeData := make([]map[string]interface{}, 0, len(nodes))

	for _, node := range nodes {
		ipAddr := ""
		if node.Register.IPAddress != "" {
			ipAddr = node.Register.IPAddress
		}
		nodeData = append(nodeData, map[string]interface{}{
			"node_id":       node.Register.NodeID,
			"node_type":     node.Register.NodeType,
			"platform":      node.Register.Platform,
			"region":        node.Register.Region,
			"gpu_type":      node.Register.GPUType,
			"status":        node.Register.Status,
			"version":       node.Register.Version,
			"ip_address":    ipAddr, // Gateway-observed source IP at registration
			"registered_at": node.Register.RegisteredAt.Format(time.RFC3339),
			"active_tasks":     node.Metrics.ActiveTasks,
			"cpu_utilization":  node.Metrics.CPUUtilization,
			"gpu_utilization":  node.Metrics.GPUUtilization,
			"temperature":      node.Metrics.Temperature,
			"memory_used_gb":   node.Metrics.MemoryUsedGB,
		})
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    nodeData,
	})
}

func (g *OpcGateway) handleNodeMetrics(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodeID := r.URL.Query().Get("node_id")
	if nodeID == "" {
		g.sendResponse(w, Response{Success: false, Error: "node_id is required"})
		return
	}

	metrics, err := g.Kernel.NodeMgr.GetNodeMetrics(nodeID)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("%v", err)})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    metrics,
	})
}

// handleNodesStats returns aggregated statistics for all nodes
func (g *OpcGateway) handleNodesStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()

	// Aggregate statistics
	onlineCount := 0
	offlineCount := 0
	byRegion := make(map[string]int)
	byType := make(map[string]int)
	byVersion := make(map[string]int)
	totalTasks := 0
	activeTasks := 0
	totalCPU := 0.0
	totalMem := 0.0

	nodeList := make([]map[string]interface{}, 0, len(nodes))

	for _, node := range nodes {
		nodeData := map[string]interface{}{
			"node_id":         node.Register.NodeID,
			"status":          node.Register.Status,
			"version":          node.Register.Version,
			"platform":         node.Register.Platform,
			"region":           node.Register.Region,
			"gpu_type":         node.Register.GPUType,
			"ip_address":       node.Register.IPAddress,
			"registered_at":    node.Register.RegisteredAt,
			"active_tasks":     node.Metrics.ActiveTasks,
			"total_tasks":      node.Metrics.TotalTasks,
			"cpu_utilization":  node.Metrics.CPUUtilization,
			"memory_used_gb":   node.Metrics.MemoryUsedGB,
		}
		nodeList = append(nodeList, nodeData)

		if node.Register.Status == "online" {
			onlineCount++
		} else {
			offlineCount++
		}

		// By region
		region := node.Register.Region
		if region == "" {
			region = "unknown"
		}
		byRegion[region]++

		// By type
		nodeType := "cpu"
		if node.Register.GPUType != "" {
			nodeType = "gpu"
		}
		byType[nodeType]++

		// By version
		ver := node.Register.Version
		if ver == "" {
			ver = "unknown"
		}
		byVersion[ver]++

		// Totals
		totalTasks += node.Metrics.TotalTasks
		activeTasks += node.Metrics.ActiveTasks
		totalCPU += node.Metrics.CPUUtilization
		totalMem += node.Metrics.MemoryUsedGB
	}

	stats := map[string]interface{}{
		"total_nodes":   len(nodes),
		"online_nodes":  onlineCount,
		"offline_nodes": offlineCount,
		"total_tasks":   totalTasks,
		"active_tasks":  activeTasks,
		"avg_cpu_util":  totalCPU / float64(max(len(nodes), 1)),
		"avg_mem_used":  totalMem / float64(max(len(nodes), 1)),
		"by_region":      byRegion,
		"by_type":        byType,
		"by_version":     byVersion,
		"nodes":          nodeList,
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    stats,
	})
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func (g *OpcGateway) handleTaskSubmit(w http.ResponseWriter, r *http.Request) {
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

	var task kernel.TaskSubmit
	if err := json.Unmarshal(body, &task); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	// Support node, node_id, and assigned_node — map everything to AssignedNode
	// Priority: node > node_id > assigned_node
	if task.Node != "" {
		if task.AssignedNode == "" {
			task.AssignedNode = task.Node
		}
		if task.NodeID == "" {
			task.NodeID = task.Node
		}
	}
	if task.NodeID != "" && task.AssignedNode == "" {
		task.AssignedNode = task.NodeID
	}
	if task.AssignedNode != "" && task.NodeID == "" {
		task.NodeID = task.AssignedNode
	}

	// If only payload is provided, use it as the command
	if task.Command == "" && task.Payload != "" {
		task.Command = task.Payload
	}

	task.SubmittedAt = time.Now()
	if task.Priority == 0 {
		task.Priority = 5
	}
	if task.SourceType == "" {
		task.SourceType = "api"
	}
	if task.SubmittedBy == "" {
		task.SubmittedBy = "gateway"
	}
	if task.MaxRetries == 0 {
		task.MaxRetries = 3
	}

	// Record task submission in Prometheus metrics
	if g.Metrics != nil {
		g.MetricsCollector.RecordTaskSubmission()
	}

	// 银河计划 Phase 2: 创建任务进度跟踪
	if g.TaskTracker != nil {
		g.TaskTracker.CreateTask(task.TaskID, task.AssignedNode)
		g.TaskTracker.UpdateStage(task.TaskID, StageQueued, "submitted",
			fmt.Sprintf("任务已提交: %s", task.Command))
	}

	// If composer is available, decompose complex tasks
	if g.Composer != nil && !isSimpleTask(task.Command) {
		logWithTimestamp("[Composer] 🧠 Complex task detected, decomposing: %s", task.Command)
		go func(cmd string, tid string) {
			result, err := g.Composer.Run(composer.TaskComposerInput{
				TaskID:       tid,
				OriginalTask: cmd,
			})
			if err != nil {
				logWithTimestamp("[Composer] ❌ Decompose failed: %v", err)
			} else {
				successCount := 0
				for _, r := range result.Results {
					if r.Success {
						successCount++
					}
				}
				logWithTimestamp("[Composer] ✅ Task %s: %d subtasks, %d success, final=%d chars",
					tid, len(result.Subtasks), successCount, len(result.FinalResult))
			}
		}(task.Command, task.TaskID)
	} else if g.Composer != nil {
		logWithTimestamp("[Composer] ➡️ Simple command, direct dispatch: %s", task.Command)
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionTaskSubmit, &task)
	resp := <-respChan

	// Phase 3: 任务 WS 推送 — 如果任务指定了目标节点，尝试 WS 推送
	// 推送成功 → Worker 立即收到，无需 HTTP 轮询
	// 推送失败 → Worker 通过 HTTP poll 兜底（向后兼容）
	if resp.Success && task.AssignedNode != "" && g.wsHub != nil {
		pollItem := &TaskPollItem{
			TaskID:     task.TaskID,
			Command:    task.Command,
			Timeout:    task.Timeout,
			Priority:   task.Priority,
			NodeID:     task.AssignedNode,
			SourceType: task.SourceType,
		}
		if g.wsHub.PushTask(task.AssignedNode, pollItem) {
			logWithTimestamp("[WS Push] 📡 任务 %s 已推送到 %s", task.TaskID, task.AssignedNode)
		} else {
			logWithTimestamp("[WS Push] ⚠️ 任务 %s WS 推送失败 (%s 不在线)，等待 HTTP poll", task.TaskID, task.AssignedNode)
		}
	}

	// 审计日志：任务提交
	g.auditLog(task.NodeID, AuditTaskSubmit, "task", task.TaskID,
		fmt.Sprintf("cmd=%s priority=%d", task.Command, task.Priority), resp.Success)

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleTaskResult(w http.ResponseWriter, r *http.Request) {
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

	var result kernel.TaskResult
	if err := json.Unmarshal(body, &result); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	// Record task completion in Prometheus metrics
	if g.Metrics != nil {
		duration, _ := time.ParseDuration(result.Duration)
		g.MetricsCollector.RecordTaskCompletion(result.Success, duration.Seconds())
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionTaskResult, &result)
	resp := <-respChan

	// 银河计划 Phase 2: 更新任务进度跟踪
	if g.TaskTracker != nil {
		if result.Success {
			g.TaskTracker.CompleteTask(result.TaskID, result.Stdout)
		} else {
			g.TaskTracker.FailTask(result.TaskID, result.Stderr)
		}
	}

	// 审计日志：任务结果
	g.auditLog(result.ExecutedOn, AuditTaskSubmit, "task", result.TaskID,
		fmt.Sprintf("success=%v duration=%s", result.Success, result.Duration), resp.Success)

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    fmt.Sprintf("%v", resp.Error),
		Duration: resp.Duration,
	})
}

func (g *OpcGateway) handleTaskList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := g.Kernel.NodeMgr.ListNodes()
	tasks := make(map[string][]map[string]interface{})

	for _, node := range nodes {
		tasks[node.Register.NodeID] = []map[string]interface{}{}
		ip := node.Register.IPAddress
		if ip == "" {
			ip = "127.0.0.1"
		}
		for taskID, ts := range node.Tasks {
			createdAt := ""
			if !ts.Created.IsZero() {
				createdAt = ts.Created.Format("15:04:05")
			} else if !ts.Task.SubmittedAt.IsZero() {
				createdAt = ts.Task.SubmittedAt.Format("15:04:05")
			}
			tasks[node.Register.NodeID] = append(tasks[node.Register.NodeID], map[string]interface{}{
				"task_id":     taskID,
				"status":      ts.Status,
				"command":     ts.Task.Command,
				"source_type": ts.Task.SourceType,
				"submitted_by": ts.Task.SubmittedBy,
				"priority":    ts.Task.Priority,
				"submitted_at": createdAt,
				"node_ip":     ip,
			})
		}
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    tasks,
	})
}

func (g *OpcGateway) handleTaskCancel(w http.ResponseWriter, r *http.Request) {
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

	var req struct {
		TaskID string `json:"task_id"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid JSON: %v", err)})
		return
	}

	if req.TaskID == "" {
		g.sendResponse(w, Response{Success: false, Error: "task_id is required"})
		return
	}

	respChan := g.Kernel.DispatchExtended("gw-"+time.Now().Format("150405"), kernel.ActionTaskCancel, req.TaskID)
	resp := <-respChan

	errStr := ""
	if resp.Error != nil {
		errStr = resp.Error.Error()
	}

	g.sendResponse(w, Response{
		Success:  resp.Success,
		Data:     resp.Data,
		Error:    errStr,
		Duration: resp.Duration,
	})
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

// ====== LLM 代理端点（Worker 节点通过 Gateway 中转调用 NewAPI） ======

// handleLlmProxy 接收 Worker 的 LLM 请求，通过 Gateway 转发到 NewAPI
// 目的：Windows 等无法访问外网的节点可以通过 Gateway 中转
func (g *OpcGateway) handleLlmProxy(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	// 读取请求体（透传 OpenAI Chat API 格式）
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, `{"error":"read body failed"}`, http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	// 注入 reasoning: false（默认关掉 thinking，调用方如需可显式传 true）
	var reqMap map[string]interface{}
	if err := json.Unmarshal(body, &reqMap); err == nil {
		if _, exists := reqMap["reasoning"]; !exists {
			reqMap["reasoning"] = false
		}
		modified, err := json.Marshal(reqMap)
		if err == nil {
			body = modified
		}
	}

	// 从 config.json → composer 读取 LLM 配置
	apiURL := g.composerAPI
	apiKey := g.composerKey
	timeout := 60
	if apiURL == "" {
		apiURL = "https://ai.zhangtuokeji.top:9090/v1"
		apiKey = "sk-28PRiilecewqbNN9G1TGHhQwML6KCa8yMtvO5HH1KzuuLKbB"
	}

	// 构造请求到上游
	targetURL := strings.TrimRight(apiURL, "/") + "/chat/completions"
	req, err := http.NewRequest("POST", targetURL, bytes.NewReader(body))
	if err != nil {
		http.Error(w, `{"error":"create upstream request failed"}`, http.StatusInternalServerError)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	// 用禁用 HTTP/2 的 transport（NewAPI proxy 的 HTTP/2 不稳定）
	transport := &http.Transport{
		TLSNextProto: make(map[string]func(authority string, c *tls.Conn) http.RoundTripper),
	}
	client := &http.Client{
		Timeout:   time.Duration(timeout) * time.Second,
		Transport: transport,
	}

	resp, err := client.Do(req)
	if err != nil {
		logWithTimestamp("[LLM Proxy] ❌ Upstream call failed: %v", err)
		http.Error(w, fmt.Sprintf(`{"error":"upstream call failed: %v"}`, err), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	// 透传状态码和头部
	for key, vals := range resp.Header {
		for _, v := range vals {
			w.Header().Add(key, v)
		}
	}
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// ====== Phase 3: Expert List Handler ======

// handleExpertList 返回所有已注册的专家 Agent 列表
func (g *OpcGateway) handleExpertList(w http.ResponseWriter, r *http.Request) {
	if g.ExpertRegistry == nil {
		g.sendResponse(w, Response{Success: false, Error: "Expert registry not initialized"})
		return
	}

	experts := g.ExpertRegistry.List()
	type expertInfo struct {
		ID          string   `json:"id"`
		Name        string   `json:"name"`
		Nickname    string   `json:"nickname"`
		Domain      string   `json:"domain"`
		Description string   `json:"description"`
		Tags        []string `json:"tags"`
	}

	list := make([]expertInfo, 0, len(experts))
	for _, e := range experts {
		list = append(list, expertInfo{
			ID:          e.ID,
			Name:        e.Name,
			Nickname:    e.Nickname,
			Domain:      e.Domain,
			Description: e.Description,
			Tags:        e.Tags,
		})
	}

	g.sendResponse(w, Response{
		Success: true,
		Data: map[string]interface{}{
			"experts": list,
			"count":   len(list),
		},
	})
}

// ====== Agent Think Handler (Layer 2) ======

// handleAgentThink 接收自然语言任务 → AI 思考 → 执行 → 回答
func (g *OpcGateway) handleAgentThink(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil {
		g.sendResponse(w, Response{
			Success: false,
			Error:   "Agent not initialized",
		})
		return
	}

	var req agent.AgentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendResponse(w, Response{
			Success: false,
			Error:   fmt.Sprintf("Invalid request body: %v", err),
		})
		return
	}

	if req.Task == "" {
		g.sendResponse(w, Response{
			Success: false,
			Error:   "task is required",
		})
		return
	}

	logWithTimestamp("[Agent] 🧠 Think request: %s (session=%s)", req.Task, req.SessionID)

	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()

	resp, err := g.Agent.Think(ctx, &req)
	if err != nil {
		logWithTimestamp("[Agent] ❌ Think failed: %v", err)
		g.sendResponse(w, Response{
			Success: false,
			Error:   fmt.Sprintf("Agent think failed: %v", err),
		})
		return
	}

	logWithTimestamp("[Agent] ✅ Think complete: %d plan steps, result=%d chars",
		len(resp.Plan), len(resp.Result))

	g.sendResponse(w, Response{
		Success: true,
		Data:    resp,
	})
}

// handleAgentStream — SSE 流式端到端对话
// 前端通过 POST 请求，后端逐步推送 thinking → plan → step → result（SSE 格式）
func (g *OpcGateway) handleAgentStream(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if g.Agent == nil {
		g.sendResponse(w, Response{Success: false, Error: "Agent not initialized"})
		return
	}

	var req agent.AgentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("Invalid request body: %v", err)})
		return
	}
	if req.Task == "" {
		g.sendResponse(w, Response{Success: false, Error: "task is required"})
		return
	}

	logWithTimestamp("[Agent] 🧠 Stream request: %s (session=%s)", req.Task, req.SessionID)

	// SSE headers
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.WriteHeader(http.StatusOK)

	flusher, ok := w.(http.Flusher)
	if !ok {
		g.sendResponse(w, Response{Success: false, Error: "streaming not supported"})
		return
	}

	// 发送 SSE 事件辅助函数
	sendSSE := func(eventType, data string) {
		fmt.Fprintf(w, "event: %s\ndata: %s\n\n", eventType, data)
		flusher.Flush()
	}

	// 心跳（每 5 秒确保连接存活）
	// ⚠️ 模型开始输出后立即停止心跳，避免 data race（两个 goroutine 同时写 ResponseWriter）
	heartbeatDone := make(chan struct{})
	firstContent := make(chan struct{}, 1)
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				fmt.Fprintf(w, ": heartbeat\n\n")
				flusher.Flush()
			case <-firstContent:
				return
			case <-heartbeatDone:
				return
			}
		}
	}()
	defer close(heartbeatDone)

	// 流式回调 → SSE 事件
	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()

	hasSentContent := false
	cb := func(ev agent.StreamEvent) {
		// 第一个内容事件到达时停止心跳
		if !hasSentContent {
			hasSentContent = true
			close(firstContent)
		}
		switch ev.Type {
		case "thought_chunk":
			sendSSE("thought", ev.Data)
		case "step_start":
			sendSSE("step", ev.Data)
		case "step_chunk":
			sendSSE("step_output", ev.Data)
		case "step_done":
			sendSSE("step_end", ev.Data)
		case "result_chunk":
			sendSSE("result", ev.Data)
		case "result":
			sendSSE("result", ev.Data)
		case "thinking":
			sendSSE("status", ev.Data)
		case "error":
			sendSSE("error", ev.Data)
		case "done":
			sendSSE("done", "")
		default:
			js, _ := json.Marshal(ev)
			if js != nil {
				sendSSE(ev.Type, string(js))
			}
		}
	}

	_, err := g.Agent.ThinkStream(ctx, &req, cb)
	if err != nil {
		logWithTimestamp("[Agent] ❌ Stream failed: %v", err)
		sendSSE("error", fmt.Sprintf("内部错误: %v", err))
		sendSSE("done", "")
		return
	}

	logWithTimestamp("[Agent] ✅ Stream complete: session=%s", req.SessionID)
}

// handleAIPage — 独立 AI 对话页面（从 web/ai.html 读取）
func (g *OpcGateway) handleAIPage(w http.ResponseWriter, r *http.Request) {
	// 从 web/ai.html 读取页面
	webDir := filepath.Join(filepath.Dir(os.Args[0]), "..", "web")
	if _, err := os.Stat(webDir); os.IsNotExist(err) {
		webDir = "web"
	}
	htmlPath := filepath.Join(webDir, "ai.html")
	
	html, err := os.ReadFile(htmlPath)
	if err != nil {
		http.Error(w, "⚠️ 页面文件未找到: "+htmlPath, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(html)
}

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


