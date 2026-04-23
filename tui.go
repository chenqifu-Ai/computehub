//go:build standalone
// +build standalone

// ComputeHub TUI - Interactive Terminal Interface
// Build with: go build -o tui tui.go
package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

// ─── API 结构 ───

type DispatchRequest struct {
	ID           string            `json:"id,omitempty"`
	Action       string            `json:"action"`
	Framework    string            `json:"framework,omitempty"`
	ResourceType string            `json:"resource_type,omitempty"`
	GPUCount     int               `json:"gpu_count,omitempty"`
	CPUCount     int               `json:"cpu_count,omitempty"`
	MemoryGB     int               `json:"memory_gb,omitempty"`
	DurationSecs int               `json:"duration_secs,omitempty"`
	Requirements map[string]string `json:"requirements,omitempty"`
	Source       string            `json:"source"`
}

type DispatchResponse struct {
	Success  bool        `json:"success"`
	TaskID   string      `json:"task_id,omitempty"`
	Status   string      `json:"status,omitempty"`
	Message  string      `json:"message,omitempty"`
	Error    string      `json:"error,omitempty"`
	Data     any         `json:"data,omitempty"`
	Duration string      `json:"duration,omitempty"`
	Verified bool        `json:"verified,omitempty"`
}

type SystemStatus struct {
	Kernel struct {
		Status          string `json:"status"`
		ScheduleLatency string `json:"schedule_latency"`
		QueueDepth      int    `json:"queue_depth"`
		TotalTasks      int    `json:"total_tasks"`
		PendingTasks    int    `json:"pending_tasks"`
		RunningTasks    int    `json:"running_tasks"`
		CompletedTasks  int    `json:"completed_tasks"`
		FailedTasks     int    `json:"failed_tasks"`
		Uptime          string `json:"uptime"`
	} `json:"kernel"`
	Pipeline struct {
		TotalPassed  int64 `json:"total_passed"`
		TotalBlocked int64 `json:"total_blocked"`
		LastLatency  string `json:"last_latency"`
	} `json:"pipeline"`
	Executor struct {
		Status       string `json:"status"`
		RunningTasks int    `json:"running_tasks"`
		SandboxPath  string `json:"sandbox_path"`
	} `json:"executor"`
	GeneStore struct {
		Total         int     `json:"total"`
		HighConfidence int    `json:"high_confidence"`
		AvgConfidence float64 `json:"avg_confidence"`
		TotalUsages   int     `json:"total_usages"`
	} `json:"gene_store"`
}

const (
	Reset   = "\033[0m"
	Red     = "\033[31m"
	Green   = "\033[32m"
	Yellow  = "\033[33m"
	Blue    = "\033[34m"
	Cyan    = "\033[36m"
	Bold    = "\033[1m"
	Dim     = "\033[2m"
	Clear   = "\033[H\033[J"
)

func renderStatusBar(status SystemStatus) {
	fmt.Print("\033[s\033[H")
	rt := status.Kernel.RunningTasks
	ct := status.Kernel.CompletedTasks
	tt := status.Kernel.TotalTasks
	qd := status.Kernel.QueueDepth
	gt := status.GeneStore.Total
	gu := status.GeneStore.TotalUsages

	fmt.Printf("%s┌─[ ComputeHub Status ]─┐%s\n", Blue, Reset)
	fmt.Printf("%s│ Tasks: %d/%d/%d | Q: %d | Genes: %d(%d) | UP: %s │%s\n",
		Blue, rt, ct, tt, qd, gt, gu, status.Kernel.Uptime, Blue+Reset)
	fmt.Printf("%s└────────────────────────%s\n", Blue, Reset)
}

func main() {
	gatewayURL := "http://localhost:8282"
	httpClient := &http.Client{Timeout: 5 * time.Second}

	fmt.Print(Clear)
	fmt.Printf("%s⚡  ComputeHub TUI v2.0.0%s\n\n", Cyan+Bold, Reset)
	fmt.Printf("   Gateway: %s\n", gatewayURL)
	fmt.Printf("%s%s%s\n\n", Blue, strings.Repeat("=", 50), Reset)
	fmt.Println("Commands: submit help status health genes clear exit")

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT)
	go func() {
		<-sigCh
		fmt.Printf("\n%s👋 Bye!%s\n", Blue, Reset)
		os.Exit(0)
	}()

	go func() {
		for {
			resp, err := httpClient.Get(gatewayURL + "/api/status")
			if err == nil {
				var s SystemStatus
				if err := json.NewDecoder(resp.Body).Decode(&s); err == nil {
					renderStatusBar(s)
				}
				resp.Body.Close()
			}
			time.Sleep(2 * time.Second)
		}
	}()

	scanner := bufio.NewScanner(os.Stdin)
	for {
		fmt.Printf("%s[CH-Shell]%s > ", Cyan+Bold, Reset)
		if !scanner.Scan() {
			break
		}
		input := strings.TrimSpace(scanner.Text())
		if input == "" {
			continue
		}
		args := strings.Fields(input)
		cmd := strings.ToLower(args[0])

		switch cmd {
		case "exit", "quit", "q":
			fmt.Printf("%s👋 Goodbye!%s\n", Blue, Reset)
			return
		case "help":
			fmt.Printf("\n%s[Commands]%s\n", Yellow+Bold, Reset)
			fmt.Println("  submit <framework> <resource_type> [--gpus=N] [--mem=N]")
			fmt.Println("  status, st                 Show system status")
			fmt.Println("  health, hlth               Health check")
			fmt.Println("  genes                      Show gene store stats")
			fmt.Println("  clear, cl                  Clear screen")
			fmt.Println("  exit, quit, q              Exit")
			fmt.Println()
		case "status", "st":
			resp, err := httpClient.Get(gatewayURL + "/api/status")
			if err != nil {
				fmt.Printf("%s❌ %v%s\n", Red, err, Reset)
				continue
			}
			defer resp.Body.Close()
			body, _ := io.ReadAll(resp.Body)
			fmt.Printf("%s[Status]%s\n%s\n", Blue, Reset, string(body))
		case "health", "hlth":
			resp, err := httpClient.Get(gatewayURL + "/api/health")
			if err != nil {
				fmt.Printf("%s❌ %v%s\n", Red, err, Reset)
				continue
			}
			defer resp.Body.Close()
			var body map[string]any
			json.NewDecoder(resp.Body).Decode(&body)
			fmt.Printf("%s✅ Health: %v%s\n", Green, body["status"], Reset)
		case "submit", "sbm":
			parts := strings.Fields(input)
			if len(parts) < 2 {
				fmt.Printf("%sUsage: submit <framework> <resource_type> [--gpus=N] [--mem=N]%s\n", Yellow, Reset)
				continue
			}
			framework := parts[1]
			resourceType := "cpu"
			if len(parts) > 2 {
				resourceType = parts[2]
			}
			gpus := 1
			mem := 8
			for i := 3; i < len(parts); i++ {
				arg := parts[i]
				if strings.HasPrefix(arg, "--gpus=") {
					fmt.Sscanf(arg, "--gpus=%d", &gpus)
				} else if strings.HasPrefix(arg, "--mem=") {
					fmt.Sscanf(arg, "--mem=%d", &mem)
				}
			}
			task := DispatchRequest{
				ID:           fmt.Sprintf("tui-%d", time.Now().UnixNano()),
				Action:       "SUBMIT",
				Framework:    framework,
				ResourceType: resourceType,
				GPUCount:     gpus,
				MemoryGB:     mem,
				Source:       "tui",
			}
			jsonData, _ := json.Marshal(task)
			resp, err := httpClient.Post(gatewayURL+"/api/dispatch", "application/json", bytes.NewBuffer(jsonData))
			if err != nil {
				fmt.Printf("%s❌ %v%s\n", Red, err, Reset)
				continue
			}
			respBody, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			var apiResp DispatchResponse
			json.Unmarshal(respBody, &apiResp)
			if !apiResp.Success {
				fmt.Printf("%s🔴 %s%s\n", Red, apiResp.Error, Reset)
				continue
			}
			fmt.Printf("%s✅ Submitted: %s (GPU: %d, Mem: %dGB)%s\n",
				Green, apiResp.TaskID, gpus, mem, Reset)
			if apiResp.Duration != "" {
				fmt.Printf("%s   Duration: %s%s\n", Dim, apiResp.Duration, Reset)
			}
		case "genes":
			resp, err := httpClient.Get(gatewayURL + "/api/status")
			if err != nil {
				fmt.Printf("%s❌ %v%s\n", Red, err, Reset)
				continue
			}
			defer resp.Body.Close()
			var status map[string]any
			json.NewDecoder(resp.Body).Decode(&status)
			gs, ok := status["gene_store"].(map[string]any)
			if !ok {
				fmt.Println("No gene store data")
				continue
			}
			fmt.Printf("\n%s[Gene Store]%s\n", Cyan+Bold, Reset)
			fmt.Printf("  Total genes:     %.0f\n", gs["total"])
			fmt.Printf("  High confidence: %.0f\n", gs["high_confidence"])
			fmt.Printf("  Avg confidence:  %.2f\n", gs["avg_confidence"])
			fmt.Printf("  Total usages:    %.0f\n", gs["total_usages"])
		case "clear", "cl":
			fmt.Print(Clear)
			fmt.Println()
		default:
			task := DispatchRequest{
				ID:     fmt.Sprintf("tui-%d", time.Now().UnixNano()),
				Action: "STATUS",
				Source: "tui",
			}
			jsonData, _ := json.Marshal(task)
			resp, err := httpClient.Post(gatewayURL+"/api/dispatch", "application/json", bytes.NewBuffer(jsonData))
			if err != nil {
				fmt.Printf("%s❌ %v%s\n", Red, err, Reset)
				continue
			}
			respBody, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			var apiResp DispatchResponse
			json.Unmarshal(respBody, &apiResp)
			if apiResp.Success {
				fmt.Printf("%s✨ %v%s\n", Blue, apiResp.Data, Reset)
			} else {
				fmt.Printf("%s🔴 %s%s\n", Red, apiResp.Error, Reset)
			}
		}
	}
}
