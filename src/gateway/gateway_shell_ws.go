// Gateway 端 TUI Shell WS 端点 — 交互式远程终端
//
// TUI 通过单独的 WS 连接 `/api/v1/tui/shell` 连接 Gateway，
// 与 Worker 侧的 `/api/v1/ws` 相互独立。
// Gateway 负责在 TUI 和 Worker 之间路由 Shell 消息。

package gateway

import (
	"encoding/json"
	"log"
	"net/http"
	"time"
)

// ── TUI Shell WS 端点 ──

// HandleTUIShellWS 处理 TUI 端的 WebSocket Shell 连接
// TUI 连接此端点开启远程交互终端
func (g *OpcGateway) HandleTUIShellWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("💻 [Shell] TUI WS 升级失败: %v", err)
		return
	}

	log.Printf("💻 [Shell] TUI 已连接 (WS)")
	defer func() {
		g.shellRouter.CloseByTUI(conn)
		conn.Close()
		log.Printf("💻 [Shell] TUI 已断开")
	}()

	readTimeout := 60 * time.Second

	for {
		conn.SetReadDeadline(time.Now().Add(readTimeout))
		_, msg, err := conn.ReadMessage()
		if err != nil {
			log.Printf("💻 [Shell] TUI 读消息失败: %v", err)
			return
		}

		var envelope struct {
			MsgType    string `json:"msg_type"`
			SessionID  string `json:"session_id"`
			TargetNode string `json:"target_node"`
			Data       string `json:"data"`
			Rows       int    `json:"rows"`
			Cols       int    `json:"cols"`
		}
		if err := json.Unmarshal(msg, &envelope); err != nil {
			continue
		}

		switch envelope.MsgType {
		case "shell_open":
			workerID := envelope.TargetNode
			if workerID == "" {
				workerID = g.pickShellWorker()
			}
			if workerID == "" {
				conn.WriteJSON(map[string]string{
					"msg_type": "error", "message": "no available workers",
				})
				continue
			}

			sessionID := g.shellRouter.CreateSession(conn, workerID)
			if envelope.Rows == 0 {
				envelope.Rows = 24
			}
			if envelope.Cols == 0 {
				envelope.Cols = 80
			}

			payload, _ := json.Marshal(map[string]interface{}{
				"session_id": sessionID,
				"rows":       envelope.Rows,
				"cols":       envelope.Cols,
			})
			g.wsHub.SendToWorker(workerID, WSMessage{
				MsgType:  MsgTypeShellOpen,
				SenderID: "gateway",
				Payload:  payload,
			})

			conn.WriteJSON(map[string]interface{}{
				"msg_type":   "shell_opened",
				"session_id": sessionID,
				"node_id":    workerID,
			})

		case "shell_input":
			session := g.shellRouter.RouteByTUI(conn)
			if session == nil {
				continue
			}
			payload, _ := json.Marshal(map[string]string{
				"session_id": session.SessionID,
				"data":       envelope.Data,
			})
			g.wsHub.SendToWorker(session.WorkerID, WSMessage{
				MsgType:  MsgTypeShellInput,
				SenderID: "gateway",
				Payload:  payload,
			})

		case "shell_resize":
			session := g.shellRouter.RouteByTUI(conn)
			if session == nil {
				continue
			}
			payload, _ := json.Marshal(map[string]interface{}{
				"session_id": session.SessionID,
				"rows":       envelope.Rows,
				"cols":       envelope.Cols,
			})
			g.wsHub.SendToWorker(session.WorkerID, WSMessage{
				MsgType:  MsgTypeShellResize,
				SenderID: "gateway",
				Payload:  payload,
			})

		case "shell_close":
			session := g.shellRouter.RouteByTUI(conn)
			if session != nil {
				payload, _ := json.Marshal(map[string]string{
					"session_id": session.SessionID,
				})
				g.wsHub.SendToWorker(session.WorkerID, WSMessage{
					MsgType:  MsgTypeShellClose,
					SenderID: "gateway",
					Payload:  payload,
				})
				g.shellRouter.CloseBySession(session.SessionID)
			}
		}
	}
}

// pickShellWorker 选择一个可用的 Worker
func (g *OpcGateway) pickShellWorker() string {
	g.wsHub.mu.RLock()
	defer g.wsHub.mu.RUnlock()

	for _, client := range g.wsHub.clients {
		if client.NodeID != "" {
			return client.NodeID
		}
	}
	return ""
}

// ── WSHub Shell 路由方法 ──

// routeShellOutputToTUI 将 Worker 的 shell_output 转发给对应的 TUI
// Worker 把 session_id 和 data 放在 WSMessage 顶层（非 payload）
func (h *WSHub) routeShellOutputToTUI(envelope *WSMessage) {
	sessionID := envelope.SessionID

	if sessionID == "" {
		// fallback: 从 payload 读（旧格式兼容）
		if envelope.Payload != nil {
			var output struct {
				SessionID string `json:"session_id"`
				Data      string `json:"data"`
			}
			if err := json.Unmarshal(envelope.Payload, &output); err == nil {
				sessionID = output.SessionID
				envelope.ShellData = output.Data
			}
		}
	}

	if sessionID == "" {
		return
	}

	if h.shellRouter == nil {
		return
	}

	sess := h.shellRouter.RouteBySession(sessionID)
	if sess == nil || sess.TUI == nil || sess.TUI.Conn == nil {
		return
	}

	tuiConn := sess.TUI.Conn
	tuiConn.SetWriteDeadline(time.Now().Add(3 * time.Second))
	tuiConn.WriteJSON(map[string]interface{}{
		"msg_type":   "shell_output",
		"session_id": sessionID,
		"data":       envelope.ShellData,
	})
}

// SendToWorker 向指定 Worker 发送 WS 消息
func (h *WSHub) SendToWorker(nodeID string, msg WSMessage) {
	h.mu.RLock()
	client, ok := h.clients[nodeID]
	h.mu.RUnlock()

	if !ok {
		log.Printf("💻 [Shell] Worker %s 不在线", nodeID)
		return
	}

	conn := client.Conn
	conn.SetWriteDeadline(time.Now().Add(5 * time.Second))
	if err := conn.WriteJSON(msg); err != nil {
		log.Printf("💻 [Shell] 发送给 Worker %s 失败: %v", nodeID, err)
	}
}