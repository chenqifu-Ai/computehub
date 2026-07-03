package gateway

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

// UpgradeCheckResponse is the response for upgrade check API
type UpgradeCheckResponse struct {
	CurrentVersion  string `json:"current_version"`
	LatestVersion   string `json:"latest_version"`
	DownloadURL     string `json:"download_url"`
	UpdateAvailable bool   `json:"update_available"`
	BinarySize      int64  `json:"binary_size,omitempty"`
	Required        bool   `json:"required"`
	SHA256          string `json:"sha256,omitempty"` // sha256 checksum for integrity verification
}

// upgradeBinaryName returns the worker binary filename for the given platform.
// Since v1.1.0 we use the all-in-one binary: computehub (no extension for Unix)
func upgradeBinaryName(platform ...string) string {
	os := runtime.GOOS
	if len(platform) > 0 && platform[0] != "" {
		// Parse "windows/amd64", "linux/arm64", "android/arm64" etc.
		parts := strings.Split(platform[0], "/")
		if len(parts) == 2 {
			os = parts[0]
		}
	}
	// Android uses the same binary as Linux
	if os == "android" {
		os = "linux"
	}
	switch os {
	case "windows":
		return "computehub.exe"
	default:
		return "computehub"
	}
}

// platformBinaryName returns a platform-specific binary filename for download/checksum.
// e.g. "computehub-linux-amd64", "computehub-linux-arm64", "computehub.exe" (windows)
// Falls back to upgradeBinaryName if platform is empty.
func platformBinaryName(platform string) string {
	if platform == "" {
		return upgradeBinaryName()
	}
	parts := strings.Split(platform, "/")
	if len(parts) != 2 {
		return upgradeBinaryName(platform)
	}
	goos, arch := parts[0], parts[1]
	// Android uses the same binary as Linux
	if goos == "android" {
		goos = "linux"
	}
	if goos == "windows" {
		return "computehub.exe" // windows is always .exe, no platform suffix
	}
	return fmt.Sprintf("computehub-%s-%s", goos, arch)
}

// normalizePlatform maps platform OS names to canonical forms.
// Android uses the same binary as Linux (same kernel ABI).
func normalizePlatform(platform string) string {
	parts := strings.Split(platform, "/")
	if len(parts) == 2 && parts[0] == "android" {
		return "linux/" + parts[1]
	}
	return platform
}

// platformDirFromPath converts "linux/amd64" → "linux-amd64"
// Also normalizes android → linux before conversion.
func platformDirFromPath(platform string) string {
	return strings.ReplaceAll(normalizePlatform(platform), "/", "-")
}

// resolveLatestVersion reads the latest version from deploy/version.txt
// or falls back to 0.0.0 if not found.
func resolveLatestVersion() string {
	deployDir := findDeployDir()
	verFile := filepath.Join(deployDir, "version.txt")
	data, err := os.ReadFile(verFile)
	if err == nil {
		v := strings.TrimSpace(string(data))
		if v != "" {
			return v
		}
	}
	// Fallback: read version from deploy directory binary stamp
	return "0.0.0"
}

// resolveDeployBinaryPath returns the path and size of the worker binary,
// searching deploy/, deploy/<platform-dir>/, and deploy/windows-worker/.
// If platform is non-empty, platform-specific subdirectory is preferred.
func resolveDeployBinaryPath(binaryName string, platform ...string) (string, int64) {
	deployDir := findDeployDir()

	candidates := []string{}

	// Platform-specific subdirectory FIRST: deploy/linux-arm64/computehub
	if len(platform) > 0 && platform[0] != "" {
		platDir := platformDirFromPath(platform[0])
		baseName := binaryName
		// For platform-specific name like "computehub-linux-arm64", use "computehub" in subdir
		if strings.Contains(binaryName, "-linux-") || strings.Contains(binaryName, "-darwin-") {
			baseName = "computehub"
		}
		candidates = append(candidates, filepath.Join(deployDir, platDir, baseName))
	}

	// Then root fallback: deploy/computehub
	candidates = append(candidates, filepath.Join(deployDir, binaryName))
	candidates = append(candidates, filepath.Join(deployDir, "windows-worker", binaryName))

	for _, path := range candidates {
		if fi, err := os.Stat(path); err == nil && !fi.IsDir() {
			return path, fi.Size()
		}
	}
	return "", 0
}

// handleUpgradeCheck handles GET /api/v1/upgrade/check
// Query params:
//   node_id (optional) — for logging
//   current_version — worker's current version string
//   platform (optional) — "windows/amd64", "linux/arm64" etc. (defaults to Gateway's platform)
func (g *OpcGateway) handleUpgradeCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	currentVersion := r.URL.Query().Get("current_version")
	nodeID := r.URL.Query().Get("node_id")
	workerPlatform := r.URL.Query().Get("platform")

	latestVersion := resolveLatestVersion()
	binaryName := upgradeBinaryName(workerPlatform)
	binaryPath, binarySize := resolveDeployBinaryPath(binaryName, workerPlatform)

	hasUpdate := false
	downloadURL := ""
	sha256Hex := ""
	if binaryPath != "" && latestVersion != "0.0.0" {
		hasUpdate = compareSemver(currentVersion, latestVersion) < 0
		// Build download URL with platform for platform-specific serving
		downloadURL = "/api/v1/download?file=" + binaryName
		if workerPlatform != "" {
			downloadURL += "&platform=" + workerPlatform
		}
		// Resolve SHA256 for integrity verification — use platform-specific lookup
		if s, err := resolveSHA256ChecksumPlatform(binaryName, workerPlatform, latestVersion); err == nil {
			sha256Hex = s
		}
	}

	g.sendResponse(w, Response{
		Success: true,
		Data: UpgradeCheckResponse{
			CurrentVersion:  currentVersion,
			LatestVersion:   latestVersion,
			DownloadURL:     downloadURL,
			UpdateAvailable: hasUpdate,
			BinarySize:      binarySize,
			Required:        false, // non-breaking updates by default
			SHA256:          sha256Hex,
		},
	})

	if hasUpdate && nodeID != "" {
		logWithTimestamp("🔄 Upgrade check: node=%s %s → %s (sha256=%s)", nodeID, currentVersion, latestVersion, sha256Hex)
	}
}

// handleUpgradeChecksum handles GET /api/v1/upgrade/checksum
// Query params:
//   binary — binary filename (e.g., "computehub", "computehub.exe")
//   version — version to look up (optional, defaults to latest)
//   platform — "linux/amd64", "linux/arm64", etc. (optional, for platform-aware checksum)
//
// Returns the hex-encoded SHA256 checksum of the binary.
func (g *OpcGateway) handleUpgradeChecksum(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"Only GET allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	binaryName := r.URL.Query().Get("binary")
	version := r.URL.Query().Get("version")
	platform := r.URL.Query().Get("platform")

	if binaryName == "" {
		g.sendResponse(w, Response{Success: false, Error: "binary parameter is required"})
		return
	}

	if version == "" {
		version = resolveLatestVersion()
	}

	checksum, err := resolveSHA256ChecksumPlatform(binaryName, platform, version)
	if err != nil {
		g.sendResponse(w, Response{Success: false, Error: fmt.Sprintf("checksum not found: %v", err)})
		return
	}

	g.sendResponse(w, Response{
		Success: true,
		Data:    checksum,
	})
}

// resolveSHA256ChecksumPlatform computes SHA256 directly from the binary file on disk.
// It finds the binary via resolveDeployBinaryPath, then hashes the file contents.
// This avoids the complex sha256sums.txt file matching logic entirely.
func resolveSHA256ChecksumPlatform(binaryName, platform, version string) (string, error) {
	// Resolve the actual binary path
	binaryPath, _ := resolveDeployBinaryPath(binaryName, platform)
	if binaryPath == "" {
		return "", fmt.Errorf("binary not found: %s", binaryName)
	}

	// Compute SHA256 directly from the file
	f, err := os.Open(binaryPath)
	if err != nil {
		return "", fmt.Errorf("cannot open binary: %w", err)
	}
	defer f.Close()

	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", fmt.Errorf("sha256 computation failed: %w", err)
	}

	return hex.EncodeToString(h.Sum(nil)), nil
}

// resolveSHA256Checksum is the backward-compatible wrapper (no platform).
func resolveSHA256Checksum(binaryName, version string) (string, error) {
	return resolveSHA256ChecksumPlatform(binaryName, "", version)
}

// handleUpgradeConfig is an internal API (POST) to set required version info.
// Body: {"version":"0.8.0"}
// This writes deploy/version.txt so workers can detect new versions.
func (g *OpcGateway) handleUpgradeConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Only POST allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Version string `json:"version"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.sendResponse(w, Response{Success: false, Error: "invalid JSON: " + err.Error()})
		return
	}
	if req.Version == "" {
		g.sendResponse(w, Response{Success: false, Error: "version is required"})
		return
	}

	deployDir := findDeployDir()
	os.MkdirAll(deployDir, 0755)
	verFile := filepath.Join(deployDir, "version.txt")
	if err := os.WriteFile(verFile, []byte(strings.TrimSpace(req.Version)+"\n"), 0644); err != nil {
		g.sendResponse(w, Response{Success: false, Error: "write failed: " + err.Error()})
		return
	}

	logWithTimestamp("🔄 Upgrade version set: %s", req.Version)
	g.sendResponse(w, Response{Success: true, Data: map[string]string{
		"version":     req.Version,
		"version_file": verFile,
	}})
}

// compareSemver compares two semantic version strings (e.g. "1.3.32").
// Returns -1 if a < b, 0 if a == b, 1 if a > b.
// Handles versions with different number of segments (e.g. "1.2" == "1.2.0").
func compareSemver(a, b string) int {
	// Strip leading 'v' if present
	a = strings.TrimPrefix(a, "v")
	b = strings.TrimPrefix(b, "v")

	// Split into segments
	as := strings.Split(a, ".")
	bs := strings.Split(b, ".")

	maxLen := len(as)
	if len(bs) > maxLen {
		maxLen = len(bs)
	}

	for i := 0; i < maxLen; i++ {
		var ai, bi int
		if i < len(as) {
			ai = atoi(as[i])
		}
		if i < len(bs) {
			bi = atoi(bs[i])
		}
		if ai < bi {
			return -1
		}
		if ai > bi {
			return 1
		}
	}
	return 0
}

// atoi converts a string to int, returning 0 on error.
func atoi(s string) int {
	n := 0
	for _, c := range s {
		if c < '0' || c > '9' {
			break
		}
		n = n*10 + int(c-'0')
	}
	return n
}
