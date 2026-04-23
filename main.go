// ComputeHub - Distributed Compute Power Platform
//
// A deterministic execution engine for global distributed compute.
// Combines OpenPC's deterministic kernel with ComputeHub's distributed market vision.
//
// Usage:
//   go build -o computehub .
//   ./computehub serve          # Start gateway
//   ./computehub status         # Check system status
//   ./computehub health         # Health check
package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/chenqifu-Ai/computehub/src/gateway"
)

// Config is the application configuration.
type Config struct {
	Port           int    `json:"port"`
	SandboxPath    string `json:"sandbox_path"`
	GenesPath      string `json:"genes_path"`
}

// ─── 配置加载 ───

func loadConfig() *Config {
	cfg := &Config{
		Port:          8282,
		SandboxPath:   "/tmp/computehub-sandbox",
		GenesPath:     "./genes.json",
	}

	data, err := os.ReadFile("config.json")
	if err == nil {
		if err := json.Unmarshal(data, cfg); err != nil {
			fmt.Printf("⚠️  Config parse error: %v, using defaults\n", err)
		} else {
			fmt.Printf("✅ Config loaded: config.json\n")
		}
	} else {
		fmt.Printf("ℹ️  No config.json, using defaults (port %d)\n", cfg.Port)
	}

	return cfg
}

// ─── main ───

func main() {
	if len(os.Args) < 2 {
		printUsage()
		return
	}

	switch os.Args[1] {
	case "serve":
		runServer()
	case "status":
		showStatus()
	case "health":
		healthCheck()
	case "version", "-v", "--version":
		printVersion()
	case "help", "--help", "-h":
		printUsage()
	default:
		fmt.Printf("❓ Unknown command: %s\n", os.Args[1])
		printUsage()
	}
}

func runServer() {
	fmt.Println("🚀 Starting ComputeHub Gateway...")
	fmt.Println("📖 Architecture: Deterministic Kernel × Distributed Market")

	cfg := loadConfig()

	gw, err := gateway.NewGateway(cfg.Port, cfg.SandboxPath, cfg.GenesPath)
	if err != nil {
		fmt.Printf("❌ Gateway init error: %v\n", err)
		os.Exit(1)
	}

	// Graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		if err := gw.Serve(cfg.Port); err != nil {
			fmt.Printf("❌ Gateway error: %v\n", err)
		}
	}()

	fmt.Println("⏳ Waiting for requests... (Ctrl+C to stop)")
	sig := <-sigCh
	fmt.Printf("\n📴 Received %v, shutting down...\n", sig)
	gw.Stop()
	fmt.Println("✅ Gateway stopped.")
}

func showStatus() {
	resp, err := http.Get("http://localhost:8282/api/status")
	if err != nil {
		fmt.Println("❌ Gateway not reachable")
		fmt.Println("ℹ️  Start with: ./computehub serve")
		os.Exit(1)
	}
	defer resp.Body.Close()

	var status map[string]any
	json.NewDecoder(resp.Body).Decode(&status)
	data, _ := json.MarshalIndent(status, "", "  ")
	fmt.Printf("%s\n", data)
}

func healthCheck() {
	resp, err := http.Get("http://localhost:8282/api/health")
	if err != nil {
		fmt.Printf("❌ Gateway not reachable: %v\n", err)
		fmt.Println("ℹ️  Start with: ./computehub serve")
		os.Exit(1)
	}
	defer resp.Body.Close()

	var body map[string]any
	json.NewDecoder(resp.Body).Decode(&body)
	fmt.Printf("✅ Health: %v (uptime: %v)\n", body["status"], body["uptime"])
}

func printVersion() {
	fmt.Println("ComputeHub v2.0.0")
	fmt.Println("Architecture: Deterministic Kernel × Distributed Market")
	fmt.Println("Go runtime")
	fmt.Println("Engine: OpenPC Deterministic Kernel")
}

func printUsage() {
	fmt.Println("ComputeHub v2.0.0 - Distributed Compute Power Platform")
	fmt.Println()
	fmt.Println("Usage:")
	fmt.Println("  computehub serve       Start the gateway server")
	fmt.Println("  computehub status      Show system status")
	fmt.Println("  computehub health      Health check")
	fmt.Println("  computehub version     Show version")
	fmt.Println("  computehub help        Show this help")
	fmt.Println()
	fmt.Println("TUI:")
	fmt.Println("  go build -o tui tui.go && ./tui    Start interactive terminal UI")
}
