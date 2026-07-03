package workercmd

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

// ═══════════════════════════════════════════
// extractVersion 测试
// ═══════════════════════════════════════════

func TestExtractVersion(t *testing.T) {
	tests := []struct {
		path     string
		expected string
	}{
		{"computehub-v1.2.3", "1.2.3"},
		{"computehub-v1.3.13", "1.3.13"},
		{"computehub-v0.7.4", "0.7.4"},
		{"computehub.bak.1.2.3", "1.2.3"},
		{"computehub.bak.1.3.13", "1.3.13"},
		{"computehub", "unknown"},
		{"", "unknown"},
		{"/home/user/.computehub/backups/computehub-v1.2.3", "1.2.3"},
		{"/home/user/.computehub/backups/computehub.bak.1.3.5", "1.3.5"},
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			got := extractVersion(tt.path)
			if got != tt.expected {
				t.Errorf("extractVersion(%q) = %q, want %q", tt.path, got, tt.expected)
			}
		})
	}
}

func TestExtractVersionWithExe(t *testing.T) {
	// Windows paths
	got := extractVersion("computehub-v1.2.3.exe")
	if got != "1.2.3" {
		t.Errorf("extractVersion with .exe = %q, want %q", got, "1.2.3")
	}

	got = extractVersion("computehub.bak.1.3.5.exe")
	if got != "1.3.5" {
		t.Errorf("extractVersion with .exe.bak = %q, want %q", got, "1.3.5")
	}
}

// ═══════════════════════════════════════════
// looksLikeVersion 测试
// ═══════════════════════════════════════════

func TestLooksLikeVersion(t *testing.T) {
	tests := []struct {
		input    string
		expected bool
	}{
		{"1.2.3", true},
		{"1.3.13", true},
		{"0.7.4", true},
		{"1.0", true},
		{"123", true},
		{"", false},
		{"abc", false},
		{"1.2.3-beta", false},
		{"v1.2.3", false},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := looksLikeVersion(tt.input)
			if got != tt.expected {
				t.Errorf("looksLikeVersion(%q) = %v, want %v", tt.input, got, tt.expected)
			}
		})
	}
}

// ═══════════════════════════════════════════
// compareVersions 测试
// ═══════════════════════════════════════════

func TestCompareVersions(t *testing.T) {
	tests := []struct {
		a, b     string
		expected int // >0, <0, or 0
	}{
		{"computehub-v1.2.3", "computehub-v1.2.2", 1},
		{"computehub-v1.2.2", "computehub-v1.2.3", -1},
		{"computehub-v1.2.3", "computehub-v1.2.3", 0},
		{"computehub-v1.3.0", "computehub-v1.2.9", 1},
		{"computehub-v1.2.9", "computehub-v1.3.0", -1},
		{"computehub-v2.0.0", "computehub-v1.9.9", 1},
		{"computehub-v1.9.9", "computehub-v2.0.0", -1},
		{"computehub-v1.3.10", "computehub-v1.3.9", 1},
		{"computehub-v1.3.9", "computehub-v1.3.10", -1},
		{"computehub-v1.3.10", "computehub-v1.3.10", 0},
		// Cross-format comparison
		{"computehub.bak.1.2.3", "computehub-v1.2.2", 1},
		// Unknown version sorts last
		{"computehub", "computehub-v1.0.0", -1},
		{"computehub-v1.0.0", "computehub", 1},
		{"computehub", "computehub", 0},
	}

	for _, tt := range tests {
		t.Run(fmt.Sprintf("%s vs %s", tt.a, tt.b), func(t *testing.T) {
			got := compareVersions(tt.a, tt.b)
			if tt.expected > 0 && got <= 0 {
				t.Errorf("compareVersions(%q, %q) = %d, expected >0", tt.a, tt.b, got)
			} else if tt.expected < 0 && got >= 0 {
				t.Errorf("compareVersions(%q, %q) = %d, expected <0", tt.a, tt.b, got)
			} else if tt.expected == 0 && got != 0 {
				t.Errorf("compareVersions(%q, %q) = %d, expected 0", tt.a, tt.b, got)
			}
		})
	}
}

// ═══════════════════════════════════════════
// binaryNameForPlatform 测试
// ═══════════════════════════════════════════

func TestBinaryNameForPlatform(t *testing.T) {
	name := binaryNameForPlatform()
	if runtime.GOOS == "windows" {
		if name != "computehub.exe" {
			t.Errorf("On Windows, expected 'computehub.exe', got %q", name)
		}
	} else {
		if name != "computehub" {
			t.Errorf("On %s, expected 'computehub', got %q", runtime.GOOS, name)
		}
	}
}

// ═══════════════════════════════════════════
// copyFile 测试
// ═══════════════════════════════════════════

func TestCopyFile(t *testing.T) {
	srcDir := t.TempDir()
	dstDir := t.TempDir()

	// Create source file
	srcPath := filepath.Join(srcDir, "source.txt")
	content := "hello computehub test"
	if err := os.WriteFile(srcPath, []byte(content), 0644); err != nil {
		t.Fatalf("Failed to create source file: %v", err)
	}

	// Copy to destination
	dstPath := filepath.Join(dstDir, "dest.txt")
	if err := copyFile(srcPath, dstPath); err != nil {
		t.Fatalf("copyFile failed: %v", err)
	}

	// Verify content
	got, err := os.ReadFile(dstPath)
	if err != nil {
		t.Fatalf("Failed to read destination: %v", err)
	}
	if string(got) != content {
		t.Errorf("Content mismatch: got %q, want %q", string(got), content)
	}

	// Verify permissions (Unix only)
	if runtime.GOOS != "windows" {
		srcInfo, _ := os.Stat(srcPath)
		dstInfo, _ := os.Stat(dstPath)
		if srcInfo.Mode().Perm() != dstInfo.Mode().Perm() {
			t.Errorf("Permission mismatch: src=%v dst=%v", srcInfo.Mode().Perm(), dstInfo.Mode().Perm())
		}
	}
}

func TestCopyFile_SrcNotFound(t *testing.T) {
	err := copyFile("/nonexistent/path/file.txt", "/tmp/dest.txt")
	if err == nil {
		t.Error("Expected error for non-existent source, got nil")
	}
}

func TestCopyFile_BinaryLarge(t *testing.T) {
	srcDir := t.TempDir()
	dstDir := t.TempDir()

	// Create a 1MB binary blob
	srcPath := filepath.Join(srcDir, "computehub-test")
	data := make([]byte, 1024*1024)
	for i := range data {
		data[i] = byte(i % 256)
	}
	if err := os.WriteFile(srcPath, data, 0755); err != nil {
		t.Fatalf("Failed to create large source: %v", err)
	}

	dstPath := filepath.Join(dstDir, "computehub-copy")
	if err := copyFile(srcPath, dstPath); err != nil {
		t.Fatalf("copyFile large file failed: %v", err)
	}

	// Verify size
	dstInfo, err := os.Stat(dstPath)
	if err != nil {
		t.Fatalf("Failed to stat destination: %v", err)
	}
	if dstInfo.Size() != int64(len(data)) {
		t.Errorf("Size mismatch: got %d, want %d", dstInfo.Size(), len(data))
	}
}

// ═══════════════════════════════════════════
// verifySHA256 测试
// ═══════════════════════════════════════════

func TestVerifySHA256(t *testing.T) {
	dir := t.TempDir()
	filePath := filepath.Join(dir, "test.bin")

	content := []byte("computehub upgrade test data")
	if err := os.WriteFile(filePath, content, 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	// Compute expected SHA256
	h := sha256.Sum256(content)
	expectedHex := hex.EncodeToString(h[:])

	// Verify match
	if err := verifySHA256(filePath, expectedHex); err != nil {
		t.Errorf("Expected SHA256 match, got error: %v", err)
	}

	// Verify mismatch
	if err := verifySHA256(filePath, "0000000000000000000000000000000000000000000000000000000000000000"); err == nil {
		t.Error("Expected error for SHA256 mismatch, got nil")
	}

	// Verify non-existent file
	if err := verifySHA256("/nonexistent/path", expectedHex); err == nil {
		t.Error("Expected error for non-existent file, got nil")
	}
}

// ═══════════════════════════════════════════
// NewUpgradeEngine 测试
// ═══════════════════════════════════════════

func TestNewUpgradeEngine_Dirs(t *testing.T) {
	state := &WorkerState{
		config: Config{
			GatewayURL: "http://localhost:8282",
		},
		nodeID: "test-node",
	}

	engine := NewUpgradeEngine(state)
	if engine == nil {
		t.Fatal("NewUpgradeEngine returned nil")
	}

	// Verify directories were created
	if _, err := os.Stat(engine.downloadDir); os.IsNotExist(err) {
		t.Errorf("downloads dir not created: %s", engine.downloadDir)
	}
	if _, err := os.Stat(engine.backupDir); os.IsNotExist(err) {
		t.Errorf("backups dir not created: %s", engine.backupDir)
	}

	// Verify defaults
	if engine.keepVersions != 3 {
		t.Errorf("expected keepVersions=3, got %d", engine.keepVersions)
	}
	if engine.client == nil || engine.client.Timeout != 120*time.Second {
		t.Errorf("client not properly initialized")
	}
}

func TestNewUpgradeEngine_DirPaths(t *testing.T) {
	state := &WorkerState{
		config: Config{
			GatewayURL: "http://localhost:8282",
		},
		nodeID: "test-node",
	}

	engine := NewUpgradeEngine(state)

	// Verify path structure (homeDir is platform-dependent, but check format)
	if engine.downloadDir == "" {
		t.Error("downloadDir should not be empty")
	}
	if engine.backupDir == "" {
		t.Error("backupDir should not be empty")
	}

	// Both should end with the expected subdirectories
	if !strings.HasSuffix(engine.downloadDir, "downloads") {
		t.Errorf("downloadDir should end with 'downloads', got %s", engine.downloadDir)
	}
	if !strings.HasSuffix(engine.backupDir, "backups") {
		t.Errorf("backupDir should end with 'backups', got %s", engine.backupDir)
	}
}

// ═══════════════════════════════════════════
// BackupCurrent / ListBackups / Cleanup 测试
// ═══════════════════════════════════════════

func TestBackupAndListBackups(t *testing.T) {
	state := &WorkerState{
		config: Config{
			GatewayURL: "http://localhost:8282",
		},
		nodeID: "test-backup",
	}

	engine := NewUpgradeEngine(state)

	// BackupCurrent relies on os.Executable — just verify it doesn't crash
	// when called with a valid binary.
	backupPath, err := engine.BackupCurrent("1.2.3")
	if err != nil {
		t.Logf("BackupCurrent returned error (expected if binary not writeable): %v", err)
	} else {
		// If backup succeeded, verify file exists
		if _, err := os.Stat(backupPath); os.IsNotExist(err) {
			t.Errorf("Backup file not found: %s", backupPath)
		}

		// Cleanup
		os.Remove(backupPath)
	}
}

func TestListBackups_Empty(t *testing.T) {
	state := &WorkerState{
		config: Config{
			GatewayURL: "http://localhost:8282",
		},
		nodeID: "test-list-empty",
	}

	engine := NewUpgradeEngine(state)

	backups := engine.ListBackups()
	// nil and empty slice are both acceptable — Go treats them the same
	if len(backups) != 0 {
		t.Errorf("Expected 0 backups, got %d: %v", len(backups), backups)
	}
}

func TestListBackups_WithFiles(t *testing.T) {
	state := &WorkerState{
		config: Config{
			GatewayURL: "http://localhost:8282",
		},
		nodeID: "test-list-files",
	}

	engine := NewUpgradeEngine(state)

	// Create fake backup files (must be >5MB to pass filter)
	createFakeBinary := func(name string) {
		data := make([]byte, 6*1024*1024) // 6MB
		os.WriteFile(filepath.Join(engine.backupDir, name), data, 0644)
	}

	createFakeBinary("computehub-v1.2.3")
	createFakeBinary("computehub-v1.3.0")
	createFakeBinary("computehub-v0.7.4")

	backups := engine.ListBackups()

	// Should be sorted newest first: 1.3.0 > 1.2.3 > 0.7.4
	if len(backups) < 3 {
		t.Fatalf("Expected at least 3 backups, got %d", len(backups))
	}

	expectedOrder := []string{"1.3.0", "1.2.3", "0.7.4"}
	for i, expectedVer := range expectedOrder {
		if !strings.Contains(backups[i], expectedVer) {
			t.Errorf("Backup[%d] = %q, expected containing %q", i, backups[i], expectedVer)
		}
	}

	// Cleanup
	for _, bk := range backups {
		os.Remove(filepath.Join(engine.backupDir, bk))
	}
}

func TestCleanupOldVersions(t *testing.T) {
	state := &WorkerState{
		config: Config{
			GatewayURL: "http://localhost:8282",
		},
		nodeID: "test-cleanup",
	}

	engine := NewUpgradeEngine(state)
	engine.keepVersions = 2

	// Create 4 fake download binaries (6MB each)
	for _, ver := range []string{"v0.7.4", "v1.2.3", "v1.3.0", "v1.3.1"} {
		name := fmt.Sprintf("computehub-%s", ver)
		if runtime.GOOS == "windows" {
			name += ".exe"
		}
		data := make([]byte, 6*1024*1024)
		os.WriteFile(filepath.Join(engine.downloadDir, name), data, 0644)
	}
	// Create 4 fake backups
	for _, ver := range []string{"v0.7.4", "v1.2.3", "v1.3.0", "v1.3.1"} {
		name := fmt.Sprintf("computehub-%s", ver)
		if runtime.GOOS == "windows" {
			name += ".exe"
		}
		data := make([]byte, 6*1024*1024)
		os.WriteFile(filepath.Join(engine.backupDir, name), data, 0644)
	}

	removed := engine.CleanupOldVersions()

	// Should have removed files
	if len(removed) == 0 {
		t.Error("Expected some files to be cleaned up")
	}

	// Keep check: only newest 2 versions should remain in backup dir
	backups := engine.ListBackups()
	if len(backups) > engine.keepVersions {
		t.Errorf("Expected at most %d backups, got %d", engine.keepVersions, len(backups))
	}

	// Cleanup all remaining
	for _, bk := range backups {
		os.Remove(filepath.Join(engine.backupDir, bk))
	}
	downloadEntries, _ := os.ReadDir(engine.downloadDir)
	for _, e := range downloadEntries {
		os.Remove(filepath.Join(engine.downloadDir, e.Name()))
	}
}

// ═══════════════════════════════════════════
// extractVersion edge cases
// ═══════════════════════════════════════════

func TestExtractVersionEdgeCases(t *testing.T) {
	tests := []struct {
		path     string
		expected string
	}{
		{"/path/to/computehub-v0.0.1", "0.0.1"},
		{"/path/to/computehub-v99.99.99", "99.99.99"},
		{"/path/to/computehub-v1.0.0-beta", "unknown"},
		// "1.0.0-beta" has non-numeric chars → extractVersion returns "unknown"
		{"/path/to/computehub.bak.1.0.0-beta", "unknown"},
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			got := extractVersion(tt.path)
			if got != tt.expected {
				t.Errorf("extractVersion(%q) = %q, want %q", tt.path, got, tt.expected)
			}
		})
	}
}