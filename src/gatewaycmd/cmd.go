package gatewaycmd

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/computehub/opc/src/gateway"
	"github.com/computehub/opc/src/version"
	"github.com/computehub/opc/src/visualizer"
)

func logWithTimestamp(format string, args ...interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	message := fmt.Sprintf(format, args...)
	fmt.Printf("[%s] %s\n", timestamp, message)
}

type ComposerConfig struct {
	APIURL         string   `json:"api_url"`
	APIKey         string   `json:"api_key"`
	Model          string   `json:"model"`
	ExecModels     []string `json:"execute_models"`
	MaxConcurrency int      `json:"max_concurrency"`
	TimeoutSeconds int      `json:"timeout_seconds"`
}

type Config struct {
	Gateway struct {
		Port           int `json:"port"`
		MaxConnections int `json:"max_connections"`
	} `json:"gateway"`
	Kernel struct {
		BufferSize int `json:"buffer_size"`
		MaxStates  int `json:"max_states"`
		MaxNodes   int `json:"max_nodes"`
	} `json:"kernel"`
	Executor struct {
		SandboxPath string `json:"sandbox_path"`
	} `json:"executor"`
	GeneStore struct {
		Path string `json:"path"`
	} `json:"gene_store"`
	Data struct {
		Dir string `json:"dir"`
	} `json:"data"`
	Visualizer struct {
		Enabled  bool `json:"enabled"`
		Simulate bool `json:"simulate"`
		Port     int  `json:"port"`
	} `json:"visualizer"`
	Composer ComposerConfig `json:"composer"`
	Gallery struct {
		RootDir string `json:"root_dir"`
	} `json:"gallery"`
	AgentKeys map[string]string `json:"agent_keys"`
}

func loadConfig(configPath string) (Config, error) {
	config := Config{}
	config.Gateway.Port = 8282
	config.Gateway.MaxConnections = 100
	config.Kernel.BufferSize = 100
	config.Kernel.MaxStates = 1000
	config.Executor.SandboxPath = "/tmp/computehub-sandbox"
	config.GeneStore.Path = "./genes.json"
	config.Visualizer.Enabled = true
	config.Visualizer.Simulate = false
	config.Visualizer.Port = 8282
	config.Composer.MaxConcurrency = 8
	config.Composer.TimeoutSeconds = 120
	config.Gallery.RootDir = "~/gallery"

	var configFile string
	homeDir, err := os.UserHomeDir()
	if err != nil {
		homeDir = "."
	}

	// Priority: --config flag > ./config.json > ~/config.json
	if configPath != "" {
		if _, err := os.Stat(configPath); err == nil {
			configFile = configPath
			logWithTimestamp("📋 Config path from --config flag: %s", configPath)
		} else {
			logWithTimestamp("⚠️  --config path not found: %s, falling back to defaults", configPath)
		}
	}
	if configFile == "" {
		configPaths := []string{"config.json", filepath.Join(homeDir, "config.json")}
		for _, path := range configPaths {
			if _, err := os.Stat(path); err == nil {
				configFile = path
				break
			}
		}
	}

	if configFile != "" {
		if data, err := os.ReadFile(configFile); err == nil {
			if err := json.Unmarshal(data, &config); err != nil {
				logWithTimestamp("⚠️  Config file parse error: %v, using default values", err)
			} else {
				logWithTimestamp("✅ Config file loaded: %s", configFile)
			}
		}
	} else {
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

func Run(args []string) {
	// Parse --port and --config overrides
	portOverride := 0
	configOverride := ""
	for i, a := range args {
		if a == "--port" && i+1 < len(args) {
			fmt.Sscanf(args[i+1], "%d", &portOverride)
		}
		if a == "--config" && i+1 < len(args) {
			configOverride = args[i+1]
		}
	}

	logWithTimestamp("🚀 Starting ComputeHub Gateway Service v%s...", version.Short())

	config, err := loadConfig(configOverride)
	if err != nil {
		logWithTimestamp("❌ Failed to load config: %v", err)
		os.Exit(1)
	}
	if portOverride > 0 {
		config.Gateway.Port = portOverride
	}

	port := config.Gateway.Port
	logWithTimestamp("Initializing Gateway on port %d", port)

	gwConfig := &gateway.GatewayConfig{
		GeneStorePath: config.GeneStore.Path,
		SandboxPath:   config.Executor.SandboxPath,
		BufferSize:    config.Kernel.BufferSize,
		MaxStates:     config.Kernel.MaxStates,
		MaxNodes:      50, // 默认最大节点数
		DataDir:       config.Data.Dir,
	}
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
		logWithTimestamp("⚠️  ════════════════════════════════════════════════════════")
		logWithTimestamp("⚠️  Composer not configured (api_url/api_key empty)")
		logWithTimestamp("⚠️  Agent features disabled: /ai page, task decomposition, LLM proxy")
		logWithTimestamp("⚠️  To enable, set in config.json:")
		logWithTimestamp("⚠️    composer.api_url:  https://ai.zhangtuokeji.top:9090/v1")
		logWithTimestamp("⚠️    composer.api_key:  <your-api-key>")
		logWithTimestamp("⚠️    composer.model:    qwen3.6-35b")
		logWithTimestamp("⚠️  Or set env vars: CONFIG_COMPOSER_API_URL, CONFIG_COMPOSER_API_KEY")
		logWithTimestamp("⚠️  ════════════════════════════════════════════════════════")
		gwConfig.ComposerMaxConcurrency = 1 // 默认值，避免配置校验失败
	}

	// 环境变量覆盖（12-Factor App）
	gwConfig.ApplyEnvOverrides()

	// 配置校验
	if errs := gwConfig.Validate(); len(errs) > 0 {
		for _, e := range errs {
			logWithTimestamp("❌ Config validation: %s", e)
		}
		logWithTimestamp("❌ Gateway startup aborted due to config errors")
		os.Exit(1)
	}
	logWithTimestamp("✅ Config validation passed")

	gw := gateway.NewOpcGateway(port, gwConfig)

	// Set auth token from environment (dev mode if empty)
	authToken := os.Getenv("AUTH_BEARER_TOKEN")
	if authToken != "" {
		gateway.AuthBearerToken = authToken
		logWithTimestamp("🔐 Auth enabled (AUTH_BEARER_TOKEN set)")
	} else {
		logWithTimestamp("⚠️  Auth disabled: AUTH_BEARER_TOKEN not set (dev mode)")
	}

	if config.Visualizer.Enabled {
		logWithTimestamp("🌍 Initializing Visualizer (simulate=%v, port=%d)", config.Visualizer.Simulate, config.Visualizer.Port)
		gpm := visualizer.NewGlobalPowerMap(config.Visualizer.Simulate)
		if config.Visualizer.Simulate {
			gpm.GenerateSimulationData()
		}
		vg := visualizer.NewVisualizerGateway(gpm, config.Visualizer.Simulate)
		vg.BridgeKernel(gw.Kernel)
		gw.SetSimUnregisterFallback(func(nodeID string) error {
			return gpm.RemoveNode(nodeID)
		})
		go func() {
			for {
				time.Sleep(5 * time.Second)
				vg.SyncFromKernel()
			}
		}()
		http.Handle("/api/v2/", vg)
		http.Handle("/ws/visual", vg)
		logWithTimestamp("🌐 Visualizer v2 API registered")
	}

	// 注册作品广场 Gallery
	galleryDir := config.Gallery.RootDir
	if strings.HasPrefix(galleryDir, "~/") {
		homeDir, _ := os.UserHomeDir()
		galleryDir = filepath.Join(homeDir, galleryDir[2:])
	}
	if galleryDir == "" {
		homeDir, _ := os.UserHomeDir()
		galleryDir = filepath.Join(homeDir, "gallery")
	}
	gateway.RegisterGallery(&gateway.GalleryConfig{
		RootDir: galleryDir,
	})
	logWithTimestamp("🎨 Gallery root: %s", galleryDir)

	// 初始化 Agent API Key 认证
	if len(config.AgentKeys) > 0 {
		gateway.SetAgentKeys(config.AgentKeys)
		logWithTimestamp("🔑 Agent API keys configured: %d agents", len(config.AgentKeys))
	} else {
		logWithTimestamp("⚠️  Agent API keys not configured (no auth for /api/v1/agent/*)")
	}

	logWithTimestamp("🌐 ComputeHub Gateway v%s listening on :%d", version.Short(), port)
	// ServeWithServer 内部已处理优雅关闭（SIGINT/SIGTERM）
	gw.Serve(port, "./code/dashboard")
}
