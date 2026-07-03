// ComputeHub Worker Agent — 每个 Worker 都是 AI 智能体
// Phase 1: Worker 内嵌 Agent，支持本地决策和对话
//
// 端点:
//   POST /api/v1/worker/think    — 自然语言对话，本地 AI 分析
//   GET  /api/v1/worker/status   — AI 理解版的状态报告
//   GET  /api/v1/worker/health   — 基础健康检查

package workercmd

import (
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/rand"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"github.com/computehub/opc/src/agent"
	"github.com/computehub/opc/src/composer"
	"github.com/computehub/opc/src/executil"
)

//go:embed worker_table.html
var tableFS embed.FS

// ── Worker 专属 Agent 工具 ──

type workerToolRegistry struct {
	state  *WorkerState
	agent  *agent.Agent
}

func newWorkerToolRegistry(state *WorkerState, um *UpgradeManager, ocBridge *OpenClawBridge) *agent.ToolRegistry {
	tr := agent.NewToolRegistry()

	// 1. self_diagnose — Worker 自我诊断
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "self_diagnose",
			Description: "检查 Worker 自身的 CPU/内存/磁盘/运行状态",
			Parameters:  []agent.Param{},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			return runSelfDiagnose(state)
		},
	})

	// 2. task_history — 查询本地任务执行历史
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "task_history",
			Description: "查询本 Worker 上最近的任务执行历史",
			Parameters: []agent.Param{
				{Name: "limit", Type: "int", Required: false, Description: "返回最近多少条（默认 10）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			limit := 10
			if l, ok := args["limit"].(float64); ok {
				limit = int(l)
			}
			return getTaskHistory(state, limit)
		},
	})

	// 3. safety_check — 🔒 Sentinel 安全审批（所有危险操作必须先过此关）
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "safety_check",
			Description: "执行危险操作前必须先通过此审批。提交 action(做什么)、why(为什么)、scope(影响谁)、rollback(失败预案)、command(命令)。返回 approved/rejected。",
			Parameters: []agent.Param{
				{Name: "action", Type: "string", Required: true, Description: "要做的操作描述（如：升级 Windows-mobile 到 v1.3.7）"},
				{Name: "why", Type: "string", Required: true, Description: "为什么做这个操作"},
				{Name: "scope", Type: "string", Required: true, Description: "影响范围（如：Windows-mobile 节点）"},
				{Name: "rollback", Type: "string", Required: true, Description: "失败预案（操作失败怎么恢复）"},
				{Name: "command", Type: "string", Required: false, Description: "要执行的实际命令"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			action, _ := args["action"].(string)
			why, _ := args["why"].(string)
			scope, _ := args["scope"].(string)
			rollback, _ := args["rollback"].(string)
			command, _ := args["command"].(string)

			var warnings []string
			approved := true

			if rollback == "" || utf8.RuneCountInString(rollback) < 5 {
				warnings = append(warnings, "❌ 无失败预案（rollback 为空或过于简略）")
				approved = false
			}
			if why == "" || utf8.RuneCountInString(why) < 10 {
				warnings = append(warnings, "❌ 未充分说明操作原因")
				approved = false
			}
			if scope == "" {
				warnings = append(warnings, "❌ 未说明影响范围")
				approved = false
			}
			if strings.Contains(command, "kill") || strings.Contains(command, "rm ") || strings.Contains(command, "del ") {
				if !strings.Contains(command, "--node-id") && !strings.Contains(command, "-pid") {
					warnings = append(warnings, "⚠️ 高危命令未指定具体目标")
				}
			}
			if strings.Contains(scope, "Windows") || strings.Contains(action, "Windows") {
				if !strings.Contains(rollback, "心跳") && !strings.Contains(rollback, "重启") {
					warnings = append(warnings, "⚠️ 操作 Windows 节点可能有网络不可达风险")
				}
			}

			verdict := "rejected"
			if approved && len(warnings) > 0 {
				verdict = "approved_with_warnings"
			} else if approved {
				verdict = "approved"
			}

			return fmt.Sprintf(`{"verdict":"%s","approved":%v,"warnings":%s,"action":"%s","timestamp":"%s"}`,
				verdict, approved, toJSONString(warnings), action, time.Now().Format("15:04:05")), nil
		},
	})

	// 3. exec_local — 本地执行命令并返回结果（受控执行）
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "exec_local",
			Description: "在本 Worker 节点上执行 shell 命令并返回结果",
			Parameters: []agent.Param{
				{Name: "command", Type: "string", Required: true, Description: "要执行的 shell 命令"},
				{Name: "timeout", Type: "int", Required: false, Description: "超时秒数（默认 30）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			command, _ := args["command"].(string)
			if command == "" {
				return "", fmt.Errorf("command is required")
			}
			timeout := 30
			if t, ok := args["timeout"].(float64); ok {
				timeout = int(t)
			}

			// ── 安全检查：拦截 SSH 自连接攻击 ──
			if err := agent.DetectSSHSelfAttack(command); err != nil {
				return "", fmt.Errorf("❌ 安全拦截: %v", err)
			}

			// 安全白名单：只允许读取/查询类命令，禁止写/删/改操作
			banned := []string{"rm -rf", "rm -f ", "dd if=", "mkfs", "fdisk", "> /etc/", "shutdown", "reboot", "poweroff", "iptables -F", "iptables -X", "apt remove", "yum remove", "pacman -R"}
			lower := strings.ToLower(command)
			for _, b := range banned {
				if strings.Contains(lower, strings.ToLower(b)) {
					return "", fmt.Errorf("forbidden command: %s", command)
				}
			}
			// 执行命令 — 平台差异化 shell
			execCtx, cancel := context.WithTimeout(ctx, time.Duration(timeout)*time.Second)
			defer cancel()
			var execCmd *exec.Cmd
			if runtime.GOOS == "windows" {
				// Windows: 直接用 powershell，不走 cmd.exe
				psCmd := fmt.Sprintf(`[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; %s`, command)
				execCmd = exec.CommandContext(execCtx, "powershell", "-Command", psCmd)
			} else {
				// Linux/Mac: 用 sh -c（兼容 Termux 安全 syscall）
				shPath := executil.SafeLookPath("sh")
				execCmd = exec.CommandContext(execCtx, shPath, "-c", command)
			}
			out, err := execCmd.CombinedOutput()
			if err != nil {
				return fmt.Sprintf("exit code: %d\n%s", 1, string(out)), err
			}
			result := strings.TrimSpace(string(out))
			if len(result) > 8192 {
				result = result[:8192] + "\n... (truncated, output exceeds 8KB)"
			}
			return result, nil
		},
	})

	// 5. manage_openclaw — 跨节点统一管理 OpenClaw 实例
	// 通过 Gateway 任务分发，在所有指定节点上执行 OpenClaw 管理命令
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "manage_openclaw",
			Description: "统一管理指定节点（或全部节点）上的 OpenClaw 实例，支持 status/start/stop/restart/install。会自动识别各节点的平台，路由到对应的命令。",
			Parameters: []agent.Param{
				{Name: "action", Type: "string", Required: true, Description: "操作: status | start | stop | restart | install"},
				{Name: "node_id", Type: "string", Required: false, Description: "目标节点 ID（空=所有在线节点）"},
				{Name: "timeout", Type: "int", Required: false, Description: "单节点超时秒数（默认 60）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			action, _ := args["action"].(string)
			if action == "" {
				return "", fmt.Errorf("action is required (status/start/stop/restart/install)")
			}
			targetNode, _ := args["node_id"].(string)
			timeout := 60
			if t, ok := args["timeout"].(float64); ok {
				timeout = int(t)
			}

			// 映射 action → 命令
			var cmd string
			switch action {
			case "status":
				cmd = "openclaw gateway status"
			case "start":
				cmd = "openclaw gateway start"
			case "stop":
				cmd = "openclaw gateway stop"
			case "restart":
				cmd = "openclaw gateway stop; sleep 2; openclaw gateway start"
			case "install":
				cmd = "npm install -g openclaw"
			default:
				return "", fmt.Errorf("unknown action: %s (支持: status/start/stop/restart/install)", action)
			}

			gwURL := state.config.GatewayURL
			if gwURL == "" {
				return "", fmt.Errorf("Gateway URL not configured")
			}

			// 获取节点列表
			targets := make([]string, 0)
			if targetNode != "" {
				targets = append(targets, targetNode)
			} else {
				// 查询所有在线节点
				client := &http.Client{Timeout: 10 * time.Second}
				resp, err := client.Get(gwURL + "/api/v1/nodes/list")
				if err != nil {
					return "", fmt.Errorf("获取节点列表失败: %w", err)
				}
				body, _ := io.ReadAll(resp.Body)
				resp.Body.Close()
				var listResp struct {
					Success bool                      `json:"success"`
					Data    []map[string]interface{}  `json:"data"`
					Error   string                    `json:"error"`
				}
				if err := json.Unmarshal(body, &listResp); err != nil || !listResp.Success {
					return "", fmt.Errorf("解析节点列表失败: %v", err)
				}
				for _, n := range listResp.Data {
					if nid, ok := n["node_id"].(string); ok && nid != "" {
						targets = append(targets, nid)
					}
				}
				if len(targets) == 0 {
					return "没有在线节点", nil
				}
			}

			client := &http.Client{Timeout: 10 * time.Second}
			var results strings.Builder
			results.WriteString(fmt.Sprintf("🔧 manage_openclaw action=%s 节点数=%d\n", action, len(targets)))

			for _, nid := range targets {
				taskID := fmt.Sprintf("oc-%s-%s-%d", action, nid, time.Now().UnixNano())
				submit := map[string]interface{}{
					"task_id":       taskID,
					"command":       cmd,
					"node_id":       nid,
					"assigned_node": nid,
					"timeout":       timeout,
					"priority":      5,
					"max_retries":   2,
					"source_type":   "agent-oc",
				}
				submitBody, _ := json.Marshal(submit)

				resp, err := client.Post(gwURL+"/api/v1/tasks/submit", "application/json", strings.NewReader(string(submitBody)))
				if err != nil {
					results.WriteString(fmt.Sprintf("  ❌ %s: 提交失败 - %v\n", nid, err))
					continue
				}
				resp.Body.Close()

				// 轮询结果
				deadline := time.Now().Add(time.Duration(timeout+10) * time.Second)
				var result string
				found := false
				for time.Now().Before(deadline) {
					select {
					case <-ctx.Done():
						return results.String(), ctx.Err()
					default:
					}
					time.Sleep(500 * time.Millisecond)

					detailURL := fmt.Sprintf("%s/api/v1/tasks/detail?task_id=%s&node_id=%s", gwURL, taskID, nid)
					resp2, err := client.Get(detailURL)
					if err != nil {
						continue
					}
					var detailResp struct {
						Success bool                   `json:"success"`
						Data    map[string]interface{} `json:"data"`
					}
					if err := json.NewDecoder(resp2.Body).Decode(&detailResp); err != nil {
						resp2.Body.Close()
						continue
					}
					resp2.Body.Close()
					if !detailResp.Success {
						continue
					}
					status, _ := detailResp.Data["status"].(string)
					if status == "completed" {
						stdout, _ := detailResp.Data["stdout"].(string)
						stderr, _ := detailResp.Data["stderr"].(string)
						exitCode := 0
						if ec, ok := detailResp.Data["exit_code"].(float64); ok {
							exitCode = int(ec)
						}
						icon := "✅"
						if exitCode != 0 {
							icon = "⚠️"
						}
						result = stdout
						if stderr != "" {
							result += "\n" + stderr
						}
						result = strings.TrimSpace(result)
						results.WriteString(fmt.Sprintf("  %s %s (exit=%d)\n", icon, nid, exitCode))
						if result != "" {
							if len(result) > 500 {
								result = result[:500] + "..."
							}
							for _, line := range strings.Split(result, "\n") {
								line = strings.TrimSpace(line)
								if line != "" {
									results.WriteString(fmt.Sprintf("    %s\n", line))
								}
							}
						}
						found = true
						break
					} else if status == "failed" || status == "cancelled" {
						stderr, _ := detailResp.Data["stderr"].(string)
						results.WriteString(fmt.Sprintf("  ❌ %s: 任务失败 - %s\n", nid, stderr))
						found = true
						break
					}
				}
				if !found {
					results.WriteString(fmt.Sprintf("  ⏰ %s: 超时\n", nid))
				}
			}

			return results.String(), nil
		},
	})

	// 6. openclaw_chat — 通过持久化管道与本地 OpenClaw Agent 通信
	// 避免每次调用都启动新 proot，节省 ~0.5s 启动开销
	if ocBridge != nil {
		ocToolWorkerIdx := len(tr.List()) // 识别码用于结果摘要
		_ = ocToolWorkerIdx
		tr.Register(&agent.ToolEntry{
			Tool: agent.Tool{
				Name:        "openclaw_chat",
				Description: "向本节点（Worker 本地）的 OpenClaw Agent 发送消息并获取回复。支持 openclaw agent --message 的所有功能。用于需要本地 AI 分析、查状态、调用本地工具的对话场景。",
				Parameters: []agent.Param{
					{Name: "message", Type: "string", Required: true, Description: "发给 OpenClaw Agent 的消息内容"},
					{Name: "timeout", Type: "int", Required: false, Description: "超时秒数（默认 60）"},
				},
			},
			Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
				msg, _ := args["message"].(string)
				if msg == "" {
					return "", fmt.Errorf("message is required")
				}
				timeout := 60
				if t, ok := args["timeout"].(float64); ok {
					timeout = int(t)
				}
				result, err := ocBridge.Chat(msg, time.Duration(timeout)*time.Second)
				if err != nil {
					// Fallback: 如果持久管道挂了，用单次 exec
					escapedMsg := strings.ReplaceAll(msg, "'", "'\\''")
					cmd := fmt.Sprintf("openclaw agent --agent main --message '%s' --json 2>&1 | tail -30", escapedMsg)
					execCtx, cancel := context.WithTimeout(ctx, time.Duration(timeout)*time.Second)
					defer cancel()
					shPath := executil.SafeLookPath("sh")
					shCmd := exec.CommandContext(execCtx, shPath, "-c", cmd)
					out, execErr := shCmd.CombinedOutput()
					if execErr != nil {
						return "", fmt.Errorf("openclaw_chat 失败 (持久管道: %v, fallback: %v)", err, execErr)
					}
					return strings.TrimSpace(string(out)), nil
				}
				return result, nil
			},
		})
	}

	// 7. Upgrade tools (registered via UpgradeManager)
	if um != nil {
		um.RegisterAgentTools(tr)
	}

	return tr
}

// ── 诊断工具实现 ──

func runSelfDiagnose(state *WorkerState) (string, error) {
	var b strings.Builder
	b.WriteString(fmt.Sprintf("Worker: %s\n", state.nodeID))
	b.WriteString(fmt.Sprintf("Platform: %s/%s\n", runtime.GOOS, runtime.GOARCH))
	b.WriteString(fmt.Sprintf("Running tasks: %d\n", len(state.runningTasks)))

	// CPU
	b.WriteString(fmt.Sprintf("CPU cores: %d\n", runtime.NumCPU()))

	// Memory (Go runtime stats)
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	b.WriteString(fmt.Sprintf("Memory: Alloc=%.1fMB Sys=%.1fMB\n",
		float64(m.Alloc)/1024/1024,
		float64(m.Sys)/1024/1024))

	// Disk
	// Simple disk check via stat of report dir
	os.MkdirAll(state.config.ReportDir, 0755)
	if fi, err := os.Stat(state.config.ReportDir); err == nil {
		b.WriteString(fmt.Sprintf("Report dir size: %d bytes\n", fi.Size()))
	}

	// Uptime (approximate via process start)
	b.WriteString(fmt.Sprintf("PID: %d\n", os.Getpid()))

	return b.String(), nil
}

func getTaskHistory(state *WorkerState, limit int) (string, error) {
	dir := state.config.ReportDir
	entries, err := os.ReadDir(dir)
	if err != nil {
		return fmt.Sprintf("no task reports found: %v", err), nil
	}

	var b strings.Builder
	count := 0
	for i := len(entries) - 1; i >= 0 && count < limit; i-- {
		if !strings.HasPrefix(entries[i].Name(), "task-") {
			continue
		}
		data, err := os.ReadFile(dir + "/" + entries[i].Name())
		if err != nil {
			continue
		}
		var report struct {
			TaskID     string `json:"task_id"`
			NodeID     string `json:"node_id"`
			FinishedAt string `json:"finished_at"`
			Result     struct {
				Success  bool   `json:"success"`
				ExitCode int    `json:"exit_code"`
				Duration string `json:"duration"`
			} `json:"result"`
		}
		if err := json.Unmarshal(data, &report); err != nil {
			continue
		}
		status := "✅"
		if !report.Result.Success {
			status = "❌"
		}
		truncatedID := report.TaskID
		if len(truncatedID) > 25 {
			truncatedID = truncatedID[:25]
		}
		b.WriteString(fmt.Sprintf("%s %s exit=%d dur=%s\n",
			status, truncatedID, report.Result.ExitCode, report.Result.Duration))
		count++
	}
	if count == 0 {
		b.WriteString("(no task history)\n")
	}
	return b.String(), nil
}

// ── Worker Agent HTTP Server ──

type WorkerAgentServer struct {
	agent       *agent.Agent
	state       *WorkerState
	server      *http.Server
	arcSeq      uint64         // 广播序列号
	arcNodes    []ArcNodeInfo  // 已知节点列表
	arcMu       sync.RWMutex
	arcQuit     chan struct{}  // 停止广播协程
	arcNodeList []ArcNodeInfo  // 本地缓存节点列表
	ocManager   *OpenClawManager // OpenClaw 实例管理器
}

type ArcNodeInfo struct {
	NodeID string `json:"node_id"`
	Label  string `json:"label"`
	Host   string `json:"host"`
	IP     string `json:"ip"`
	Platform string `json:"platform"`
	Model  string `json:"model"`
	Status string `json:"status"`
}

func startWorkerAgent(state *WorkerState, um *UpgradeManager, port int) *WorkerAgentServer {
	// 从 config.json → composer 配置加载 LLM Client
	// 配置示例:
	//   api_url: "https://ai.zhangtuokeji.top:9090/v1"  → 直连（ECS 等能联网节点）
	//   api_url: "http://127.0.0.1:8282/api/v1/llm"     → 走 Gateway 中转（Windows 等不能联网节点）
	llmAPI := state.config.ComposerAPIURL
	llmKey := state.config.ComposerAPIKey
	llmModel := state.config.ComposerModel
	if llmAPI == "" {
		// 没有配置时，走 Gateway LLM Proxy（安全兜底）
		gw := state.config.GatewayURL
		llmAPI = gw + "/api/v1/llm"
		llmKey = ""
	}
	if llmModel == "" {
		llmModel = "gemma4:31b"
	}
	llm := composer.NewLLMClient(llmAPI, llmKey, llmModel)
	llm.SetTimeout(60 * time.Second)

	// 🔗 创建持久化 OpenClaw 桥接（避免每次 openclaw 调用都启动 proot）
	ocBridge := NewOpenClawBridge(state.nodeID)
	if err := ocBridge.Start(); err != nil {
		fmt.Printf(" %s⚠️ OpenClaw 桥接启动失败 (fallback to single-exec): %v%s\n", red(bold("")), err, reset())
	} else {
		fmt.Printf(" %s🔗 OpenClaw 持久化管道已连接 (node=%s)%s\n", green(bold("")), state.nodeID, reset())
	}

	// Create Worker-specific tool registry (with upgrade + openclaw_chat tools)
	tools := newWorkerToolRegistry(state, um, ocBridge)
	tools.SetGatewayURL(state.config.GatewayURL)
	tools.SetLLMClient(llm)

	// Create Agent
	agt := agent.NewAgent(llm, tools, "")  // Worker 记忆可选，"" 使用默认路径

	// Inject local kernel so Agent can execute shell commands directly on this Worker
	kernelProvider := NewWorkerKernelProvider(
		state.nodeID,
		state.config.GatewayURL,
		state.config.GPUType,
		state.config.CPUCores,
		int(state.config.MemoryGB),
	)
	// 从 Gateway 同步所有在线节点（Agent 需要知道远程节点才能跨节点调度）
	// 启动周期性同步循环（每 30s），确保延迟注册的节点也能被识别
	kernelProvider.StartSyncLoop()
	agt.SetKernel(kernelProvider)
	agt.SetNodeProvider(kernelProvider.GetNodeManager())

	// 🏛️ 创建并启动大厅客户端（ARC-AI-NET-003 群聊）
	nodeDisplayName := state.nodeID
	if state.config.Region != "" {
		nodeDisplayName = state.nodeID + " [" + state.config.Region + "]"
	}
	hallClient := NewHallClient(state.nodeID, nodeDisplayName, state.config.GatewayURL)
	hallClient.SetAgent(agt)
	hallClient.SetWSOnlineFlag(&state.isWSConnected)
	hallClient.SetTaskHandler(func(taskID, command string, timeout int) {
		// Phase 3: WS 推送的任务直接交给 Worker 执行
		state.executeTask(&TaskDetail{
			TaskID:   taskID,
			Command:  command,
			NodeID:   state.nodeID,
			Timeout:  timeout,
			Priority: 5,
		})
	})
	hallClient.StartPollLoop()

	// 注册 hall_speak 工具 — Agent 可以通过 Tool 发送大厅消息
	registerHallTools(tools, hallClient)

	// 🧠 创建记忆同步客户端（SPEC-DMEM-001 Phase 1）
	memSync := NewMemorySyncClient(state.config.GatewayURL, state.nodeID)
	registerMemorySyncTools(tools, memSync)

	// Phase 2: 将记忆同步回调注入 Agent，每次 recordEpisode 后自动同步到 Gateway
	agt.SetMemorySyncFn(func(task, result string, success bool, learned string) {
		memSync.SyncEpisode(task, result, success, learned)
	})

	// Phase 2: 将知识同步回调注入 Agent，每次 SaveKnowledge 后自动同步到 Gateway
	agt.SetKnowledgeSyncFn(func(topic, content string) {
		memSync.SyncKnowledge(topic, content, []string{})
	})

	// Phase 2: 将共享记忆查询回调注入 Agent，每次 injectMemoryContext 时搜索 ClusterMemory
	agt.SetClusterSearchFn(func(query string, limit int) (string, error) {
		return memSync.SearchRemote(query, limit)
	})

	// 🌌 Phase 3b: 自主进化引擎 — 任务复盘、知识沉淀、专家路由
	expertRegistry := agent.NewExpertRegistry(llm)
	phase3 := agent.NewGalaxyPhase3Manager(agt, expertRegistry, agt.GetMemory(), llm)
	// 注入事件同步回调 — Phase 3 操作日志推送到 Gateway
	phase3.SetEventSyncFn(func(event agent.Phase3Event) {
		memSync.SyncPhase3Event(event)
	})
	agt.SetPhase3(phase3)
	fmt.Printf(" 🌌 Phase 3b 自主进化引擎已激活 (node=%s)\n", state.nodeID)

	// 🚀 创建 OpenClaw 管理器 — 管理本节点上的 OpenClaw 实例
	ocConfig := &OpenClawConfig{
		Port:    18789,
		DataDir: getWorkerHomeDir() + "/.openclaw",
	}
	// 从 config.json 读取 OpenClaw 配置（如果有）
	if state.config.OpenClawPort > 0 {
		ocConfig.Port = state.config.OpenClawPort
	}
	if state.config.OpenClawRemote != "" {
		ocConfig.Remote = state.config.OpenClawRemote
	}
	if state.config.OpenClawToken != "" {
		ocConfig.Token = state.config.OpenClawToken
	}
	ocManager := NewOpenClawManager(state, ocConfig)
	ocManager.RegisterAgentTools(tools)
	// 启动健康检查循环（自动自愈）
	ocManager.StartHealthLoop()

	// Create HTTP server
	ws := &WorkerAgentServer{
		agent:     agt,
		state:     state,
		ocManager: ocManager,
		arcSeq:    1,
		arcQuit:   make(chan struct{}),
	}

	// 初始化本地节点列表（先只知道自己）
	ws.arcNodes = append(ws.arcNodes, ArcNodeInfo{
		NodeID:   state.nodeID,
		Label:    state.config.NodeID,
		Host:     "localhost",
		IP:       "127.0.0.1",
		Platform: runtime.GOOS + "/" + runtime.GOARCH,
		Model:    state.config.ComposerModel,
		Status:   "online",
	})

	mux := http.NewServeMux()
	mux.HandleFunc("/api/v1/worker/think", ws.handleThink)
	mux.HandleFunc("/api/v1/worker/arc_net", ws.handleArcNetBroadcast)
	mux.HandleFunc("/api/v1/worker/status", ws.handleStatus)
	mux.HandleFunc("/api/v1/worker/health", ws.handleHealth)
	mux.HandleFunc("/api/v1/worker/safety_check", ws.handleSafetyCheck) // 🔒 Sentinel 审批
	mux.HandleFunc("/api/v1/worker/openclaw_status", ws.handleOpenClawStatus) // 🩺 OpenClaw 状态
	mux.HandleFunc("/", ws.handleDashboard)
	mux.HandleFunc("/table", ws.handleTable) // 🃏 扑克牌桌
	mux.HandleFunc("/api/v1/worker/game_join", ws.handleGameJoin)
	mux.HandleFunc("/api/v1/worker/game_state", ws.handleGameState)
	mux.HandleFunc("/api/v1/worker/game_action", ws.handleGameAction)
	mux.HandleFunc("/api/v1/worker/game_players", ws.handleGamePlayers)

	ws.server = &http.Server{
		Addr:         fmt.Sprintf(":8383"),
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
	}

	go func() {
		fmt.Printf(" %s🧠 Worker Agent listening on :%d%s\n", tscolor(), port, reset())
		if err := ws.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			fmt.Printf(" %s❌ Worker Agent server error: %v%s\n", red(bold("")), err, reset())
		}
	}()

	return ws
}

// ── Handlers ──

func (ws *WorkerAgentServer) handleThink(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"POST required"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Task      string `json:"task"`
		SessionID string `json:"session_id,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, map[string]string{"error": "Invalid JSON: " + err.Error()})
		return
	}

	if req.Task == "" {
		writeJSON(w, map[string]string{"error": "task is required"})
		return
	}
	if req.SessionID == "" {
		req.SessionID = fmt.Sprintf("worker-%s-%d", ws.state.nodeID, time.Now().UnixNano())
	}

	ctx, cancel := context.WithTimeout(r.Context(), 60*time.Second)
	defer cancel()

	resp, err := ws.agent.Think(ctx, &agent.AgentRequest{
		Task:      req.Task,
		SessionID: req.SessionID,
	})
	if err != nil {
		writeJSON(w, map[string]interface{}{
			"error":   err.Error(),
			"thought": "Agent processing failed",
			"plan":    []agent.PlanStep{},
			"result":  "",
		})
		return
	}

	writeJSON(w, map[string]interface{}{
		"thought":    resp.Thought,
		"plan":       resp.Plan,
		"result":     resp.Result,
		"session_id": resp.SessionID,
		"error":      resp.Error,
	})
}

func (ws *WorkerAgentServer) handleStatus(w http.ResponseWriter, r *http.Request) {
	diagnosis, _ := runSelfDiagnose(ws.state)

	writeJSON(w, map[string]interface{}{
		"node_id":    ws.state.nodeID,
		"status":     "online",
		"diagnosis":  diagnosis,
		"gpu_type":   ws.state.config.GPUType,
		"region":     ws.state.config.Region,
		"concurrent": ws.state.config.MaxConcurrent,
		"platform":   runtime.GOOS + "/" + runtime.GOARCH,
	})
}

func (ws *WorkerAgentServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]interface{}{
		"status":  "ok",
		"node_id": ws.state.nodeID,
	})
}

// handleOpenClawStatus — GET /api/v1/worker/openclaw_status
// 返回本节点 OpenClaw 实例的状态
func (ws *WorkerAgentServer) handleOpenClawStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"GET required"}`, http.StatusMethodNotAllowed)
		return
	}

	if ws.ocManager == nil {
		writeJSON(w, map[string]interface{}{
			"success": false,
			"error":   "OpenClaw manager not initialized",
		})
		return
	}

	status := ws.ocManager.GetStatus()
	writeJSON(w, map[string]interface{}{
		"success": true,
		"data":    status,
	})
}

// ── ARC-AI-NET 集群广播 ──

// handleArcNetBroadcast 处理 arc_net 广播消息
// POST /api/v1/worker/arc_net
// 不走 LLM 推理管道，直接提取 arc_net 字段处理
func (ws *WorkerAgentServer) handleArcNetBroadcast(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"POST required"}`, http.StatusMethodNotAllowed)
		return
	}

	var req map[string]interface{}
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&req); err != nil {
		writeJSON(w, map[string]string{"error": "Invalid JSON: " + err.Error()})
		return
	}

	// 检查是否为 arc_net 广播消息
	if msgType, ok := req["type"].(string); ok && msgType == "arc_net_broadcast" {
		arcNet, ok := req["arc_net"].(map[string]interface{})
		if !ok {
			writeJSON(w, map[string]string{"error": "Missing arc_net field"})
			return
		}

		// 提取事件信息
		event, _ := arcNet["event"].(string)
		seq, _ := arcNet["seq"].(float64)
		sender, _ := arcNet["sender"].(map[string]interface{})
		senderID, _ := sender["node_id"].(string)
		payload, _ := arcNet["payload"].(map[string]interface{})

		// 去重检查（跳过自己发来的）
		if senderID == ws.state.nodeID {
			writeJSON(w, map[string]interface{}{
				"status":  "ok",
				"message": "self-broadcast skipped",
				"type":    "arc_net",
			})
			return
		}

		log.Printf("📡 ARC-NET broadcast received: event=%s, sender=%s, seq=%.0f", event, senderID, seq)

		// 根据事件类型处理
		switch event {
		case "node_join":
			log.Printf("🟢 新节点加入: %s", senderID)
			if payload != nil {
				if affectedNode, ok := payload["affected_node"].(map[string]interface{}); ok {
					node := ArcNodeInfo{
						NodeID:   senderID,
						Host:     fmt.Sprintf("%v", affectedNode["host"]),
						IP:       fmt.Sprintf("%v", affectedNode["ip"]),
						Platform: fmt.Sprintf("%v", affectedNode["platform"]),
						Model:    fmt.Sprintf("%v", affectedNode["model"]),
						Status:   "online",
					}
					ws.arcMu.Lock()
					ws.updateOrAddNode(node)
					ws.arcMu.Unlock()
				}
			}
		case "node_leave":
			log.Printf("🔴 节点离开: %s", senderID)
			ws.arcMu.Lock()
			ws.removeNode(senderID)
			ws.arcMu.Unlock()
		case "topology_update":
			log.Printf("🔄 拓扑变更: %s", senderID)
			ws.updateTopologyFromPayload(payload)
		case "heartbeat":
			// 静默处理心跳，更新节点心跳时间
			if payload != nil {
				ws.arcMu.Lock()
				ws.updateNodeHeartbeat(senderID, payload)
				ws.arcMu.Unlock()
			}
		case "sync_request":
			log.Printf("📋 同步请求: %s (通过 WS, 忽略旧请求)", senderID)
			writeJSON(w, map[string]interface{}{
				"status":  "ok",
				"message": "sync ignored - WS handles topology",
			})
			return
		default:
			log.Printf("⚠️ 未知广播事件: %s", event)
		}

		writeJSON(w, map[string]interface{}{
			"status":  "ok",
			"message": "arc_net_broadcast processed",
			"type":    "arc_net",
		})
		return
	}

	// 不是 arc_net 消息，返回错误
	writeJSON(w, map[string]string{"error": "Not an arc_net_broadcast message"})
}

// ── ARC-AI-NET 拓扑管理 ──

// updateOrAddNode 更新或添加节点信息
func (ws *WorkerAgentServer) updateOrAddNode(node ArcNodeInfo) {
	for i, n := range ws.arcNodes {
		if n.NodeID == node.NodeID {
			ws.arcNodes[i] = node
			return
		}
	}
	ws.arcNodes = append(ws.arcNodes, node)
}

// removeNode 移除节点
func (ws *WorkerAgentServer) removeNode(nodeID string) {
	newNodes := make([]ArcNodeInfo, 0, len(ws.arcNodes))
	for _, n := range ws.arcNodes {
		if n.NodeID != nodeID {
			newNodes = append(newNodes, n)
		}
	}
	ws.arcNodes = newNodes
}

// updateNodeHeartbeat 更新节点心跳时间
func (ws *WorkerAgentServer) updateNodeHeartbeat(nodeID string, payload map[string]interface{}) {
	for i, n := range ws.arcNodes {
		if n.NodeID == nodeID {
			if _, ok := payload["load"].(float64); ok {
				ws.arcNodes[i].Status = "online" // 更新状态
			}
			return
		}
	}
}

// updateTopologyFromPayload 从 payload 更新拓扑
func (ws *WorkerAgentServer) updateTopologyFromPayload(payload map[string]interface{}) {
	if payload == nil {
		return
	}
	if clusterState, ok := payload["cluster_state"].(map[string]interface{}); ok {
		if liveNodes, ok := clusterState["live_nodes"].([]interface{}); ok {
			ws.arcMu.Lock()
			defer ws.arcMu.Unlock()
			// 保留自己的节点
			self := ArcNodeInfo{}
			for i, n := range ws.arcNodes {
				if n.NodeID == ws.state.nodeID {
					self = n
					ws.arcNodes = append(ws.arcNodes[:i], ws.arcNodes[i+1:]...)
					break
				}
			}
			for _, raw := range liveNodes {
				if id, ok := raw.(string); ok {
					if id != ws.state.nodeID {
						ws.arcNodes = append(ws.arcNodes, ArcNodeInfo{
							NodeID: id,
							Status: "online",
						})
					}
				}
			}
			ws.arcNodes = append(ws.arcNodes, self)
		}
	}
}

// ── Sentinel 安全审批 ──
// 所有危险操作（kill/delete/覆盖/重装等）必须通过此端点审批才能执行。
// 其他节点（包括小智）在执行危险操作前，必须先 POST 到这里拿 approval。

func (ws *WorkerAgentServer) handleSafetyCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"POST required"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Action   string `json:"action"`   // 要做的操作描述
		Why      string `json:"why"`      // 为什么做
		Scope    string `json:"scope"`    // 影响谁
		Rollback string `json:"rollback"` // 失败预案
		Command  string `json:"command"`  // 实际要执行的命令（可选）
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, map[string]interface{}{
			"verdict":  "error",
			"reason":   "invalid request: " + err.Error(),
			"approved": false,
		})
		return
	}

	// 安全检查项
	var warnings []string
	approved := true

	// 规则 1: 必须有失败预案（使用 utf8.RuneCount 支持中文正确计数）
	if req.Rollback == "" {
		warnings = append(warnings, "❌ 无失败预案（rollback 为空）")
		approved = false
	} else if utf8.RuneCountInString(req.Rollback) < 5 {
		warnings = append(warnings, "❌ 失败预案不充分（至少 5 个中文字或明确步骤）")
		approved = false
	}

	// 规则 2: 必须说明为什么
	if req.Why == "" {
		warnings = append(warnings, "❌ 未说明操作原因")
		approved = false
	} else if utf8.RuneCountInString(req.Why) < 10 {
		warnings = append(warnings, "❌ 操作原因过于简略（至少 10 字）")
		approved = false
	}

	// 规则 3: 必须说明影响范围
	if req.Scope == "" {
		warnings = append(warnings, "❌ 未说明影响范围")
		approved = false
	}

	// 规则 4: 高危命令检查 — kill/rm/del 必须有具体目标
	if strings.Contains(req.Command, "kill") || strings.Contains(req.Command, "taskkill") {
		if !strings.Contains(req.Command, "--node-id") && !strings.Contains(req.Command, "-PID") && !strings.Contains(req.Command, "PID") {
			warnings = append(warnings, "⚠️ kill 命令未指定具体目标，可能误杀")
		}
	}

	// 规则 5: 跨节点操作 — Windows 节点提醒网络风险
	if strings.Contains(req.Scope, "Windows") || strings.Contains(req.Action, "Windows") {
		if !strings.Contains(req.Rollback, "心跳") && !strings.Contains(req.Rollback, "重启") {
			warnings = append(warnings, "⚠️ 操作 Windows 节点可能有网络不可达风险")
		}
	}

	status := "approved"
	if !approved {
		status = "rejected"
	} else if len(warnings) > 0 {
		status = "approved_with_warnings"
	}

	result := map[string]interface{}{
		"verdict":    status,
		"approved":   approved,
		"warnings":   warnings,
		"action":     req.Action,
		"reviewed_by": ws.state.nodeID,
		"timestamp":  time.Now().Format("15:04:05"),
		"suggestion": "",
	}

	if !approved {
		// 生成改进建议
		suggestions := []string{}
		for _, w := range warnings {
			if strings.HasPrefix(w, "❌") {
				suggestions = append(suggestions, "请补充: "+w[2:])
			}
		}
		if len(suggestions) > 0 {
			result["suggestion"] = strings.Join(suggestions, "; ")
		}
	}

	writeJSON(w, result)
}

// ── 本地状态看板 ──

var dashboardHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🤖 ComputeHub Worker</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;background:#0f0c29;color:#e0e0e0;min-height:100vh}
.header{padding:20px 24px 12px;border-bottom:1px solid rgba(255,255,255,0.08)}
.header h1{font-size:22px;background:linear-gradient(90deg,#f7971e,#ffd200);-webkit-background-clip:text;-webkit-text-fill-color:transparent;display:inline}
.header .badge{display:inline-block;margin-left:10px;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:600;background:rgba(76,175,80,0.18);color:#66bb6a;vertical-align:middle}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;padding:16px 24px}
.card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:14px}
.card .label{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px}
.card .value{font-size:20px;font-weight:700;margin-top:4px}
.card .value.gold{color:#f7971e}
.card .value.blue{color:#42a5f5}
.card .value.green{color:#66bb6a}
.section{margin:8px 24px}
.section h3{font-size:14px;color:#f7971e;margin-bottom:8px}
.task-list{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px}
.task-item{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:13px}
.task-item:last-child{border-bottom:none}
.task-id{color:#aaa;font-family:monospace;font-size:12px}
.task-status{font-weight:600}
.status-ok{color:#66bb6a}
.status-busy{color:#ffa726}
.status-err{color:#ef5350}
.refresh{text-align:center;padding:8px;font-size:12px;color:#555}
.log-section{margin:8px 24px 24px}
.log-box{background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;font-family:monospace;font-size:12px;line-height:1.6;max-height:200px;overflow-y:auto;color:#aaa}
.log-box .info{color:#66bb6a}
.log-box .warn{color:#ffa726}
.log-box .err{color:#ef5350}
@media(max-width:600px){.grid{grid-template-columns:1fr 1fr;padding:12px 16px}.header{padding:16px}}
</style>
</head>
<body>
<div class="header">
<h1>🤖 ComputeHub Worker</h1>
<span class="badge" id="statusBadge">● online</span>
</div>
<div class="grid" id="infoGrid">
<div class="card"><div class="label">node id</div><div class="value gold" id="nodeId">-</div></div>
<div class="card"><div class="label">platform</div><div class="value blue" id="platform">-</div></div>
<div class="card"><div class="label">gpu</div><div class="value" id="gpuType">-</div></div>
<div class="card"><div class="label">max concurrent</div><div class="value" id="concurrent">-</div></div>
<div class="card"><div class="label">running tasks</div><div class="value green" id="runningTasks">0</div></div>
<div class="card"><div class="label">uptime</div><div class="value" id="uptime">-</div></div>
</div>
<div class="section">
<h3>📋 最近任务</h3>
<div class="task-list" id="taskHistory"><span style="color:#555;font-size:13px">加载中...</span></div>
</div>
<div class="section">
<h3>🔧 快速操作</h3>
<div style="display:flex;gap:8px;flex-wrap:wrap">
<button onclick="runCmd('self_diagnose')" style="padding:8px 16px;border-radius:8px;border:none;background:rgba(247,151,30,0.15);color:#f7971e;cursor:pointer;font-size:13px">🔍 自检</button>
<button onclick="refreshAll()" style="padding:8px 16px;border-radius:8px;border:none;background:rgba(255,255,255,0.08);color:#ccc;cursor:pointer;font-size:13px">🔄 刷新</button>
</div>
<div id="cmdResult" style="margin-top:8px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px;font-family:monospace;font-size:12px;line-height:1.6;color:#aaa;display:none"></div>
</div>
<div class="log-section">
<h3>🚦 调试信息</h3>
<div class="log-box" id="debugLog"></div>
</div>
<p class="refresh" id="refreshInfo">⏳ 自动刷新中...</p>
<script>
let startTime = Date.now();
function log(msg,type) {
  const box = document.getElementById('debugLog');
  const cls = type==='err'?'err':type==='warn'?'warn':'info';
  box.innerHTML += '<span class="'+cls+'">['+new Date().toLocaleTimeString()+']</span> '+msg+'\n';
  box.scrollTop = box.scrollHeight;
}
async function fetchAPI(path) {
  const r = await fetch(path);
  return r.json();
}
async function refreshAll() {
  try {
    const [status, tasks] = await Promise.all([
      fetchAPI('/api/v1/worker/status'),
      fetchAPI('/api/v1/worker/health')
    ]);
    document.getElementById('nodeId').textContent = status.node_id||'-';
    document.getElementById('platform').textContent = status.platform||'-';
    document.getElementById('gpuType').textContent = status.gpu_type||'-';
    document.getElementById('concurrent').textContent = status.concurrent||'-';
    document.getElementById('runningTasks').textContent = '0';
    document.getElementById('uptime').textContent = Math.floor((Date.now()-startTime)/1000)+'s';
    document.getElementById('statusBadge').textContent = '● '+(status.status||'online');
    log('✅ 状态已更新','info');
  } catch(e) {
    log('❌ 获取状态失败: '+e.message,'err');
    document.getElementById('statusBadge').textContent = '● unknown';
  }
}
async function runCmd(name) {
  const box = document.getElementById('cmdResult');
  box.style.display = 'block';
  box.innerHTML = '⏳ 执行 '+name+'...';
  try {
    const r = await fetch('/api/v1/worker/think', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({task:'请执行 '+name})
    });
    const d = await r.json();
    box.innerHTML = (d.result||d.thought||'无输出').replace(/\\n/g,'<br>');
  } catch(e) {
    box.innerHTML = '<span style="color:#f66">❌ '+e.message+'</span>';
  }
}
refreshAll();
setInterval(refreshAll, 5000);
</script>
</body></html>`

func (ws *WorkerAgentServer) handleDashboard(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(dashboardHTML))
}

// handleTable serves the poker table page
func (ws *WorkerAgentServer) handleTable(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/table" {
		http.NotFound(w, r)
		return
	}
	data, err := tableFS.ReadFile("worker_table.html")
	if err != nil {
		http.Error(w, "Table file not found", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	w.Write(data)
}

// ── Card Game (分布式联机牌桌) ──

type Card struct {
	Suit string `json:"suit"`
	Val  string `json:"val"`
}

type Player struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	Hand   []Card `json:"hand"`
	Bet    int    `json:"bet"`
	Chips  int    `json:"chips"`
	AllIn  bool   `json:"allIn"`
	Stood  bool   `json:"stood"`
}

type GameState struct {
	Deck     []Card   `json:"deck"`
	Table    []Card   `json:"table"`
	Players  []Player `json:"players"`
	DealerID string   `json:"dealer_id"`
	Current  string   `json:"current"` // active player id
	Phase    string   `json:"phase"`   // deal/flop/turn/river/showdown
	Pot      int      `json:"pot"`
	Hidden   bool     `json:"hidden"`
}

var gameMu sync.Mutex
var gameStates = make(map[string]*GameState) // key: dealerWorker

func newDeck() []Card {
	suits := []string{"♠", "♥", "♦", "♣"}
	vals := []string{"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"}
	var deck []Card
	for _, s := range suits {
		for _, v := range vals {
			deck = append(deck, Card{Suit: s, Val: v})
		}
	}
	return deck
}

func shuffleDeck(deck []Card) []Card {
	for i := len(deck) - 1; i > 0; i-- {
		j := rand.Intn(i + 1)
		deck[i], deck[j] = deck[j], deck[i]
	}
	return deck
}

func cardValue(c Card) int {
	vals := map[string]int{"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,"J":11,"Q":12,"K":13,"A":14}
	return vals[c.Val]
}

func handScore(hand []Card) int {
	score := 0
	for _, c := range hand {
		score += cardValue(c)
	}
	return score
}

func init() { rand.Seed(time.Now().UnixNano()) }

func (ws *WorkerAgentServer) handleGameJoin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, map[string]string{"error": "POST required"})
		return
	}
	var req struct {
		WorkerAddr string `json:"worker_addr"`
		PlayerName string `json:"player_name"`
	}
	json.NewDecoder(r.Body).Decode(&req)
	if req.WorkerAddr == "" { req.WorkerAddr = "http://127.0.0.1:8383" }
	if req.PlayerName == "" { req.PlayerName = "Player" + fmt.Sprintf("%d", time.Now().UnixNano()%10000) }

	gameMu.Lock()
	defer gameMu.Unlock()

	key := req.WorkerAddr
	state, ok := gameStates[key]
	if !ok {
		// 创建新牌局
		state = &GameState{
			Deck:     shuffleDeck(newDeck()),
			Players:  []Player{{ID: "dealer", Name: req.PlayerName + " (庄家)", Chips: 1000, Bet: 0}},
			DealerID: "dealer",
			Phase:    "waiting",
			Pot:      0,
		}
		gameStates[key] = state
		writeJSON(w, map[string]interface{}{
			"action":  "created",
			"message": "牌桌创建成功",
			"state":   state,
		})
		return
	}

	// 加入现有牌桌
	if len(state.Players) >= 4 {
		writeJSON(w, map[string]string{"error": "桌满 (4人)"})
		return
	}
	state.Players = append(state.Players, Player{
		ID:     fmt.Sprintf("p%d", time.Now().UnixNano()%100000),
		Name:   req.PlayerName,
		Chips:  1000,
		Bet:    0,
	})
	writeJSON(w, map[string]interface{}{
		"action":  "joined",
		"message": "加入成功",
		"players": state.Players,
	})
}

func (ws *WorkerAgentServer) handleGameState(w http.ResponseWriter, r *http.Request) {
	gameMu.Lock()
	defer gameMu.Unlock()
	if len(gameStates) == 0 {
		writeJSON(w, map[string]string{"error": "无牌局"})
		return
	}
	// 默认取第一个牌局
	for _, key := range []string{"http://127.0.0.1:8383"} {
		if s, ok := gameStates[key]; ok {
			writeJSON(w, s)
			return
		}
	}
	for _, s := range gameStates {
		writeJSON(w, s)
		return
	}
	writeJSON(w, map[string]string{"error": "无牌局"})
}

func (ws *WorkerAgentServer) handleGamePlayers(w http.ResponseWriter, r *http.Request) {
	gameMu.Lock()
	defer gameMu.Unlock()
	if len(gameStates) == 0 {
		writeJSON(w, map[string]string{"error": "无牌局"})
		return
	}
	for _, s := range gameStates {
		writeJSON(w, map[string]interface{}{"players": s.Players})
		return
	}
}

func (ws *WorkerAgentServer) handleGameAction(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, map[string]string{"error": "POST required"})
		return
	}
	var req struct {
		PlayerID string `json:"player_id"`
		Action   string `json:"action"` // deal/hide/fold/show/bet/raise
		Amount   int    `json:"amount"`
	}
	json.NewDecoder(r.Body).Decode(&req)

	gameMu.Lock()
	defer gameMu.Unlock()

	if len(gameStates) == 0 {
		writeJSON(w, map[string]string{"error": "无牌局"})
		return
	}
	key := "http://127.0.0.1:8383"
	state, ok := gameStates[key]
	if !ok {
		// 自动创建
		state = &GameState{
			Deck:     shuffleDeck(newDeck()),
			Players:  []Player{{ID: "dealer", Name: "Dealer", Chips: 1000}},
			DealerID: "dealer",
			Phase:    "waiting",
		}
		gameStates[key] = state
	}

	switch req.Action {
	case "start":
		state.Deck = shuffleDeck(state.Deck)
		state.Table = nil
		state.Pot = 0
		for i := range state.Players {
			state.Players[i].Hand = nil
			state.Players[i].Bet = 0
			state.Players[i].Stood = false
			state.Players[i].AllIn = false
		}
		// 发2张牌给每人
		for i := range state.Players {
			if len(state.Deck) >= 2 {
				state.Players[i].Hand = append(state.Players[i].Hand, state.Deck[len(state.Deck)-2], state.Deck[len(state.Deck)-1])
				state.Deck = state.Deck[:len(state.Deck)-2]
			}
		}
		state.Pot = len(state.Players) * 10 // ante
		state.Phase = "preflop"
		writeJSON(w, map[string]interface{}{"action": "started", "state": state})

	case "bet":
		amt := req.Amount
		if amt <= 0 { amt = 10 }
		for i := range state.Players {
			if state.Players[i].ID == req.PlayerID {
				if state.Players[i].Chips >= amt {
					state.Players[i].Chips -= amt
					state.Players[i].Bet += amt
					state.Pot += amt
				}
				break
			}
		}
		writeJSON(w, map[string]interface{}{"action": "bet", "state": state})

	case "stand":
		for i := range state.Players {
			if state.Players[i].ID == req.PlayerID {
				state.Players[i].Stood = true
			}
		}
		// 翻牌
		if len(state.Deck) >= 3 {
			state.Table = append(state.Table, state.Deck[len(state.Deck)-3], state.Deck[len(state.Deck)-2], state.Deck[len(state.Deck)-1])
			state.Deck = state.Deck[:len(state.Deck)-3]
			state.Phase = "flop"
		}
		writeJSON(w, map[string]interface{}{"action": "stand", "state": state})

	case "showdown":
		for i := range state.Players {
			state.Players[i].Hand = nil // 明牌
		}
		state.Phase = "showdown"
		// 找最高分
		best := 0
		for i := range state.Players {
			if handScore(state.Players[i].Hand) > handScore(state.Players[best].Hand) {
				best = i
			}
		}
		state.Players[best].Chips += state.Pot
		writeJSON(w, map[string]interface{}{
			"action": "showdown",
			"winner": state.Players[best].Name,
			"state":  state,
		})

	default:
		writeJSON(w, map[string]string{"error": "未知操作: " + req.Action})
	}
}

func (ws *WorkerAgentServer) Stop() {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	ws.server.Shutdown(ctx)
}

// ── Utils ──

func writeJSON(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

// toJSONString 将任意值序列化为 JSON 字符串（用于 tool 返回值）
func toJSONString(v interface{}) string {
	b, _ := json.Marshal(v)
	return string(b)
}
