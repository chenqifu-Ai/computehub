// ComputeHub Worker OpenClaw Manager
// 在每个 Worker Agent 上管理 OpenClaw 实例的生命周期：
//   安装/升级、启动/停止、健康检查、自动自愈、配置同步
//
// 架构:
//   OpenClawManager (生命周期管理)
//     ├── Install()     — npm install -g openclaw
//     ├── Start()       — openclaw gateway start
//     ├── Stop()        — openclaw gateway stop
//     ├── Status()      — health check + 版本查询
//     ├── Configure()   — 设置 remote URL / pairing token
//     └── HealthLoop()  — 周期性检查 + 自动重启
//
// 依赖:
//   - Node.js (npm) 已安装
//   - openclaw 已通过 npm install -g 安装

package workercmd

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/computehub/opc/src/agent"
	"github.com/computehub/opc/src/executil"
)

// ═══════════════════════════════════════════
// OpenClawManager — 管理 OpenClaw 实例
// ═══════════════════════════════════════════

type OpenClawManager struct {
	mu          sync.RWMutex
	nodeID      string
	gatewayURL  string
	state       *WorkerState

	// OpenClaw 配置
	ocPort     int      // OpenClaw Gateway 端口（默认 18789）
	ocDataDir  string   // OpenClaw 数据目录
	ocRemote   string   // 远程 Gateway URL（用于配对）
	ocToken    string   // 配对 token

	// 运行状态
	running     bool
	pid         int
	lastHealth  time.Time
	healthOK    bool
	version     string
	installPath string // openclaw binary 路径

	// 自愈控制
	healthStopCh chan struct{}
	healthActive bool
	autoHeal     bool // 是否启用自动自愈

	// 统计
	restartCount int
	installCount int
	lastError    string
}

// OpenClawConfig OpenClaw 实例配置
type OpenClawConfig struct {
	Port    int    `json:"port"`    // Gateway 端口
	DataDir string `json:"data_dir"` // 数据目录
	Remote  string `json:"remote"`  // 远程 Gateway URL（配对用）
	Token   string `json:"token"`   // 配对 token
}

// OpenClawStatus OpenClaw 状态报告
type OpenClawStatus struct {
	NodeID      string `json:"node_id"`
	Installed   bool   `json:"installed"`
	Running     bool   `json:"running"`
	Version     string `json:"version"`
	Port        int    `json:"port"`
	HealthOK    bool   `json:"health_ok"`
	LastHealth  string `json:"last_health"`
	RestartCount int   `json:"restart_count"`
	InstallCount int   `json:"install_count"`
	LastError   string `json:"last_error"`
	AutoHeal    bool   `json:"auto_heal"`
	Platform    string `json:"platform"`
}

// NewOpenClawManager 创建 OpenClaw 管理器
func NewOpenClawManager(state *WorkerState, config *OpenClawConfig) *OpenClawManager {
	if config == nil {
		config = &OpenClawConfig{}
	}
	if config.Port == 0 {
		config.Port = 18789
	}
	if config.DataDir == "" {
		homeDir := getWorkerHomeDir()
		config.DataDir = homeDir + "/.openclaw"
	}

	// 尝试查找 openclaw 路径
	installPath := findOpenClawPath()

	return &OpenClawManager{
		nodeID:      state.nodeID,
		gatewayURL:  state.config.GatewayURL,
		state:       state,
		ocPort:      config.Port,
		ocDataDir:   config.DataDir,
		ocRemote:    config.Remote,
		ocToken:     config.Token,
		installPath: installPath,
		autoHeal:    true,
		healthStopCh: make(chan struct{}),
	}
}

// ── 工具注册 ──

// RegisterAgentTools 向 Agent 注册 OpenClaw 管理工具
func (m *OpenClawManager) RegisterAgentTools(tr *agent.ToolRegistry) {
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "openclaw_install",
			Description: "安装或升级 OpenClaw（npm install -g openclaw）。返回安装结果和版本号。",
			Parameters: []agent.Param{
				{Name: "version", Type: "string", Required: false, Description: "指定版本号（如 2026.3.13），空=最新版"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			version, _ := args["version"].(string)
			return m.Install(version)
		},
	})

	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "openclaw_start",
			Description: "启动 OpenClaw Gateway 服务。返回启动结果。",
			Parameters: []agent.Param{
				{Name: "port", Type: "int", Required: false, Description: "Gateway 端口（默认 18789）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			port := m.ocPort
			if p, ok := args["port"].(float64); ok {
				port = int(p)
			}
			return m.Start(port)
		},
	})

	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "openclaw_stop",
			Description: "停止 OpenClaw Gateway 服务。返回停止结果。",
			Parameters: []agent.Param{},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			return m.Stop()
		},
	})

	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "openclaw_status",
			Description: "查询 OpenClaw 运行状态（是否安装、是否运行、版本、健康检查结果）。",
			Parameters: []agent.Param{},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			status := m.GetStatus()
			data, _ := json.MarshalIndent(status, "", "  ")
			return string(data), nil
		},
	})

	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "openclaw_configure",
			Description: "配置 OpenClaw 的远程 Gateway 地址和配对 token。用于跨网络连接。",
			Parameters: []agent.Param{
				{Name: "remote", Type: "string", Required: true, Description: "远程 Gateway URL（如 http://36.250.122.43:18789）"},
				{Name: "token", Type: "string", Required: false, Description: "配对 token（可选）"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			remote, _ := args["remote"].(string)
			token, _ := args["token"].(string)
			return m.Configure(remote, token)
		},
	})
}

// ── 核心操作 ──

// Install 安装/升级 OpenClaw
func (m *OpenClawManager) Install(version string) (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	var b strings.Builder
	b.WriteString(fmt.Sprintf("📦 安装 OpenClaw (version=%s, platform=%s/%s)...\n", version, runtime.GOOS, runtime.GOARCH))

	// 1. 检查 Node.js 是否可用
	nodePath := executil.SafeLookPath("node")
	npmPath := executil.SafeLookPath("npm")
	if nodePath == "" || npmPath == "" {
		return "", fmt.Errorf("Node.js/npm 未安装。请先安装 Node.js (node >= 18)")
	}

	// 检查 node 版本
	nodeVer := execCmd("node", "--version")
	b.WriteString(fmt.Sprintf("  Node.js: %s\n", strings.TrimSpace(nodeVer)))

	// 2. 设置 npm registry（国内加速）
	execCmd("npm", "config", "set", "registry", "https://registry.npmmirror.com")

	// 3. 安装/升级
	npmArgs := []string{"install", "-g", "openclaw"}
	if version != "" {
		npmArgs = append(npmArgs, version)
	}

	b.WriteString(fmt.Sprintf("  执行: npm %s\n", strings.Join(npmArgs, " ")))

	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, npmPath, npmArgs...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		m.lastError = fmt.Sprintf("npm install 失败: %v", err)
		b.WriteString(fmt.Sprintf("  ❌ %s\n", m.lastError))
		b.WriteString(fmt.Sprintf("  输出: %s\n", string(output)))
		return b.String(), fmt.Errorf(m.lastError)
	}

	// 4. 验证安装
	newPath := findOpenClawPath()
	if newPath == "" {
		m.lastError = "安装后找不到 openclaw 命令"
		b.WriteString(fmt.Sprintf("  ❌ %s\n", m.lastError))
		return b.String(), fmt.Errorf(m.lastError)
	}

	m.installPath = newPath
	m.installCount++

	// 5. 获取版本
	ver := execCmd(newPath, "--version")
	m.version = strings.TrimSpace(ver)

	b.WriteString(fmt.Sprintf("  ✅ 安装成功: %s\n", m.version))
	b.WriteString(fmt.Sprintf("  路径: %s\n", newPath))

	return b.String(), nil
}

// Start 启动 OpenClaw Gateway
func (m *OpenClawManager) Start(port int) (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	var b strings.Builder

	// 1. 检查是否已安装
	if m.installPath == "" {
		m.installPath = findOpenClawPath()
		if m.installPath == "" {
			return "", fmt.Errorf("OpenClaw 未安装，请先执行 openclaw_install")
		}
	}

	// 2. 检查是否已在运行
	if m.running {
		status := m.checkHealth()
		if status {
			b.WriteString(fmt.Sprintf("  ℹ️  OpenClaw 已在运行 (port=%d, pid=%d)\n", m.ocPort, m.pid))
			return b.String(), nil
		}
		// 健康检查失败，标记为未运行，重新启动
		b.WriteString("  ⚠️  进程存在但健康检查失败，将重新启动\n")
	}

	// 3. 停止旧实例
	m.killExisting()

	// 4. 启动新实例
	args := []string{"gateway", "start", "--port", fmt.Sprintf("%d", port)}

	// 如果有 remote 配置，添加
	if m.ocRemote != "" {
		args = append(args, "--remote", m.ocRemote)
	}

	b.WriteString(fmt.Sprintf("  执行: %s %s\n", m.installPath, strings.Join(args, " ")))

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, m.installPath, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		m.lastError = fmt.Sprintf("启动失败: %v", err)
		b.WriteString(fmt.Sprintf("  ❌ %s\n", m.lastError))
		b.WriteString(fmt.Sprintf("  输出: %s\n", string(output)))
		return b.String(), fmt.Errorf(m.lastError)
	}

	// 5. 等待服务就绪
	time.Sleep(3 * time.Second)

	// 6. 验证
	healthOK := m.checkHealth()
	if healthOK {
		m.running = true
		m.healthOK = true
		m.lastHealth = time.Now()
		m.ocPort = port
		b.WriteString(fmt.Sprintf("  ✅ OpenClaw Gateway 已启动 (port=%d)\n", port))
	} else {
		m.lastError = "启动后健康检查失败"
		b.WriteString(fmt.Sprintf("  ⚠️  启动命令已执行，但健康检查未通过: %s\n", m.lastError))
	}

	return b.String(), nil
}

// Stop 停止 OpenClaw Gateway
func (m *OpenClawManager) Stop() (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	var b strings.Builder

	if m.installPath == "" {
		m.installPath = findOpenClawPath()
	}

	if m.installPath == "" {
		b.WriteString("  ℹ️  OpenClaw 未安装，无需停止\n")
		return b.String(), nil
	}

	// 1. 用 openclaw gateway stop
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, m.installPath, "gateway", "stop")
	output, err := cmd.CombinedOutput()
	if err != nil {
		b.WriteString(fmt.Sprintf("  ⚠️  gateway stop 命令失败: %v\n", err))
	}

	// 2. 强制 kill 残留进程
	m.killExisting()

	m.running = false
	m.healthOK = false
	m.pid = 0

	b.WriteString(fmt.Sprintf("  ✅ OpenClaw Gateway 已停止\n"))
	if len(output) > 0 {
		b.WriteString(fmt.Sprintf("  输出: %s\n", string(output)))
	}

	return b.String(), nil
}

// Status 查询状态
func (m *OpenClawManager) Status() (string, error) {
	status := m.GetStatus()
	data, _ := json.MarshalIndent(status, "", "  ")
	return string(data), nil
}

// GetStatus 获取结构化状态
func (m *OpenClawManager) GetStatus() *OpenClawStatus {
	m.mu.RLock()
	defer m.mu.RUnlock()

	status := &OpenClawStatus{
		NodeID:       m.nodeID,
		Installed:    m.installPath != "" || findOpenClawPath() != "",
		Running:      m.running,
		Version:      m.version,
		Port:         m.ocPort,
		HealthOK:     m.healthOK,
		RestartCount: m.restartCount,
		InstallCount: m.installCount,
		LastError:    m.lastError,
		AutoHeal:     m.autoHeal,
		Platform:     runtime.GOOS + "/" + runtime.GOARCH,
	}

	if !m.lastHealth.IsZero() {
		status.LastHealth = m.lastHealth.Format(time.RFC3339)
	}

	// 如果标记为运行但很久没健康检查了，重新检查
	if m.running && time.Since(m.lastHealth) > 30*time.Second {
		m.mu.RUnlock()
		ok := m.checkHealth()
		m.mu.RLock()
		status.HealthOK = ok
		if ok {
			status.LastHealth = time.Now().Format(time.RFC3339)
		}
	}

	// 二次探测：Manager 不跟踪手动启动的 OpenClaw 实例，
	// 但标准端口 18789 上可能有已运行的实例
	if !m.running && !m.healthOK {
		m.mu.RUnlock()
		detectedPort := probeOpenClawOnPort(18789)
		m.mu.RLock()
		if detectedPort > 0 {
			status.Running = true
			status.HealthOK = true
			status.Port = detectedPort
			status.LastHealth = time.Now().Format(time.RFC3339)
		}
	}

	return status
}

// Configure 配置远程 Gateway 连接
func (m *OpenClawManager) Configure(remote, token string) (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	var b strings.Builder

	if remote == "" {
		return "", fmt.Errorf("remote URL 不能为空")
	}

	m.ocRemote = remote
	if token != "" {
		m.ocToken = token
	}

	b.WriteString(fmt.Sprintf("  📡 配置远程 Gateway: %s\n", remote))
	if token != "" {
		b.WriteString(fmt.Sprintf("  🔑 Token: %s...\n", token[:min(len(token), 8)]))
	}

	// 写入配置文件
	configDir := m.ocDataDir
	if configDir == "" {
		homeDir := getWorkerHomeDir()
		configDir = homeDir + "/.openclaw"
	}
	os.MkdirAll(configDir, 0755)

	configFile := configDir + "/remote_config.json"
	config := map[string]string{
		"remote": remote,
		"token":  token,
	}
	data, _ := json.MarshalIndent(config, "", "  ")
	if err := os.WriteFile(configFile, data, 0644); err != nil {
		b.WriteString(fmt.Sprintf("  ⚠️  写入配置文件失败: %v\n", err))
	} else {
		b.WriteString(fmt.Sprintf("  ✅ 配置已保存到 %s\n", configFile))
	}

	// 如果 OpenClaw 正在运行，尝试通过 openclaw 命令配置
	if m.installPath != "" {
		// 尝试用 openclaw 的 device-pair 插件配置
		// openclaw gateway config set --key gateway.remote.url --value <remote>
		// 但 openclaw 命令行可能不支持直接设置，所以先记录配置
		b.WriteString("  ℹ️  配置已保存。重启 OpenClaw Gateway 后生效。\n")
		b.WriteString("  💡 执行 openclaw_start 重启 Gateway\n")
	}

	return b.String(), nil
}

// ── 健康检查与自愈 ──

// StartHealthLoop 启动周期性健康检查（每 30 秒）
func (m *OpenClawManager) StartHealthLoop() {
	m.mu.Lock()
	if m.healthActive {
		m.mu.Unlock()
		return
	}
	m.healthActive = true
	m.healthStopCh = make(chan struct{})
	m.mu.Unlock()

	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				m.healthCheckTick()
			case <-m.healthStopCh:
				return
			}
		}
	}()

	fmt.Printf(" %s🩺 OpenClaw 健康检查已启动 (间隔 30s)%s\n", tscolor(), reset())
}

// StopHealthLoop 停止健康检查
func (m *OpenClawManager) StopHealthLoop() {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.healthActive {
		close(m.healthStopCh)
		m.healthActive = false
	}
}

// healthCheckTick 健康检查 tick
func (m *OpenClawManager) healthCheckTick() {
	m.mu.RLock()
	running := m.running
	autoHeal := m.autoHeal
	installPath := m.installPath
	port := m.ocPort
	m.mu.RUnlock()

	if !running {
		return
	}

	ok := m.checkHealth()
	m.mu.Lock()
	m.healthOK = ok
	if ok {
		m.lastHealth = time.Now()
	}
	m.mu.Unlock()

	if !ok && autoHeal && installPath != "" {
		fmt.Printf(" %s⚠️ OpenClaw 健康检查失败，尝试自动重启...%s\n", yellow(bold("")), reset())
		m.mu.Lock()
		m.restartCount++
		m.mu.Unlock()

		// 自动重启
		result, err := m.Start(port)
		if err != nil {
			fmt.Printf(" %s❌ OpenClaw 自动重启失败: %v%s\n", red(bold("")), err, reset())
			m.mu.Lock()
			m.lastError = fmt.Sprintf("自动重启失败: %v", err)
			m.mu.Unlock()
		} else {
			fmt.Printf(" %s✅ OpenClaw 自动重启成功%s\n", green(bold("")), reset())
			fmt.Printf("   %s\n", strings.ReplaceAll(result, "\n", "\n   "))
		}
	}
}

// probeOpenClawOnPort 探测指定端口是否有 OpenClaw 在运行
// 通过网络健康检查判断，不依赖 Manager 的进程跟踪
func probeOpenClawOnPort(port int) int {
	url := fmt.Sprintf("http://127.0.0.1:%d/health", port)
	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return 0
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0
	}

	var health struct {
		OK     bool   `json:"ok"`
		Status string `json:"status"`
	}
	if err := json.Unmarshal(body, &health); err != nil {
		return 0
	}

	if health.OK && health.Status == "live" {
		return port
	}
	return 0
}

// checkHealth 检查 OpenClaw Gateway 健康状态
func (m *OpenClawManager) checkHealth() bool {
	port := m.ocPort
	url := fmt.Sprintf("http://127.0.0.1:%d/health", port)

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return false
	}

	// 解析响应
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return false
	}

	var health struct {
		OK     bool   `json:"ok"`
		Status string `json:"status"`
	}
	if err := json.Unmarshal(body, &health); err != nil {
		return false
	}

	return health.OK && health.Status == "live"
}

// ── 内部辅助 ──

// killExisting 杀死已有的 OpenClaw 进程
func (m *OpenClawManager) killExisting() {
	if runtime.GOOS == "windows" {
		// Windows: taskkill
		execCmd("taskkill", "/F", "/IM", "node.exe", "/FI", "WINDOWTITLE eq openclaw*")
		execCmd("taskkill", "/F", "/IM", "openclaw*")
	} else {
		// Linux: pkill
		execCmd("pkill", "-f", "openclaw-gateway")
		execCmd("pkill", "-f", "openclaw gateway")
	}
}

// findOpenClawPath 查找 openclaw 可执行文件路径
func findOpenClawPath() string {
	// 1. 直接查找 PATH
	if path := executil.SafeLookPath("openclaw"); path != "" {
		return path
	}

	// 2. 常见 npm 全局安装路径
	homeDir := getWorkerHomeDir()
	candidates := []string{
		homeDir + "/npm-packages/bin/openclaw",
		homeDir + "/.npm-global/bin/openclaw",
		"/usr/local/bin/openclaw",
		"/usr/bin/openclaw",
		"/opt/homebrew/bin/openclaw",
	}

	// Windows 特有路径
	if runtime.GOOS == "windows" {
		appData := os.Getenv("APPDATA")
		if appData != "" {
			candidates = append(candidates,
				appData+"\\npm\\openclaw",
				appData+"\\npm\\openclaw.cmd",
				appData+"\\npm\\openclaw.ps1",
			)
		}
		programFiles := os.Getenv("ProgramFiles")
		if programFiles != "" {
			candidates = append(candidates,
				programFiles+"\\nodejs\\openclaw",
				programFiles+"\\nodejs\\openclaw.cmd",
			)
		}
	}

	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}

	return ""
}

// execCmd 执行命令并返回 stdout
func execCmd(name string, args ...string) string {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, name, args...)
	output, err := cmd.Output()
	if err != nil {
		return ""
	}
	return string(output)
}
