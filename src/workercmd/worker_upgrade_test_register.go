// ComputeHub Worker Test-Register — Phase 3
//
// --test-register mode:
//   Child process spawned from staging binary.
//   Registers to Gateway, confirms connectivity, then waits for parent's ack.
//   After parent exits: replaces old binary → re-registers clean → enters Worker loop.
//
// This file runs IN THE CHILD PROCESS (the new binary).

package workercmd

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/computehub/opc/src/version"
)

// ═══════════════════════════════════════════
// RunTestRegister — 子进程入口点
// ═══════════════════════════════════════════

// RunTestRegister is the entry point for --test-register mode.
// It connects to parent via TCP, registers to Gateway, and awaits parent's fate.
//
// Returns an os.Exit-style code:
//   0 = success (parent confirmed, parent gone, binary replaced, ready to run)
//   1 = registration or IPC failure
func RunTestRegister(args []string) int {
	// ── 1. Parse args ──
	parentCtrlAddr := ""
	for i := 0; i < len(args); i++ {
		if args[i] == "--parent-ctrl" && i+1 < len(args) {
			parentCtrlAddr = args[i+1]
			i++
		}
	}

	if parentCtrlAddr == "" {
		fmt.Printf(" %s❌ --test-register requires --parent-ctrl <addr>%s\n", red(bold("")), reset())
		return 1
	}

	fmt.Printf("\n %s🔬 Test-Register 模式: 连接父进程 @ %s%s\n", yellow(bold("")), cyan(parentCtrlAddr), reset())

	// ── 2. Parse full config (same as normal Worker) ──
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

	// ── 3. Connect to parent via TCP ──
	conn, err := net.DialTimeout("tcp", parentCtrlAddr, 30*time.Second)
	if err != nil {
		fmt.Printf(" %s❌ 无法连接父进程 @ %s: %v%s\n", red(bold("")), parentCtrlAddr, err, reset())
		return 1
	}
	defer conn.Close()
	fmt.Printf(" %s✅ 已连接父进程 @ %s%s\n", green(""), cyan(parentCtrlAddr), reset())

	// ── 4. Create temporary WorkerState for registration ──
	state := &WorkerState{
		config:       cfg,
		client:       &http.Client{Timeout: 30 * time.Second},
		runningTasks: make(map[string]*exec.Cmd),
	}
	state.nodeID = cfg.NodeID

	// ── 5. Register to Gateway with test-register status ──
	fmt.Printf(" %s📝 注册节点 %s (test-register模式)...%s", yellow(""), cyan(cfg.NodeID), reset())

	if err := registerTestNode(state); err != nil {
		fmt.Printf("\n %s❌ test-register 注册失败: %v%s\n", red(bold("")), err, reset())
		conn.Write([]byte("fail:" + err.Error() + "\n"))
		return 1
	}
	fmt.Printf(" %s✅%s\n", green(""), reset())

	// ── 6. Send "ready" to parent ──
	conn.Write([]byte("ready\n"))
	fmt.Printf(" %s✅ 已通知父进程 'ready'，等待ack...%s", yellow(""), reset())

	// ── 7. Wait for parent's "ack" ──
	buf := make([]byte, 64)
	conn.SetReadDeadline(time.Now().Add(120 * time.Second))
	n, err := conn.Read(buf)
	if err != nil {
		fmt.Printf("\n %s❌ 未收到父进程ack: %v%s\n", red(bold("")), err, reset())
		return 1
	}
	ack := strings.TrimSpace(string(buf[:n]))
	if ack != "ack" {
		fmt.Printf("\n %s❌ 收到异常ack: %q%s\n", red(bold("")), ack, reset())
		return 1
	}
	fmt.Printf(" %s✅ 收到父进程ack!%s\n", green(bold("")), reset())

	// ── 8. Parent will exit soon. Wait for parent to disappear. ──
	// We wait by monitoring the TCP connection — parent's process exit
	// will close its end of the connection.
	fmt.Printf(" %s⏳ 等待父进程退出...%s", dim(""), reset())

	// Read until EOF (connection closed = parent exited)
	conn.SetReadDeadline(time.Now().Add(120 * time.Second))
	_, readErr := conn.Read(buf)
	if readErr == nil {
		// Shouldn't happen — parent should close the connection on exit
		fmt.Printf(" %s⚠️  父进程仍在通信，强制等待...%s", yellow(""), reset())
	}

	// Double-check by testing the connection
	// (Short sleep to ensure parent has fully cleaned up)
	time.Sleep(2 * time.Second)
	fmt.Printf(" %s✅ 父进程已退出%s\n", green(""), reset())

	// ── 9. Replace old binary with this staging binary ──
	// We're running from staging directory. We need to copy ourselves to the
	// original install path. We can do this safely because we're NOT the running
	// binary at that path (we loaded a separate copy into memory).
	currentExe, err := os.Executable()
	if err != nil || currentExe == "" {
		fmt.Printf(" %s⚠️  无法确定自身路径，跳过替换 (将继续用当前binary运行)%s\n", yellow(""), reset())
	} else {
		// Determine the original install path
		originalExe := resolveOriginalBinaryPath(currentExe)
		backupFile := fmt.Sprintf("%s.bak.pre-upgrade", originalExe)

		fmt.Printf(" %s📦 替换binary: %s%s\n", yellow(bold("")), cyan(originalExe), reset())

		// Backup current (if not already done by parent)
		if _, err := os.Stat(backupFile); os.IsNotExist(err) {
			if err := copyFile(originalExe, backupFile); err != nil {
				fmt.Printf(" %s⚠️  创建回滚备份失败: %v%s\n", yellow(""), err, reset())
			} else {
				fmt.Printf(" %s📦 回滚备份: %s%s\n", dim(""), cyan(backupFile), reset())
			}
		}

		// Replace original with staging binary
		if err := copyFile(currentExe, originalExe); err != nil {
			fmt.Printf(" %s❌ 替换binary失败: %v%s\n", red(bold("")), err, reset())
			fmt.Printf(" %s⚠️  将继续用当前staging binary运行%s\n", yellow(""), reset())
		} else {
			if runtime.GOOS != "windows" {
				os.Chmod(originalExe, 0755)
			}
			fmt.Printf(" %s✅ binary已替换: %s%s\n", green(bold("")), cyan(originalExe), reset())
		}
	}

	// ── 10. Re-register (clean, no test flag) ──
	fmt.Printf(" %s📝 重新注册 (clean)...%s", yellow(""), reset())

	if err := state.register(); err != nil {
		fmt.Printf("\n %s❌ 重新注册失败: %v，将在心跳中重试%s\n", red(bold("")), err, reset())
	} else {
		fmt.Printf(" %s✅ 已重新注册!%s\n", green(bold("")), reset())
	}

	// ── 11. Cleanup: remove staging binary ──
	go func() {
		stagingPath := getStagingPath(cfg.NodeID)
		os.RemoveAll(stagingPath)
	}()

	// ── 12. Enter normal Worker loop ──
	fmt.Printf("\n %s🎉 升级成功! %s 正式进入Worker循环%s\n\n",
		green(bold("")), cyan(cfg.NodeID), reset())

	// Set up signal handling for graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	// Start heartbeats, polling, agent — everything the normal Worker does
	go state.heartbeatLoop()

	// Create UpgradeManager (will detect we're latest version)
	state.um = NewUpgradeManager(state)
	
	// CRITICAL FIX: Update cache so next restart won't trigger upgrade loop.
	// CachedVersion must match the current binary version, otherwise the
	// next systemd restart → loadCache() reads old version → triggers upgrade.
	if state.um != nil {
		state.um.cache.CachedVersion = version.Short()
		state.um.cache.LastCheckTime = time.Now()
		state.um.cache.UpgradeCount++
		state.um.saveCache()
	}
	
	go state.upgradeLoop()

	// Start task poller
	go state.taskPollLoop()

	// Start Worker Agent
	state.startWorkerAgent()

	// Wait for signal
	<-sigCh

	fmt.Printf("\n %s⚠️  收到终止信号，正在关闭...%s\n", yellow(bold("")), reset())
	state.unregister()
	return 0
}

// ═══════════════════════════════════════════
// 辅助函数
// ═══════════════════════════════════════════

// registerTestNode registers to Gateway with "online-test" status.
// This tells Gateway this is a verification-only registration
// that won't receive task assignments.
func registerTestNode(s *WorkerState) error {
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
		Status:         "online-test", // special status: test registration
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

	if !result.Success && !strings.Contains(result.Error, "already registered") {
		return fmt.Errorf("注册被拒: %s", result.Error)
	}

	return nil
}

// resolveOriginalBinaryPath determines the original install path from the staging path.
// Staging paths look like: ~/.computehub/downloads/computehub-v1.3.2
// The original install path is where the parent binary was running from.
func resolveOriginalBinaryPath(currentExe string) string {
	baseName := filepath.Base(currentExe)
	if runtime.GOOS == "windows" {
		baseName = "computehub.exe"
	} else {
		baseName = "computehub"
	}

	// Try common install locations first — staging path is in ~/.computehub/downloads/
	// so we know we're NOT at the install location.
	candidates := []string{
		"/usr/local/bin/" + baseName,
		"/usr/bin/" + baseName,
		"/opt/computehub/" + baseName,
		filepath.Join(os.Getenv("HOME"), "bin", baseName),
		// Current directory (common for development)
		filepath.Join(".", baseName),
	}
	if runtime.GOOS == "windows" {
		candidates = []string{
			"C:\\computehub\\" + baseName,
			filepath.Join(os.Getenv("ProgramFiles"), "ComputeHub", baseName),
			"C:\\tmp\\" + baseName,
			filepath.Join(os.Getenv("USERPROFILE"), "computehub.exe"),
		}
	}

	for _, c := range candidates {
		fi, err := os.Stat(c)
		if err == nil && !fi.IsDir() && fi.Size() > 5*1024*1024 {
			abs, _ := filepath.Abs(c)
			return abs
		}
	}

	// Last resort: search PATH (manual, avoid faccessat2 SIGSYS on Android/Termux)
	if p := findInPath(baseName); p != "" {
		abs, _ := filepath.Abs(p)
		return abs
	}

	// Fallback to the staging dir name without version suffix
	dir := filepath.Dir(currentExe)
	return filepath.Join(dir, baseName)
}

// getStagingPath returns the staging directory for this node's downloads.
func getStagingPath(nodeID string) string {
	return filepath.Join(getWorkerHomeDir(), ".computehub", "downloads")
}

// startWorkerAgent is a helper to start the worker agent server from child process.
func (s *WorkerState) startWorkerAgent() {
	agentPort := 8383
	if p := os.Getenv("WORKER_AGENT_PORT"); p != "" {
		if port, err := strconv.Atoi(p); err == nil && port > 0 {
			agentPort = port
		}
	}
	workerAgentServer = startWorkerAgent(s, s.um, agentPort)
}

// findInPath manually searches PATH for an executable, avoiding faccessat2 (SIGSYS on Android/Termux).
func findInPath(name string) string {
	pathEnv := os.Getenv("PATH")
	if pathEnv == "" {
		return ""
	}
	dirs := filepath.SplitList(pathEnv)
	for _, dir := range dirs {
		candidate := filepath.Join(dir, name)
		fi, err := os.Stat(candidate)
		if err != nil {
			continue
		}
		if fi.IsDir() {
			continue
		}
		// On Unix, check executable bit manually (avoid faccessat2)
		if runtime.GOOS != "windows" {
			if fi.Mode()&0111 == 0 {
				continue
			}
		}
		return candidate
	}
	return ""
}