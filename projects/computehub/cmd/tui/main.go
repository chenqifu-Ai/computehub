// Command: go run ./cmd/tui
// Launches the ComputeHub TUI client (connects to running gateway).

package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const gatewayURL = "http://localhost:8282"

// ─── ANSI Colors ───
const (
	Reset  = "\033[0m"
	Bold   = "\033[1m"
	Red    = "\033[31m"
	Green  = "\033[32m"
	Yellow = "\033[33m"
	Blue   = "\033[34m"
	Cyan   = "\033[36m"
)

// TUIRequest 发送到 gateway 的请求结构
type TUIRequest struct {
	ID      string `json:"id"`
	Command string `json:"command"`
}

// TUIResponse gateway 返回的响应结构
type TUIResponse struct {
	ID       string      `json:"id"`
	Success  bool        `json:"success"`
	Data     interface{} `json:"data,omitempty"`
	Error    string      `json:"error,omitempty"`
	Duration string      `json:"duration,omitempty"`
	Verified bool        `json:"verified"`
}

func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Printf("[%s] %s\n", timestamp, fmt.Sprintf(format, args...))
}

func printBox(title string, content interface{}, color string) {
	fmt.Printf("\n%s╔══════════════════════════════════════╗%s\n", color, Reset)
	fmt.Printf("%s║ %s%s%s\n", color, Bold, title, Reset)
	fmt.Printf("%s╚══════════════════════════════════════╝%s\n", color, Reset)
	fmt.Printf("%s%s%s\n", color, content, Reset)
}

func main() {
	logWithTimestamp("🚀 ComputeHub TUI Client")
	logWithTimestamp("🌐 Connecting to %s", gatewayURL)

	// 先检查 gateway 是否在运行
	resp, err := http.Get(gatewayURL + "/api/health")
	if err != nil {
		logWithTimestamp("❌ Cannot reach gateway at %s: %v", gatewayURL, err)
		logWithTimestamp("💡 Make sure 'go run .' is running first")
		return
	}
	resp.Body.Close()
	logWithTimestamp("✅ Gateway is live!")

	fmt.Printf("\n%s╔══════════════════════════════════════╗%s\n", Cyan, Reset)
	fmt.Printf("%s║      ComputeHub TUI Console v0.2    ║%s\n", Cyan, Reset)
	fmt.Printf("%s╚══════════════════════════════════════╝%s\n", Cyan, Reset)
	fmt.Printf("%sType 'help' for commands, 'exit' to quit.%s\n\n", Yellow, Reset)

	for {
		fmt.Printf("\n%s[OPC-Shell]%s > ", Cyan+Bold, Reset)
		var input string
		fmt.Scanf("%s", &input)
		input = strings.TrimSpace(input)

		if strings.ToLower(input) == "exit" {
			break
		}
		if input == "" {
			continue
		}
		if strings.ToLower(input) == "help" {
			fmt.Printf("\n%sAvailable Commands:%s\n", Yellow+Bold, Reset)
			fmt.Println("  PING          - Test kernel connectivity")
			fmt.Println("  EXEC <cmd>    - Execute a physical shell command")
			fmt.Println("  STATUS        - Manual status check")
			fmt.Println("  STATUS2       - System status (gateway API)")
			fmt.Println("  NODES         - List registered nodes")
			fmt.Println("  DISPATCH      - Dispatch a task to a node")
			fmt.Println("  GPUMON        - GPU monitoring status")
			fmt.Println("  REGIONS       - Global power map regions")
			fmt.Println("  exit          - Power off")
			continue
		}

		reqID := fmt.Sprintf("tui-%d", time.Now().UnixNano())
		reqBody := TUIRequest{ID: reqID, Command: input}
		jsonData, _ := json.Marshal(reqBody)

		resp, err := http.Post(gatewayURL+"/api/dispatch", "application/json", bytes.NewBuffer(jsonData))
		if err != nil {
			fmt.Printf("%s🌐 [Connection Error]: %v%s\n", Red, err, Reset)
			continue
		}

		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		var systemResp TUIResponse
		if err := json.Unmarshal(body, &systemResp); err != nil {
			fmt.Printf("%s❌ [Protocol Error]: %v%s\n", Red, err, Reset)
			continue
		}

		if !systemResp.Success {
			fmt.Printf("%s🔴 [System Error]: %s%s\n", Red+Bold, systemResp.Error, Reset)
			continue
		}

		if strings.Contains(strings.ToUpper(input), "EXEC") {
			if systemResp.Verified {
				printBox("PHYSICAL VERIFICATION SUCCESS", systemResp.Data, Green)
				fmt.Printf("%s⏱️  Execution Duration: %s%s\n", Blue, systemResp.Duration, Reset)
			} else {
				printBox("PHYSICAL VERIFICATION FAILED", systemResp.Data, Red)
			}
		} else {
			fmt.Printf("%s✨ [Kernel] %sResponse: %v%s\n", Blue, Bold, systemResp.Data, Reset)
		}
	}
}
