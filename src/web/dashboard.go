// Package web implements the ComputeHub Web Dashboard (Sprint 4).
// Built with Go html/templates + HTMX for zero-dependency real-time UI.
package web

import (
	"encoding/json"
	"fmt"
	"html/template"
	"net/http"
	"sync"
	"time"

	"github.com/chenqifu-Ai/computehub/src/blockchain"
	"github.com/chenqifu-Ai/computehub/src/node"
)

// ════════════════════════════════════════════════════════════════════
// Dashboard 数据模型
// ════════════════════════════════════════════════════════════════════

// DashboardData 仪表板完整数据
type DashboardData struct {
	Uptime            string            `json:"uptime"`
	NodeCount         int               `json:"node_count"`
	ActiveTasks       int               `json:"active_tasks"`
	QueueDepth        int               `json:"queue_depth"`
	TotalStaked       float64           `json:"total_staked"`
	TotalStakeRewards float64           `json:"total_stake_rewards"`
	ActiveStakers     int               `json:"active_stakers"`
	BlockCounter      int64             `json:"block_counter"`

	Nodes     []NodeInfo     `json:"nodes"`
	Tasks     []TaskInfo     `json:"tasks"`

	TotalEscrows   int `json:"total_escrows"`
	LockedEscrows  int `json:"locked_escrows"`
	ReleasedEscrows int `json:"released_escrows"`
	RefundedEscrows int `json:"refunded_escrows"`
	DisputeCount   int `json:"dispute_count"`

	BlockHeight  int   `json:"block_height"`
	TxCount      int   `json:"tx_count"`
	MempoolSize  int   `json:"mempool_size"`
	TokenSymbol  string `json:"token_symbol"`
}

// NodeInfo 节点摘要
type NodeInfo struct {
	ID         string          `json:"id"`
	Name       string          `json:"name"`
	Status     string          `json:"status"`
	GPUEnabled bool            `json:"gpu_enabled"`
	GPUs       []node.GPUInfo  `json:"gpus,omitempty"`
	Load       float64         `json:"load"`
	Region     string          `json:"region"`
}

// TaskInfo 任务摘要
type TaskInfo struct {
	ID           string  `json:"id"`
	Status       string  `json:"status"`
	NodeAddr     string  `json:"node_addr"`
	GPUCount     int     `json:"gpu_count"`
	ResourceType string  `json:"resource_type"`
}

// ════════════════════════════════════════════════════════════════════
// Dashboard Server
// ════════════════════════════════════════════════════════════════════

// DashboardServer 仪表板HTTP服务
type DashboardServer struct {
	mu       sync.RWMutex
	started  time.Time

	// 数据源
	NodeMgr   NodeProvider
	BlockchainProvider
	TaskProvider
}

// NodeProvider 节点数据接口
type NodeProvider interface {
	GetOnlineNodes() []*node.Node
	GetTotalNodes() int
}

// BlockchainProvider 区块链数据接口
type BlockchainProvider interface {
	GetChainInfo() map[string]any
	GetStakingStats() map[string]interface{}
	GetEscrowStats() map[string]int
	GetDisputeStats() map[string]int
	GetTokenSymbol() string
}

// TaskProvider 任务数据接口
type TaskProvider interface {
	GetAllTasks() []*blockchain.TaskRecord
	GetTaskStats() map[string]int
}

// ════════════════════════════════════════════════════════════════════
// 数据收集器 (从 Gateway 适配)
// ════════════════════════════════════════════════════════════════════

// GatewayAdapter 将 Gateway 适配为 Dashboard 数据源
type GatewayAdapter struct {
	GetOnlineNodesFn func() []*node.Node
	GetTotalNodesFn  func() int

	GetChainInfoFn   func() map[string]any
	StakingStatsFn   func() map[string]interface{}
	EscrowStatsFn    func() map[string]int
	DisputeStatsFn   func() map[string]int

	TaskStatsFn      func() map[string]int
	ListAllTasksFn   func() []*blockchain.TaskRecord
	TokenSymbolVal   string
}

func (a *GatewayAdapter) GetOnlineNodes() []*node.Node {
	if a.GetOnlineNodesFn != nil { return a.GetOnlineNodesFn() }
	return nil
}
func (a *GatewayAdapter) GetTotalNodes() int {
	if a.GetTotalNodesFn != nil { return a.GetTotalNodesFn() }
	return 0
}
func (a *GatewayAdapter) GetChainInfo() map[string]any {
	if a.GetChainInfoFn != nil { return a.GetChainInfoFn() }
	return nil
}
func (a *GatewayAdapter) GetStakingStats() map[string]interface{} {
	if a.StakingStatsFn != nil { return a.StakingStatsFn() }
	return nil
}
func (a *GatewayAdapter) GetEscrowStats() map[string]int {
	if a.EscrowStatsFn != nil { return a.EscrowStatsFn() }
	return nil
}
func (a *GatewayAdapter) GetDisputeStats() map[string]int {
	if a.DisputeStatsFn != nil { return a.DisputeStatsFn() }
	return nil
}
func (a *GatewayAdapter) GetAllTasks() []*blockchain.TaskRecord {
	if a.ListAllTasksFn != nil { return a.ListAllTasksFn() }
	return nil
}
func (a *GatewayAdapter) GetTaskStats() map[string]int {
	if a.TaskStatsFn != nil { return a.TaskStatsFn() }
	return nil
}
func (a *GatewayAdapter) GetTokenSymbol() string { return a.TokenSymbolVal }

// ════════════════════════════════════════════════════════════════════
// 初始化
// ════════════════════════════════════════════════════════════════════

// NewDashboardServer 创建仪表板
func NewDashboardServer() *DashboardServer {
	return &DashboardServer{
		started: time.Now(),
	}
}

// SetProviders 设置数据源提供者
func (ds *DashboardServer) SetProviders(nodes NodeProvider, bc BlockchainProvider, tasks TaskProvider) {
	ds.mu.Lock()
	defer ds.mu.Unlock()
	ds.NodeMgr = nodes
	ds.BlockchainProvider = bc
	ds.TaskProvider = tasks
}

// ─── 数据收集 ──────────────────────────────────────────────────────

// CollectData 收集仪表板所需的所有数据
func (ds *DashboardServer) CollectData() DashboardData {
	ds.mu.RLock()
	defer ds.mu.RUnlock()

	data := DashboardData{
		Uptime:      formatDuration(time.Since(ds.started)),
		TokenSymbol: "CHB",
	}

	// 节点
	if ds.NodeMgr != nil {
		nodes := ds.NodeMgr.GetOnlineNodes()
		data.NodeCount = len(nodes)
		for _, n := range nodes {
			data.Nodes = append(data.Nodes, NodeInfo{
				ID:         n.ID,
				Name:       n.Name,
				Status:     n.Status,
				GPUEnabled: n.Capability.GPUEnabled,
				GPUs:       n.Capability.GPUs,
				Load:       n.Load,
				Region:     n.Region,
			})
		}
	}

	// 任务
	if ds.TaskProvider != nil {
		stats := ds.TaskProvider.GetTaskStats()
		data.ActiveTasks = stats["running"]
		for s, c := range stats {
			_ = s
			_ = c
		}
	}

	// 区块链
	if ds.BlockchainProvider != nil {
		chainInfo := ds.BlockchainProvider.GetChainInfo()
		if chainInfo != nil {
			data.BlockHeight = toInt(chainInfo["height"])
			data.TxCount = toInt(chainInfo["total_settlements"])
			data.MempoolSize = toInt(chainInfo["mempool_size"])
		}

		staking := ds.BlockchainProvider.GetStakingStats()
		if staking != nil {
			data.TotalStaked = toFloat(staking["total_staked"])
			data.TotalStakeRewards = toFloat(staking["total_rewards"])
			data.ActiveStakers = toInt(staking["active_stakers"])
			data.BlockCounter = int64(toInt(staking["block_counter"]))
		}

		escrow := ds.BlockchainProvider.GetEscrowStats()
		if escrow != nil {
			data.TotalEscrows = escrow["total"]
			data.LockedEscrows = escrow["locked"]
			data.ReleasedEscrows = escrow["released"]
			data.RefundedEscrows = escrow["refunded"]
		}

		dispute := ds.BlockchainProvider.GetDisputeStats()
		if dispute != nil {
			data.DisputeCount = dispute["total"]
		}

		data.TokenSymbol = ds.BlockchainProvider.GetTokenSymbol()
	}

	return data
}

// ════════════════════════════════════════════════════════════════════
// HTTP Handler
// ════════════════════════════════════════════════════════════════════

var dashboardTmpl *template.Template

func init() {
	dashboardTmpl = template.Must(template.New("dashboard").Parse(dashboardHTML))
}

const dashboardHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ComputeHub Dashboard</title>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <style>
        :root {
            --bg: #0d1117; --card: #161b22; --border: #30363d;
            --text: #c9d1d9; --text-dim: #8b949e;
            --green: #3fb950; --red: #f85149; --yellow: #d29922;
            --blue: #58a6ff; --purple: #bc8cff;
        }
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:-apple-system,'Segoe UI','Monaco',monospace;background:var(--bg);color:var(--text);padding:20px;}
        .header{display:flex;justify-content:space-between;align-items:center;padding:16px 24px;background:var(--card);border:1px solid var(--border);border-radius:12px;margin-bottom:20px;}
        .header h1{color:var(--blue);font-size:1.3em;}
        .badge{font-size:0.85em;padding:4px 12px;border-radius:20px;}
        .badge-on{background:#0f2d1a;color:var(--green);border:1px solid #1a4a2a;}
        .grid{display:grid;gap:16px;}
        .g4{grid-template-columns:repeat(4,1fr);}
        .g2{grid-template-columns:repeat(2,1fr);}
        .g3{grid-template-columns:repeat(3,1fr);}
        @media(max-width:1200px){.g4{grid-template-columns:repeat(2,1fr);}}
        @media(max-width:768px){.g4,.g3,.g2{grid-template-columns:1fr;}}
        .card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;}
        .card:hover{border-color:#484f5e;}
        .ct{color:var(--text-dim);font-size:0.8em;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;}
        .cv{font-size:1.8em;font-weight:bold;}
        .green{color:var(--green);}.red{color:var(--red);}.blue{color:var(--blue);}.yellow{color:var(--yellow);}
        table{width:100%;border-collapse:collapse;font-size:0.9em;}
        th,td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);}
        th{color:var(--text-dim);font-weight:500;}
        .tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.8em;}
        .t-green{background:#0f2d1a;color:var(--green);}.t-red{background:#2d0f0f;color:var(--red);}
        .t-blue{background:#0f1a2d;color:var(--blue);}.t-yellow{background:#2d2a0f;color:var(--yellow);}
        .mt{margin-top:16px;}.flex{display:flex;gap:8px;align-items:center;}
        .rb{position:fixed;bottom:20px;right:20px;background:var(--card);border:1px solid var(--border);
            padding:8px 16px;border-radius:20px;font-size:0.8em;display:flex;align-items:center;gap:8px;}
        .dot{width:8px;height:8px;border-radius:50%;background:var(--green);}
    </style>
</head>
<body>

<div class="header">
    <div class="flex"><h1>⚡ ComputeHub</h1><span class="badge badge-on">● 运行中</span></div>
    <div style="font-size:0.85em;color:var(--text-dim);">
        <span id="node-count">{{.NodeCount}} 节点</span>
        <span style="margin:0 8px">|</span>
        <span id="uptime">{{.Uptime}}</span>
    </div>
</div>

<!-- 核心指标卡片 -->
<div class="grid g4" hx-get="/web/api/metrics" hx-trigger="every 5s" hx-swap="innerHTML">
    <div class="card"><div class="ct">运行时长</div><div class="cv green">{{.Uptime}}</div></div>
    <div class="card"><div class="ct">节点在线</div><div class="cv blue">{{.NodeCount}}</div></div>
    <div class="card"><div class="ct">活跃任务</div><div class="cv yellow">{{.ActiveTasks}}</div></div>
    <div class="card"><div class="ct">质押总量</div><div class="cv" style="color:var(--purple)">{{printf "%.0f" .TotalStaked}} CHB</div></div>
</div>

<!-- 主要内容 -->
<div class="grid g2 mt">
    <div class="card">
        <div class="ct">📡 节点状态</div>
        <table>
            <tr><th>名称</th><th>状态</th><th>GPU</th><th>负载</th><th>区域</th></tr>
            {{range .Nodes}}
            <tr>
                <td style="font-size:0.85em">{{.Name}}</td>
                <td><span class="tag {{if eq .Status "online"}}t-green{{else}}t-red{{end}}">{{.Status}}</span></td>
                <td>{{if .GPUEnabled}}{{len .GPUs}} GPU{{else}}—{{end}}</td>
                <td>{{printf "%.0f" .Load}}%</td>
                <td style="font-size:0.85em">{{.Region}}</td>
            </tr>
            {{else}}<tr><td colspan="5" style="color:var(--text-dim);text-align:center">暂无节点</td></tr>{{end}}
        </table>
    </div>
    <div class="card">
        <div class="ct">🔗 区块链</div>
        <table>
            <tr><td>区块高度</td><td>{{.BlockHeight}}</td></tr>
            <tr><td>结算记录</td><td>{{.TxCount}}</td></tr>
            <tr><td>内存池</td><td>{{.MempoolSize}}</td></tr>
            <tr><td>Token</td><td>{{.TokenSymbol}}</td></tr>
            <tr><td>质押池</td><td>{{.ActiveStakers}} 节点, {{printf "%.1f" .TotalStaked}} CHB</td></tr>
            <tr><td>累计奖励</td><td>{{printf "%.2f" .TotalStakeRewards}} CHB</td></tr>
            <tr><td>托管中</td><td>{{.LockedEscrows}} / {{.TotalEscrows}}</td></tr>
            <tr><td>争议</td><td>{{.DisputeCount}}</td></tr>
        </table>
    </div>
</div>

<div class="rb"><span class="dot"></span><span>每5秒自动刷新</span></div>
</body>
</html>`

// ServeDashboard 渲染仪表板页面
func (ds *DashboardServer) ServeDashboard(w http.ResponseWriter, r *http.Request) {
	data := ds.CollectData()

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := dashboardTmpl.Execute(w, data); err != nil {
		http.Error(w, "render error", http.StatusInternalServerError)
	}
}

// ServeMetrics 返回 JSON 格式的指标数据 (供 HTMX 轮询)
func (ds *DashboardServer) ServeMetrics(w http.ResponseWriter, r *http.Request) {
	data := ds.CollectData()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

// ════════════════════════════════════════════════════════════════════
// 辅助函数
// ════════════════════════════════════════════════════════════════════

func formatDuration(d time.Duration) string {
	d = d.Round(time.Second)
	h := d / time.Hour
	d -= h * time.Hour
	m := d / time.Minute
	d -= m * time.Minute
	s := d / time.Second
	return fmt.Sprintf("%dh %dm %ds", h, m, s)
}

func toInt(v any) int {
	switch val := v.(type) {
	case int:      return val
	case int64:    return int(val)
	case float64:  return int(val)
	case int32:    return int(val)
	default:       return 0
	}
}

func toFloat(v any) float64 {
	switch val := v.(type) {
	case float64: return val
	case int:     return float64(val)
	case int64:   return float64(val)
	default:      return 0
	}
}
