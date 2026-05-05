// Command: go run ./cmd/node (or: go build -o compute-node ./cmd/node)
//
// ComputeNode CLI — 节点注册/管理/心跳工具
//
// Usage:
//   compute-node register             交互式注册新节点
//   compute-node register --json '...' 直接提交 JSON
//   compute-node list                  列出所有节点
//   compute-node heartbeat <node_id>   发送心跳（+ GPU 指标）
//   compute-node gateway <url>         设置网关地址（默认 http://localhost:8282）
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"
)

const defaultGateway = "http://localhost:8282"

var gatewayURL = defaultGateway

func main() {
	if len(os.Args) < 2 {
		printHelp()
		os.Exit(1)
	}

	cmd := os.Args[1]
	args := os.Args[2:]

	// Parse --gw / gateway flag from any position
	for i, a := range os.Args {
		if a == "gateway" && i+1 < len(os.Args) {
			gatewayURL = os.Args[i+1]
		}
		if a == "--gw" && i+1 < len(os.Args) {
			gatewayURL = os.Args[i+1]
		}
	}

	switch cmd {
	case "register":
		cmdRegister(args)
	case "unregister", "remove":
		cmdUnregister(args)
	case "list":
		cmdList()
	case "heartbeat":
		cmdHeartbeat(args)
	case "help", "--help", "-h":
		printHelp()
	default:
		fmt.Printf("未知命令: %s\n\n", cmd)
		printHelp()
		os.Exit(1)
	}
}

func printHelp() {
	fmt.Print(`ComputeNode CLI v0.1 — 节点注册与管理工具

用法:
  compute-node register              交互式注册新节点
  compute-node register --json '...' 直接提交 JSON 注册
  compute-node list                  列出已注册节点
  compute-node unregister <node_id>  删除节点
  compute-node heartbeat <node_id>   发送心跳（GPU 利用率/温度等）
  compute-node --gw <url>            设置网关地址
  compute-node help                  显示帮助

示例:
  compute-node register
  compute-node unregister my-node-1
  compute-node register --gw http://192.168.1.17:8282
  compute-node list
  compute-node heartbeat my-node-1
  compute-node register --json '{
    "node_id": "my-rtx4090-1",
    "node_type": "gpu",
    "gpu_type": "RTX4090",
    "region": "cn-east",
    "cpu_cores": 16,
    "memory_gb": 64,
    "gpu_memory_gb": 24,
    "max_concurrency": 4,
    "ip_address": "192.168.1.100",
    "status": "online"
  }'
`)
}

// ── Register ──

type nodeRegisterPayload struct {
	NodeID        string `json:"node_id"`
	NodeType      string `json:"node_type"`
	GPUType       string `json:"gpu_type"`
	Region        string `json:"region"`
	CPUCores      int    `json:"cpu_cores"`
	MemoryGB      float64 `json:"memory_gb"`
	GPUMemoryGB   float64 `json:"gpu_memory_gb"`
	MaxConcurrency int   `json:"max_concurrency"`
	IPAddress     string `json:"ip_address"`
	Status        string `json:"status"`
}

func cmdRegister(args []string) {
	var payload nodeRegisterPayload

	// Check for --json flag
	if len(args) >= 2 && args[0] == "--json" {
		jsonStr := strings.Join(args[1:], " ")
		if err := json.Unmarshal([]byte(jsonStr), &payload); err != nil {
			fmt.Printf("❌ JSON 解析失败: %v\n", err)
			os.Exit(1)
		}
		if payload.NodeID == "" {
			fmt.Println("❌ JSON 中必须包含 node_id")
			os.Exit(1)
		}
	} else if len(args) == 1 && args[0] != "--json" {
		payload.NodeID = args[0]
	}

	// Interactive mode (if no JSON and no single arg)
	if payload.NodeID == "" {
		payload = interactiveRegister()
	}

	// Defaults
	if payload.Status == "" {
		payload.Status = "online"
	}
	if payload.Region == "" {
		payload.Region = "unknown"
	}
	if payload.NodeType == "" {
		payload.NodeType = "gpu"
	}
	if payload.MaxConcurrency == 0 {
		payload.MaxConcurrency = 4
	}

	body, _ := json.Marshal(payload)
	url := fmt.Sprintf("%s/api/v1/nodes/register", gatewayURL)

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		fmt.Printf("❌ 连接失败: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	var apiResp struct {
		Success bool            `json:"success"`
		Data    json.RawMessage `json:"data"`
		Error   string          `json:"error"`
		Duration string         `json:"duration"`
	}
	json.NewDecoder(resp.Body).Decode(&apiResp)

	if apiResp.Success {
		fmt.Printf("✅ 节点注册成功！(%s)\n", apiResp.Duration)
		if len(apiResp.Data) > 0 {
			fmt.Printf("   响应: %s\n", string(apiResp.Data))
		}
		fmt.Printf("   ────────────────────\n")
		fmt.Printf("   ID:      %s\n", payload.NodeID)
		fmt.Printf("   GPU:     %s\n", payload.GPUType)
		fmt.Printf("   区域:    %s\n", payload.Region)
		fmt.Printf("   IP:      %s\n", payload.IPAddress)
		fmt.Printf("   ────────────────────\n")
	} else {
		fmt.Printf("❌ 注册失败: %s\n", apiResp.Error)
	}
}

func interactiveRegister() nodeRegisterPayload {
	p := nodeRegisterPayload{}

	fmt.Println("\n📝 交互式节点注册")
	fmt.Println(strings.Repeat("─", 40))

	fmt.Print("节点ID: ")
	fmt.Scanln(&p.NodeID)

	fmt.Print("GPU 型号 (H100/A100/V100/RTX4090): ")
	fmt.Scanln(&p.GPUType)

	fmt.Print("区域 (us-west/eu-west/cn-east/ap-southeast): ")
	fmt.Scanln(&p.Region)

	fmt.Print("IP 地址: ")
	fmt.Scanln(&p.IPAddress)

	fmt.Print("CPU 核心数 (默认 16): ")
	fmt.Scanf("%d", &p.CPUCores)
	if p.CPUCores == 0 {
		p.CPUCores = 16
	}

	fmt.Print("内存 GB (默认 64): ")
	fmt.Scanf("%f", &p.MemoryGB)
	if p.MemoryGB == 0 {
		p.MemoryGB = 64
	}

	fmt.Print("显存 GB (默认 24): ")
	fmt.Scanf("%f", &p.GPUMemoryGB)
	if p.GPUMemoryGB == 0 {
		p.GPUMemoryGB = 24
	}

	return p
}

// ── List ──

func cmdList() {
	url := fmt.Sprintf("%s/api/v2/nodes", gatewayURL)
	resp, err := http.Get(url)
	if err != nil {
		fmt.Printf("❌ 连接失败: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	var result struct {
		Nodes       []map[string]interface{} `json:"nodes"`
		TotalNodes  int    `json:"total_nodes"`
		OnlineNodes int    `json:"online_nodes"`
		Regions     int    `json:"regions"`
	}
	json.NewDecoder(resp.Body).Decode(&result)

	fmt.Printf("\n📡 节点列表 (共 %d, 在线 %d, 区域 %d 个)\n",
		result.TotalNodes, result.OnlineNodes, result.Regions)
	fmt.Println(strings.Repeat("─", 80))
	fmt.Printf("%-28s │ %-12s │ %-8s │ %-6s │ %s\n", "Node ID", "Region", "GPU Type", "Tasks", "Status")
	fmt.Println(strings.Repeat("─", 80))

	for _, n := range result.Nodes {
		id, _ := n["id"].(string)
		region, _ := n["region"].(string)
		gpuType, _ := n["gpu_type"].(string)
		status, _ := n["status"].(string)
		tasks, _ := n["active_tasks"].(float64)

		statusMarker := "🟢"
		if status == "offline" {
			statusMarker = "🔴"
		} else if status == "draining" {
			statusMarker = "🟡"
		}

		fmt.Printf(" %s%-26s │ %-12s │ %-8s │ %3.0f    │ %s\n",
			statusMarker, id, region, gpuType, tasks, status)
	}
	fmt.Println()
}

// ── Heartbeat ──

type heartbeatPayload struct {
	NodeID       string  `json:"node_id"`
	CPUUtil      float64 `json:"cpu_utilization"`
	MemoryUsedGB float64 `json:"memory_used_gb"`
	GPUModel     string  `json:"gpu_model"`
	GPUUtil      float64 `json:"gpu_utilization"`
	GPUTemp      float64 `json:"gpu_temperature"`
	GPUMemUsed   float64 `json:"gpu_memory_used_gb"`
	GPUMemTotal  float64 `json:"gpu_memory_total_gb"`
	ActiveTasks  int     `json:"active_tasks"`
	MaxTasks     int     `json:"max_tasks"`
}

// ── Unregister ──

func cmdUnregister(args []string) {
	if len(args) == 0 {
		fmt.Println("❌ 用法: compute-node unregister <node_id>")
		os.Exit(1)
	}
	nodeID := args[0]

	payload := map[string]string{"node_id": nodeID}
	body, _ := json.Marshal(payload)
	url := fmt.Sprintf("%s/api/v1/nodes/unregister", gatewayURL)

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		fmt.Printf("❌ 连接失败: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	var apiResp struct {
		Success bool            `json:"success"`
		Data    json.RawMessage `json:"data"`
		Error   string          `json:"error"`
		Duration string         `json:"duration"`
	}
	json.NewDecoder(resp.Body).Decode(&apiResp)

	if apiResp.Success {
		fmt.Printf("✅ 节点已删除: %s (%s)\n", nodeID, apiResp.Duration)
		if len(apiResp.Data) > 0 {
			fmt.Printf("   响应: %s\n", string(apiResp.Data))
		}
	} else {
		fmt.Printf("❌ 删除失败: %s\n", apiResp.Error)
	}
}

func cmdHeartbeat(args []string) {
	if len(args) == 0 {
		fmt.Println("❌ 用法: compute-node heartbeat <node_id>")
		os.Exit(1)
	}

	nodeID := args[0]

	// Build heartbeat with mock hardware metrics (real implementation would read from NVIDIA-SMI)
	hb := heartbeatPayload{
		NodeID:       nodeID,
		CPUUtil:      float64(time.Now().UnixNano()%100) * 0.5, // pseudo-random 0-50%
		MemoryUsedGB: 32.0 + float64(time.Now().UnixNano()%20),
		GPUModel:     "H100",
		GPUUtil:      float64(time.Now().UnixNano()%80) * 0.8,
		GPUTemp:      45.0 + float64(time.Now().UnixNano()%25),
		GPUMemUsed:   20.0 + float64(time.Now().UnixNano()%10),
		GPUMemTotal:  80.0,
		ActiveTasks:  int(time.Now().UnixNano() % 5),
		MaxTasks:     8,
	}

	body, _ := json.Marshal(hb)
	url := fmt.Sprintf("%s/api/v1/nodes/heartbeat", gatewayURL)

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		fmt.Printf("❌ 心跳发送失败: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	var apiResp struct {
		Success bool   `json:"success"`
		Error   string `json:"error"`
	}
	json.NewDecoder(resp.Body).Decode(&apiResp)

	if apiResp.Success {
		fmt.Printf("💓 心跳已发送: %s | GPU: %.0f%% / %.0f°C\n",
			nodeID, hb.GPUUtil, hb.GPUTemp)
	} else {
		fmt.Printf("❌ 心跳失败: %s\n", apiResp.Error)
	}
}
