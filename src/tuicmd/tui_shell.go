// TUI 交互式远程终端 — 连 WS → Gateway → Worker → PTY (bash)
//
// 用法: 在 TUI 主菜单输入 'shell' → 选择 Worker → 进入交互终端

package tuicmd

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
	"golang.org/x/term"
)

// ── Shell 会话状态 ──

// shellState 全局 Shell 会话状态
type shellState struct {
	conn      *websocket.Conn
	sessionID string
	nodeID    string
	cols      int
	rows      int
	connected bool
}

var shState = &shellState{}

// screenInteractiveShell 进入交互式远程终端
func screenInteractiveShell(state *AppState) {
	// 先选择目标 Worker
	workerID := pickTargetWorker()
	if workerID == "" {
		fmt.Printf("%s⚠️  没有可用的 Worker%s\n", Red, Reset)
		waitAnyKey()
		return
	}

	clearScreen()
	fmt.Printf("%s╔═══════════════════════════════════════════╗%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s║  💻 交互式远程终端                         ║%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s║  Worker: %-36s ║%s\n", Cyan+Bold, workerID, Reset)
	fmt.Printf("%s║  Ctrl+D  退出  Ctrl+C  中断               ║%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s╚═══════════════════════════════════════════╝%s\n", Cyan+Bold, Reset)
	fmt.Println()
	fmt.Printf("%s正在连接 %s/tui/shell ...%s\n", Dim, gw, Reset)

	// 获取终端大小
	shState.cols, shState.rows = getTermSize()
	if shState.cols < 40 {
		shState.cols = 80
	}
	if shState.rows < 10 {
		shState.rows = 24
	}

	// 连接 WS
	wsURL := "ws" + strings.TrimPrefix(gw, "http") + "/api/v1/tui/shell"
	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		fmt.Printf("%s❌ 连接失败: %v%s\n", Red, err, Reset)
		waitAnyKey()
		return
	}

	shState.conn = conn
	defer func() {
		shState.connected = false
		if shState.sessionID != "" {
			conn.WriteJSON(map[string]string{
				"msg_type":   "shell_close",
				"session_id": shState.sessionID,
			})
		}
		conn.Close()
	}()

	// 发送 shell_open
	openMsg := map[string]interface{}{
		"msg_type":    "shell_open",
		"target_node": workerID,
		"rows":        shState.rows,
		"cols":        shState.cols,
	}
	if err := conn.WriteJSON(openMsg); err != nil {
		fmt.Printf("%s❌ 打开 shell 失败: %v%s\n", Red, err, Reset)
		waitAnyKey()
		return
	}

	// 等待 shell_opened 回复
	conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	var resp struct {
		MsgType   string `json:"msg_type"`
		SessionID string `json:"session_id"`
		NodeID    string `json:"node_id"`
		Message   string `json:"message"`
	}
	if err := conn.ReadJSON(&resp); err != nil {
		fmt.Printf("%s❌ 等待 shell 回复失败: %v%s\n", Red, err, Reset)
		waitAnyKey()
		return
	}
	if resp.MsgType == "error" {
		fmt.Printf("%s❌ %s%s\n", Red, resp.Message, Reset)
		waitAnyKey()
		return
	}

	shState.sessionID = resp.SessionID
	shState.nodeID = resp.NodeID
	shState.connected = true

	// 进入交互模式
	enterRawMode(conn)
}

// pickTargetWorker 选择目标 Worker
func pickTargetWorker() string {
	// 从 Gateway 获取节点列表
	resp, err := httpPostJSON(gw+"/api/v1/nodes/list", nil)
	if err != nil {
		return ""
	}

	var nodes struct {
		Success bool `json:"success"`
		Data    []struct {
			NodeID string `json:"node_id"`
			Status string `json:"status"`
			IP     string `json:"ip_address"`
			Region string `json:"region"`
		} `json:"data"`
	}
	if err := json.Unmarshal([]byte(toJSON(resp.Data)), &nodes.Data); err != nil {
		// 直接解析 resp.Data
		dataBytes, _ := json.Marshal(resp.Data)
		json.Unmarshal(dataBytes, &nodes.Data)
	}

	// 过滤在线的
	online := make([]string, 0)
	for _, n := range nodes.Data {
		if n.Status == "online" {
			online = append(online, n.NodeID)
		}
	}

	if len(online) == 0 {
		return ""
	}
	if len(online) == 1 {
		return online[0]
	}

	// 多个 Worker 时让用户选择
	fmt.Printf("%s选择目标 Worker:%s\n", Yellow, Reset)
	for i, id := range online {
		fmt.Printf("  %d. %s\n", i+1, id)
	}
	fmt.Printf("  (直接回车选第一个) > ")
	input := readLine("")
	if input == "" {
		return online[0]
	}
	idx := 0
	fmt.Sscanf(input, "%d", &idx)
	if idx < 1 || idx > len(online) {
		return online[0]
	}
	return online[idx-1]
}

// enterRawMode 进入原始终端模式，读取键盘输入发送到 WS
func enterRawMode(conn *websocket.Conn) {
	oldState, err := term.MakeRaw(int(os.Stdin.Fd()))
	if err != nil {
		fmt.Printf("%s❌ 无法设置 raw 模式: %v%s\n", Red, err, Reset)
		return
	}
	defer term.Restore(int(os.Stdin.Fd()), oldState)

	// 信号处理: Ctrl+C 不 kill 整个进程
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	defer signal.Stop(sigCh)

	// 协程: 读 WS 输出 → 写 stdout
	errCh := make(chan error, 1)
	go func() {
		for {
			var msg struct {
				MsgType   string `json:"msg_type"`
				SessionID string `json:"session_id"`
				Data      string `json:"data"`
				Status    string `json:"status"`
			}
			if err := conn.ReadJSON(&msg); err != nil {
				errCh <- err
				return
			}

			switch msg.MsgType {
			case "shell_output":
				os.Stdout.Write([]byte(msg.Data))
			case "shell_close":
				errCh <- fmt.Errorf("shell closed: %s", msg.Status)
				return
			}
		}
	}()

	// 主循环: 读 stdin → 发送 WS
	buf := make([]byte, 4096)
	for {
		select {
		case <-sigCh:
			// Ctrl+C → 发送到 PTY
			conn.WriteJSON(map[string]interface{}{
				"msg_type":   "shell_input",
				"session_id": shState.sessionID,
				"data":       "\x03",
			})
		case err := <-errCh:
			if err != nil && !strings.Contains(err.Error(), "close") {
				log.Printf("Shell read error: %v", err)
			}
			return
		default:
			n, err := os.Stdin.Read(buf)
			if err != nil {
				return
			}
			if n == 0 {
				continue
			}

			data := string(buf[:n])

			// Ctrl+D → 退出
			if strings.Contains(data, "\x04") {
				conn.WriteJSON(map[string]interface{}{
					"msg_type":   "shell_close",
					"session_id": shState.sessionID,
				})
				time.Sleep(200 * time.Millisecond)
				return
			}

			// 发送到 WS
			conn.SetWriteDeadline(time.Now().Add(3 * time.Second))
			if err := conn.WriteJSON(map[string]interface{}{
				"msg_type":   "shell_input",
				"session_id": shState.sessionID,
				"data":       data,
			}); err != nil {
				return
			}
		}
	}
}

// getTermSize 获取终端大小
func getTermSize() (int, int) {
	cols, rows, err := term.GetSize(int(os.Stdout.Fd()))
	if err != nil {
		return 80, 24
	}
	return cols, rows
}

// waitAnyKey 等待任意键继续
func waitAnyKey() {
	fmt.Printf("\n%s按回车键继续...%s", Dim, Reset)
	bufio.NewReader(os.Stdin).ReadBytes('\n')
}

// toJSON 将任意值转为 JSON 字符串
func toJSON(v interface{}) string {
	b, _ := json.Marshal(v)
	return string(b)
}

// screenShellLegacy 原 OPC-Shell 模式（保留）
func screenShellLegacy(state *AppState) {
	clearScreen()
	fmt.Printf("%s ╔══════════════════════════════════════╗%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s ║      OPC-Shell (Legacy Mode)         ║%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s ╚══════════════════════════════════════╝%s\n", Cyan+Bold, Reset)
	fmt.Printf("%s  输入命令直接发送到网关%s\n", Dim, Reset)
	fmt.Printf("%s  'back' 返回  'help' 查看命令%s\n\n", Dim, Reset)

	for {
		input := readLine("\r" + Cyan + Bold + " [OPC-Shell] > " + Reset)
		if input == "" {
			return
		}
		if input == "back" || input == "exit" || input == "q" {
			return
		}
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

// 修复 readLine — Unicode 安全读取