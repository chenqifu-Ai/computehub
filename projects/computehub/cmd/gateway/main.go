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
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/computehub/opc/src/gateway"
	"github.com/computehub/opc/src/version"
	"github.com/computehub/opc/src/visualizer"
)

// logWithTimestamp 添加时间戳的日志函数
func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
}

// ComposerConfig 大模型编排配置
type ComposerConfig struct {
	APIURL   string   `json:"api_url"`
	APIKey   string   `json:"api_key"`
	Model    string   `json:"model"`
	ExecModels []string `json:"execute_models"`
	MaxConcurrency int    `json:"max_concurrency"`
	TimeoutSeconds  int    `json:"timeout_seconds"`
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
	Composer ComposerConfig `json:"composer"`
}

// loadConfig 加载配置文件，返回完整配置
func loadConfig() (Config, error) {
	// 默认配置
	config := Config{}
	config.Gateway.Port = 8282
	config.Gateway.MaxConnections = 100
	config.Kernel.BufferSize = 100
	config.Kernel.MaxStates = 1000
	config.Executor.SandboxPath = "/tmp/computehub-sandbox"
	config.GeneStore.Path = "./genes.json"
	config.Visualizer.Enabled = true
	config.Visualizer.Simulate = false
	config.Visualizer.Port = 8282 // same port as gateway (different URL paths)
	config.Composer.MaxConcurrency = 8
	config.Composer.TimeoutSeconds = 120

	// 查找配置文件（优先级：项目目录 → 用户家目录）
	var configFile string
	homeDir, err := os.UserHomeDir()
	if err != nil {
		homeDir = "."
	}
	configPaths := []string{"config.json", filepath.Join(homeDir, "config.json")}
	for _, path := range configPaths {
		if _, err := os.Stat(path); err == nil {
			configFile = path
			break
		}
	}

	// 尝试读取配置文件
	if configFile != "" {
		if data, err := os.ReadFile(configFile); err == nil {
			if err := json.Unmarshal(data, &config); err != nil {
				logWithTimestamp("⚠️  Config file parse error: %v, using default values", err)
			} else {
				logWithTimestamp("✅ Config file loaded: %s", configFile)
			}
		} else {
			logWithTimestamp("⚠️  Config file not found (%s), using default values", configFile)
		}
	} else {
		// 找不到文件时，自动创建默认配置
		configPath := filepath.Join(homeDir, "config.json")
		data, err := json.MarshalIndent(config, "", "  ")
		if err != nil {
			logWithTimestamp("⚠️  Failed to marshal config: %v", err)
		} else {
			if err := os.MkdirAll(filepath.Dir(configPath), 0755); err != nil {
				logWithTimestamp("⚠️  Failed to create config dir: %v", err)
			} else if err := os.WriteFile(configPath, data, 0644); err != nil {
				logWithTimestamp("⚠️  Failed to write config: %v", err)
			} else {
				logWithTimestamp("ℹ️  Created default config: %s", configPath)
			}
		}
	}

	return config, nil
}

func main() {
	logWithTimestamp("🚀 Starting ComputeHub Gateway Service v%s...", version.Short())

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

	// 读取 Composer 配置（从 config.json，无硬编码 fallback）
	if config.Composer.APIURL != "" || config.Composer.APIKey != "" {
		gwConfig.ComposerAPIURL = config.Composer.APIURL
		gwConfig.ComposerKey = config.Composer.APIKey
		if config.Composer.Model != "" {
			gwConfig.ComposerModel = config.Composer.Model
		}
		if len(config.Composer.ExecModels) > 0 {
			gwConfig.ComposerExecModels = config.Composer.ExecModels
		}
		if config.Composer.MaxConcurrency > 0 {
			gwConfig.ComposerMaxConcurrency = config.Composer.MaxConcurrency
		}
		logWithTimestamp("📝 Composer configured: model=%s, max_concurrency=%d",
			config.Composer.Model, config.Composer.MaxConcurrency)
	} else {
		logWithTimestamp("⚠️  Composer not configured (api_url/api_key empty). Task decomposition disabled.")
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

	logWithTimestamp("🌐 ComputeHub Gateway v%s listening on :%d", version.Short(), port)

	// 优雅关闭: 监听 SIGINT/SIGTERM
	srv := gw.ServeWithServer(port, "./code/dashboard")

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logWithTimestamp("Shutting down gateway...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		logWithTimestamp("❌ Gateway forced shutdown: %v", err)
	} else {
		logWithTimestamp("✅ Gateway shut down gracefully")
	}

	logWithTimestamp("Gateway service stopped")
}
