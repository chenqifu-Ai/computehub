package gatewaycmd

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
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
}

func loadConfig() (Config, error) {
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
	configPaths := []string{"config.json", filepath.Join(homeDir, "config.json")}
	for _, path := range configPaths {
		if _, err := os.Stat(path); err == nil {
			configFile = path
			break
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
	// Parse --port override
	portOverride := 0
	for i, a := range args {
		if a == "--port" && i+1 < len(args) {
			fmt.Sscanf(args[i+1], "%d", &portOverride)
		}
	}

	logWithTimestamp("🚀 Starting ComputeHub Gateway Service v%s...", version.Short())

	config, err := loadConfig()
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
		logWithTimestamp("⚠️  Composer not configured (api_url/api_key empty). Task decomposition disabled.")
	}

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

	logWithTimestamp("🌐 ComputeHub Gateway v%s listening on :%d", version.Short(), port)
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
