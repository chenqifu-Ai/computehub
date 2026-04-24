package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/chzyer/readline"
)

// --- API SCHEMAS ---

type Request struct {
	ID      string `json:"id"`
	Command string `json:"command"`
}

type Response struct {
	ID        string      `json:"id"`
	Success   bool        `json:"success"`
	Data      interface{} `json:"data,omitempty"`
	Error     string      `json:"error,omitempty"`
	Duration  string      `json:"duration,omitempty"`
	Verified  bool        `json:"verified"`
}

type SystemStatus struct {
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

// --- UI CONSTANTS ---

const (
	Reset  = "\033[0m"
	Red    = "\033[31m"
	Green  = "\033[32m"
	Yellow = "\033[33m"
	Blue   = "\033[34m"
	Cyan   = "\033[36m"
	Magenta = "\033[35m"
	Bold   = "\033[1m"
	Clear  = "\033[H\033[J"
)

var currentStatus SystemStatus

func renderStatusBar() {
	// Save cursor, move to top, print, restore cursor
	fmt.Print("\033[s") // Save cursor position
	fmt.Print("\033[H") // Move to 0,0
	
	l1 := fmt.Sprintf("%s(%s)", currentStatus.Kernel.Status, currentStatus.Kernel.ScheduleLatency)
	l2 := fmt.Sprintf("%s(%s)", currentStatus.Pipeline.Status, currentStatus.Pipeline.PureLatency)
	l3 := fmt.Sprintf("%s(%.1f%%)", currentStatus.Executor.Status, currentStatus.Executor.VerificationRate)
	genes := fmt.Sprintf("%d", currentStatus.GeneStore.Size)
	uptime := currentStatus.Uptime

	// Use simple Println with string concatenation to eliminate any Printf argument mismatch
	fmt.Print(Blue + Bold + "┌──────────────────────────────────────────────────────────────────────────────────────┐" + Reset + "\n")
	
	statusLine := Blue + Bold + " │ " + Cyan + "[ OPC CORE STATUS ]" + Reset + " " + 
		Blue + "L1: " + fmt.Sprintf("%-15s", l1) + " | " + 
		"L2: " + fmt.Sprintf("%-15s", l2) + " | " + 
		"L3: " + fmt.Sprintf("%-15s", l3) + " | " + 
		"Genes: " + fmt.Sprintf("%-5s", genes) + " | " + 
		"UP: " + fmt.Sprintf("%-8s", uptime) + " " + 
		Blue + Bold + "│" + Reset
	
	fmt.Println(statusLine)
	fmt.Print(Blue + Bold + "└──────────────────────────────────────────────────────────────────────────────────────┘" + Reset + "\n")
	
	fmt.Print("\033[u") // Restore cursor position
}

func printBox(title string, content interface{}, color string) {
	border := strings.Repeat("─", 60)
	fmt.Printf("\n%s┌%s┬%s┐%s\n", color+Bold, border, " ", Reset)
	fmt.Printf("%s│ %s%-56s%s │%s\n", color+Bold, title, "", Reset, color+Bold, Reset)
	fmt.Printf("%s├%s┴%s┤%s\n", color+Bold, border, " ", Reset)
	fmt.Printf("%s│ %s%v%s                                                       │%s\n", color+Bold, Reset, content, Reset, color+Bold, Reset)
	fmt.Printf("%s└%s┴%s┘%s\n", color+Bold, border, " ", Reset)
}

// Config 配置文件结构
type Config struct {
	Gateway struct {
		Port           int `json:"port"`
		MaxConnections int `json:"max_connections"`
	} `json:"gateway"`
}

// getGatewayPort 获取网关端口
func getGatewayPort() int {
	configFile := "config.json"
	
	// 默认端口
	port := 8181
	
	// 尝试读取配置文件
	if data, err := os.ReadFile(configFile); err == nil {
		var config Config
		if err := json.Unmarshal(data, &config); err == nil {
			if config.Gateway.Port != 0 {
				port = config.Gateway.Port
			}
		}
	}
	
	return port
}

func main() {
	// 获取网关端口
	gatewayPort := getGatewayPort()
	gatewayURL := fmt.Sprintf("http://localhost:%d/api/dispatch", gatewayPort)
	statusURL := fmt.Sprintf("http://localhost:%d/api/status", gatewayPort)
	httpClient := &http.Client{Timeout: 5 * time.Second}

	fmt.Print(Clear)
	// Leave space for the status bar (3 lines)
	fmt.Print("\n\n\n")
	fmt.Printf("%s%s🚀  OpenPC System TUI v0.3.1 [Refined Mode]%s\n", Blue+Bold, Cyan, Reset)
	fmt.Printf("   Connected to: http://localhost:%d\n", gatewayPort)
	fmt.Printf("%s%s%s\n", Blue, strings.Repeat("=", 50), Reset)
	fmt.Println("Type 'exit' to quit, 'help' for instructions")

	// --- ASYNC STATUS UPDATER ---
	go func() {
		for {
			resp, err := httpClient.Get(statusURL)
			if err == nil {
				var s SystemStatus
				if err := json.NewDecoder(resp.Body).Decode(&s); err == nil {
					currentStatus = s
					renderStatusBar()
				}
				resp.Body.Close()
			}
			time.Sleep(1 * time.Second)
		}
	}()

	// Initialize Readline with a null history to avoid .opc_history noise in the console
	rl, err := readline.NewEx(&readline.Config{
		HistoryFile: "/dev/null",
	})
	if err != nil {
		fmt.Printf("Warning: Readline failed: %v\n", err)
	}
	defer rl.Close()

	for {
		fmt.Printf("\n%s[OPC-Shell]%s > ", Cyan+Bold, Reset)
		
		input, err := rl.Readline()
		if err != nil {
			continue
		}
		input = strings.TrimSpace(input)

		if strings.ToLower(input) == "exit" {
			break
		}
		if strings.ToLower(input) == "help" {
			fmt.Printf("\n%sAvailable Commands:%s\n", Yellow+Bold, Reset)
			fmt.Println("  PING          - Test kernel connectivity")
			fmt.Println("  EXEC <<<cmdcmd>    - Execute a physical shell command")
			fmt.Println("  STATUS        - Manual status check")
			fmt.Println("  exit          - Power off")
			continue
		}

		reqID := fmt.Sprintf("tui-%d", time.Now().UnixNano())
		reqBody := Request{ID: reqID, Command: input}
		jsonData, _ := json.Marshal(reqBody)

		fmt.Printf("%s[Snd] %sDispatching to Kernel...%s\n", Blue, Bold, Reset)
		resp, err := httpClient.Post(gatewayURL, "application/json", bytes.NewBuffer(jsonData))
		if err != nil {
			fmt.Printf("%s🌐 [Connection Error]: %v%s\n", Red, err, Reset)
			continue
		}

		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		var systemResp Response
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
