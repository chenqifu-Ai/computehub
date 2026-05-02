// ComputeHub Gateway Server
// Usage:
//   go run .                          # Start gateway server
//   go run . --tui                    # Start TUI client

package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/computehub/opc/src/gateway"
)

// logWithTimestamp 添加时间戳的日志函数
func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
}

// Config 配置文件结构
type Config struct {
	Gateway struct {
		Port           int `json:"port"`
		MaxConnections int `json:"max_connections"`
	} `json:"gateway"`
	Kernel struct {
		BufferSize int `json:"buffer_size"`
		MaxStates  int `json:"max_states"`
	} `json:"kernel"`
	Executor struct {
		SandboxPath string `json:"sandbox_path"`
	} `json:"executor"`
	GeneStore struct {
		Path string `json:"path"`
	} `json:"gene_store"`
}

// loadConfig 加载配置文件，返回完整配置
func loadConfig() Config {
	configFile := "config.json"
	config := Config{}
	config.Gateway.Port = 8282
	config.Gateway.MaxConnections = 100
	config.Kernel.BufferSize = 100
	config.Kernel.MaxStates = 1000
	config.Executor.SandboxPath = "/tmp/opc-sandbox"
	config.GeneStore.Path = "./genes.json"

	if data, err := os.ReadFile(configFile); err == nil {
		if err := json.Unmarshal(data, &config); err != nil {
			logWithTimestamp("⚠️  Config file parse error: %v, using default values", err)
		} else {
			logWithTimestamp("✅ Config file loaded: %s", configFile)
		}
	} else {
		logWithTimestamp("⚠️  Config file not found (%s), using default values", configFile)
	}
	return config
}

// ─── Gateway Server Mode ───

func runGateway(config Config) {
	port := config.Gateway.Port
	logWithTimestamp("🚀 Starting ComputeHub Gateway Service on port %d", port)

	gwConfig := &gateway.GatewayConfig{
		GeneStorePath: config.GeneStore.Path,
		SandboxPath:   config.Executor.SandboxPath,
		BufferSize:    config.Kernel.BufferSize,
		MaxStates:     config.Kernel.MaxStates,
	}

	gw := gateway.NewOpcGateway(port, gwConfig)
	logWithTimestamp("Gateway service starting...")
	gw.Serve(port)
}

// ─── TUI Client Mode ───

type TUIRequest struct {
	ID      string `json:"id"`
	Command string `json:"command"`
}

type TUIResponse struct {
	ID       string      `json:"id"`
	Success  bool        `json:"success"`
	Data     interface{} `json:"data,omitempty"`
	Error    string      `json:"error,omitempty"`
	Duration string      `json:"duration,omitempty"`
	Verified bool        `json:"verified"`
}

type TUIStatus struct {
	Kernel struct {
		Status          string `json:"status"`
		ScheduleLatency string `json:"schedule_latency"`
		QueueDepth      int    `json:"queue_depth"`
	} `json:"kernel"`
	Pipeline struct {
		Status        string `json:"status"`
		Interceptions int    `json:"interceptions"`
		PureLatency   string `json:"pure_latency"`
	} `json:"pipeline"`
	Executor struct {
		Status           string  `json:"status"`
		VerificationRate float64 `json:"verification_rate"`
		SandboxPath      string  `json:"sandbox_path"`
	} `json:"executor"`
	GeneStore struct {
		Size       int     `json:"size"`
		RecallRate float64 `json:"recall_rate"`
	} `json:"geneStore"`
	Uptime string `json:"uptime"`
}

const (
	Reset   = "\033[0m"
	Red     = "\033[31m"
	Green   = "\033[32m"
	Yellow  = "\033[33m"
	Blue    = "\033[34m"
	Cyan    = "\033[36m"
	Magenta = "\033[35m"
	Bold    = "\033[1m"
	Clear   = "\033[H\033[J"
)

var currentStatus TUIStatus

func renderStatusBar() {
	fmt.Print("\033[s\033[H")
	l1 := fmt.Sprintf("%s(%s)", currentStatus.Kernel.Status, currentStatus.Kernel.ScheduleLatency)
	l2 := fmt.Sprintf("%s(%s)", currentStatus.Pipeline.Status, currentStatus.Pipeline.PureLatency)
	l3 := fmt.Sprintf("%s(%.1f%%)", currentStatus.Executor.Status, currentStatus.Executor.VerificationRate)
	genes := fmt.Sprintf("%d", currentStatus.GeneStore.Size)
	uptime := currentStatus.Uptime

	fmt.Print(Blue + Bold + "┌──────────────────────────────────────────────────────────────────────────────────────┐" + Reset + "\n")
	fmt.Print(Blue + Bold + " │ " + Cyan + "[ OPC CORE STATUS ]" + Reset + " " +
		Blue + "L1: " + fmt.Sprintf("%-15s", l1) + " | " +
		"L2: " + fmt.Sprintf("%-15s", l2) + " | " +
		"L3: " + fmt.Sprintf("%-15s", l3) + " | " +
		"Genes: " + fmt.Sprintf("%-5s", genes) + " | " +
		"UP: " + fmt.Sprintf("%-8s", uptime) + " " +
		Blue + Bold + "│" + Reset + "\n")
	fmt.Print(Blue + Bold + "└──────────────────────────────────────────────────────────────────────────────────────┘" + Reset + "\n")
	fmt.Print("\033[u")
}

func printBox(title string, content interface{}, color string) {
	border := strings.Repeat("─", 60)
	fmt.Printf("\n%s┌%s┬%s┐%s\n", color+Bold, border, " ", Reset)
	fmt.Printf("%s│ %s%-56s%s │%s\n", color+Bold, title, "", Reset, color+Bold, Reset)
	fmt.Printf("%s├%s┴%s┤%s\n", color+Bold, border, " ", Reset)
	fmt.Printf("%s│ %s%v%s                                                       │%s\n", color+Bold, Reset, content, Reset, color+Bold, Reset)
	fmt.Printf("%s└%s┴%s┘%s\n", color+Bold, border, " ", Reset)
}

func runTUI(config Config) {
	port := config.Gateway.Port
	if port == 0 {
		port = 8181
	}
	gatewayURL := fmt.Sprintf("http://localhost:%d/api/dispatch", port)
	statusURL := fmt.Sprintf("http://localhost:%d/api/status", port)
	httpClient := &http.Client{Timeout: 5 * time.Second}

	fmt.Print(Clear)
	fmt.Print("\n\n\n")
	fmt.Printf("%s%s🚀  OpenPC System TUI v0.3.1 [Refined Mode]%s\n", Blue+Bold, Cyan, Reset)
	fmt.Printf("   Connected to: http://localhost:%d\n", port)
	fmt.Printf("%s%s%s\n", Blue, strings.Repeat("=", 50), Reset)
	fmt.Println("Type 'exit' to quit, 'help' for instructions")

	go func() {
		for {
			resp, err := httpClient.Get(statusURL)
			if err == nil {
				var s TUIStatus
				if err := json.NewDecoder(resp.Body).Decode(&s); err == nil {
					currentStatus = s
					renderStatusBar()
				}
				resp.Body.Close()
			}
			time.Sleep(1 * time.Second)
		}
	}()

	for {
		fmt.Printf("\n%s[OPC-Shell]%s > ", Cyan+Bold, Reset)
		var input string
		fmt.Scanf("%s", &input)
		input = strings.TrimSpace(input)

		if strings.ToLower(input) == "exit" {
			break
		}
		if strings.ToLower(input) == "help" {
			fmt.Printf("\n%sAvailable Commands:%s\n", Yellow+Bold, Reset)
			fmt.Println("  PING          - Test kernel connectivity")
			fmt.Println("  EXEC <cmd>    - Execute a physical shell command")
			fmt.Println("  STATUS        - Manual status check")
			fmt.Println("  exit          - Power off")
			continue
		}

		reqID := fmt.Sprintf("tui-%d", time.Now().UnixNano())
		reqBody := TUIRequest{ID: reqID, Command: input}
		jsonData, _ := json.Marshal(reqBody)

		fmt.Printf("%s[Snd] %sDispatching to Kernel...%s\n", Blue, Bold, Reset)
		resp, err := httpClient.Post(gatewayURL, "application/json", bytes.NewBuffer(jsonData))
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

// ─── Main Entry Point ───

func main() {
	tuiMode := flag.Bool("tui", false, "Run TUI client instead of gateway server")
	flag.Parse()

	config := loadConfig()

	if *tuiMode {
		runTUI(config)
	} else {
		runGateway(config)
	}
}
