package workercmd

import (
	"fmt"
	"os"
	"runtime"
	"strings"
	"testing"
	"time"
)

// ═══════════════════════════════════════════
// UpgradeCache 序列化/反序列化 测试
// ═══════════════════════════════════════════

func TestUpgradeCache_LoadSave(t *testing.T) {
	// Use temp dir to avoid polluting real cache
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)
	if runtime.GOOS == "windows" {
		t.Setenv("USERPROFILE", tmpDir)
	}

	// Use test-mode config
	state := &WorkerState{
		config: Config{
			GatewayURL:        "http://localhost:8282",
			HeartbeatInterval: 25 * time.Second,
			ReportDir:         tmpDir,
		},
		nodeID: "test-cache-node",
	}

	// Override cache path via env if needed
	os.Unsetenv("COMPUTEHUB_UPGRADE_STRATEGY")

	m := NewUpgradeManager(state)
	if m == nil {
		t.Fatal("NewUpgradeManager returned nil")
	}

	// Verify initial cache state
	if m.cache == nil {
		t.Fatal("cache should not be nil after load")
	}
	if m.cache.CachedVersion == "" {
		t.Error("CachedVersion should not be empty")
	}
	if m.cache.UpgradeCount != 0 {
		t.Errorf("Expected UpgradeCount=0, got %d", m.cache.UpgradeCount)
	}
	if m.cache.RollbackCount != 0 {
		t.Errorf("Expected RollbackCount=0, got %d", m.cache.RollbackCount)
	}

	// Modify cache and save
	m.cache.UpgradeCount = 5
	m.cache.RollbackCount = 1
	m.cache.LastUpgradeResult = "success"
	m.cache.LastUpgradeTime = time.Now()
	m.saveCache()

	// Create a new manager (should load saved cache)
	m2 := NewUpgradeManager(state)
	if m2.cache.UpgradeCount != 5 {
		t.Errorf("After reload: expected UpgradeCount=5, got %d", m2.cache.UpgradeCount)
	}
	if m2.cache.RollbackCount != 1 {
		t.Errorf("After reload: expected RollbackCount=1, got %d", m2.cache.RollbackCount)
	}
	if m2.cache.LastUpgradeResult != "success" {
		t.Errorf("After reload: expected LastUpgradeResult='success', got %q", m2.cache.LastUpgradeResult)
	}
}

// ═══════════════════════════════════════════
// parseStrategy 测试
// ═══════════════════════════════════════════

func TestParseStrategy(t *testing.T) {
	tests := []struct {
		input    string
		expected UpgradeStrategy
	}{
		{"auto", UpgradeAuto},
		{"", UpgradeAuto},
		{"AUTO", UpgradeAuto},
		{"scheduled", UpgradeScheduled},
		{"Scheduled", UpgradeScheduled},
		{"manual", UpgradeManual},
		{"MANUAL", UpgradeManual},
		{"rolling", UpgradeRolling},
		{"Rolling", UpgradeRolling},
		{"unknown", UpgradeAuto},
		{"random_stuff", UpgradeAuto},
	}

	for _, tt := range tests {
		t.Run(fmt.Sprintf("%q", tt.input), func(t *testing.T) {
			got := parseStrategy(tt.input)
			if got != tt.expected {
				t.Errorf("parseStrategy(%q) = %v, want %v", tt.input, got, tt.expected)
			}
		})
	}
}

// ═══════════════════════════════════════════
// UpgradeManager 初始化
// ═══════════════════════════════════════════

func TestNewUpgradeManager_Defaults(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)

	state := &WorkerState{
		config: Config{
			GatewayURL: "http://localhost:8282",
			ReportDir:  tmpDir,
		},
		nodeID: "test-defaults",
	}

	m := NewUpgradeManager(state)

	if m.strategy != UpgradeAuto {
		t.Errorf("Expected default strategy=auto, got %v", m.strategy)
	}
	if m.windowStartHour != 2 {
		t.Errorf("Expected default windowStartHour=2, got %d", m.windowStartHour)
	}
	if m.windowEndHour != 4 {
		t.Errorf("Expected default windowEndHour=4, got %d", m.windowEndHour)
	}
	if m.engine == nil {
		t.Error("engine should not be nil")
	}
	if m.executor == nil {
		t.Error("executor should not be nil")
	}
	if m.forceSkipVersion != "" {
		t.Errorf("forceSkipVersion should be empty, got %q", m.forceSkipVersion)
	}
}

func TestNewUpgradeManager_StrategyFromEnv(t *testing.T) {
	tmpDir := t.TempDir()
	t.Setenv("HOME", tmpDir)
	t.Setenv("COMPUTEHUB_UPGRADE_STRATEGY", "scheduled")

	state := &WorkerState{
		config: Config{
			GatewayURL: "http://localhost:8282",
			ReportDir:  tmpDir,
		},
		nodeID: "test-strategy-env",
	}

	m := NewUpgradeManager(state)
	if m.strategy != UpgradeScheduled {
		t.Errorf("Expected strategy=scheduled from env, got %v", m.strategy)
	}
}

// ═══════════════════════════════════════════
// UpgradeStrategyInfo 测试
// ═══════════════════════════════════════════

func TestUpgradeStrategyInfo(t *testing.T) {
	info := UpgradeStrategyInfo()
	if info == "" {
		t.Error("UpgradeStrategyInfo should not be empty")
	}
	if !strings.Contains(info, "auto") {
		t.Error("Info should mention 'auto'")
	}
	if !strings.Contains(info, "scheduled") {
		t.Error("Info should mention 'scheduled'")
	}
	if !strings.Contains(info, "manual") {
		t.Error("Info should mention 'manual'")
	}
	if !strings.Contains(info, "rolling") {
		t.Error("Info should mention 'rolling'")
	}
}

// ═══════════════════════════════════════════
// getCachePath 测试
// ═══════════════════════════════════════════

func TestGetCachePath(t *testing.T) {
	path := getCachePath("test-node")
	if path == "" {
		t.Error("getCachePath should not return empty")
	}
	if !strings.Contains(path, "test-node") {
		t.Errorf("cache path should contain node ID: %s", path)
	}
	if !strings.HasSuffix(path, ".json") {
		t.Errorf("cache path should end with .json: %s", path)
	}
}

// ═══════════════════════════════════════════
// UserConfig API 测试 (non-HTTP, structural)
// ═══════════════════════════════════════════

func TestDefaultConfig(t *testing.T) {
	if defaultConfig.GatewayURL != "http://localhost:8282" {
		t.Errorf("default GatewayURL should be http://localhost:8282, got %s", defaultConfig.GatewayURL)
	}
	if defaultConfig.MaxConcurrent != 4 {
		t.Errorf("default MaxConcurrent should be 4, got %d", defaultConfig.MaxConcurrent)
	}
	if defaultConfig.HeartbeatInterval != 25*time.Second {
		t.Errorf("default HeartbeatInterval should be 25s, got %v", defaultConfig.HeartbeatInterval)
	}
}

// ═══════════════════════════════════════════
// upgrade_engine.go: compareVersions 边界
// ═══════════════════════════════════════════

func TestCompareVersions_ZeroValueParts(t *testing.T) {
	// Different length parts
	if compareVersions("computehub-v1.2", "computehub-v1.2.0") != 0 {
		t.Error("1.2 should equal 1.2.0")
	}
	if compareVersions("computehub-v1.2.0", "computehub-v1.2") != 0 {
		t.Error("1.2.0 should equal 1.2")
	}
	if compareVersions("computehub-v1.2", "computehub-v1.3") >= 0 {
		t.Error("1.2 should be < 1.3")
	}
}