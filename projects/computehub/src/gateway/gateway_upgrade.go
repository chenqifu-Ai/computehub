package gateway

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

// UpgradeCheckResponse is the response for upgrade check API
type UpgradeCheckResponse struct {
	CurrentVersion string `json:"current_version"`
	LatestVersion  string `json:"latest_version"`
	DownloadURL    string `json:"download_url"`
	UpdateAvailable bool  `json:"update_available"`
	BinarySize     int64  `json:"binary_size,omitempty"`
	Required       bool   `json:"required"`
}

// upgradeBinaryName returns the worker binary filename for the given platform.
// If platform is empty, uses the Gateway's own platform.
// Matches what's stored in deploy/windows-worker/ or deploy/ directory.
func upgradeBinaryName(platform ...string) string {
	os := runtime.GOOS
	arch := runtime.GOARCH
	if len(platform) > 0 && platform[0] != "" {
		// Parse "windows/amd64", "linux/arm64" etc.
		parts := strings.Split(platform[0], "/")
		if len(parts) == 2 {
			os = parts[0]
			arch = parts[1]
		}
	}
	switch os {
	case "windows":
		if arch == "arm64" {
			return "computehub-worker-win-arm64.exe"
		}
		return "computehub-worker-win-amd64.exe"
	case "linux":
		if arch == "arm64" {
			return "computehub-worker-linux-arm64"
		}
		return "computehub-worker-linux-amd64"
	default:
		return "computehub-worker-" + os + "-" + arch
	}
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
// searching both deploy/ and deploy/windows-worker/ directories.
func resolveDeployBinaryPath(binaryName string) (string, int64) {
	deployDir := findDeployDir()

	candidates := []string{
		filepath.Join(deployDir, binaryName),
		filepath.Join(deployDir, "windows-worker", binaryName),
	}

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

	// 如果 Worker 没传 platform，尝试从 NodeMgr 查注册信息
	// NodeRegister 没有 Platform 字段，platform 必须 Worker 自己传

	latestVersion := resolveLatestVersion()
	binaryName := upgradeBinaryName(workerPlatform)
	binaryPath, binarySize := resolveDeployBinaryPath(binaryName)

	hasUpdate := false
	downloadURL := ""
	if binaryPath != "" && latestVersion != "0.0.0" {
		hasUpdate = (currentVersion != latestVersion)
		downloadURL = "/api/v1/download?file=" + binaryName
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
		},
	})

	if hasUpdate && nodeID != "" {
		logWithTimestamp("🔄 Upgrade check: node=%s %s → %s", nodeID, currentVersion, latestVersion)
	}
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
