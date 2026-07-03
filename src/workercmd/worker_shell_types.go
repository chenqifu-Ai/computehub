// Worker 交互式 Shell — 类型定义（全平台共享）

package workercmd

import (
	"io"
	"os"
	"os/exec"
	"sync"

	"github.com/gorilla/websocket"
)

// ShellSession Worker 侧的一个交互 Shell 会话
type ShellSession struct {
	SessionID string
	NodeID    string
	master    *os.File        // PTY master fd（PTY 模式）
	slave     *os.File        // PTY slave fd（PTY 模式）
	pipeIn    io.WriteCloser  // stdin pipe（Pipe 模式）
	pipeOut   io.Reader       // stdout pipe（Pipe 模式）
	pipe      bool            // 是否 Pipe 模式
	cmd       *exec.Cmd
	conn      *websocket.Conn
	mu        sync.Mutex
	closed    bool
	done      chan struct{}
}

// ShellManager 管理 Worker 上所有活跃 Shell 会话
type ShellManager struct {
	mu       sync.Mutex
	sessions map[string]*ShellSession
}

var globalShellManager = &ShellManager{
	sessions: make(map[string]*ShellSession),
}

// GetShellManager 获取全局 ShellManager 实例
func GetShellManager() *ShellManager {
	return globalShellManager
}