//go:build linux || darwin

// Worker 交互式 Shell — Pipe 模式（PROot/容器/原生 Linux 全兼容）
// 通过 stdin/stdout pipe 与 shell 进程交互
// ⚠️ 不依赖 PTY，支援所有容器环境

package workercmd

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
)

func (sm *ShellManager) StartShell(sessionID, nodeID string, conn *websocket.Conn, rows, cols uint16) error {
	sm.mu.Lock()
	if old, ok := sm.sessions[sessionID]; ok {
		old.Close()
	}
	sm.mu.Unlock()

	// 使用 script 命令模拟 PTY 环境（兼容 PROot/容器/原生 Linux）
	// script -q -c "bash -i" /dev/null 创建伪终端上下文，确保行缓冲输出
	// -q: 安静模式  -c: 命令  /dev/null: 不记录输出文件
	cmd := exec.Command("script", "-q", "-f", "-c", "bash -i", "/dev/null")
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return fmt.Errorf("stdin pipe: %w", err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("stdout pipe: %w", err)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return fmt.Errorf("stderr pipe: %w", err)
	}
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("shell start: %w", err)
	}

	sess := &ShellSession{
		SessionID: sessionID, NodeID: nodeID,
		pipeIn: stdin, pipeOut: stdout,
		cmd: cmd, conn: conn,
		done: make(chan struct{}), pipe: true,
	}

	sm.mu.Lock()
	sm.sessions[sessionID] = sess
	sm.mu.Unlock()

	log.Printf("💻 [Shell] 会话 %s 已启动 (PID=%d, mode=PIPE)", sessionID, cmd.Process.Pid)

	go sess.readPipes(stdout, stderr)
	go sess.waitLoop()

	return nil
}

func (sm *ShellManager) HandleShellInput(sessionID string, data []byte, isBinary bool) error {
	sm.mu.Lock()
	sess, ok := sm.sessions[sessionID]
	sm.mu.Unlock()
	if !ok {
		return nil
	}
	sess.mu.Lock()
	defer sess.mu.Unlock()
	if sess.closed || sess.pipeIn == nil {
		return nil
	}

	var input string
	if isBinary {
		input = string(data)
	} else {
		var msg struct{ Data string }
		if err := json.Unmarshal(data, &msg); err == nil {
			input = msg.Data
		} else {
			input = string(data)
		}
	}

	_, err := sess.pipeIn.Write([]byte(input))
	return err
}

func (sm *ShellManager) HandleShellResize(sessionID string, rows, cols uint16) {
	// Pipe 模式下 resize 无效果，忽略
}

func (sm *ShellManager) CloseSession(sessionID string, conn *websocket.Conn) {
	sm.mu.Lock()
	sess, ok := sm.sessions[sessionID]
	if ok {
		delete(sm.sessions, sessionID)
	}
	sm.mu.Unlock()
	if ok {
		sess.Close()
	}
}

func (sm *ShellManager) CloseAllByConn(conn *websocket.Conn) {
	sm.mu.Lock()
	toClose := make([]string, 0)
	for id, sess := range sm.sessions {
		if sess.conn == conn {
			toClose = append(toClose, id)
		}
	}
	for _, id := range toClose {
		delete(sm.sessions, id)
	}
	sm.mu.Unlock()
	for _, id := range toClose {
		log.Printf("💻 [Shell] WS 断开，关闭会话 %s", id)
		sm.CloseSession(id, conn)
	}
}

// readPipes 从 stdout/stderr 读取并发送到 WS
// 使用原始读取而非 bufio.Scanner 确保即时输出
func (s *ShellSession) readPipes(stdout, stderr io.Reader) {
	var wg sync.WaitGroup
	wg.Add(2)

	pipeFn := func(reader io.Reader, name string) {
		defer wg.Done()
		buf := make([]byte, 4096)
		for {
			n, err := reader.Read(buf)
			if err != nil {
				if err != io.EOF && !isClosedErr(err) {
					log.Printf("💻 [Shell] %s read: %v", name, err)
				}
				return
			}
			if n > 0 {
				s.sendOutput(string(buf[:n]))
			}
		}
	}

	go pipeFn(stdout, "stdout")
	go pipeFn(stderr, "stderr")
	wg.Wait()
	wg.Wait()

	s.mu.Lock()
	conn := s.conn
	s.mu.Unlock()
	if conn != nil {
		conn.WriteJSON(map[string]interface{}{
			"msg_type":   "shell_close",
			"session_id": s.SessionID,
			"status":     "exited",
		})
	}
}

func (s *ShellSession) sendOutput(data string) {
	s.mu.Lock()
	conn := s.conn
	s.mu.Unlock()
	if conn == nil {
		return
	}
	conn.SetWriteDeadline(time.Now().Add(3 * time.Second))
	conn.WriteJSON(map[string]interface{}{
		"msg_type":   "shell_output",
		"session_id": s.SessionID,
		"data":       data,
	})
}

func (s *ShellSession) waitLoop() {
	s.cmd.Wait()
	s.mu.Lock()
	conn := s.conn
	s.closed = true
	s.mu.Unlock()
	if conn != nil {
		conn.WriteJSON(map[string]interface{}{
			"msg_type":   "shell_close",
			"session_id": s.SessionID,
			"status":     "exited",
		})
	}
	close(s.done)
	GetShellManager().CloseSession(s.SessionID, conn)
}

func isClosedErr(err error) bool {
	if err == nil {
		return false
	}
	s := err.Error()
	return s == "file already closed" || s == "bad file descriptor" || s == os.ErrClosed.Error()
}

func (s *ShellSession) Close() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed {
		return
	}
	s.closed = true
	if s.pipeIn != nil {
		s.pipeIn.Close()
		s.pipeIn = nil
	}
	if s.cmd != nil && s.cmd.Process != nil {
		s.cmd.Process.Kill()
	}
	log.Printf("💻 [Shell] 会话 %s 已关闭", s.SessionID)
}