// Package workercmd — 持久化 OpenClaw CLI 管道
// BUGFIX: 省掉每次调用 `openclaw agent --message` 时 proot 启动的 ~0.5s 开销。
//
// 原理：
//   Worker 启动时 spawn 一个 proot-distro login ubuntu bash 进程并保持常驻。
//   Agent 的 exec_shell/openclaw_chat 工具通过此进程的 stdin/stdout 管道通信，
//   无需每次重新启动 proot 容器。
//
// 生命周期：
//   Start() → 启动持久 proot bash 进程
//   Exec(cmd) → 通过管道发送命令，读取输出
//   Close() → 关闭进程

package workercmd

import (
	"bufio"
	"bytes"
	"context"
	"fmt"
	"io"
	"os/exec"
	"strings"
	"sync"
	"time"

	"github.com/computehub/opc/src/executil"
)

// PersistentShell 持久化 shell 会话
// 持有一个 long-lived 的 shell 进程，通过 stdin/stdout 管道通信
type PersistentShell struct {
	mu         sync.Mutex
	cmd        *exec.Cmd
	stdin      io.WriteCloser
	stdout     io.ReadCloser
	stderr     io.ReadCloser
	scanner    *bufio.Scanner // 用于逐行读取 stdout
	ready      bool
	closeCh    chan struct{}
	shellPath  string         // 实际 shell 路径（sh 或 powershell）
	shellArgs  []string       // 额外参数
	detectDone chan struct{}  // 检测脚本完成后关闭
}

// NewPersistentShell 创建持久化 shell 会话
// shell: "sh"（默认）或 "powershell"（Windows）
// 对于 Android，会在 proot 中启动 sh
func NewPersistentShell() *PersistentShell {
	ps := &PersistentShell{
		closeCh:    make(chan struct{}),
		detectDone: make(chan struct{}),
	}

	// 检测 proot 是否可用
	if executil.SafeLookPath("proot-distro") != "" {
		// Android Termux: 在 proot ubuntu 中启动 shell
		ps.shellPath = "proot-distro"
		ps.shellArgs = []string{"login", "ubuntu", "--", "bash", "-i"}
	} else {
		// 普通 Linux: 直接 sh
		shPath := executil.SafeLookPath("sh")
		if shPath == "" {
			shPath = "/bin/sh"
		}
		ps.shellPath = shPath
		ps.shellArgs = []string{"-i"} // interactive mode
	}

	return ps
}

// NewDirectShell 创建持久化 shell，直接使用原生 sh（不经过 proot）。
// 用于需要执行主机命令的场景（如 openclaw CLI），与 NewPersistentShell() 的 proot 检测逻辑相反。
func NewDirectShell() *PersistentShell {
	ps := &PersistentShell{
		closeCh:    make(chan struct{}),
		detectDone: make(chan struct{}),
	}
	shPath := executil.SafeLookPath("sh")
	if shPath == "" {
		shPath = "/bin/sh"
	}
	ps.shellPath = shPath
	ps.shellArgs = []string{"-i"}
	return ps
}

// Start 启动持久化 shell 会话
func (ps *PersistentShell) Start() error {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	if ps.ready {
		return nil
	}

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, ps.shellPath, ps.shellArgs...)

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return fmt.Errorf("创建 stdin pipe 失败: %w", err)
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("创建 stdout pipe 失败: %w", err)
	}

	stderr, err := cmd.StderrPipe()
	if err != nil {
		return fmt.Errorf("创建 stderr pipe 失败: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("启动 shell 失败: %w", err)
	}

	ps.cmd = cmd
	ps.stdin = stdin
	ps.stdout = stdout
	ps.stderr = stderr
	ps.scanner = bufio.NewScanner(stdout)

	// 等待 shell 就绪
	readyCh := make(chan bool, 1)
	go func() {
		// 发送一个 echo 标记检测 shell 是否就绪
		fmt.Fprintf(stdin, `echo "__SHELL_READY__"`+"\n")
		scanner := bufio.NewScanner(stdout)
		for scanner.Scan() {
			line := scanner.Text()
			if strings.Contains(line, "__SHELL_READY__") {
				readyCh <- true
				return
			}
		}
		readyCh <- false
	}()

	select {
	case ready := <-readyCh:
		if !ready {
			cmd.Process.Kill()
			return fmt.Errorf("shell 就绪检测失败")
		}
	case <-time.After(10 * time.Second):
		cmd.Process.Kill()
		return fmt.Errorf("shell 就绪检测超时")
	}

	// 启动后台清理协程：如果 subprocess 异常退出，标记 not ready
	go func() {
		cmd.Wait()
		ps.mu.Lock()
		ps.ready = false
		ps.mu.Unlock()
		close(ps.closeCh)
	}()

	ps.ready = true
	close(ps.detectDone)

	fmt.Printf(" %s💡 持久化 shell 已启动 (%s %s)%s\n", dim(""), ps.shellPath, strings.Join(ps.shellArgs, " "), reset())
	return nil
}

// Exec 通过持久化 shell 执行一条命令
// 使用标记法隔离输出：echo "__CMD_START__" + command + echo "__CMD_END__"
// 返回 stdout 文本
func (ps *PersistentShell) Exec(command string, timeout time.Duration) (string, error) {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	if !ps.ready || ps.cmd == nil || ps.cmd.Process == nil {
		return "", fmt.Errorf("持久化 shell 未就绪")
	}

	if timeout == 0 {
		timeout = 30 * time.Second
	}

	// 使用标记法包裹命令输出
	markerStart := fmt.Sprintf("__CMD_%d_START__", time.Now().UnixNano())
	markerEnd := fmt.Sprintf("__CMD_%d_END__", time.Now().UnixNano())

	fullCmd := fmt.Sprintf("echo '%s'\n%s\necho '%s'\n", markerStart, command, markerEnd)

	// 写入 stdin
	if _, err := io.WriteString(ps.stdin, fullCmd); err != nil {
		ps.ready = false
		return "", fmt.Errorf("写入 stdin 失败: %w", err)
	}

	// 读取输出直到遇到 markerEnd
	var output bytes.Buffer
	started := false
	// unused
	scanner := bufio.NewScanner(ps.stdout)

	// 需要额外 goroutine 来扫描，避免阻塞
	resultCh := make(chan string, 1)
	errCh := make(chan error, 1)

	go func() {
		for scanner.Scan() {
			line := scanner.Text()
			if strings.Contains(line, markerStart) {
				started = true
				continue
			}
			if strings.Contains(line, markerEnd) {
				resultCh <- output.String()
				return
			}
			if started {
				if output.Len() > 0 {
					output.WriteString("\n")
				}
				output.WriteString(line)
			}
		}
		errCh <- scanner.Err()
	}()

	select {
	case result := <-resultCh:
		return strings.TrimSpace(result), nil
	case err := <-errCh:
		ps.ready = false
		return "", fmt.Errorf("读取输出失败: %w", err)
	case <-time.After(timeout):
		ps.ready = false
		return "", fmt.Errorf("命令执行超时 (%v)", timeout)
	case <-ps.closeCh:
		return "", fmt.Errorf("shell 进程已退出")
	}
}

// Execv 便捷版：直接执行一个命令，使用默认超时
func (ps *PersistentShell) Execv(command string) (string, error) {
	return ps.Exec(command, 30*time.Second)
}

// Close 关闭持久化 shell
func (ps *PersistentShell) Close() {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	if ps.cmd != nil && ps.cmd.Process != nil {
		ps.cmd.Process.Kill()
		ps.cmd.Wait()
	}

	ps.ready = false
	fmt.Printf(" %s💡 持久化 shell 已关闭%s\n", dim(""), reset())
}

// IsReady 返回 shell 是否就绪
func (ps *PersistentShell) IsReady() bool {
	ps.mu.Lock()
	defer ps.mu.Unlock()
	return ps.ready
}

// ── OpenClaw 桥接工具 ——

// OpenClawBridge 本地 OpenClaw 持久化通信桥梁
// 通过 PersistentShell 与 proot 中的 openclaw 通信
// 避免每次调用都启动 proot 容器
type OpenClawBridge struct {
	shell    *PersistentShell
	ready    bool
	mu       sync.RWMutex
	nodeID   string
}

// NewOpenClawBridge 创建 OpenClaw 桥接
// 注意：使用 NewDirectShell() 直接在主机 shell 中运行 openclaw CLI，
// 不经过 proot（openclaw 安装在 Termux 主机，不在 proot 容器内）。
func NewOpenClawBridge(nodeID string) *OpenClawBridge {
	return &OpenClawBridge{
		shell:  NewDirectShell(),
		nodeID: nodeID,
	}
}

// Start 启动桥接（启动持久化 proot shell）
func (b *OpenClawBridge) Start() error {
	if err := b.shell.Start(); err != nil {
		return err
	}
	b.mu.Lock()
	b.ready = true
	b.mu.Unlock()

	fmt.Printf(" %s🔗 OpenClaw 桥接已启动 (%s)%s\n", green(bold("")), b.nodeID, reset())
	return nil
}

// Chat 向本机 OpenClaw Agent 发送消息并获取回复
// 直接通过持久化 shell 调用 openclaw agent CLI
func (b *OpenClawBridge) Chat(message string, timeout time.Duration) (string, error) {
	b.mu.RLock()
	ready := b.ready
	b.mu.RUnlock()

	if !ready {
		return "", fmt.Errorf("OpenClaw 桥接未就绪")
	}

	// 构建安全命令：用单引号包裹消息，避免 bash 展开
	escapedMsg := strings.ReplaceAll(message, "'", "'\\''")
	cmd := fmt.Sprintf("cd /root && openclaw agent --agent main --message '%s' --json 2>&1 | tail -20", escapedMsg)

	return b.shell.Exec(cmd, timeout)
}

// Exec 向本机 OpenClaw 执行任意 shell 命令
func (b *OpenClawBridge) Exec(command string) (string, error) {
	b.mu.RLock()
	ready := b.ready
	b.mu.RUnlock()

	if !ready {
		return "", fmt.Errorf("OpenClaw 桥接未就绪")
	}

	return b.shell.Execv(command)
}

// Close 关闭桥接
func (b *OpenClawBridge) Close() {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.ready {
		b.shell.Close()
		b.ready = false
	}
}

// IsReady 返回桥接是否就绪
func (b *OpenClawBridge) IsReady() bool {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.ready
}