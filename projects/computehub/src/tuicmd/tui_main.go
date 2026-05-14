// Command: go run ./cmd/tui (or build: go build -o computehub-tui ./cmd/tui)
//
// ComputeHub TUI - Full v2 API Integration
//
// Features (v2 full):
//   Dashboard  → 集群概览 (KPI卡片 + 实时指标)
//   Nodes      → 节点浏览器 (region/status/gpu-type 过滤 + 搜索)
//   NodeDetail → 节点详情 (8 GPU 雷达 + 完整指标)
//   GPUMon     → GPU 实时监控 (按型号聚合 + hot GPU 追踪)
//   Tasks      → 任务管理器 (list/submit/kill/cancel)
//   Alerts     → 告警面板 (severity/type 过滤)
//   History    → 历史趋势 (多项指标火花图)
//   Regions    → 全球算力地图 (9区域)
//   Health     → 系统健康检查
//   Shell      → OPC-Shell 传统模式

package tuicmd

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"sort"
	"strings"
	"time"
	"unicode"

	"golang.org/x/term"

	computeHubVersion "github.com/computehub/opc/src/version"
)

// ── ANSI ──
const (
	Reset   = "\033[0m"
	Bold    = "\033[1m"
	Dim     = "\033[2m"
	Italic  = "\033[3m"
	Red     = "\033[31m"
	Green   = "\033[32m"
	Yellow  = "\033[33m"
	Blue    = "\033[34m"
	Magenta = "\033[35m"
	Cyan    = "\033[36m"
	White   = "\033[37m"
	BgRed   = "\033[41m"
	BgGreen = "\033[42m"
	BgBlue  = "\033[44m"
	BgYellow = "\033[43m"
	ClrScr  = "\033[2J\033[H"
	SaveCur = "\033[s"
	RestCur = "\033[u"
)

// ── Width constant ──
const termW = 80

// ── Version ──
var appVersion = computeHubVersion.Short()

// ── History (for arrow-key recall) ──
var cmdHistory []string
var cmdHistIdx int = -1

const maxHistory = 64

// readLine reads a line from raw stdin with arrow-key history & cursor movement support.
func readLine(prompt string) string {
	fd := int(os.Stdin.Fd())
	old, err := term.MakeRaw(fd)
	if err != nil {
		// Fallback: read a line using bufio
		fmt.Print(prompt)
		s, _ := bufio.NewReader(os.Stdin).ReadString('\n')
		return strings.TrimSpace(s)
	}
	defer term.Restore(fd, old)

	fmt.Print(prompt)
	var buf []byte
	cursor := 0 // cursor position within buf (0 = before first char)
	histIdx := cmdHistIdx // local copy, -1 means fresh input

	// redrawLine redraws the input line from scratch at cursor position
	redrawLine := func() {
		fmt.Print("\r" + prompt + string(buf))
		// clear to end of line
		fmt.Print("\033[K")
		// move cursor back to actual position
		right := len(buf) - cursor
		if right > 0 {
			fmt.Printf("\033[%dD", right)
		}
	}

	for {
		var b [1]byte
		n, _ := os.Stdin.Read(b[:])
		if n == 0 {
			continue
		}
		ch := b[0]

		switch ch {
		case 3: // Ctrl+C
			os.Exit(0)
		case 4: // Ctrl+D
			return ""
		case 13, 10: // Enter
			fmt.Print("\r\n")
			line := string(buf)
			if line != "" {
				// Add to history (dedup last)
				if len(cmdHistory) == 0 || cmdHistory[len(cmdHistory)-1] != line {
					cmdHistory = append(cmdHistory, line)
					if len(cmdHistory) > maxHistory {
						cmdHistory = cmdHistory[1:]
					}
				}
				cmdHistIdx = len(cmdHistory)
			}
			return line
		case 1: // Ctrl+A → Home
			for cursor > 0 {
				fmt.Print("\033[D")
				cursor--
			}
		case 5: // Ctrl+E → End
			for cursor < len(buf) {
				fmt.Print("\033[C")
				cursor++
			}
		case 27: // ESC sequence
			var b2 [1]byte
			if n2, _ := os.Stdin.Read(b2[:]); n2 == 0 {
				continue
			}
			// Detect Alt+<key>: ESC <char>
			if b2[0] != '[' {
				// Alt+key — treat as normal char (e.g. Alt+b / Alt+f)
				// We just skip it since these are not common in this TUI
				continue
			}
			var b3 [1]byte
			if n3, _ := os.Stdin.Read(b3[:]); n3 == 0 {
				continue
			}
			switch b3[0] {
			case 'A': // Up arrow
				if histIdx <= 0 {
					histIdx = 0
				} else {
					histIdx--
				}
				if histIdx >= 0 && histIdx < len(cmdHistory) {
					buf = []byte(cmdHistory[histIdx])
					cursor = len(buf)
					redrawLine()
				}
			case 'B': // Down arrow
				if histIdx < len(cmdHistory)-1 {
					histIdx++
					buf = []byte(cmdHistory[histIdx])
					cursor = len(buf)
					redrawLine()
				} else {
					histIdx = len(cmdHistory)
					buf = nil
					cursor = 0
					redrawLine()
				}
			case 'C': // Right arrow
				if cursor < len(buf) {
					fmt.Print("\033[C")
					cursor++
				}
			case 'D': // Left arrow
				if cursor > 0 {
					fmt.Print("\033[D")
					cursor--
				}
			case 'H': // Home (ESC [ H)
				if cursor > 0 {
					fmt.Printf("\033[%dD", cursor)
					cursor = 0
				}
			case 'F': // End (ESC [ F)
				if cursor < len(buf) {
					n := len(buf) - cursor
					fmt.Printf("\033[%dC", n)
					cursor = len(buf)
				}
			case '1': // Home (ESC [ 1 ~) or PgUp (ESC [ 5 ~) or PgDn (ESC [ 6 ~) or End (ESC [ 4 ~)
				// Read the fourth byte to distinguish 1~ vs 5~ vs 6~ vs 4~
				var b4 [1]byte
				if n4, _ := os.Stdin.Read(b4[:]); n4 == 0 {
					continue
				}
				switch b4[0] {
				case '~':
					switch b3[0] {
					case '1': // Home
						if cursor > 0 {
							fmt.Printf("\033[%dD", cursor)
							cursor = 0
						}
					case '4': // End
						if cursor < len(buf) {
							n := len(buf) - cursor
							fmt.Printf("\033[%dC", n)
							cursor = len(buf)
						}
					case '5': // PgUp → go to beginning of line
						if cursor > 0 {
							fmt.Printf("\033[%dD", cursor)
							cursor = 0
						}
					case '6': // PgDn → go to end of line
						if cursor < len(buf) {
							n := len(buf) - cursor
							fmt.Printf("\033[%dC", n)
							cursor = len(buf)
						}
					}
				}
			case '4': // End (ESC [ 4 ~)
				var b4 [1]byte
				if n4, _ := os.Stdin.Read(b4[:]); n4 == 0 {
					continue
				}
				if b4[0] == '~' {
					if cursor < len(buf) {
						n := len(buf) - cursor
						fmt.Printf("\033[%dC", n)
						cursor = len(buf)
					}
				}
			case '5': // PgUp (ESC [ 5 ~)
				var b4 [1]byte
				if n4, _ := os.Stdin.Read(b4[:]); n4 == 0 {
					continue
				}
				if b4[0] == '~' {
					if cursor > 0 {
						fmt.Printf("\033[%dD", cursor)
						cursor = 0
					}
				}
			case '6': // PgDn (ESC [ 6 ~)
				var b4 [1]byte
				if n4, _ := os.Stdin.Read(b4[:]); n4 == 0 {
					continue
				}
				if b4[0] == '~' {
					if cursor < len(buf) {
						n := len(buf) - cursor
						fmt.Printf("\033[%dC", n)
						cursor = len(buf)
					}
				}
			case '3': // Delete (ESC [ 3 ~)
				if cursor < len(buf) {
					// Remove char at cursor
					buf = append(buf[:cursor], buf[cursor+1:]...)
					// Redraw from cursor position
					fmt.Print("\033[P")
				}
				var b4 [1]byte
				os.Stdin.Read(b4[:]) // consume ~
			}
		case 127, 8: // Backspace
			if cursor > 0 {
				cursor--
				buf = append(buf[:cursor], buf[cursor+1:]...)
				// Move cursor left, push rest, clean up
				fmt.Print("\033[D")
				fmt.Print(string(buf[cursor:]) + " ")
				fmt.Printf("\033[%dD", len(buf)-cursor+1)
			}
		default:
			if ch >= 32 {
				// Insert at cursor position
				buf = append(buf, 0)
				copy(buf[cursor+1:], buf[cursor:])
				buf[cursor] = ch
				// Write char + rest of string
				fmt.Print(string(buf[cursor:]))
				cursor++
				// Move cursor back
				right := len(buf) - cursor
				if right > 0 {
					fmt.Printf("\033[%dD", right)
				}
			}
		}
	}
}

// ── Data Types ──

// v1 /api/status
type SystemStatus struct {
	Kernel      KernelStatus      `json:"kernel"`
	Pipeline    PipelineStatus    `json:"pipeline"`
	Executor    ExecutorStatus    `json:"executor"`
	GeneStore   GeneStoreStatus   `json:"geneStore"`
	NodeManager NodeManagerStatus `json:"nodeManager"`
	Uptime      string            `json:"uptime"`
}
type KernelStatus struct {
	Status          string `json:"status"`
	ScheduleLatency string `json:"schedule_latency"`
	QueueDepth      int    `json:"queue_depth"`
}
type PipelineStatus struct {
	Status        string `json:"status"`
	Interceptions int    `json:"interceptions"`
	PureLatency   string `json:"pure_latency"`
}
type ExecutorStatus struct {
	Status           string  `json:"status"`
	VerificationRate float64 `json:"verification_rate"`
	SandboxPath      string  `json:"sandbox_path"`
}
type GeneStoreStatus struct {
	Size       int     `json:"size"`
	RecallRate float64 `json:"recall_rate"`
}
type NodeManagerStatus struct {
	TotalNodes  int          `json:"total_nodes"`
	OnlineNodes int          `json:"online_nodes"`
	TotalTasks  int          `json:"total_tasks"`
	ActiveTasks int          `json:"active_tasks"`
	Nodes       []NodeStatus `json:"nodes"`
}
type NodeStatus struct {
	NodeID      string             `json:"node_id"`
	Region      string             `json:"region"`
	GPUType     string             `json:"gpu_type"`
	Status      string             `json:"status"`
	ActiveTasks int                `json:"active_tasks"`
	CPUUtil     float64            `json:"cpu_utilization"`
	GPUMetrics  []GPUMetricSummary `json:"gpu_metrics,omitempty"`
}
type GPUMetricSummary struct {
	Utilization float64 `json:"utilization"`
	Temperature float64 `json:"temperature"`
	MemoryUsed  float64 `json:"memory_used_gb"`
}

// v2 API types
type V2Health struct {
	Status          string `json:"status"`
	OnlineNodes     int    `json:"online_nodes"`
	TotalNodes      int    `json:"total_nodes"`
	TotalGPUs       int    `json:"total_gpus"`
	TotalTFLOPS     float64 `json:"total_tflops"`
	HealthyRegions  int    `json:"healthy_regions"`
	DegradedRegions int    `json:"degraded_regions"`
	TotalAlerts     int    `json:"total_alerts"`
	Timestamp       string `json:"timestamp"`
	Visualization   struct {
		GlobalMap  string `json:"global_map"`
		GPURealtime string `json:"gpu_realtime"`
		Nodes      string `json:"nodes"`
		WebSocket  string `json:"websocket"`
	} `json:"visualization"`
}

type V2Node struct {
	ID              string   `json:"id"`
	Region          string   `json:"region"`
	Country         string   `json:"country"`
	IPAddress       string   `json:"ip_address"`
	Status          string   `json:"status"`
	GPUType         string   `json:"gpu_type"`
	GPUs            []V2GPU  `json:"gpus"`
	CPUCores        int      `json:"cpu_cores"`
	MemoryGB        float64  `json:"memory_gb"`
	Load            float64  `json:"load"`
	NetworkLatency  float64  `json:"network_latency_ms"`
	ActiveTasks     int      `json:"active_tasks"`
	MaxTasks        int      `json:"max_tasks"`
	SuccessRate     float64  `json:"success_rate"`
	HealthStatus    string   `json:"health_status"`
	RegisteredAt    string   `json:"registered_at"`
}

type V2GPU struct {
	ID            string  `json:"id"`
	Model         string  `json:"model"`
	Utilization   float64 `json:"utilization"`
	Temperature   float64 `json:"temperature"`
	MemoryUsedGB  float64 `json:"memory_used_gb"`
	MemoryTotalGB float64 `json:"memory_total_gb"`
	PowerWatts    float64 `json:"power_watts"`
	Status        string  `json:"status"`
}

type V2NodesResponse struct {
	Nodes       []V2Node `json:"nodes"`
	OnlineNodes int      `json:"online_nodes"`
	OfflineNodes int     `json:"offline_nodes"`
	TotalNodes  int      `json:"total_nodes"`
	Regions     int      `json:"regions"`
	Timestamp   string   `json:"timestamp"`
}

type V2Region struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Country     string `json:"country"`
	Lat         float64 `json:"lat"`
	Lng         float64 `json:"lng"`
	TotalNodes  int     `json:"total_nodes"`
	OnlineNodes int     `json:"online_nodes"`
	TotalGPUs   int     `json:"total_gpus"`
	TotalCPUCores int   `json:"total_cpu_cores"`
	TotalRAMGB  float64 `json:"total_ram_gb"`
	TotalTFLOPS float64 `json:"total_tflops"`
	AvgGPUUtil  float64 `json:"avg_gpu_util"`
	AvgTemp     float64 `json:"avg_temp"`
	ActiveTasks int     `json:"active_tasks"`
	Status      string  `json:"status"`
	Alerts      []interface{} `json:"alerts"`
	Nodes       []V2Node `json:"nodes"`
}

type V2MapResponse struct {
	ActiveTasks int         `json:"active_tasks"`
	AvgGPUUtil  float64     `json:"avg_gpu_util"`
	OnlineNodes int         `json:"online_nodes"`
	Regions     map[string]*V2Region `json:"regions"`
	Timestamp   string      `json:"timestamp"`
	TotalGPUs   int         `json:"total_gpus"`
	TotalNodes  int         `json:"total_nodes"`
	TotalRegions int        `json:"total_regions"`
	TotalTFLOPS float64     `json:"total_tflops"`
}

type V2GPURealtimeEntry struct {
	NodeID     string  `json:"node_id"`
	GPUId      string  `json:"gpu_id"`
	Model      string  `json:"model"`
	Utilization float64 `json:"utilization"`
	Temperature float64 `json:"temperature"`
	MemoryUsed float64 `json:"memory_used_gb"`
	Timestamp  string  `json:"timestamp"`
}

type V2GPURealtimeResponse struct {
	Batches    int      `json:"batches"`
	ColdGPUs   int      `json:"cold_gpus"`
	GPUs       []V2GPURealtimeEntry `json:"gpus"`
	HotGPUs    int      `json:"hot_gpus"`
	Timestamp  string   `json:"timestamp"`
	TotalGPUs  int      `json:"total_gpus"`
}

type V2Alert struct {
	AlertID   string `json:"alert_id"`
	Severity  string `json:"severity"`
	Type      string `json:"type"`
	Message   string `json:"message"`
	Source    string `json:"source"`
	NodeID    string `json:"node_id"`
	Timestamp string `json:"timestamp"`
}

type V2AlertsResponse struct {
	Alerts     []V2Alert `json:"alerts"`
	Critical   int       `json:"critical"`
	Info       int       `json:"info"`
	Warning    int       `json:"warning"`
	Timestamp  string    `json:"timestamp"`
	Total      int       `json:"total"`
}

type V2HistoryEntry struct {
	Timestamp    string  `json:"timestamp"`
	TotalNodes   float64 `json:"total_nodes"`
	OnlineNodes  float64 `json:"online_nodes"`
	TotalGPUs    float64 `json:"total_gpus"`
	TotalTFLOPS  float64 `json:"total_tflops"`
	AvgGPUUtil   float64 `json:"avg_gpu_util"`
	ActiveTasks  float64 `json:"active_tasks"`
	MemoryUsedGB float64 `json:"memory_used_gb"`
}

type V2HistoryResponse struct {
	History   []V2HistoryEntry `json:"history"`
	Timestamp string           `json:"timestamp"`
}

type TUIRequest struct {
	ID      string `json:"id"`
	Command string `json:"command"`
}
type TUIResponse struct {
	ID       string      `json:"id"`
	Success  bool        `json:"success"`
	Data     interface{} `json:"data,omitempty"`
	Error    string      `json:"error,omitempty"`
	Duration string      `json:"duration,omitempty"`
	Verified bool        `json:"verified"`
}

// ── State ──
type AppState struct {
	status        *SystemStatus
	v2Nodes       []V2Node
	v2Health      *V2Health
	v2Map         *V2MapResponse
	v2GPUs        []V2GPURealtimeEntry
	v2Alerts      []V2Alert
	v2History     []V2HistoryEntry
	lastErr       string
	lastUpdate    time.Time
}

// ── HTTP helpers ──
var gw = "http://localhost:8282"

func httpGetJSON(url string, target interface{}) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	return json.Unmarshal(body, target)
}

func httpPostJSON(url string, payload interface{}) (*TUIResponse, error) {
	data, _ := json.Marshal(payload)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(data))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var tr TUIResponse
	if err := json.Unmarshal(body, &tr); err != nil {
		return nil, err
	}
	return &tr, nil
}

func fetchStatus() *SystemStatus {
	var s SystemStatus
	if err := httpGetJSON(gw+"/api/status", &s); err != nil {
		return nil
	}
	return &s
}

func fetchV2Health() *V2Health {
	var h V2Health
	if err := httpGetJSON(gw+"/api/v2/health", &h); err != nil {
		return nil
	}
	return &h
}

func fetchV2Nodes() []V2Node {
	var resp V2NodesResponse
	if err := httpGetJSON(gw+"/api/v2/nodes", &resp); err != nil {
		return nil
	}
	return resp.Nodes
}

func fetchV2Map() *V2MapResponse {
	var m V2MapResponse
	if err := httpGetJSON(gw+"/api/v2/map/global", &m); err != nil {
		return nil
	}
	return &m
}

func fetchV2Alerts() []V2Alert {
	var resp V2AlertsResponse
	if err := httpGetJSON(gw+"/api/v2/alerts", &resp); err != nil {
		return nil
	}
	return resp.Alerts
}

func fetchV2GPUs() []V2GPURealtimeEntry {
	var resp V2GPURealtimeResponse
	if err := httpGetJSON(gw+"/api/v2/gpu/realtime", &resp); err != nil {
		return nil
	}
	return resp.GPUs
}

func fetchV2History() []V2HistoryEntry {
	var resp V2HistoryResponse
	if err := httpGetJSON(gw+"/api/v2/history", &resp); err != nil {
		return nil
	}
	return resp.History
}

// ── Task list (v1) ──

type TaskListInfo struct {
	TaskID      string `json:"task_id"`
	Source      string `json:"source"`
	Priority    int    `json:"priority"`
	Status      string `json:"status"`
	Retries     int    `json:"retries"`
	CreatedAt   string `json:"created_at"`
	SubmittedAt string `json:"submitted_at"`
	NodeIP      string `json:"node_ip"`
}

func fetchTaskList() map[string][]TaskListInfo {
	url := gw + "/api/v1/tasks/list"
	resp, err := http.Get(url)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	// The response is wrapped in a TUIResponse envelope
	var wrapper struct {
		Success bool                      `json:"success"`
		Data    map[string][]TaskListInfo `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&wrapper); err != nil {
		return nil
	}
	if !wrapper.Success {
		return nil
	}
	return wrapper.Data
}

func fetchQueueDepth() int {
	s := fetchStatus()
	if s == nil {
		return -1
	}
	return s.Kernel.QueueDepth
}

// ── Node management helpers ──

type addNodeResponse struct {
	Success bool   `json:"success"`
	Error   string `json:"error"`
}

func registerNode(nodeID, gpuType, region string, cpuCores int, memoryGB float64) error {
	payload := map[string]interface{}{
		"node_id":   nodeID,
		"gpu_type":  gpuType,
		"region":    region,
		"cpu_cores": cpuCores,
		"memory_gb": memoryGB,
		"status":    "online",
	}
	data, _ := json.Marshal(payload)
	resp, err := http.Post(gw+"/api/v1/nodes/register", "application/json", bytes.NewBuffer(data))
	if err != nil {
		return fmt.Errorf("connection failed: %w", err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var ar addNodeResponse
	if err := json.Unmarshal(body, &ar); err != nil {
		return fmt.Errorf("parse error: %w", err)
	}
	if !ar.Success {
		return fmt.Errorf("%s", ar.Error)
	}
	return nil
}

type unregisterResponse struct {
	Success bool   `json:"success"`
	Error   string `json:"error"`
}

func unregisterNode(nodeID string) error {
	payload := map[string]string{"node_id": nodeID}
	data, _ := json.Marshal(payload)
	resp, err := http.Post(gw+"/api/v1/nodes/unregister", "application/json", bytes.NewBuffer(data))
	if err != nil {
		return fmt.Errorf("connection failed: %w", err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var ur unregisterResponse
	if err := json.Unmarshal(body, &ur); err != nil {
		return fmt.Errorf("parse error: %w", err)
	}
	if !ur.Success {
		return fmt.Errorf("%s", ur.Error)
	}
	return nil
}

// ── Color helpers ──
func statusColor(s string) string {
	switch strings.ToLower(s) {
	case "online", "healthy", "running", "active", "ready", "ok", "nominal":
		return Green + Bold + s + Reset
	case "offline", "unhealthy", "critical", "error", "no", "fail":
		return Red + Bold + s + Reset
	case "degraded", "warning", "busy":
		return Yellow + Bold + s + Reset
	case "idle":
		return Green + s + Reset
	default:
		return White + s + Reset
	}
}

func pctColor(v float64) string {
	if v > 90 { return Red + Bold + fmt.Sprintf("%5.1f%%", v) + Reset }
	if v > 70 { return Yellow + fmt.Sprintf("%5.1f%%", v) + Reset }
	return Green + fmt.Sprintf("%5.1f%%", v) + Reset
}

func tempColor(t float64) string {
	if t > 85 { return Red + Bold + fmt.Sprintf("%.0f°C", t) + Reset }
	if t > 70 { return Yellow + fmt.Sprintf("%.0f°C", t) + Reset }
	return Green + fmt.Sprintf("%.0f°C", t) + Reset
}

func memColor(used, total float64) string {
	r := used / total
	if r > 0.9 { return Red + Bold + fmt.Sprintf("%.0f/%.0fGB", used, total) + Reset }
	if r > 0.7 { return Yellow + fmt.Sprintf("%.0f/%.0fGB", used, total) + Reset }
	return Blue + fmt.Sprintf("%.0f/%.0fGB", used, total) + Reset
}

// visiblePad 对字符串加颜色后按可见宽度右填充，确保表格对齐
func visiblePad(s, color, reset string, width int) string {
	p := width - len(s)
	if p < 0 { p = 0 }
	return color + s + reset + strings.Repeat(" ", p)
}

func powerColor(w float64) string {
	if w > 430 { return Red + Bold + fmt.Sprintf("%.0fW", w) + Reset }
	if w > 370 { return Yellow + fmt.Sprintf("%.0fW", w) + Reset }
	return White + fmt.Sprintf("%.0fW", w) + Reset
}

func clearScreen() {
	fmt.Print("\033[2J\033[H\033[3J") // 清屏 + 清滚动缓冲区 + 归位
}

func printLine(c, s string) {
	fmt.Println(c + s + Reset)
}

func printf(c string, format string, args ...interface{}) {
	fmt.Print(c)
	fmt.Printf(format, args...)
	fmt.Print(Reset)
}

func renderBar(val, max float64, width int) string {
	if max <= 0 { return strings.Repeat("░", width) }
	filled := int(val / max * float64(width))
	if filled > width { filled = width }
	if filled < 0 { filled = 0 }
	color := Green
	r := val / max
	if r > 0.85 { color = Red }
	if r > 0.65 { color = Yellow }
	return color + strings.Repeat("█", filled) + Reset + Dim + strings.Repeat("░", width-filled) + Reset
}

func printHeader(title, subtitle string) {
	w := termW - 6
	fmt.Println()
	fmt.Printf("%s ┌─%s┐%s\n", Cyan+Bold, strings.Repeat("─", w), Reset)
	fmt.Printf("%s │ %s%s", Cyan+Bold, title, Reset)
	padding := w - len(title) - len(subtitle) - 2
	if padding < 0 { padding = 0 }
	fmt.Print(strings.Repeat(" ", padding))
	fmt.Printf("%s%s%s", Dim, subtitle, Reset)
	fmt.Printf("%s │%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s └─%s┘%s\n", Cyan+Bold, strings.Repeat("─", w), Reset)
}

func printPrompt() {
	fmt.Printf("\n%s [r]刷新  [q]返回/退出  输入命令或选择%s\n> ", Dim, Reset)
}

func printHelp() {
	fmt.Println()
	fmt.Printf("%s ComputeHub TUI v%s%s\n", Yellow+Bold, appVersion, Reset)
	fmt.Printf(" %s━━━ 快捷键 ━━━%s\n", Cyan+Bold, Reset)
	fmt.Printf("  %-20s %s\n", "d / dashboard", "📊 系统仪表板")
	fmt.Printf("  %-20s %s\n", "n / nodes", "🔌 节点浏览器")
	fmt.Printf("  %-20s %s\n", "g / gpu / gpumon", "🎮 GPU 实时监控")
	fmt.Printf("  %-20s %s\n", "r / map / regions", "🌍 全球算力地图")
	fmt.Printf("  %-20s %s\n", "t / tasks", "📋 任务管理器")
	fmt.Printf("  %-20s %s\n", "a / alerts", "🔔 告警面板")
	fmt.Printf("  %-20s %s\n", "h / history", "📈 历史趋势")
	fmt.Printf("  %-20s %s\n", "health / chk", "🏥 系统健康检查")
	fmt.Printf("  %-20s %s\n", "shell", "💻 OPC-Shell (Legacy)")
	fmt.Printf("  %-20s %s\n", "? / help", "📖 帮助")
	fmt.Printf("  %-20s %s\n", "q / quit / exit", "👋 退出")
	fmt.Println()
}

// ═══════════════════════════════════════════
// DASHBOARD — 集群总览（手动刷新）
// ═══════════════════════════════════════════

func screenDashboard(state *AppState) {
	renderDashboard(state)

	for {
		input := readLine("\r> ")
		if input == "" { continue }
		cmd := strings.ToLower(input)
		switch {
		case cmd == "q" || cmd == "quit" || cmd == "exit":
			return
		case cmd == "r" || cmd == "refresh" || cmd == "dashboard" || cmd == "d":
			fmt.Print("\n" + Dim + strings.Repeat("─", 80) + Reset + "\n")
			renderDashboard(state)
		case cmd == "n" || cmd == "nodes":
			screenNodes(state)
		case cmd == "g" || cmd == "gpu" || cmd == "gpumon":
			screenGPUMonitor(state)
		case cmd == "map" || cmd == "regions" || cmd == "region":
			screenRegions(state)
		case cmd == "t" || cmd == "tasks":
			screenTasks(state)
		case cmd == "a" || cmd == "alerts":
			screenAlerts(state)
		case cmd == "h" || cmd == "history":
			screenHistory(state)
		case cmd == "health" || cmd == "chk":
			screenHealth(state)
		case cmd == "shell":
			screenShell(state)
		case cmd == "?" || cmd == "help":
			printHelp()
		default:
			fmt.Printf("%s \u672a\u77e5\u547d\u4ee4: %s%s\n", Red, input, Reset)
		}
		printPrompt()
	}
}

// renderDashboard — 绘制单帧仪表板内容（不含清屏和循环控制）
func renderDashboard(state *AppState) {
	s := fetchStatus()
	h := fetchV2Health()
	nodes := fetchV2Nodes()
	if s == nil && h == nil {
		printf(Red+Bold, " ⚠ 无法连接网关 %s\n", gw)
		printPrompt()
		return
	}
	state.status = s
	state.v2Health = h
	state.v2Nodes = nodes
	state.lastUpdate = time.Now()

	// KPI 卡片
	onlineNodes := 0
	totalNodes := 0
	totalGPUs := 0
	totalTFLOPS := 0.0
	avgUtil := 0.0

	if h != nil {
		onlineNodes = h.OnlineNodes
		totalNodes = h.TotalNodes
		totalGPUs = h.TotalGPUs
		totalTFLOPS = h.TotalTFLOPS
	} else if s != nil {
		onlineNodes = s.NodeManager.OnlineNodes
		totalNodes = s.NodeManager.TotalNodes
	}

	// GPU 型号分布
	gpuModelCount := make(map[string]int)
	gpuModelUtil := make(map[string]float64)
	totalGPUCount := 0
	for _, n := range nodes {
		for _, g := range n.GPUs {
			model := g.Model
			gpuModelCount[model]++
			gpuModelUtil[model] += g.Utilization
			avgUtil += g.Utilization
			totalGPUCount++
		}
	}
	if totalGPUCount > 0 {
		avgUtil /= float64(totalGPUCount)
	}

	printHeader("📊 ComputeHub 系统仪表板", fmt.Sprintf("v%s  %s", appVersion, state.lastUpdate.Format("15:04:05")))

	// ── Row 1: Core KPI ──
	fmt.Println()
	fmt.Printf(" %s━━━ 核心指标 ━━━%s\n", Cyan+Bold, Reset)
	fmt.Printf(" %-16s %s  %-16s %s  %-16s\n",
		padded("● 节点", 12)+": "+statusColor(fmt.Sprintf("%d/%d", onlineNodes, totalNodes)),
		"│",
		padded("● GPU", 12)+": "+Cyan+Bold+fmt.Sprintf("%d", totalGPUs)+Reset,
		"│",
		padded("● 总算力", 12)+": "+Magenta+Bold+fmt.Sprintf("%.0fK TFLOPS", totalTFLOPS/1000)+Reset)
	fmt.Printf(" %s\n", padded("● 平均GPU利用率", 12)+": "+pctColor(avgUtil))

	// ── Row 2: System Status ──
	fmt.Println()
	fmt.Printf(" %s━━━ 系统状态 ━━━%s\n", Cyan+Bold, Reset)
	if s != nil {
		fmt.Printf("  内核: %s  队列: %d 调度延迟: %s\n",
			statusColor(s.Kernel.Status), s.Kernel.QueueDepth, s.Kernel.ScheduleLatency)
		fmt.Printf("  执行器: %s  沙箱: %s  验证率: %.0f%%\n",
			statusColor(s.Executor.Status), s.Executor.SandboxPath, s.Executor.VerificationRate*100)
	}
	if h != nil {
		fmt.Printf("  健康区域: %s%d%s 告警: %s  运行区域: %d\n",
			Green, h.HealthyRegions, Reset,
			statusColor(fmt.Sprintf("%d", h.TotalAlerts)),
			h.HealthyRegions+h.DegradedRegions)
	}
	if s != nil {
		fmt.Printf("  运行时间: %s  基因库: %d entries (召回率 %.0f%%)\n",
			s.Uptime, s.GeneStore.Size, s.GeneStore.RecallRate*100)
	}

	// ── GPU 型号分布 ──
	fmt.Println()
	fmt.Printf(" %s━━━ GPU 型号分布 ━━━%s\n", Cyan+Bold, Reset)

	// Sort by count
	type gpuModelStat struct { name string; count int; util float64 }
	var stats []gpuModelStat
	for m, c := range gpuModelCount {
		u := gpuModelUtil[m] / float64(c)
		stats = append(stats, gpuModelStat{m, c, u})
	}
	sort.Slice(stats, func(i, j int) bool { return stats[i].count > stats[j].count })

	for _, st := range stats {
		bar := renderBar(st.util, 100, 30)
		fmt.Printf("  %s%-10s%s %sx%3d%s %s %.1f%%\n",
			Magenta, st.name, Reset, Dim, st.count, Reset, bar, st.util)
	}

	// ── 活跃节点列表 (top 10 by tasks) ──
	fmt.Println()
	fmt.Printf(" %s━━━ 活跃节点 Top 10 ━━━%s\n", Cyan+Bold, Reset)
	type nodeTask struct { id, region, gpu string; tasks int; util, temp float64; status string }
	var ntList []nodeTask
	for _, n := range nodes {
		if len(ntList) >= 10 { break }
		avgU, avgT := 0.0, 0.0
		for _, g := range n.GPUs {
			avgU += g.Utilization
			avgT += g.Temperature
		}
		if len(n.GPUs) > 0 { avgU /= float64(len(n.GPUs)); avgT /= float64(len(n.GPUs)) }
		ntList = append(ntList, nodeTask{n.ID, n.Region, n.GPUType, n.ActiveTasks, avgU, avgT, n.Status})
	}
	sort.Slice(ntList, func(i, j int) bool { return ntList[i].tasks > ntList[j].tasks })

	fmt.Printf("  %-24s │ %-10s │ %-8s │ %-6s │ %-8s │ %-8s\n", "Node ID", "Region", "GPU", "Tasks", "GPU Ut", "Temp")
	for _, nt := range ntList {
		c := White
		if nt.tasks > 200 { c = Red }
		if nt.tasks > 100 { c = Yellow }
		fmt.Printf("  %s%-24s%s │ %-10s │ %-8s │ %s%4d%s    │ %s  │ %s\n",
			c, nt.id, Reset, nt.region, nt.gpu,
			Yellow+Bold, nt.tasks, Reset, pctColor(nt.util), tempColor(nt.temp))
	}

	// ── 最热 GPU ──
	fmt.Println()
	fmt.Printf(" %s━━━ 🔥 最热 GPU Top 5 ━━━%s\n", Red+Bold, Reset)
	type hotGPU struct { node, gpu, model string; temp, util float64 }
	var hotList []hotGPU
	for _, n := range nodes {
		for _, g := range n.GPUs {
			if g.Temperature > 75 {
				hotList = append(hotList, hotGPU{n.ID, g.ID, g.Model, g.Temperature, g.Utilization})
			}
		}
	}
	sort.Slice(hotList, func(i, j int) bool { return hotList[i].temp > hotList[j].temp })
	if len(hotList) > 5 { hotList = hotList[:5] }

	if len(hotList) > 0 {
		fmt.Printf("  %-24s │ %-8s │ %-6s │ %-8s │ %-8s\n", "Node", "GPU", "Model", "Temp", "Util")
		for _, hg := range hotList {
			fmt.Printf("  %s%-24s%s │ %s%-8s%s │ %-6s │ %s │ %s\n",
				Red, hg.node, Reset,
				Red, hg.gpu, Reset,
				hg.model,
				tempColor(hg.temp),
				pctColor(hg.util))
		}
	} else {
		fmt.Printf("  %s✅ 所有 GPU 温度正常%s\n", Green, Reset)
	}

	printPrompt()
}

func padded(s string, n int) string {
	if len(s) >= n { return s }
	return s + strings.Repeat(" ", n-len(s))
}

// ═══════════════════════════════════════════
// NODE BROWSER — 节点浏览器
// ═══════════════════════════════════════════

func screenNodes(state *AppState) {
	clearScreen()
	nodes := fetchV2Nodes()
	if nodes == nil {
		printf(Red+Bold, " ⚠ 无法获取节点数据\n")
		printPrompt()
		return
	}
	state.v2Nodes = nodes

	// Statistics
	totalOn := 0; totalOff := 0
	regionCount := make(map[string]int)
	statusCount := make(map[string]int)
	gpuTypeCount := make(map[string]int)
	for _, n := range nodes {
		if n.Status == "online" { totalOn++ } else { totalOff++ }
		regionCount[n.Region]++
		statusCount[n.Status]++
		gpuTypeCount[n.GPUType]++
	}

	printHeader("🔌 节点浏览器", fmt.Sprintf("%d online / %d total", totalOn, len(nodes)))

	fmt.Printf(" %sRegions:%s ", Cyan, Reset)
	rs := make([]string, 0, len(regionCount))
	for r := range regionCount { rs = append(rs, r) }
	sort.Strings(rs)
	for _, r := range rs {
		fmt.Printf("%s%s:%d%s ", Dim, r, regionCount[r], Reset)
	}
	fmt.Println()
	fmt.Printf(" %sGPU Types:%s ", Magenta, Reset)
	for g, c := range gpuTypeCount {
		fmt.Printf("%s%s:%d%s ", Dim, g, c, Reset)
	}
	fmt.Println()
	fmt.Printf(" %sStatus:%s ", Yellow, Reset)
	for s, c := range statusCount {
		fmt.Printf("%s", statusColor(fmt.Sprintf("%s:%d", s, c)))
		fmt.Print(" ")
	}
	fmt.Println()
	fmt.Println()

	// Table header (9 columns: NodeID | Region | GPU | Health | Tasks | IP | JoinTime | Lat | GPU)
		fmt.Printf(" %s%-20s │ %-10s │ %-10s │ %-8s │ %-6s │ %-12s │ %-8s │ %-8s │ %s%s\n",
		White+Bold, "Node ID", "Region", "GPU Type", "Health", "Tasks", "IP", "Join", "Lat(ms)", "GPU Ut/Temp"+Reset)
	fmt.Printf(" %s%s%s\n", Dim, strings.Repeat("─", 108), Reset)

	for _, n := range nodes {
		avgU, avgT := 0.0, 0.0
		for _, g := range n.GPUs {
			avgU += g.Utilization
			avgT += g.Temperature
		}
		if len(n.GPUs) > 0 { avgU /= float64(len(n.GPUs)); avgT /= float64(len(n.GPUs)) }

		c := White
		if n.Status == "offline" { c = Red }
		if avgU > 80 || avgT > 80 { c = Yellow }

		healthStr := n.HealthStatus
		if healthStr == "" { healthStr = n.Status }

		// Extract join time from registered_at (ISO 8601)
		regTime := "—"
		if n.RegisteredAt != "" {
			if t, ok := extractTime(n.RegisteredAt); ok {
				regTime = t
			}
		}

		ip := n.IPAddress
		if ip == "" { ip = "—" }

		fmt.Printf(" %s%-20s%s │ %-10s │ %-10s │ %s │ %s%4d%s  │ %-12s │ %-8s │ %s%7.0f%s │ %s / %s\n",
			c, truncate(n.ID, 20), Reset,
			n.Region, n.GPUType,
			statusColor(healthStr),
			Yellow+Bold, n.ActiveTasks, Reset,
			Dim+ip+Reset,
			Dim+regTime+Reset,
			c, n.NetworkLatency, Reset,
			pctColor(avgU), tempColor(avgT))
	}

	fmt.Println()
	fmt.Printf(" %s输入节点ID查看详情 | d + 节点 ID 删除 | a 新增 | Enter 返回%s\n", Yellow, Reset)
	fmt.Printf(" node> ")
	input := readLine("")
	input = strings.TrimSpace(input)

	if input == "" {
		return
	}
	if input == "q" || input == "quit" || input == "exit" {
		return
	}

	// Add node
	if strings.ToLower(input) == "a" || strings.ToLower(input) == "add" || strings.ToLower(input) == "new" {
		fmt.Printf("\n")
		fmt.Printf(" %s━━━ 新增节点 ━━━%s\n", Cyan+Bold, Reset)
		fmt.Printf(" %s输入节点信息（直接 Enter 跳过可选字段）%s\n\n", Yellow, Reset)
		fmt.Printf(" 节点ID > ")
		nid := readLine("")
		if nid == "" {
			fmt.Printf(" %s❌ 节点 ID 不能为空%s\n", Red+Bold, Reset)
		} else {
			fmt.Printf(" GPU 类型 (默认 H100) > ")
			gpu := readLine("")
			if gpu == "" { gpu = "H100" }
			fmt.Printf(" 区域 (默认 cn-east) > ")
			region := readLine("")
			if region == "" { region = "cn-east" }
			fmt.Printf(" CPU 核心 (默认 16) > ")
			cpuStr := readLine("")
			cpu := 16
			if cpuStr != "" { fmt.Sscanf(cpuStr, "%d", &cpu) }
			fmt.Printf(" 内存 (默认 32 GB) > ")
			memStr := readLine("")
			mem := 32.0
			if memStr != "" { fmt.Sscanf(memStr, "%f", &mem) }
			registerNode(nid, gpu, region, cpu, mem)
		}
		fmt.Printf("\n %s按 Enter 返回%s", Yellow, Reset)
		readLine("\r")
		return
	}

	// Delete node: check for 'd <id>' or 'delete <id>' format
	if strings.HasPrefix(strings.ToLower(input), "d ") || strings.HasPrefix(strings.ToLower(input), "delete ") {
		parts := strings.Fields(input)
		if len(parts) >= 2 {
			targetNode := parts[len(parts)-1] // get last field as node ID
			fmt.Printf("\n %s正在删除节点 %s...%s", Yellow, targetNode, Reset)
			if err := unregisterNode(targetNode); err != nil {
				fmt.Printf("\n %s❌ 删除失败: %v%s\n", Red+Bold, err, Reset)
			} else {
				fmt.Printf("\n %s✅ 节点 %s 已删除%s\n", Green+Bold, targetNode, Reset)
			}
			fmt.Printf("\n %s按 Enter 返回%s", Yellow, Reset)
			readLine("\r")
			return
		}
	}

	// View node detail
	if input != "" {
		screenNodeDetail(state, input)
		// Return to node list
		fmt.Printf("\n %s按 Enter 返回%s", Yellow, Reset)
		readLine("\r")
		return
	}
}

func truncate(s string, n int) string {
	if len(s) <= n { return s }
	return s[:n-1] + "…"
}

// extractTime extracts "MM-DD HH:MM" from an ISO 8601 timestamp like "2026-05-13T18:11:00Z"
func extractTime(iso string) (string, bool) {
	// Try parsing standard format
	t, err := time.Parse(time.RFC3339, iso)
	if err != nil {
		// Try with fractional seconds
		t, err = time.Parse("2006-01-02T15:04:05.000Z07:00", iso)
		if err != nil {
			// Fallback: grab substring if it looks like ISO format
			if len(iso) >= 16 {
				return iso[11:16], true
			}
			return "", false
		}
	}
	return t.Format("01-02 15:04"), true
}

// ═══════════════════════════════════════════
// NODE DETAIL — 节点详情
// ═══════════════════════════════════════════

func screenNodeDetail(state *AppState, prefix string) {
	clearScreen()
	nodes := fetchV2Nodes()
	if nodes == nil {
		printf(Red+Bold, " ⚠ 无法获取节点数据\n")
		return
	}

	// Find matching node
	var node *V2Node
	for i := range nodes {
		if nodes[i].ID == prefix || strings.HasPrefix(nodes[i].ID, prefix) {
			node = &nodes[i]
			break
		}
	}
	if node == nil {
		printf(Red+Bold, " ⚠ 节点 '%s' 未找到\n", prefix)
		return
	}

	printHeader(fmt.Sprintf("🔍 节点详情: %s", node.ID), fmt.Sprintf("区域: %s (%s)", node.Region, node.Country))

	// General info
	fmt.Printf("\n %s━━━ 基本信息 ━━━%s\n", Cyan+Bold, Reset)
	fmt.Printf("  IP: %-15s 状态: %s  健康: %s  注册: %s\n",
		node.IPAddress,
		statusColor(node.Status),
		statusColor(node.HealthStatus),
		node.RegisteredAt[:10])
	fmt.Printf("  CPU: %d Cores  RAM: %.0f GB  负载: %s%%  延迟: %.0fms  成功率: %s%%\n",
		node.CPUCores, node.MemoryGB,
		pctColor(node.Load), node.NetworkLatency,
		pctColor(node.SuccessRate*100))

	// Task info
	fmt.Printf("\n %s━━━ 任务状态 ━━━%s\n", Cyan+Bold, Reset)
	taskBar := renderBar(float64(node.ActiveTasks), float64(node.MaxTasks), 20)
	fmt.Printf("  任务: %s%d / %d%s %s\n",
		Yellow+Bold, node.ActiveTasks, node.MaxTasks, Reset, taskBar)

	// GPU radar
	fmt.Printf("\n %s━━━ GPU 雷达 ━━━%s\n", Cyan+Bold, Reset)
	fmt.Printf("  %-10s │ %-6s │ %-6s │ %-16s │ %-8s │ %-8s │ %s\n",
		"GPU ID", "Model", "Status", "Utilization", "Temp", "Memory", "Power")
	fmt.Printf("  %s%s\n", Dim, strings.Repeat("─", 86))

	for _, g := range node.GPUs {
		bar := renderBar(g.Utilization, 100, 12)
		memBar := renderBar(g.MemoryUsedGB, g.MemoryTotalGB, 8)

		fmt.Printf("  %-10s │ %-6s │ %s │ %s %s%s%5.1f%% │ %s %s │ %s\n",
			g.ID,
			g.Model,
			statusColor(g.Status),
			bar, Dim, Reset,
			g.Utilization,
			memBar,
			memColor(g.MemoryUsedGB, g.MemoryTotalGB),
			powerColor(g.PowerWatts))
	}

	fmt.Printf("\n %s[d] 删除此节点 | 按 Enter 返回%s\n", Yellow, Reset)
}

// ═══════════════════════════════════════════
// GPU MONITOR — GPU 实时监控
// ═══════════════════════════════════════════

func screenGPUMonitor(state *AppState) {
	clearScreen()
	gpus := fetchV2GPUs()
	if gpus == nil {
		// Fallback to v2/nodes
		nodes := fetchV2Nodes()
		if nodes == nil {
			printf(Red+Bold, " ⚠ 无法获取 GPU 数据\n")
			printPrompt()
			return
		}
		// Aggregate GPU from nodes
		for _, n := range nodes {
			for _, g := range n.GPUs {
				gpus = append(gpus, V2GPURealtimeEntry{
					NodeID:      n.ID,
					GPUId:       g.ID,
					Model:       g.Model,
					Utilization: g.Utilization,
					Temperature: g.Temperature,
					MemoryUsed:  g.MemoryUsedGB,
				})
			}
		}
	}
	state.v2GPUs = gpus

	printHeader("🎮 GPU 实时监控", fmt.Sprintf("%d GPUs total", len(gpus)))

	// Aggregate by model
	type gpuStat struct {
		count      int
		utilSum    float64
		tempSum    float64
		memSum     float64
		hotCount   int
	}
	byModel := make(map[string]*gpuStat)
	for _, g := range gpus {
		model := g.Model
		if model == "" { model = "unknown" }
		if byModel[model] == nil { byModel[model] = &gpuStat{} }
		byModel[model].count++
		byModel[model].utilSum += g.Utilization
		byModel[model].tempSum += g.Temperature
		byModel[model].memSum += g.MemoryUsed
		if g.Temperature > 75 { byModel[model].hotCount++ }
	}

	// Summary table
	fmt.Printf("\n %s━━━ 按型号汇总 ━━━%s\n", Cyan+Bold, Reset)
	fmt.Printf("  %-12s │ %-6s │ %-6s │ %-8s │ %-8s │ %-8s │ %s\n",
		"Model", "Count", "🔥Hot", "Avg Util", "Avg Temp", "Avg Mem", "Util Bar")
	fmt.Printf("  %s%s\n", Dim, strings.Repeat("─", 82))

	// Sort by count
	type ms struct{ n string; s *gpuStat }
	var sorted []ms
	for m, s := range byModel { sorted = append(sorted, ms{m, s}) }
	sort.Slice(sorted, func(i, j int) bool { return sorted[i].s.count > sorted[j].s.count })

	for _, m := range sorted {
		avgU := m.s.utilSum / float64(m.s.count)
		avgT := m.s.tempSum / float64(m.s.count)
		avgMem := m.s.memSum / float64(m.s.count)
		bar := renderBar(avgU, 100, 24)
		hotStr := ""
		if m.s.hotCount > 0 { hotStr = Red + Bold + fmt.Sprintf("%d", m.s.hotCount) + Reset }
		fmt.Printf("  %-12s │ %4d   │ %-6s │ %s │ %s │ %s │ %s\n",
			Magenta+m.n+Reset,
			m.s.count,
			hotStr,
			pctColor(avgU),
			tempColor(avgT),
			fmt.Sprintf("%.1fGB", avgMem),
			bar)
	}

	// 🔥 Hot GPUs
	fmt.Printf("\n %s━━━ 🔥 高温 GPU (temp > 75°C) ━━━%s\n", Red+Bold, Reset)
	type hotEntry struct { node, gpu, model string; temp, util, mem float64 }
	var hotList []hotEntry
	for _, g := range gpus {
		if g.Temperature > 75 {
			hotList = append(hotList, hotEntry{g.NodeID, g.GPUId, g.Model, g.Temperature, g.Utilization, g.MemoryUsed})
		}
	}
	sort.Slice(hotList, func(i, j int) bool { return hotList[i].temp > hotList[j].temp })
	if len(hotList) > 10 { hotList = hotList[:10] }

	if len(hotList) > 0 {
		fmt.Printf("  %-6s │ %-24s │ %-8s │ %-6s │ %-8s │ %s\n", "#", "Node", "GPU", "Model", "Temp", "Util")
		for i, hg := range hotList {
			fmt.Printf("  %s%-2d%s   │ %s%-24s%s │ %s%-8s%s │ %-6s │ %s │ %s\n",
				Red+Bold, i+1, Reset,
				Red, truncate(hg.node, 24), Reset,
				Red, hg.gpu, Reset,
				hg.model,
				tempColor(hg.temp),
				pctColor(hg.util))
		}
	} else {
		fmt.Printf("  %s✅ 所有 GPU 温度正常%s\n", Green, Reset)
	}

	printPrompt()
}

// ═══════════════════════════════════════════
// REGIONS / GLOBAL MAP
// ═══════════════════════════════════════════

func screenRegions(state *AppState) {
	clearScreen()
	m := fetchV2Map()
	if m == nil {
		printf(Red+Bold, " ⚠ 无法获取全球算力地图数据\n")
		printPrompt()
		return
	}
	state.v2Map = m

	printHeader("🌍 全球算力地图", fmt.Sprintf("%d 区域, %d/%d 节点在线", m.TotalRegions, m.OnlineNodes, m.TotalNodes))

	// Sort regions by name
	type regionPair struct { name string; r *V2Region }
	var pairs []regionPair
	for name, r := range m.Regions {
		pairs = append(pairs, regionPair{name, r})
	}
	sort.Slice(pairs, func(i, j int) bool { return pairs[i].name < pairs[j].name })

	for _, p := range pairs {
		r := p.r
		fmt.Printf("\n")
		fmt.Printf(" %s┌─ %s", Cyan+Bold, r.Name)
		if r.Country != "" {
			fmt.Printf(" %s(%s)%s", Dim, r.Country, Reset)
		}
		fmt.Printf(" %s\n", Reset)

		// Online bar
		onlineRatio := 0.0
		if r.TotalNodes > 0 { onlineRatio = float64(r.OnlineNodes) / float64(r.TotalNodes) }
		bar := renderBar(onlineRatio, 1.0, 36)

		fmt.Printf(" %s│    Nodes:  %s %s  %s%d online / %d total%s  |  GPUs: %s%d%s  |  TFLOPS: %s%.0f%s\n",
			Dim, Reset,
			bar,
			Green+Bold, r.OnlineNodes, r.TotalNodes, Reset,
			Cyan+Bold, r.TotalGPUs, Reset,
			Magenta+Bold, r.TotalTFLOPS, Reset)
		fmt.Printf(" %s│    Status: %s  Avg Ut: %s  Avg Temp: %s  Tasks: %s%d%s\n",
			Dim,
			statusColor(r.Status),
			pctColor(r.AvgGPUUtil),
			tempColor(float64(r.AvgTemp)),
			Yellow+Bold, r.ActiveTasks, Reset)

		// Show node health breakdown in this region
		healthCount := make(map[string]int)
		for _, n := range r.Nodes {
			h := n.HealthStatus
			if h == "" { h = n.Status }
			healthCount[h]++
		}
		if len(healthCount) > 0 {
			fmt.Printf(" %s│    Health: ", Dim)
			for h, c := range healthCount {
				fmt.Printf("%s %s:%d", statusColor(h), Dim+Italic, c)
			}
			fmt.Printf("%s\n", Reset)
		}
	}

	fmt.Printf("\n %s总计: %d 区域, %d 节点, %d GPU, %.0fK TFLOPS%s\n",
		Cyan+Bold, m.TotalRegions, m.TotalNodes, m.TotalGPUs, m.TotalTFLOPS/1000, Reset)

	printPrompt()
}

// ═══════════════════════════════════════════
// TASKS — 任务管理器
// ═══════════════════════════════════════════

func priorityColor(p int) string {
	switch {
	case p >= 9:
		return Red + Bold
	case p >= 7:
		return Magenta + Bold
	case p >= 5:
		return Yellow
	default:
		return Green
	}
}

func priorityLabel(p int) string {
	switch {
	case p >= 9:
		return "CRITICAL"
	case p >= 7:
		return "HIGH"
	case p >= 5:
		return "MEDIUM"
	default:
		return "LOW"
	}
}

func screenTasks(state *AppState) {
	for { // loop until user goes back
		clearScreen()

		nodes := fetchV2Nodes()
		if nodes == nil {
			printf(Red+Bold, " ⚠ 无法获取节点数据\n")
			printPrompt()
			return
		}
		state.v2Nodes = nodes

		// Fetch task details and queue depth
		taskMap := fetchTaskList()
		queueDepth := fetchQueueDepth()

		printHeader("📋 任务管理器", "优先级调度")

		// ── 全局统计 ──
		totalTasks := 0
		prioCount := map[string]int{"critical": 0, "high": 0, "medium": 0, "low": 0}
		var allTasks []TaskListInfo

		for _, tasks := range taskMap {
			for _, t := range tasks {
				totalTasks++
				allTasks = append(allTasks, t)
				switch {
				case t.Priority >= 9:
					prioCount["critical"]++
				case t.Priority >= 7:
					prioCount["high"]++
				case t.Priority >= 5:
					prioCount["medium"]++
				default:
					prioCount["low"]++
				}
			}
		}

		fmt.Printf("\n %s━━━ 任务概览 ━━━%s\n", Cyan+Bold, Reset)
		fmt.Printf("  活跃任务: %s%3d%s", Yellow+Bold, totalTasks, Reset)

		if queueDepth >= 0 {
			fmt.Printf("  等待队列: %s%3d%s", Dim, queueDepth, Reset)
		} else {
			fmt.Printf("  等待队列: %s N/A%s", Dim, Reset)
		}

		// 优先级分布条
		fmt.Printf("\n")
		fmt.Printf("  优先级: ")
		if prioCount["critical"] > 0 {
			fmt.Printf("%s⬛ Critical:%d%s ", Red+Bold, prioCount["critical"], Reset)
		}
		if prioCount["high"] > 0 {
			fmt.Printf("%s⬛ High:%d%s ", Magenta+Bold, prioCount["high"], Reset)
		}
		if prioCount["medium"] > 0 {
			fmt.Printf("%s⬛ Medium:%d%s ", Yellow, prioCount["medium"], Reset)
		}
		if prioCount["low"] > 0 {
			fmt.Printf("%s⬛ Low:%d%s ", Green, prioCount["low"], Reset)
		}
		if totalTasks == 0 {
			fmt.Printf("%s(无活跃任务)%s", Dim, Reset)
		}
		fmt.Println()

		// ── 节点任务分布 ──
		fmt.Printf("\n %s━━━ 节点任务分布 ━━━%s\n\n", Cyan+Bold, Reset)

		type nodeTaskInfo struct {
			id, region, gpu, ip string
			active, max         int
		}
		var list []nodeTaskInfo
		for _, n := range nodes {
			ip := n.IPAddress
			if ip == "" || ip == "0.0.0.0" {
				ip = "—"
			}
			list = append(list, nodeTaskInfo{n.ID, n.Region, n.GPUType, ip, n.ActiveTasks, n.MaxTasks})
		}
		sort.Slice(list, func(i, j int) bool { return list[i].active > list[j].active })

		// header
		fmt.Printf("  │ %-24s │ %-10s │ %-8s │ %-15s │ %-18s │\n", "Node", "Region", "GPU", "IP", "Load (active/max)")
		fmt.Printf("  │%s%s│\n", Dim, strings.Repeat("─", 86))

		for _, li := range list {
			loadStr := fmt.Sprintf("%d/%d", li.active, li.max)
			pct := 0.0
			if li.max > 0 {
				pct = float64(li.active) / float64(li.max) * 100
			}
			pctColor := Green
			if pct > 85 {
				pctColor = Red
			} else if pct > 65 {
				pctColor = Yellow
			}
			fmt.Printf("  │ %-24s │ %-10s │ %-8s │ %-15s │ %s%-7s%s %s│\n",
				truncate(li.id, 24),
				li.region,
				li.gpu,
				li.ip,
				pctColor, loadStr, Reset,
				renderBar(float64(li.active), float64(li.max), 10))
		}

	// ── 按节点展示任务详情（含优先级） ──
	if len(allTasks) > 0 {
		fmt.Printf("\n %s━━━ 任务明细（优先级降序）━━━%s\n", Cyan+Bold, Reset)
		fmt.Printf("  │ %-22s │ %-12s │ %-8s │ %-8s │ %-10s │ %-8s │ %-15s│\n",
			"Task ID", "Node", "Priority", "Status", "Time", "Source", "IP")
		fmt.Printf("  │%s%s│\n", Dim, strings.Repeat("─", 100))

		sort.Slice(allTasks, func(i, j int) bool {
			if allTasks[i].Priority != allTasks[j].Priority {
				return allTasks[i].Priority > allTasks[j].Priority
			}
			return allTasks[i].TaskID < allTasks[j].TaskID
		})

		for _, t := range allTasks {
			pc := priorityColor(t.Priority)
			sc := statusColor(t.Status)
			prioStr := fmt.Sprintf("%d", t.Priority)
			timeStr := t.SubmittedAt
			if timeStr == "" {
				timeStr = t.CreatedAt
			}
			ipStr := t.NodeIP
			if ipStr == "" {
				ipStr = findNodeIPForTask(taskMap, t.TaskID)
			}
			fmt.Printf("  │ %-22s │ %-12s │ %s │ %s │ %-8s │ %-8s│ %-15s│\n",
				truncate(t.TaskID, 22),
				truncate(findNodeIDForTask(taskMap, t.TaskID), 12),
				visiblePad(prioStr, pc, Reset, 8),
				visiblePad(t.Status, sc, Reset, 8),
				timeStr,
				truncate(t.Source, 8),
				truncate(ipStr, 15))
		}
		fmt.Println()
		fmt.Printf("  %s↑ 按优先级降序排列 | 数值 1-10, 10=Critical | 时间=提交时间 | IP=节点IP%s\n", Dim, Reset)
	}

	fmt.Println()
	fmt.Printf(" %sCommands:%s\n", Yellow+Bold, Reset)
	fmt.Printf("  %-25s %s\n", "submit <node_id> <cmd>", "提交任务到节点")
	fmt.Printf("  %-25s %s\n", "cancel <task_id>", "取消任务")
	fmt.Printf("  %-25s %s\n", "list", "刷新任务列表")
	fmt.Println()

	// ── 任务命令循环（内联） ──
	fmt.Printf(" %s输入命令 (submit/cancel/list/back)%s\n", Yellow+Bold, Reset)
	fmt.Printf(" task> ")

	input := readLine("")
	input = strings.TrimSpace(input)

	if input == "" || strings.ToLower(input) == "list" || strings.ToLower(input) == "l" || strings.ToLower(input) == "r" || strings.ToLower(input) == "refresh" {
		continue // re-render task screen
	}
	if strings.ToLower(input) == "back" || strings.ToLower(input) == "q" {
		break // return to main menu
	}

	parts := strings.Fields(input)
	if len(parts) == 0 {
		continue
	}

	cmd := strings.ToLower(parts[0])
	if cmd == "submit" && len(parts) >= 3 {
		// submit <node_id> <command>
		nodeID := parts[1]
		command := strings.Join(parts[2:], " ")
		fmt.Printf(" %s正在提交任务到节点 %s...%s\n", Yellow, nodeID, Reset)
		submitTask(nodeID, command)
		fmt.Printf("\n %s按 Enter 继续...%s", Dim, Reset)
		readLine("")
		continue
	} else if cmd == "submit" && len(parts) == 2 {
		nodeID := parts[1]
		fmt.Printf(" %s输入命令 > %s", Yellow, Reset)
		command := readLine("")
		if command == "" {
			fmt.Printf(" %s取消提交%s\n", Dim, Reset)
			fmt.Printf("\n %s按 Enter 继续...%s", Dim, Reset)
			readLine("")
			continue
		}
		fmt.Printf(" %s正在提交任务到节点 %s...%s\n", Yellow, nodeID, Reset)
		submitTask(nodeID, command)
		fmt.Printf("\n %s按 Enter 继续...%s", Dim, Reset)
		readLine("")
		continue
	} else if cmd == "cancel" && len(parts) >= 2 {
		taskID := parts[1]
		cancelTask(taskID)
		fmt.Printf("\n %s按 Enter 继续...%s", Dim, Reset)
		readLine("")
		continue
	} else {
		fmt.Printf(" %s未知命令: %s%s\n", Red, input, Reset)
		fmt.Printf("  可用: submit <node_id> <cmd> | cancel <task_id> | list | back\n")
		fmt.Printf("\n %s按 Enter 继续...%s", Dim, Reset)
		readLine("")
		continue
	}
	}

	// Exit task manager
	clearScreen()
}

// findNodeIDForTask 从 taskMap 中查找任务所在的节点
func findNodeIDForTask(taskMap map[string][]TaskListInfo, targetID string) string {
	for nodeID, tasks := range taskMap {
		for _, t := range tasks {
			if t.TaskID == targetID {
				return nodeID
			}
		}
	}
	return "—"
}

func findNodeIPForTask(taskMap map[string][]TaskListInfo, targetID string) string {
	for _, tasks := range taskMap {
		for _, t := range tasks {
			if t.TaskID == targetID && t.NodeIP != "" {
				return t.NodeIP
			}
		}
	}
	return "?"
}

// ═══════════════════════════════════════════
// TASK COMMANDS — submit / cancel / list / live
// ═══════════════════════════════════════════

// StreamOutput represents the streaming output from Gateway
type StreamOutput struct {
	TaskID    string `json:"task_id"`
	NodeID    string `json:"node_id"`
	Stdout    string `json:"stdout"`
	Stderr    string `json:"stderr"`
	UpdatedAt string `json:"updated_at"`
	Running   bool   `json:"running"`
	ExitCode  int    `json:"exit_code,omitempty"`
	Duration  string `json:"duration,omitempty"`
}

// StreamResponse wraps the Gateway progress response
type StreamResponse struct {
	Success bool          `json:"success"`
	Data    *StreamOutput `json:"data,omitempty"`
	Error   string        `json:"error,omitempty"`
}

func fetchStreamOutput(taskID string) *StreamOutput {
	url := fmt.Sprintf("%s/api/v1/tasks/progress?task_id=%s", gw, taskID)
	resp, err := http.Get(url)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	var sr StreamResponse
	if err := json.NewDecoder(resp.Body).Decode(&sr); err != nil {
		return nil
	}
	if !sr.Success || sr.Data == nil {
		return nil
	}
	return sr.Data
}

// screenTaskLive — 实时输出监控屏幕，每秒轮询刷新
func screenTaskLive(taskID, nodeID string) {
	clearScreen()
	fmt.Printf("%s ┌─%s┐%s\n", Cyan+Bold, strings.Repeat("─", termW-6), Reset)
	fmt.Printf("%s │  📡 实时输出监控  %s%s", Cyan+Bold, Reset, Dim)
	fmt.Printf("  任务: %s  |  节点: %s", taskID, nodeID)
	padding := termW - 6 - 14 - len(taskID) - len(nodeID)
	if padding < 0 { padding = 0 }
	fmt.Print(strings.Repeat(" ", padding))
	fmt.Printf("%s │%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s └─%s┘%s\n", Cyan+Bold, strings.Repeat("─", termW-6), Reset)

	lastLen := 0
	pollCount := 0
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	done := make(chan struct{})
	go func() {
		for range ticker.C {
			so := fetchStreamOutput(taskID)
			if so == nil {
				continue
			}

			currentLen := len(so.Stdout) + len(so.Stderr)
			if currentLen > lastLen {
				// Print new output
				if len(so.Stdout) > lastLen {
					newOut := so.Stdout[lastLen:]
					if len(newOut) > 0 {
						fmt.Print(newOut)
					}
				}
				lastLen = currentLen
			}

			pollCount++

			if !so.Running || so.ExitCode != 0 || so.Duration != "" {
				// Task has completed (either success or fail)
				fmt.Printf("\n\n%s━━━ 任务完成 ━━━%s\n", Green+Bold, Reset)
				if so.ExitCode == 0 && so.Duration != "" {
					fmt.Printf(" %s✅ 成功 (耗时: %s)%s\n", Green+Bold, so.Duration, Reset)
				} else {
					fmt.Printf(" %s%s❌ 失败 (exit=%d)%s\n", Red+Bold, so.Duration, so.ExitCode, Reset)
				}
				fmt.Printf("\n %s[s] 查看完整输出  [Enter] 返回%s\n", Yellow+Bold, Reset)
				fmt.Printf(" > ")
				close(done)
				return
			}
		}
	}()

	// Wait for completion or user input
	select {
	case <-done:
		// Task completed
	case <-time.After(3600 * time.Second):
		fmt.Printf("\n\n%s⚠️ 超时 (1h)%s\n", Yellow+Bold, Reset)
	}

	// Read user response
	reply := readLine("")
	reply = strings.TrimSpace(strings.ToLower(reply))
	if reply == "s" {
		// Show full output (fetch latest)
		so := fetchStreamOutput(taskID)
		clearScreen()
		fmt.Printf("%s 📋 任务 %s 完整输出%s\n\n", Yellow+Bold, taskID, Reset)
		if so != nil {
			if so.Stdout != "" {
				fmt.Println(so.Stdout)
			}
			if so.Stderr != "" {
				fmt.Printf("%s%s%s\n", Red, so.Stderr, Reset)
			}
		}
		fmt.Printf("\n %s按 Enter 返回%s", Dim, Reset)
		readLine("")
	}
	return
}

func submitTask(nodeID, command string) {
	taskID := fmt.Sprintf("tui-%d", time.Now().UnixNano())
	payload := map[string]interface{}{
		"task_id":        taskID,
		"command":        command,
		"source_type":    "tui",
		"priority":       5,
		"max_retries":    3,
		"timeout":        3600,
		"env_vars":       map[string]string{},
		"assigned_node":  nodeID,
	}
	data, _ := json.Marshal(payload)
	resp, err := http.Post(gw+"/api/v1/tasks/submit", "application/json", bytes.NewBuffer(data))
	if err != nil {
		fmt.Printf(" %s❌ 提交失败 (连接错误): %v%s\n", Red+Bold, err, Reset)
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var tr TUIResponse
	json.Unmarshal(body, &tr)

	if tr.Success {
		fmt.Printf(" %s✅ 任务提交成功!%s\n", Green+Bold, Reset)
		fmt.Printf("   📋 任务ID: %s%s%s\n", Yellow, taskID, Reset)
		fmt.Printf("   🎯 节点: %s%s%s\n", Yellow, nodeID, Reset)
		fmt.Printf("   ⚙️  命令: %s%s%s\n", Dim, truncate(command, 50), Reset)
		fmt.Printf("   %s提示: 可用 cancel %s 取消此任务%s\n", Dim, taskID, Reset)

		// Ask user if they want to watch live output
		fmt.Printf("\n %s[l] 查看实时输出  [Enter] 返回%s\n", Yellow+Bold, Reset)
		fmt.Printf(" > ")
		reply := readLine("")
		reply = strings.TrimSpace(strings.ToLower(reply))
		if reply == "l" || reply == "live" {
			screenTaskLive(taskID, nodeID)
		}
	} else {
		fmt.Printf(" %s❌ 提交失败: %s%s\n", Red+Bold, tr.Error, Reset)
	}
}

func cancelTask(taskID string) {
	payload := map[string]interface{}{
		"task_id": taskID,
	}
	data, _ := json.Marshal(payload)
	resp, err := http.Post(gw+"/api/v1/tasks/cancel", "application/json", bytes.NewBuffer(data))
	if err != nil {
		fmt.Printf(" %s❌ 取消失败 (连接错误): %v%s\n", Red+Bold, err, Reset)
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var tr TUIResponse
	json.Unmarshal(body, &tr)

	if tr.Success {
		fmt.Printf(" %s✅ 任务 %s 已取消%s\n", Green+Bold, taskID, Reset)
	} else {
		fmt.Printf(" %s❌ 取消失败: %s%s\n", Red+Bold, tr.Error, Reset)
	}
}

// fieldsN 类似 strings.Fields 但最多分成 n 个部分
func fieldsN(s string, n int) []string {
	if n <= 0 {
		return strings.Fields(s)
	}
	fields := []string{}
	remaining := s
	for i := 0; i < n-1; i++ {
		idx := strings.IndexFunc(remaining, unicode.IsSpace)
		if idx < 0 {
			if remaining != "" {
				fields = append(fields, remaining)
			}
			break
		}
		fields = append(fields, strings.TrimSpace(remaining[:idx]))
		remaining = strings.TrimSpace(remaining[idx:])
	}
	if remaining != "" {
		fields = append(fields, remaining)
	}
	return fields
}

// ═══════════════════════════════════════════
// ALERTS
// ═══════════════════════════════════════════

func screenAlerts(state *AppState) {
	clearScreen()
	alerts := fetchV2Alerts()
	if alerts == nil {
		printf(Red+Bold, " ⚠ 无法获取告警数据\n")
		printPrompt()
		return
	}
	state.v2Alerts = alerts

	// Count by severity
	sevCount := map[string]int{"critical": 0, "warning": 0, "info": 0}
	sevTotal := 0
	for _, a := range alerts {
		sevCount[a.Severity]++
		sevTotal++
	}

	printHeader("🔔 系统告警", fmt.Sprintf("共 %d 条  🔴 %d critical  🟡 %d warning  🔵 %d info",
		sevTotal, sevCount["critical"], sevCount["warning"], sevCount["info"]))

	if len(alerts) == 0 {
		fmt.Printf("\n %s✅ 无活跃告警 — 系统运行正常%s\n", Green+Bold, Reset)
		printPrompt()
		return
	}

	fmt.Printf("\n %s%-8s │ %-10s │ %-12s │ %-30s │ %-16s%s\n",
		White+Bold, "Severity", "Type", "Node", "Message", "Timestamp", Reset)
	fmt.Printf(" %s%s%s\n", Dim, strings.Repeat("─", 92), Reset)

	for _, a := range alerts {
		sc := White
		switch a.Severity {
		case "critical": sc = Red + Bold
		case "warning":  sc = Yellow
		case "info":     sc = Cyan
		}
		msg := a.Message
		if len(msg) > 28 { msg = msg[:27] + "…" }
		ts := a.Timestamp
		if len(ts) > 19 { ts = ts[:19] }

		fmt.Printf(" %s%-8s%s │ %-10s │ %-12s │ %-30s │ %s\n",
			sc, a.Severity, Reset,
			a.Type,
			a.NodeID,
			msg, ts)
	}

	printPrompt()
}

// ═══════════════════════════════════════════
// HISTORY — 历史趋势
// ═══════════════════════════════════════════

func screenHistory(state *AppState) {
	clearScreen()
	history := fetchV2History()
	if len(history) == 0 {
		printf(Yellow+Bold, " ⚠ 暂无历史数据 (需运行 gateway 一段时间)\n")
		printPrompt()
		return
	}
	state.v2History = history

	printHeader("📈 历史趋势", fmt.Sprintf("%d 个数据点", len(history)))

	// Extract series
	type series struct {
		name   string
		values []float64
		maxVal float64
	}
	var timestamps []string
	seriesList := []*series{
		{name: "Nodes  ", values: make([]float64, 0)},
		{name: "GPU%   ", values: make([]float64, 0)},
		{name: "TFLOPS ", values: make([]float64, 0)},
		{name: "Tasks  ", values: make([]float64, 0)},
		{name: "Mem(TB)", values: make([]float64, 0)},
	}

	for _, h := range history {
		ts := h.Timestamp
		if len(ts) > 16 { ts = ts[11:16] }
		timestamps = append(timestamps, ts)
		seriesList[0].values = append(seriesList[0].values, h.OnlineNodes)
		seriesList[1].values = append(seriesList[1].values, h.AvgGPUUtil)
		seriesList[2].values = append(seriesList[2].values, h.TotalTFLOPS/1000.0)
		seriesList[3].values = append(seriesList[3].values, h.ActiveTasks)
		seriesList[4].values = append(seriesList[4].values, h.MemoryUsedGB/1024.0)
	}

	// Compute max for each
	for _, s := range seriesList {
		for _, v := range s.values {
			if v > s.maxVal { s.maxVal = v }
		}
	}

	// Print sparklines
	sparkChars := []rune("▁▂▃▄▅▆▇█")
	for _, s := range seriesList {
		if s.maxVal <= 0 { continue }
		curr := s.values[len(s.values)-1]
		currColor := Green
		if s.maxVal > 0 && curr/s.maxVal > 0.8 { currColor = Red } else if s.maxVal > 0 && curr/s.maxVal > 0.6 { currColor = Yellow }

		fmt.Printf(" %s ", s.name)
		fmt.Print(currColor)
		for _, v := range s.values {
			idx := int(v / s.maxVal * float64(len(sparkChars)-1))
			if idx >= len(sparkChars) { idx = len(sparkChars) - 1 }
			if idx < 0 { idx = 0 }
			fmt.Printf("%c", sparkChars[idx])
		}
		fmt.Print(Reset)

		// Value label
		fmt.Printf(" %s%.1f%s", Dim, curr, Reset)

		// Bar at end
		bar := renderBar(curr, s.maxVal, 15)
		fmt.Printf(" %s\n", bar)
	}

	// Timeline axis
	if len(timestamps) > 0 {
		fmt.Printf("        ")
		step := len(timestamps) / 6
		if step < 1 { step = 1 }
		for i := 0; i < len(timestamps); i += step {
			fmt.Printf("%s ", timestamps[i])
		}
		fmt.Println()
	}

	// Latest snapshot
	fmt.Println()
	fmt.Printf(" %sLatest:%s\n", Yellow+Bold, Reset)
	if len(history) > 0 {
		last := history[len(history)-1]
		fmt.Printf("  时间: %s  |  节点: %s%.0f%s / %.0f  |  GPU 利用率: %s  |  总算力: %s%.0f%sK  |  任务: %s%.0f%s  |  内存: %s%.1f%sTB\n",
			last.Timestamp[:19],
			Green+Bold, last.OnlineNodes, Reset, last.TotalNodes,
			pctColor(last.AvgGPUUtil),
			Magenta+Bold, last.TotalTFLOPS/1000, Reset,
			Yellow+Bold, last.ActiveTasks, Reset,
			Blue+Bold, last.MemoryUsedGB/1024, Reset)
	}

	printPrompt()
}

// ═══════════════════════════════════════════
// HEALTH CHECK
// ═══════════════════════════════════════════

func screenHealth(state *AppState) {
	clearScreen()
	h := fetchV2Health()
	s := fetchStatus()
	nodes := fetchV2Nodes()

	printHeader("🏥 系统健康检查", time.Now().Format("15:04:05"))

	// Connectivity
	fmt.Printf("\n %s━━━ 连通性检查 ━━━%s\n", Cyan+Bold, Reset)
	if h != nil {
		fmt.Printf("  Gateway: %s  延迟: ~0ms\n", statusColor("reachable"))
		fmt.Printf("  v2/health: %s\n", statusColor(h.Status))
	}
	if s != nil {
		fmt.Printf("  v1/status: 内核 %s, 执行器 %s%s\n",
			statusColor(s.Kernel.Status),
			statusColor(s.Executor.Status),
			Reset)
	}

	fmt.Printf("\n %s━━━ 集群规模 ━━━%s\n", Cyan+Bold, Reset)
	if h != nil {
		fmt.Printf("  节点: %s%d online%s / %d total\n", Green+Bold, h.OnlineNodes, Reset, h.TotalNodes)
		fmt.Printf("  GPU: %s%d%s\n", Cyan+Bold, h.TotalGPUs, Reset)
		fmt.Printf("  总算力: %s%.0f%s TFLOPS\n", Magenta+Bold, h.TotalTFLOPS, Reset)
		fmt.Printf("  区域: %d healthy / %d degraded\n", h.HealthyRegions, h.DegradedRegions)
		fmt.Printf("  告警数: %d\n", h.TotalAlerts)
	}

	fmt.Printf("\n %s━━━ 资源利用率 ━━━%s\n", Cyan+Bold, Reset)
	if nodes != nil {
		totalMem := 0.0
		totalMemUsed := 0.0
		totalGPU := 0
		utilSum := 0.0
		tempSum := 0.0
		for _, n := range nodes {
			totalMem += n.MemoryGB
			for _, g := range n.GPUs {
				totalGPU++
				utilSum += g.Utilization
				tempSum += g.Temperature
				totalMemUsed += g.MemoryUsedGB
			}
		}

		avgUtil := utilSum / float64(totalGPU)
		avgTemp := tempSum / float64(totalGPU)
		memPct := totalMemUsed / (float64(totalGPU) * 64.0) * 100

		fmt.Printf("  平均 GPU 利用率: %s\n", pctColor(avgUtil))
		fmt.Printf("  平均 GPU 温度: %s\n", tempColor(avgTemp))
		fmt.Printf("  平均 GPU 显存占用: %.1f%%\n", memPct)

		// Health bar
		onlineRatio := 0.0
		if h != nil { onlineRatio = float64(h.OnlineNodes) / float64(h.TotalNodes) }
		bar := renderBar(onlineRatio, 1.0, 30)
		fmt.Printf("  节点在线率: %s %.0f%%\n", bar, onlineRatio*100)
	}

	fmt.Printf("\n %sOverall:%s ", Green+Bold, Reset)
	if h != nil && h.Status == "healthy" && s != nil && s.Kernel.Status == "RUNNING" {
		fmt.Printf("%s✅ ALL SYSTEMS NOMINAL%s\n", Green+Bold, Reset)
	} else {
		fmt.Printf("%s⚠️ DEGRADED — 请检查组件%s\n", Yellow+Bold, Reset)
	}

	printPrompt()
}

// ═══════════════════════════════════════════
// OPC-SHELL (Legacy)
// ═══════════════════════════════════════════

func screenShell(state *AppState) {
	clearScreen()
	fmt.Printf("%s ╔══════════════════════════════════════╗%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s ║      OPC-Shell (Legacy Mode)         ║%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s ╚══════════════════════════════════════╝%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s  输入命令直接发送到网关%s\n", Dim, Reset)
	fmt.Printf("%s  'back' 返回  'help' 查看命令%s\n\n", Dim, Reset)

	for {
		input := readLine("\r" + Cyan + Bold + " [OPC-Shell] > " + Reset)
		if input == "" { return }
		if input == "back" || input == "exit" || input == "q" { return }
		if input == "help" {
			fmt.Printf("%s 命令: PING / EXEC <cmd> / STATUS / NODES / DISPATCH / GPUMON / REGIONS%s\n", Yellow, Reset)
			continue
		}

		reqID := fmt.Sprintf("tui-%d", time.Now().UnixNano())
		reqBody := TUIRequest{ID: reqID, Command: input}
		resp, err := httpPostJSON(gw+"/api/dispatch", reqBody)
		if err != nil {
			fmt.Printf("%s [连接错误]: %v%s\n", Red, err, Reset)
			continue
		}
		if !resp.Success {
			fmt.Printf("%s [错误]: %s%s\n", Red, resp.Error, Reset)
			continue
		}
		if strings.Contains(strings.ToUpper(input), "EXEC") {
			if resp.Verified {
				fmt.Printf("%s ✅ [已验证] %s%v%s\n", Green+Bold, Dim, resp.Data, Reset)
			} else {
				fmt.Printf("%s ❌ [验证失败] %s%v%s\n", Red+Bold, Dim, resp.Data, Reset)
			}
			if resp.Duration != "" {
				fmt.Printf("%s    耗时: %s%s\n", Dim, resp.Duration, Reset)
			}
		} else {
			fmt.Printf("%s %v%s\n", Blue, resp.Data, Reset)
		}
	}
}

// ═══════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════

func Run(args []string) {
	// Parse --gw flag from args
	if args != nil {
		for i := 0; i < len(args); i++ {
			if args[i] == "--gw" && i+1 < len(args) {
				url := args[i+1]
				if !strings.HasPrefix(url, "http://") && !strings.HasPrefix(url, "https://") {
					url = "http://" + url
				}
				url = strings.TrimRight(url, "/")
				if url != "" {
					gw = url
				}
				break
			}
		}
	}

	// Check gateway
	if err := checkGateway(); err != nil {
		fmt.Printf("%s\u274c \u65e0\u6cd5\u8fde\u63a5\u7f51\u5173 %s: %v%s\n", Red, gw, err, Reset)
		fmt.Printf("%s\U0001f4a1 \u8bf7\u5148\u542f\u52a8\u7f51\u5173: cd %s && go run ./cmd/gateway%s\n", Yellow, projectDir(), Reset)
		fmt.Printf("%s   \u6216\u6307\u5b9a\u8fdc\u7a0b\u7f51\u5173: ./computehub tui --gw http://192.168.1.x:8282%s\n", Yellow, Reset)
		return
	}

	state := &AppState{}

	// Show dashboard on startup
	screenDashboard(state)

	for {
		input := readLine("\r> ")
		if input == "" { continue }

		// Strip leading "/" so /d → d, /nodes → nodes, etc.
		input = strings.TrimLeft(input, "/")
		cmd := strings.ToLower(input)

		switch {
		case cmd == "q" || cmd == "quit" || cmd == "exit":
			clearScreen()
			fmt.Printf("%s\U0001f44b Goodbye!%s\n", Cyan, Reset)
			return

		case cmd == "d" || cmd == "dashboard" || cmd == "r" || cmd == "refresh" || cmd == "back":
			screenDashboard(state)

		case cmd == "n" || cmd == "nodes":
			screenNodes(state)

		case cmd == "g" || cmd == "gpu" || cmd == "gpumon":
			screenGPUMonitor(state)

		case cmd == "map" || cmd == "regions" || cmd == "region":
			screenRegions(state)

		case cmd == "t" || cmd == "tasks":
			screenTasks(state)

		case cmd == "a" || cmd == "alerts":
			screenAlerts(state)

		case cmd == "h" || cmd == "history":
			screenHistory(state)

		case cmd == "health" || cmd == "chk":
			screenHealth(state)

		case cmd == "shell":
			screenShell(state)
			screenDashboard(state)
			continue

		case cmd == "?" || cmd == "help":
			printHelp()

		default:
			fmt.Printf("%s \u672a\u77e5\u547d\u4ee4: %s%s\n", Red, input, Reset)
			printHelp()
		}

		printPrompt()
	}
}

func checkGateway() error {
	resp, err := http.Get(gw + "/api/health")
	if err != nil {
		return err
	}
	resp.Body.Close()
	return nil
}

func projectDir() string {
	return "/root/.openclaw/workspace/projects/computehub"
}
