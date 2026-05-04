// Command: go run ./cmd/gateway
// Launches the ComputeHub gateway server + Visualizer dashboard.
//
// 端口: 8282
// API 端点:
//   /api/health          → 健康检查 (OpcGateway v1)
//   /api/status          → 系统状态 (OpcGateway v1)
//   /api/v1/nodes/*      → 节点管理 (OpcGateway v1)
//   /api/v1/tasks/*      → 任务管理 (OpcGateway v1)
//   /api/v2/map/global   → 全球算力地图 (Visualizer v2)
//   /api/v2/gpu/realtime → GPU 实时监控 (Visualizer v2)
//   /api/v2/nodes        → 节点可视化 (Visualizer v2)
//   /api/v2/alerts       → 告警 (Visualizer v2)
//   /api/v2/health       → 系统健康 (Visualizer v2)
//   /api/v2/history      → 历史趋势 (Visualizer v2)
//   /ws/visual           → WebSocket 实时推送 (Visualizer v2)

package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/computehub/opc/src/gateway"
	"github.com/computehub/opc/src/visualizer"
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
	Visualizer struct {
		Enabled  bool `json:"enabled"`
		Simulate bool `json:"simulate"`
		Port     int  `json:"port"`
	} `json:"visualizer"`
}

// loadConfig 加载配置文件，返回完整配置
func loadConfig() (Config, error) {
	configFile := "config.json"

	// 默认配置
	config := Config{}
	config.Gateway.Port = 8282
	config.Gateway.MaxConnections = 100
	config.Kernel.BufferSize = 100
	config.Kernel.MaxStates = 1000
	config.Executor.SandboxPath = "/tmp/opc-sandbox"
	config.GeneStore.Path = "./genes.json"
	config.Visualizer.Enabled = true
	config.Visualizer.Simulate = true
	config.Visualizer.Port = 8282 // same port as gateway (different URL paths)

	// 尝试读取配置文件
	if data, err := os.ReadFile(configFile); err == nil {
		if err := json.Unmarshal(data, &config); err != nil {
			logWithTimestamp("⚠️  Config file parse error: %v, using default values", err)
		} else {
			logWithTimestamp("✅ Config file loaded: %s", configFile)
		}
	} else {
		logWithTimestamp("⚠️  Config file not found (%s), using default values", configFile)
	}

	return config, nil
}

func main() {
	logWithTimestamp("🚀 Starting ComputeHub Gateway Service...")

	config, err := loadConfig()
	if err != nil {
		logWithTimestamp("❌ Failed to load config: %v", err)
		os.Exit(1)
	}

	port := config.Gateway.Port
	logWithTimestamp("Initializing Gateway on port %d", port)

	gwConfig := &gateway.GatewayConfig{
		GeneStorePath: config.GeneStore.Path,
		SandboxPath:   config.Executor.SandboxPath,
		BufferSize:    config.Kernel.BufferSize,
		MaxStates:     config.Kernel.MaxStates,
	}

	gw := gateway.NewOpcGateway(port, gwConfig)

	// Initialize Visualizer (global power map + v2 API + WebSocket)
	if config.Visualizer.Enabled {
		logWithTimestamp("🌍 Initializing Visualizer (simulate=%v, port=%d)", config.Visualizer.Simulate, config.Visualizer.Port)

		// Create global power map
		gpm := visualizer.NewGlobalPowerMap(config.Visualizer.Simulate)
		if config.Visualizer.Simulate {
			gpm.GenerateSimulationData()
		}

		// Create visualizer gateway and register routes (same port, different paths)
		vg := visualizer.NewVisualizerGateway(gpm, config.Visualizer.Simulate)
		vg.BridgeKernel(gw.Kernel)

		// Wire up unregister fallback so simulated nodes can also be deleted
		gw.SetSimUnregisterFallback(func(nodeID string) error {
			return gpm.RemoveNode(nodeID)
		})

		// 定时从 kernel 同步真实节点数据（每 5s）
		go func() {
			for {
				time.Sleep(5 * time.Second)
				vg.SyncFromKernel()
			}
		}()

		// Register v2 API routes on the default ServeMux
		http.Handle("/api/v2/", vg)
		http.Handle("/ws/visual", vg)

		logWithTimestamp("🌐 Visualizer v2 API registered:")
		logWithTimestamp("   - /api/v2/map/global  → 全球算力地图")
		logWithTimestamp("   - /api/v2/gpu/realtime → GPU 实时监控")
		logWithTimestamp("   - /api/v2/nodes        → 节点可视化")
		logWithTimestamp("   - /api/v2/alerts       → 告警")
		logWithTimestamp("   - /api/v2/health       → 系统健康")
		logWithTimestamp("   - /api/v2/history      → 历史趋势")
		logWithTimestamp("   - /ws/visual           → WebSocket 实时推送")
	}

	logWithTimestamp("Gateway service starting on :%d...", port)
	gw.Serve(port, "./code/dashboard")

	logWithTimestamp("Gateway service stopped")
}
