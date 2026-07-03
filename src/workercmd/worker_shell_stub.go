//go:build !linux && !darwin

package workercmd

import (
	"github.com/gorilla/websocket"
)

func (sm *ShellManager) StartShell(sessionID, nodeID string, conn *websocket.Conn, rows, cols uint16) error {
	return nil
}

func (sm *ShellManager) HandleShellInput(sessionID string, data []byte, isBinary bool) error {
	return nil
}

func (sm *ShellManager) HandleShellResize(sessionID string, rows, cols uint16) {}

func (sm *ShellManager) CloseSession(sessionID string, conn *websocket.Conn) {}

func (sm *ShellManager) CloseAllByConn(conn *websocket.Conn) {}