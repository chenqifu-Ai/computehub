// ComputeHub Worker Upgrade Executor — Phase 3
//
// Zero-downtime upgrade via test-register pattern:
//   1. Download new binary to staging
//   2. Spawn child (staging) --test-register
//   3. Child registers to Gateway (temp node_id)
//   4. Child notifies parent "ready"
//   5. Parent sends "ack" to child
//   6. Parent backups old binary, unregisters, exits
//   7. Child detects parent gone, replaces file, registers clean, enters worker loop
//
// No script-based file replacement — all orchestrated via TCP IPC.

package workercmd

import (
	"bufio"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/computehub/opc/src/version"
)

// ═══════════════════════════════════════════
// UpgradeExecutor — 升级执行器
// ═══════════════════════════════════════════

// UpgradeExecutor owns the parent-side orchestration of test-register upgrade.
// It delegates file operations to UpgradeEngine (download, backup, cleanup).
type UpgradeExecutor struct {
	state  *WorkerState
	engine *UpgradeEngine
}

// NewUpgradeExecutor creates an executor bound to a WorkerState.
func NewUpgradeExecutor(state *WorkerState) *UpgradeExecutor {
	return &UpgradeExecutor{
		state:  state,
		engine: NewUpgradeEngine(state),
	}
}

// ═══════════════════════════════════════════
// Execute — 完整升级流程 (父进程侧)
// ═══════════════════════════════════════════

// Execute performs a test-register upgrade:
//   - Downloads new binary
//   - Spawns child with --test-register
//   - Waits for child's register result via TCP
//   - On success: backups old binary, unregisters, exits
//   - On failure: kills child, returns error (no files touched)
//
// Called by UpgradeManager.RunOnce(). This function does NOT return
// on success — it calls os.Exit(0) after the handoff.
func (e *UpgradeExecutor) Execute(newVersion string) error {
	// ── 1. Download new binary ──
	e.log("⬇️  下载版本 %s", newVersion)
	newBinary, err := e.engine.DownloadWithChecksum(newVersion)
	if err != nil {
		return fmt.Errorf("下载失败: %w", err)
	}
	e.log("✅ 已下载到: %s", newBinary)

	// ── 2. Verify downloaded binary ──
	if err := e.verifyBinaryVersion(newBinary, newVersion); err != nil {
		return fmt.Errorf("版本验证失败: %w", err)
	}

	// ── 3. Start TCP listener for IPC ──
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return fmt.Errorf("启动IPC listener失败: %w", err)
	}
	ctrlPort := listener.Addr().(*net.TCPAddr).Port

	// ── 4. Spawn child with --test-register ──
	childArgs := e.buildChildArgs(ctrlPort)
	e.log("🚀 Spawn子进程: %s --test-register ...", filepath.Base(newBinary))

	childCmd := exec.Command(newBinary, childArgs...)
	childCmd.Stdout = os.Stdout
	childCmd.Stderr = os.Stderr
	childCmd.Stdin = nil

	if err := childCmd.Start(); err != nil {
		listener.Close()
		return fmt.Errorf("spawn子进程失败: %w", err)
	}
	childPID := childCmd.Process.Pid
	e.log("👶 子进程 PID=%d", childPID)

	// ── 5. Wait for child to connect via TCP ──
	// Set a deadline so we don't hang forever
	listener.(*net.TCPListener).SetDeadline(time.Now().Add(60 * time.Second))

	conn, acceptErr := listener.Accept()
	listener.Close()

	if acceptErr != nil {
		// Kill child, cleanup
		e.killChild(childCmd)
		return fmt.Errorf("等待子进程连接超时 (60s): %w", acceptErr)
	}
	defer conn.Close()

	// ── 6. Read child's status ──
	reader := bufio.NewReader(conn)
	status, readErr := reader.ReadString('\n')
	status = strings.TrimSpace(status)

	if readErr != nil {
		e.killChild(childCmd)
		return fmt.Errorf("无法读取子进程状态: %w", readErr)
	}

	if strings.HasPrefix(status, "fail") {
		e.killChild(childCmd)
		return fmt.Errorf("子进程注册失败: %s", status)
	}

	if status != "ready" {
		e.killChild(childCmd)
		return fmt.Errorf("子进程返回未知状态: %s", status)
	}

	// ── 7. Child registered successfully! ──
	e.log("✅ 子进程注册成功，发送ack...")

	// Send "ack" to child — tells child to proceed
	conn.Write([]byte("ack\n"))

	// ── 8. Backup old binary ──
	currentExe, _ := os.Executable()
	if currentExe != "" {
		if _, err := e.engine.BackupCurrent(version.Short()); err != nil {
			e.log("⚠️  备份警告: %v", err)
		}
	} else {
		e.log("⚠️  无法获取当前exe路径，跳过备份")
	}

	// ── 9. Unregister from Gateway ──
	e.log("🗑️  注销节点 %s", e.state.nodeID)
	e.state.unregister()

	// ── 10. Cleanup old versions (non-blocking) ──
	go e.engine.CleanupOldVersions()

	// ── 11. Say goodbye — child takes over ──
	e.log("✅ 升级交接完成，父进程退出。子进程 (PID=%d) 将: 替换binary → 重新注册 → 正式运行", childPID)
	fmt.Printf("\n %s🔄 UpgradeExecutor: %s → %s 交接成功 (子PID=%d)%s\n",
		green(bold("")), version.Short(), newVersion, childPID, reset())

	// Small delay so child has time to see we're still alive
	time.Sleep(500 * time.Millisecond)
	os.Exit(0)
	return nil // unreachable
}

// ═══════════════════════════════════════════
// 辅助函数
// ═══════════════════════════════════════════

// buildChildArgs constructs the arguments for the child process.
// Takes the parent's args, strips --confirm-connect (not needed),
// and adds --test-register + --parent-ctrl.
func (e *UpgradeExecutor) buildChildArgs(ctrlPort int) []string {
	// Start with all of the parent's original args
	args := os.Args[1:]

	// Filter out flags that shouldn't be passed to child
	var filtered []string
	skipNext := false
	for _, a := range args {
		if skipNext {
			skipNext = false
			continue
		}
		// Skip --confirm-connect (test mode, not needed)
		if a == "--confirm-connect" {
			continue
		}
		// Skip --test-register if somehow present
		if a == "--test-register" {
			continue
		}
		// Skip --parent-ctrl
		if a == "--parent-ctrl" {
			skipNext = true
			continue
		}
		filtered = append(filtered, a)
	}

	// Add test-register flags
	filtered = append(filtered, "--test-register")
	filtered = append(filtered, "--parent-ctrl", fmt.Sprintf("127.0.0.1:%d", ctrlPort))

	return filtered
}

// verifyBinaryVersion runs the binary with "version" to confirm the version string matches.
func (e *UpgradeExecutor) verifyBinaryVersion(binaryPath string, expectedVersion string) error {
	e.log("🔍 验证下载的二进制版本...")
	verOut, err := exec.Command(binaryPath, "version").CombinedOutput()
	if err != nil {
		return fmt.Errorf("二进制无法执行: %w", err)
	}
	actualVer := strings.TrimSpace(string(verOut))
	if !strings.Contains(actualVer, expectedVersion) && !strings.Contains(expectedVersion, actualVer) {
		return fmt.Errorf("版本不匹配: 下载了 %s, 期待 %s", actualVer, expectedVersion)
	}
	e.log("✅ 版本验证通过: %s", actualVer)
	return nil
}

// killChild terminates the child process forcefully.
func (e *UpgradeExecutor) killChild(cmd *exec.Cmd) {
	if cmd == nil || cmd.Process == nil {
		return
	}
	e.log("💀 Kill子进程 PID=%d", cmd.Process.Pid)
	if runtime.GOOS == "windows" {
		// Windows: use taskkill for clean child tree kill
		exec.Command("taskkill", "/F", "/T", "/PID", fmt.Sprintf("%d", cmd.Process.Pid)).Run()
	} else {
		cmd.Process.Signal(os.Interrupt)
		time.Sleep(2 * time.Second)
		if cmd.Process != nil {
			cmd.Process.Kill()
		}
	}
}

func (e *UpgradeExecutor) log(format string, args ...interface{}) {
	t := time.Now().Format("15:04:05")
	fmt.Printf("\033[2m[%s] [Executor]\033[0m "+format+"\n", append([]interface{}{t}, args...)...)
}