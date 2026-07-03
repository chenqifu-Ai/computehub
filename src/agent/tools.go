// Package agent — Tool Registry
// 为 Agent 提供可调用的工具（exec_shell, exec_llm, node_status 等）
package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/computehub/opc/src/composer"
)

// ═══════════════════════════════════════════
// SSH 自连接攻击检测
// ═══════════════════════════════════════════

// getLocalIPs 获取所有本地 IP 地址（含回环地址）
func getLocalIPs() []string {
	var ips []string
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return ips
	}
	for _, addr := range addrs {
		if ipnet, ok := addr.(*net.IPNet); ok {
			ips = append(ips, ipnet.IP.String())
		}
	}
	return ips
}

// DetectSSHSelfAttack 检测命令是否尝试 SSH/SCP 连接到本机。
// 这是防止 Agent 生成自连接命令导致 SSH 风暴的关键防线。
// 用于 exec_shell 和 executeLocal 等 shell 执行入口。
//
// 检测逻辑:
//   - 收集所有本地网卡 IP（回环 + 内网）
//   - 尝试获取公网 IP（通过 ifconfig.me 等外部服务，失败不阻断）
//   - 若 ssh/scp 目标匹配任一本地 IP → 拦截
func DetectSSHSelfAttack(cmd string) error {
	lower := strings.ToLower(strings.TrimSpace(cmd))

	// 快速过滤：不含 ssh/scp 的跳过
	if !strings.Contains(lower, "ssh ") && !strings.Contains(lower, "scp ") &&
		!strings.HasPrefix(lower, "ssh ") && !strings.HasPrefix(lower, "scp ") {
		return nil
	}

	// 获取本地 IP（缓存结果避免频繁查询）
	localIPs := getLocalIPs()

	// ── 尝试获取公网 IP（NAT 环境下的补充） ──
	// 只在首次调用时获取，失败不影响主逻辑
	publicIP := getPublicIP()

	lines := strings.Split(cmd, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || line[0] == '#' {
			continue
		}

		lowerLine := strings.ToLower(line)
		isSSH := strings.HasPrefix(lowerLine, "ssh ") || strings.Contains(lowerLine, "|ssh ") ||
			strings.Contains(lowerLine, ";ssh ") || strings.Contains(lowerLine, "&&ssh ")
		isSCP := strings.HasPrefix(lowerLine, "scp ") || strings.Contains(lowerLine, "|scp ") ||
			strings.Contains(lowerLine, ";scp ") || strings.Contains(lowerLine, "&&scp ")

		if !isSSH && !isSCP {
			continue
		}

		// ── 拦截 SSH 自连接 ──
		if isSSH {
			// 检查 localhost / 127.0.0.1 / ::1
			if strings.Contains(lowerLine, "@localhost") ||
				strings.Contains(lowerLine, "@127.0.0.1") ||
				strings.Contains(lowerLine, "@::1") {
				return fmt.Errorf("🚫 SSH 自连接攻击拦截: 命令尝试通过 SSH 连接到 localhost。"+
					"如需本地执行请直接使用 shell 命令而非 SSH。")
			}

			// 检查所有本地 IP（含内网 IP）
			for _, ip := range localIPs {
				if strings.Contains(lowerLine, "@"+ip) {
					return fmt.Errorf("🚫 SSH 自连接攻击拦截: 命令尝试通过 SSH 连接到本机IP (%s)。"+
						"已拦截。如需远程节点执行，请使用 node_id 参数指定目标节点。", ip)
				}
			}

			// 检查公网 IP（NAT 环境）
			if publicIP != "" && strings.Contains(lowerLine, "@"+publicIP) {
				return fmt.Errorf("🚫 SSH 自连接攻击拦截: 命令尝试通过 SSH 连接到本机公网IP (%s)。"+
					"已拦截。如需远程节点执行，请使用 node_id 参数指定目标节点。", publicIP)
			}
		}

		// ── 拦截 SCP 自连接 ──
		if isSCP {
			for _, ip := range localIPs {
				if strings.Contains(lowerLine, ip+":") {
					return fmt.Errorf("🚫 SCP 自连接拦截: 命令尝试通过 SCP 连接到本机IP (%s)。"+
						"已拦截。", ip)
				}
			}
			if publicIP != "" && strings.Contains(lowerLine, publicIP+":") {
				return fmt.Errorf("🚫 SCP 自连接拦截: 命令尝试通过 SCP 连接到本机公网IP (%s)。"+
					"已拦截。", publicIP)
			}
		}
	}

	return nil
}

// ── 公网 IP 获取 ──

var cachedPublicIP string
var publicIPOnce sync.Once

// getPublicIP 获取本机公网 IP（通过外部服务，失败返回空字符串）
func getPublicIP() string {
	publicIPOnce.Do(func() {
		client := &http.Client{Timeout: 3 * time.Second}
		// 尝试多个公网 IP 服务（从可靠到不可靠）
		services := []string{
			"https://icanhazip.com",
			"https://ifconfig.me/ip",
			"https://api.ipify.org",
		}
		for _, svc := range services {
			resp, err := client.Get(svc)
			if err != nil {
				continue
			}
			body, err := io.ReadAll(resp.Body)
			resp.Body.Close()
			if err == nil {
				ip := strings.TrimSpace(string(body))
				// 确保结果是一个有效的 IP 地址（不是 HTML）
				if ip != "" && !strings.Contains(ip, "<") && net.ParseIP(ip) != nil {
					cachedPublicIP = ip
					return
				}
			}
		}
	})
	return cachedPublicIP
}

// ====== 工具定义 ======

// Tool 工具元信息
type Tool struct {
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Parameters  []Param  `json:"parameters"`
}

// Param 参数定义
type Param struct {
	Name        string `json:"name"`
	Type        string `json:"type"` // "string" | "int" | "bool"
	Required    bool   `json:"required"`
	Description string `json:"description"`
}

// ToolFunc 工具执行函数
type ToolFunc func(ctx context.Context, args map[string]interface{}) (string, error)

// ToolEntry 注册的工具条目
type ToolEntry struct {
	Tool
	Execute ToolFunc
}

// ToolRegistry 工具注册表
type ToolRegistry struct {
	tools      map[string]*ToolEntry
	GatewayURL string           // 可选，让工具通过 Gateway API 获取真实数据
	LLMClient  *composer.LLMClient // 可选，让 exec_llm 工具真正调大模型
}

// NewToolRegistry 创建注册表并注册内置工具
func NewToolRegistry() *ToolRegistry {
	tr := &ToolRegistry{
		tools: make(map[string]*ToolEntry),
	}
	tr.registerBuiltins()
	return tr
}

// SetGatewayURL 设置 Gateway 地址，使工具能通过 API 获取真实数据
func (tr *ToolRegistry) SetGatewayURL(url string) {
	tr.GatewayURL = strings.TrimRight(url, "/")
}

// SetLLMClient 设置 LLM 客户端，使 exec_llm 工具能真正调大模型
func (tr *ToolRegistry) SetLLMClient(llm *composer.LLMClient) {
	tr.LLMClient = llm
}

// Register 注册工具
func (tr *ToolRegistry) Register(entry *ToolEntry) {
	tr.tools[entry.Name] = entry
}

// Get 获取工具
func (tr *ToolRegistry) Get(name string) *ToolEntry {
	return tr.tools[name]
}

// List 列出所有工具
func (tr *ToolRegistry) List() []Tool {
	tools := make([]Tool, 0, len(tr.tools))
	for _, entry := range tr.tools {
		tools = append(tools, entry.Tool)
	}
	return tools
}

// ListDescriptions 返回工具描述（用于 LLM 系统提示）
func (tr *ToolRegistry) ListDescriptions() string {
	var b strings.Builder
	b.WriteString("可用工具:\n\n")
	for _, entry := range tr.tools {
		b.WriteString(fmt.Sprintf("- %s: %s\n", entry.Name, entry.Description))
		if len(entry.Parameters) > 0 {
			b.WriteString("  参数:\n")
			for _, p := range entry.Parameters {
				req := ""
				if p.Required {
					req = " (必填)"
				}
				b.WriteString(fmt.Sprintf("    - %s (%s%s): %s\n", p.Name, p.Type, req, p.Description))
			}
		}
		b.WriteString("\n")
	}
	return b.String()
}

// ====== 工具函数（HTTP 客户端） ======

var toolHTTPClient = &http.Client{Timeout: 10 * time.Second}

func (tr *ToolRegistry) gatewayGet(path string) ([]byte, error) {
	if tr.GatewayURL == "" {
		return nil, fmt.Errorf("gateway URL not set (call SetGatewayURL first)")
	}
	resp, err := toolHTTPClient.Get(tr.GatewayURL + path)
	if err != nil {
		return nil, fmt.Errorf("gateway请求失败: %w", err)
	}
	defer resp.Body.Close()
	return io.ReadAll(resp.Body)
}

// ====== 内置工具 ======

func (tr *ToolRegistry) registerBuiltins() {
	// 1. exec_shell — 在远程节点执行 shell 命令（通过 Gateway API 提交任务）
	tr.Register(&ToolEntry{
		Tool: Tool{
			Name:        "exec_shell",
			Description: "在指定 Worker 节点上执行 shell 命令（通过 Gateway 提交任务，等待完成后返回结果）",
			Parameters: []Param{
				{Name: "command", Type: "string", Required: true, Description: "要执行的 shell 命令"},
				{Name: "node_id", Type: "string", Required: false, Description: "目标节点 ID（空=自动分配）"},
				{Name: "timeout", Type: "int", Required: false, Description: "超时秒数（默认 300）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			cmd, _ := args["command"].(string)
			if cmd == "" {
				return "", fmt.Errorf("command is required")
			}
			nodeID, _ := args["node_id"].(string)
			timeout := 300
			if t, ok := args["timeout"].(float64); ok {
				timeout = int(t)
			}

			if tr.GatewayURL == "" {
				return "", fmt.Errorf("exec_shell 需要设置 GatewayURL")
			}

			// ── 安全检查：拦截 SSH 自连接攻击 ──
			if err := DetectSSHSelfAttack(cmd); err != nil {
				return "", fmt.Errorf("❌ 安全拦截: %v", err)
			}

			// 1. 构造任务提交
			taskID := fmt.Sprintf("tool-exec-%d", time.Now().UnixNano())
			submit := map[string]interface{}{
				"task_id":       taskID,
				"command":       cmd,
				"node_id":       nodeID,
				"assigned_node": nodeID,
				"timeout":       timeout,
				"priority":      5,
				"max_retries":   2,
				"source_type":   "agent-tool",
			}
			submitBody, _ := json.Marshal(submit)

			// 2. POST 到 Gateway
			client := &http.Client{Timeout: 10 * time.Second}
			resp, err := client.Post(tr.GatewayURL+"/api/v1/tasks/submit", "application/json", strings.NewReader(string(submitBody)))
			if err != nil {
				return "", fmt.Errorf("提交任务到 Gateway 失败: %w", err)
			}
			resp.Body.Close()

			// 3. 轮询任务完成
			deadline := time.Now().Add(time.Duration(timeout+30) * time.Second)
			for time.Now().Before(deadline) {
				select {
				case <-ctx.Done():
					return "", fmt.Errorf("上下文取消")
				default:
				}

				time.Sleep(500 * time.Millisecond)

				detailURL := fmt.Sprintf("%s/api/v1/tasks/detail?task_id=%s", tr.GatewayURL, taskID)
				if nodeID != "" {
					detailURL += "&node_id=" + nodeID
				}

				resp, err := client.Get(detailURL)
				if err != nil {
					continue
				}

				var wrapper struct {
					Success bool                   `json:"success"`
					Data    map[string]interface{} `json:"data"`
				}
				if err := json.NewDecoder(resp.Body).Decode(&wrapper); err != nil {
					resp.Body.Close()
					continue
				}
				resp.Body.Close()

				if !wrapper.Success {
					continue
				}

				status, _ := wrapper.Data["status"].(string)
				switch status {
				case "completed":
					stdout, _ := wrapper.Data["stdout"].(string)
					stderr, _ := wrapper.Data["stderr"].(string)
					exitCode := 0
					if ec, ok := wrapper.Data["exit_code"].(float64); ok {
						exitCode = int(ec)
					}
					duration, _ := wrapper.Data["duration"].(string)
					var b strings.Builder
					b.WriteString(fmt.Sprintf("任务完成 (exit=%d, %s):\n", exitCode, duration))
					if stdout != "" {
						b.WriteString(stdout)
					}
					if stderr != "" {
						if stdout != "" {
							b.WriteString("\n")
						}
						b.WriteString(stderr)
					}
					result := strings.TrimSpace(b.String())
					if len(result) > 8192 {
						result = result[:8192] + "\n... (truncated)"
					}
					return result, nil
				case "failed", "cancelled":
					stderr, _ := wrapper.Data["stderr"].(string)
					return fmt.Sprintf("❌ 任务失败:\n%s", stderr), fmt.Errorf("task ended with status: %s", status)
				}
			}

			return "", fmt.Errorf("任务超时 (%ds 内未完成)", timeout+30)
		},
	})

	// 2. exec_llm — 直接调用 LLM 做分析（使用注册的 LLMClient）
	tr.Register(&ToolEntry{
		Tool: Tool{
			Name:        "exec_llm",
			Description: "调用大模型执行文本分析、代码生成、翻译等自然语言任务",
			Parameters: []Param{
				{Name: "prompt", Type: "string", Required: true, Description: "给 LLM 的提示词"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			prompt, _ := args["prompt"].(string)
			if prompt == "" {
				return "", fmt.Errorf("prompt is required")
			}
			if tr.LLMClient == nil {
				// 无 LLMClient 时退化为简单响应
				return fmt.Sprintf("(未配置 LLM 客户端，无法调用大模型)\n\n收到提示词: %s", prompt), nil
			}
			msgs := []composer.ChatMessage{
				{Role: "system", Content: "你是一个专业的 AI 分析助手。请根据用户的要求完成分析、生成或回答。"},
				{Role: "user", Content: prompt},
			}
			result, err := tr.LLMClient.Chat(msgs, 2048)
			if err != nil {
				return "", fmt.Errorf("LLM 调用失败: %w", err)
			}
			return result, nil
		},
	})

	// 3. node_status — 查询节点状态（通过 Gateway API）
	tr.Register(&ToolEntry{
		Tool: Tool{
			Name:        "node_status",
			Description: "查询指定节点的状态信息（CPU、内存、GPU），空 node_id=全部节点",
			Parameters: []Param{
				{Name: "node_id", Type: "string", Required: false, Description: "节点 ID（空=全部节点）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			targetNode, _ := args["node_id"].(string)

			body, err := tr.gatewayGet("/api/v1/nodes/list")
			if err != nil {
				return "", fmt.Errorf("无法获取节点列表: %w", err)
			}

			var wrapper struct {
				Success bool                      `json:"success"`
				Data    []map[string]interface{}  `json:"data"`
				Error   string                    `json:"error"`
			}
			if err := json.Unmarshal(body, &wrapper); err != nil || !wrapper.Success {
				return "节点列表查询失败", nil
			}

			var b strings.Builder
			count := 0
			for _, n := range wrapper.Data {
				nodeID, _ := n["node_id"].(string)
				if targetNode != "" && nodeID != targetNode {
					continue
				}
				count++
				status, _ := n["status"].(string)
				gpuType, _ := n["gpu_type"].(string)
				if gpuType == "" {
					gpuType = "CPU"
				}
				activeTasks := 0
				if at, ok := n["active_tasks"].(float64); ok {
					activeTasks = int(at)
				}
				region, _ := n["region"].(string)

				b.WriteString(fmt.Sprintf("  %s [%s] GPU=%s region=%s tasks=%d\n",
					nodeID, status, gpuType, region, activeTasks))
			}

			if count == 0 {
				if targetNode != "" {
					return fmt.Sprintf("节点 %s 未找到", targetNode), nil
				}
				return "没有在线节点", nil
			}

			return fmt.Sprintf("节点状态 (%d 个):\n%s", count, b.String()), nil
		},
	})

	// 4. task_list — 查询任务（通过 Gateway API）
	tr.Register(&ToolEntry{
		Tool: Tool{
			Name:        "task_list",
			Description: "查询集群中的任务列表（可按状态过滤）",
			Parameters: []Param{
				{Name: "status", Type: "string", Required: false, Description: "过滤条件: pending/running/completed/failed"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			filterStatus, _ := args["status"].(string)

			body, err := tr.gatewayGet("/api/v1/tasks/list")
			if err != nil {
				return "", fmt.Errorf("无法获取任务列表: %w", err)
			}

			var wrapper struct {
				Success bool                            `json:"success"`
				Data    map[string][]map[string]interface{} `json:"data"`
				Error   string                          `json:"error"`
			}
			if err := json.Unmarshal(body, &wrapper); err != nil || !wrapper.Success {
				return "任务列表查询失败", nil
			}

			var b strings.Builder
			total := 0
			for nodeID, tasks := range wrapper.Data {
				nodeCount := 0
				for _, t := range tasks {
					status, _ := t["status"].(string)
					if filterStatus != "" && status != filterStatus {
						continue
					}
					nodeCount++
				}
				if nodeCount == 0 {
					continue
				}
				total += nodeCount
				b.WriteString(fmt.Sprintf("\n%s (%d 个任务):\n", nodeID, nodeCount))
				for _, t := range tasks {
					status, _ := t["status"].(string)
					if filterStatus != "" && status != filterStatus {
						continue
					}
					taskID, _ := t["task_id"].(string)
					taskCmd, _ := t["command"].(string)
					createdAt, _ := t["submitted_at"].(string)

					icon := "⬜"
					switch status {
					case "completed": icon = "✅"
					case "running": icon = "🔄"
					case "failed": icon = "❌"
					case "pending": icon = "⏳"
					}
					if len(taskCmd) > 60 {
						taskCmd = taskCmd[:60] + "..."
					}
					b.WriteString(fmt.Sprintf("  %s %s [%s] %s %s\n",
						icon, taskID[:min(len(taskID), 24)], status, createdAt, taskCmd))
				}
			}

			if total == 0 {
				if filterStatus != "" {
					return fmt.Sprintf("没有状态为 '%s' 的任务", filterStatus), nil
				}
				return "没有任务", nil
			}

			return fmt.Sprintf("任务列表 (共 %d 个):%s", total, b.String()), nil
		},
	})

	// 5. gallery_list — 查询作品广场
	tr.Register(&ToolEntry{
		Tool: Tool{
			Name:        "gallery_list",
			Description: "查询 Gallery 作品列表",
			Parameters: []Param{
				{Name: "limit", Type: "int", Required: false, Description: "返回数量（默认 10）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			limit := 10
			if l, ok := args["limit"].(float64); ok {
				limit = int(l)
			}

			body, err := tr.gatewayGet(fmt.Sprintf("/api/v1/gallery/list?limit=%d", limit))
			if err != nil {
				return "", fmt.Errorf("无法获取 Gallery 列表: %w", err)
			}

			// Gallery 返回格式多样，尝试通用的响应格式
			var wrapper struct {
				Success bool          `json:"success"`
				Data    interface{}   `json:"data"`
				Error   string        `json:"error"`
			}
			if err := json.Unmarshal(body, &wrapper); err != nil {
				// Gallery 可能返回纯数组，尝试其他格式
				return fmt.Sprintf("Gallery 响应: %s", string(body[:min(len(body), 500)])), nil
			}
			if !wrapper.Success {
				return fmt.Sprintf("Gallery 查询失败: %s", wrapper.Error), nil
			}

			dataJSON, _ := json.MarshalIndent(wrapper.Data, "", "  ")
			return fmt.Sprintf("Gallery 作品:\n%s", string(dataJSON)), nil
		},
	})

	// 6. web_search — 联网搜索信息（通过 Bing 搜索）
	tr.Register(&ToolEntry{
		Tool: Tool{
			Name:        "web_search",
			Description: "在互联网上搜索信息，返回搜索结果摘要。适用于查询最新资讯、技术文档、代码示例、错误信息等。使用 Bing (cn.bing.com) 搜索，国内可直达。",
			Parameters: []Param{
				{Name: "query", Type: "string", Required: true, Description: "搜索关键词，建议用中文或英文"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			query, _ := args["query"].(string)
			if query == "" {
				return "", fmt.Errorf("query is required")
			}
			return webSearchBing(query)
		},
	})
}

// ====== web_search 工具实现 ======

// webSearchHTTPClient 独立的 HTTP 客户端用于搜索（更长的超时）
var webSearchHTTPClient = &http.Client{Timeout: 15 * time.Second}

// webSearchBing 通过 Bing 国内版 (cn.bing.com) 搜索，无需 API Key。
func webSearchBing(query string) (string, error) {
	encoded := url.QueryEscape(query)
	searchURL := fmt.Sprintf("https://cn.bing.com/search?q=%s&count=10", encoded)

	req, err := http.NewRequest("GET", searchURL, nil)
	if err != nil {
		return "", fmt.Errorf("创建请求失败: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")

	resp, err := webSearchHTTPClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("Bing 搜索请求失败: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("读取响应失败: %w", err)
	}

	html := string(body)
	var b strings.Builder

	// 解析 Bing 搜索结果
	results := parseBingResults(html)

	if len(results) > 0 {
		b.WriteString(fmt.Sprintf("搜索「%s」结果 (%d 条):\n\n", query, len(results)))
		for i, r := range results {
			if i >= 8 {
				break
			}
			b.WriteString(fmt.Sprintf("%d. %s\n", i+1, r.Title))
			if r.URL != "" {
				b.WriteString(fmt.Sprintf("   %s\n", r.URL))
			}
			if r.Snippet != "" {
				b.WriteString(fmt.Sprintf("   %s\n", r.Snippet))
			}
			b.WriteString("\n")
		}
	} else {
		text := extractBingText(html)
		if text != "" {
			b.WriteString(fmt.Sprintf("搜索「%s」结果:\n\n%s\n", query, text))
		} else {
			b.WriteString(fmt.Sprintf("搜索「%s」未返回可解析的结果", query))
		}
	}

	result := strings.TrimSpace(b.String())
	if result == "" {
		result = fmt.Sprintf("搜索「%s」未返回结果", query)
	}
	if len(result) > 8000 {
		result = result[:8000] + "\n... (truncated)"
	}
	return result, nil
}

// bingResult 单条搜索结果
type bingResult struct {
	Title   string
	URL     string
	Snippet string
}

// parseBingResults 从 Bing HTML 提取搜索结果
func parseBingResults(html string) []bingResult {
	var results []bingResult
	seen := make(map[string]bool)

	re := regexp.MustCompile(`<li class="b_algo"[^>]*>(.*?)</li>`)
	matches := re.FindAllStringSubmatch(html, -1)

	for _, m := range matches {
		if len(m) < 2 {
			continue
		}
		block := m[1]
		var r bingResult

		hrefRe := regexp.MustCompile(`<h2[^>]*><a[^>]*href="([^"]*)"[^>]*>(.*?)</a></h2>`)
		hrefMatch := hrefRe.FindStringSubmatch(block)
		if len(hrefMatch) >= 3 {
			r.URL = hrefMatch[1]
			r.Title = stripHTMLTags(hrefMatch[2])
		}

		if r.Title == "" || seen[r.Title] {
			continue
		}
		seen[r.Title] = true

		pRe := regexp.MustCompile(`<p[^>]*>(.*?)</p>`)
		pMatch := pRe.FindStringSubmatch(block)
		if len(pMatch) >= 2 {
			r.Snippet = stripHTMLTags(pMatch[1])
		}

		results = append(results, r)
	}
	return results
}

// extractBingText 从 Bing 页面提取纯文本（兜底）
func extractBingText(html string) string {
	re := regexp.MustCompile(`<script[^>]*>.*?</script>`)
	html = re.ReplaceAllString(html, "")
	re = regexp.MustCompile(`<style[^>]*>.*?</style>`)
	html = re.ReplaceAllString(html, "")
	text := stripHTMLTags(html)
	lines := strings.Split(text, "\n")
	var clean []string
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if len(line) > 20 {
			clean = append(clean, line)
		}
	}
	return strings.Join(clean, "\n")
}

// stripHTMLTags 简单移除 HTML 标签
func stripHTMLTags(s string) string {
	var b strings.Builder
	inTag := false
	for _, r := range s {
		if r == '<' {
			inTag = true
			continue
		}
		if r == '>' {
			inTag = false
			continue
		}
		if !inTag {
			b.WriteRune(r)
		}
	}
	return strings.TrimSpace(b.String())
}
// ToJSON 序列化工具列表为 JSON（给 LLM 用）
func (tr *ToolRegistry) ToJSON() string {
	tools := tr.List()
	data, _ := json.MarshalIndent(tools, "", "  ")
	return string(data)
}