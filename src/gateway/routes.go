package gateway

import (
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/computehub/opc/src/prometheus"
)

// registerRoutes registers all API routes on http.DefaultServeMux.
// Both Serve() and ServeWithServer() call this to avoid duplication.
func (g *OpcGateway) registerRoutes(port int, dashboardDir ...string) {
	// ── Legacy endpoints (backward compatible) ──
	http.HandleFunc("/api/dispatch", g.handleDispatch)
	http.HandleFunc("/api/health", g.handleHealth)
	http.HandleFunc("/api/status", g.handleStatus)

	// ── 深度健康检查 ──
	http.HandleFunc("/api/v1/health/detailed", g.handleHealthDetailed)
	logWithTimestamp("🩺 Detailed health endpoint registered: /api/v1/health/detailed")

	// ── ComputeHub API: Nodes ──
	http.HandleFunc("/api/v1/nodes/register", g.handleNodeRegister)
	http.HandleFunc("/api/v1/nodes/unregister", g.handleNodeUnregister)
	http.HandleFunc("/api/v1/nodes/heartbeat", g.handleNodeHeartbeat)
	http.HandleFunc("/api/v1/nodes/list", g.handleNodeList)
	http.HandleFunc("/api/v1/nodes/metrics", g.handleNodeMetrics)
	http.HandleFunc("/api/v1/nodes/stats", g.handleNodesStats)

	// ── ComputeHub API: Tasks ──
	http.HandleFunc("/api/v1/tasks/submit", g.handleTaskSubmit)
	http.HandleFunc("/api/v1/tasks/result", g.handleTaskResult)
	http.HandleFunc("/api/v1/tasks/cancel", g.handleTaskCancel)
	http.HandleFunc("/api/v1/tasks/list", g.handleTaskList)
	http.HandleFunc("/api/v1/tasks/detail", g.handleTaskDetail)
	http.HandleFunc("/api/v1/tasks/poll", g.handleTaskPoll)
	http.HandleFunc("/api/v1/tasks/progress", g.handleTaskProgress) // streaming output

	// ── Agent Registry (AI agent discovery) ──
	http.HandleFunc("/api/v1/agents/register", g.handleAgentRegister)
	http.HandleFunc("/api/v1/agents/heartbeat", g.handleAgentHeartbeat)
	http.HandleFunc("/api/v1/agents/unregister", g.handleAgentUnregister)
	http.HandleFunc("/api/v1/agents/list", g.handleAgentList)
	http.HandleFunc("/api/v1/agents/get", g.handleAgentGet)
	logWithTimestamp("🤖 Agent Registry endpoints registered: /api/v1/agents/*")

	// ── OpenClaw 管理 ──
	http.HandleFunc("/api/v1/openclaw/status", g.handleOpenClawStatus)
	logWithTimestamp("🩺 OpenClaw status endpoint registered: /api/v1/openclaw/status")

	// ── Prometheus metrics ──
	http.HandleFunc("/metrics", prometheus.MetricsHandler(g.Metrics.Registry))
	logWithTimestamp("📈 Prometheus /metrics endpoint registered")

	// ── Video generation (worker built-in video pipeline) ──
	http.HandleFunc("/api/v1/video/generate", g.handleVideoGenerate)
	http.HandleFunc("/api/v1/video/progress", g.handleVideoProgress)
	http.HandleFunc("/api/v1/video/list", g.handleVideoList)
	logWithTimestamp("🎬 Video endpoints registered: /api/v1/video/*")

	// ── File download (self-bootstrap transport for workers) ──
	http.HandleFunc("/api/v1/download", g.handleFileDownload)
	logWithTimestamp("📦 Download endpoint registered: /api/v1/download")

	// ── Upgrade check (worker auto-update) ──
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
	http.HandleFunc("/api/v1/galaxy/phase3/event", g.handlePhase3Event)    // POST — Worker 推送事件
	http.HandleFunc("/api/v1/galaxy/phase3/events", g.handlePhase3Events)  // GET — 获取事件列表
	http.HandleFunc("/api/v1/galaxy/phase3/control", g.handlePhase3Control) // POST — 控制模式/间隔
	http.HandleFunc("/phase3", g.handlePhase3Page)                         // GET — 监控页面
	logWithTimestamp("🌌 Galaxy Phase 3 endpoints registered: /api/v1/galaxy/phase3/*")

	// ── WebSocket Hub (SPEC-WS-001) ──
	http.HandleFunc("/api/v1/ws", g.wsHub.HandleWSUpgrade)
	logWithTimestamp("📡 WebSocket Hub registered: /api/v1/ws")
	http.HandleFunc("/api/v1/ws/health", g.handleWSHealth)
	logWithTimestamp("📡 WS Health endpoint registered: /api/v1/ws/health")

	// ── TUI Shell WS (交互式远程终端) ──
	http.HandleFunc("/api/v1/tui/shell", g.HandleTUIShellWS)
	logWithTimestamp("💻 TUI Shell endpoint registered: /api/v1/tui/shell")

	// ── AI Hall 多 Agent 群聊 ──
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

	// ── Phase 3: 专家 Agent 端点 ──
	http.HandleFunc("/api/v1/experts/list", g.handleExpertList)
	logWithTimestamp("🏛️ Phase 3: Expert endpoints registered: /api/v1/experts/*")

	// ── Agent Direct Message（银河计划 Phase 2 — 2026-06-30） ──
	http.HandleFunc("/api/v1/agent/send", g.handleAgentSend)
	http.HandleFunc("/api/v1/agent/send/result", g.handleAgentSendResult)
	logWithTimestamp("📡 Agent DM endpoints registered: /api/v1/agent/send*")

	// ── 初始化交流大厅持久化 ──
	exeDir := filepath.Dir(os.Args[0])
	InitHallData(exeDir)
	logWithTimestamp("🏛️ AI Hall data persistence: %s", hallDataFile)

	// ── Ollama 本地模型对话 ──
	http.HandleFunc("/api/v1/ollama/status", g.handleOllamaStatus)
	http.HandleFunc("/api/v1/ollama/start", g.handleOllamaStart)
	http.HandleFunc("/api/v1/ollama/models", g.handleOllamaModels)
	http.HandleFunc("/api/v1/ollama/chat", g.handleOllamaChat)
	logWithTimestamp("🦙 Ollama endpoints registered: /api/v1/ollama/*")

	// ── OCR 文字识别 ──
	http.HandleFunc("/api/v1/ocr", g.handleOCR)
	http.HandleFunc("/api/v1/ocr/stats", g.handleOCRStats)
	logWithTimestamp("📝 OCR endpoints registered: /api/v1/ocr/*")

	// ── 对话历史 Git 管理 ──
	http.HandleFunc("/api/v1/chat/save", g.handleChatSave)
	http.HandleFunc("/api/v1/chat/history", g.handleChatHistory)
	http.HandleFunc("/api/v1/chat/sessions", g.handleChatSessions)
	logWithTimestamp("📝 Chat history endpoints registered: /api/v1/chat/*")

	// ── ARC-AI-NET 集群广播 + 全量拓扑 ──
	http.HandleFunc("/api/v1/cluster/broadcast", g.handleBroadcast)
	logWithTimestamp("📡 ARC-AI-NET broadcast registered: /api/v1/cluster/broadcast")
	http.HandleFunc("/api/v1/cluster/topology", g.handleTopologySync)
	logWithTimestamp("📡 ARC-AI-NET topology sync registered: /api/v1/cluster/topology")

	// ── 分布式共享记忆层（SPEC-DMEM-001 Phase 1） ──
	http.HandleFunc("/api/v1/memory", g.handleMemorySync) // 兼容: POST /api/v1/memory
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

	// ── LLM Proxy (workers without internet access) ──
	http.HandleFunc("/api/v1/llm/chat/completions", g.handleLlmProxy)
	logWithTimestamp("🌉 LLM Proxy endpoint registered: /api/v1/llm/chat/completions")

	// ── Agent Think (Layer 2: natural language task execution) ──
	if g.Agent != nil {
		http.HandleFunc("/api/v1/agent/think", g.handleAgentThink)
		http.HandleFunc("/api/v1/agent/stream", g.handleAgentStream)
		http.HandleFunc("/ai", g.handleAIPage)
		logWithTimestamp("🧠 Agent Think endpoint registered: /api/v1/agent/think")
		logWithTimestamp("🌊 Agent Stream endpoint registered: /api/v1/agent/stream")
		logWithTimestamp("🤖 AI Chat page: /ai")
	}

	// ── Dashboard static files (if directory provided) ──
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
}
