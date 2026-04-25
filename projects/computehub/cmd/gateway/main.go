// Command: go run ./cmd/gateway
// Launches the ComputeHub gateway server.

package main

import (
	"encoding/json"
	"fmt"
	"os"
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

	logWithTimestamp("Gateway service starting...")
	gw.Serve(port)

	logWithTimestamp("Gateway service stopped")
}
