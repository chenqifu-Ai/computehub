// ComputeHub Worker Upgrade Engine — Phase 2
//
// Purpose: Provide a unified, cross-platform upgrade engine that handles:
//   1. Download with SHA256 integrity verification
//   2. Independent script execution (detached from Worker process)
//   3. Post-upgrade health verification with automatic rollback
//   4. Multi-version backup and cleanup
//   5. Rolling cache cleanup for disk space management
//
// The engine sits below UpgradeManager — UpgradeManager owns policy/strategy,
// the engine owns the mechanics of safe binary replacement.

package workercmd

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"
)

// ═══════════════════════════════════════════
// UpgradeEngine — 升级执行引擎
// ═══════════════════════════════════════════

// UpgradeEngine handles the mechanics of safe binary upgrades.
// It is stateless (config passed in) and safe for concurrent use.
type UpgradeEngine struct {
	state        *WorkerState
	client       *http.Client // long timeout (300s) — for binary download
	apiClient    *http.Client // short timeout (20s) — for API calls (check, SHA256)
	keepVersions int          // how many old binaries to keep (default 3)
	downloadDir  string
	backupDir    string
}

// getWorkerHomeDir returns a writeable home directory for Worker data.
// On Windows, SYSTEM/machine accounts (USERNAME ending with $) don't have
// a real user profile directory. Falls back to binary's parent directory.
func getWorkerHomeDir() string {
	if runtime.GOOS != "windows" {
		home, _ := os.UserHomeDir()
		if home == "" {
			home = "/tmp"
		}
		return home
	}

	// Windows: try real user home first
	username := os.Getenv("USERNAME")
	if username != "" && !strings.HasSuffix(username, "$") {
		home := filepath.Join("C:", "Users", username)
		// Quick test: can we write here?
		testDir := filepath.Join(home, ".computehub")
		if err := os.MkdirAll(testDir, 0755); err == nil {
			return home
		}
	}

	// Fallback: use directory next to the running binary
	exe, err := os.Executable()
	if err == nil && exe != "" {
		exeDir := filepath.Dir(exe)
		// Verify writeable
		testDir := filepath.Join(exeDir, ".computehub")
		if err := os.MkdirAll(testDir, 0755); err == nil {
			return exeDir
		}
	}

	// Last resort
	return "C:"
}

// NewUpgradeEngine creates an upgrade engine bound to a WorkerState.
func NewUpgradeEngine(state *WorkerState) *UpgradeEngine {
	homeDir := getWorkerHomeDir()

	// Custom transport with separate connection timeout and total timeout.
	// API calls (fetchSHA256) use fast timeout; download uses long total timeout
	// but limited connection timeout.
	dialer := &net.Dialer{
		Timeout:   10 * time.Second, // connection timeout: fail fast if unreachable
		KeepAlive: 30 * time.Second,
	}
	transport := &http.Transport{
		Proxy:                 http.ProxyFromEnvironment,
		DialContext:           dialer.DialContext,
		MaxIdleConns:          5,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 5 * time.Second,
	}

	e := &UpgradeEngine{
		state:        state,
		client:       &http.Client{Transport: transport, Timeout: 300 * time.Second}, // 5min total for download
		keepVersions: 3,
		downloadDir:  filepath.Join(homeDir, ".computehub", "downloads"),
		backupDir:    filepath.Join(homeDir, ".computehub", "backups"),
	}

	// apiClient: fast client for lightweight API calls (upgrade check, SHA256 fetch)
	e.apiClient = &http.Client{
		Transport: transport,
		Timeout:   20 * time.Second, // JSON API calls should never take >20s
	}

	os.MkdirAll(e.downloadDir, 0755)
	os.MkdirAll(e.backupDir, 0755)

	e.log("UpgradeEngine ready: downloads=%s backups=%s keep=%d", e.downloadDir, e.backupDir, e.keepVersions)
	return e
}

// ═══════════════════════════════════════════
// 1. SHA256 — 从 Gateway 获取校验和
// ═══════════════════════════════════════════

// fetchSHA256 gets the sha256 checksum for the given binary from the Gateway.
// Gateway resolves it from deploy/sha256sums-<version>.txt.
func (e *UpgradeEngine) fetchSHA256(binaryName, version string) (string, error) {
	platform := runtime.GOOS + "/" + runtime.GOARCH
	url := fmt.Sprintf("%s/api/v1/upgrade/checksum?binary=%s&version=%s&platform=%s",
		e.state.config.GatewayURL, binaryName, version, url.QueryEscape(platform))

	resp, err := e.apiClient.Get(url)
	if err != nil {
		return "", fmt.Errorf("连接失败: %w", err)
	}
	defer resp.Body.Close()

	var wrapper struct {
		Success bool   `json:"success"`
		Data    string `json:"data"`
		Error   string `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&wrapper); err != nil {
		return "", fmt.Errorf("JSON解析失败: %w", err)
	}
	if !wrapper.Success {
		return "", fmt.Errorf("API错误: %s", wrapper.Error)
	}

	return strings.TrimSpace(wrapper.Data), nil
}

// verifySHA256 computes the sha256 of a file and compares it to expected.
func verifySHA256(filePath, expectedHex string) error {
	f, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("无法打开文件: %w", err)
	}
	defer f.Close()

	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return fmt.Errorf("计算sha256失败: %w", err)
	}

	actual := hex.EncodeToString(h.Sum(nil))
	if !strings.EqualFold(actual, expectedHex) {
		return fmt.Errorf("SHA256不匹配: 期望 %s, 实际 %s", expectedHex, actual)
	}
	return nil
}

// ═══════════════════════════════════════════
// 2. 下载 + SHA256 校验
// ═══════════════════════════════════════════

// DownloadWithChecksum downloads a binary and verifies its SHA256.
// Returns the path to the verified binary.
func (e *UpgradeEngine) DownloadWithChecksum(version string) (string, error) {
	// Determine binary name for this platform
	platform := runtime.GOOS + "/" + runtime.GOARCH
	binaryName := binaryNameForPlatform()
	downloadURL := fmt.Sprintf("%s/api/v1/download?file=%s&platform=%s",
		e.state.config.GatewayURL, binaryName, url.QueryEscape(platform))

	// Destination in downloads dir
	destFile := filepath.Join(e.downloadDir, fmt.Sprintf("computehub-v%s", version))
	if runtime.GOOS == "windows" {
		destFile += ".exe"
	}

	// Already downloaded and verified?
	if fi, err := os.Stat(destFile); err == nil {
		if fi.Size() > 5*1024*1024 {
			// Try to verify with sha256 (non-fatal if checksum not available)
			expectedSHA, shaErr := e.fetchSHA256(binaryName, version)
			if shaErr == nil && expectedSHA != "" {
				if err := verifySHA256(destFile, expectedSHA); err == nil {
					e.log("⏭️  已下载并已验证: %s (%.1fMB)", destFile, float64(fi.Size())/1024/1024)
					return destFile, nil
				}
				e.log("⚠️  已下载但SHA256不匹配，重新下载: %v", err)
				os.Remove(destFile)
			} else {
				// No checksum available — just check file size threshold
				e.log("⏭️  已下载: %s (%.1fMB, 无SHA256)", destFile, float64(fi.Size())/1024/1024)
				return destFile, nil
			}
		}
	}

	// Download
	e.log("⬇️  下载新版本: %s", downloadURL)
	resp, err := e.client.Get(downloadURL)
	if err != nil {
		return "", fmt.Errorf("下载失败: %w", err)
	}
	defer resp.Body.Close()

	// Write to temp file first
	tmpFile := destFile + ".tmp"
	out, err := os.Create(tmpFile)
	if err != nil {
		return "", fmt.Errorf("创建临时文件失败: %w", err)
	}

	written, err := io.Copy(out, resp.Body)
	out.Close()
	if err != nil {
		os.Remove(tmpFile)
		return "", fmt.Errorf("写入失败: %w", err)
	}

	e.log("✅ 下载完成: %.1fMB", float64(written)/1024/1024)

	// Verify minimum size
	if written < 5*1024*1024 {
		os.Remove(tmpFile)
		return "", fmt.Errorf("文件过小 (%d bytes), 可能不完整", written)
	}

	// SHA256 verification
	expectedSHA, shaErr := e.fetchSHA256(binaryName, version)
	if shaErr == nil && expectedSHA != "" {
		if err := verifySHA256(tmpFile, expectedSHA); err != nil {
			os.Remove(tmpFile)
			return "", fmt.Errorf("SHA256校验失败: %w", err)
		}
		e.log("🔐 SHA256验证通过")
	} else {
		e.log("ℹ️  无SHA256校验信息, 跳过验证")
	}

	// Make executable and rename
	if runtime.GOOS != "windows" {
		os.Chmod(tmpFile, 0755)
	}
	if err := os.Rename(tmpFile, destFile); err != nil {
		// Cross-device rename — fallback to copy
		if err := copyFile(tmpFile, destFile); err != nil {
			os.Remove(tmpFile)
			return "", fmt.Errorf("移动文件失败: %w", err)
		}
		os.Remove(tmpFile)
	}
	os.Chmod(destFile, 0755)

	return destFile, nil
}

// ═══════════════════════════════════════════
// 3. 备份管理
// ═══════════════════════════════════════════

// BackupCurrent copies the current running binary to the backup directory.
// Returns the backup path.
func (e *UpgradeEngine) BackupCurrent(version string) (string, error) {
	currentExe, err := os.Executable()
	if err != nil || currentExe == "" {
		return "", fmt.Errorf("无法定位当前exe: %w", err)
	}

	backupFile := filepath.Join(e.backupDir, fmt.Sprintf("computehub-v%s", version))
	if runtime.GOOS == "windows" {
		backupFile += ".exe"
	}

	if err := copyFile(currentExe, backupFile); err != nil {
		return "", fmt.Errorf("备份失败: %w", err)
	}

	e.log("📦 已备份: %s → %s", currentExe, backupFile)
	return backupFile, nil
}

// ListBackups returns all backup versions sorted by version (newest first).
func (e *UpgradeEngine) ListBackups() []string {
	entries, err := os.ReadDir(e.backupDir)
	if err != nil {
		return nil
	}

	var backups []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		info, err := entry.Info()
		if err != nil || info.Size() < 5*1024*1024 {
			continue
		}
		backups = append(backups, entry.Name())
	}

	// Sort by version (newest first)
	sort.Slice(backups, func(i, j int) bool {
		return compareVersions(backups[i], backups[j]) > 0
	})

	return backups
}

// CleanupOldVersions removes old backups and download caches beyond keepVersions.
func (e *UpgradeEngine) CleanupOldVersions() []string {
	var removed []string

	// Clean download caches
	entries, _ := os.ReadDir(e.downloadDir)
	var downloadFiles []os.DirEntry
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		info, err := entry.Info()
		if err != nil || info.Size() < 5*1024*1024 {
			continue
		}
		downloadFiles = append(downloadFiles, entry)
	}

	sort.Slice(downloadFiles, func(i, j int) bool {
		return compareVersions(downloadFiles[i].Name(), downloadFiles[j].Name()) > 0
	})

	for i := e.keepVersions; i < len(downloadFiles); i++ {
		fullPath := filepath.Join(e.downloadDir, downloadFiles[i].Name())
		os.Remove(fullPath)
		removed = append(removed, fullPath)
	}

	// Clean backups
	backupFiles, _ := os.ReadDir(e.backupDir)
	var validBackups []os.DirEntry
	for _, entry := range backupFiles {
		if entry.IsDir() {
			continue
		}
		info, err := entry.Info()
		if err != nil || info.Size() < 5*1024*1024 {
			continue
		}
		validBackups = append(validBackups, entry)
	}

	sort.Slice(validBackups, func(i, j int) bool {
		return compareVersions(validBackups[i].Name(), validBackups[j].Name()) > 0
	})

	for i := e.keepVersions; i < len(validBackups); i++ {
		fullPath := filepath.Join(e.backupDir, validBackups[i].Name())
		os.Remove(fullPath)
		removed = append(removed, fullPath)
	}

	if len(removed) > 0 {
		e.log("🧹 已清理 %d 个旧版本", len(removed))
	}
	return removed
}

// ═══════════════════════════════════════════
// 4. 独立脚本执行 (跨平台)
// ═══════════════════════════════════════════

// ScheduleIndependentUpgrade writes and executes an upgrade script that
// runs independently of the Worker process. The script handles binary
// replacement, health verification, and rollback on failure.
func (e *UpgradeEngine) ScheduleIndependentUpgrade(newBinary, version string) error {
	// Get current binary path
	currentExe, err := os.Executable()
	if err != nil || currentExe == "" {
		currentExe = binaryNameForPlatform()
	}
	exeDir := filepath.Dir(currentExe)

	// The upgrade script will be placed next to the binary (same dir as install target)
	scriptDir := exeDir
	if runtime.GOOS == "windows" {
		// schtasks runs in System32, so put script in a safe place
		scriptDir = e.downloadDir
	}

	// Build script content
	scriptContent, scriptName := e.buildDetachedScript(newBinary, currentExe, version, scriptDir)
	scriptPath := filepath.Join(scriptDir, scriptName)

	if err := os.WriteFile(scriptPath, []byte(scriptContent), 0755); err != nil {
		return fmt.Errorf("写入升级脚本失败: %w", err)
	}
	e.log("📜 升级脚本已写入: %s", scriptPath)

	// Execute independently
	if runtime.GOOS == "windows" {
		return e.runWindowsDetached(scriptPath, newBinary)
	}
	return e.runUnixDetached(scriptPath)
}

// buildDetachedScript generates the platform-specific upgrade script content.
func (e *UpgradeEngine) buildDetachedScript(newBinary, currentExe, version, scriptDir string) (content, filename string) {
	gwURL := e.state.config.GatewayURL
	nodeID := e.state.nodeID

	if runtime.GOOS == "windows" {
		return e.buildWindowsScript(newBinary, currentExe, version, gwURL, nodeID), "upgrade_worker.bat"
	}
	return e.buildUnixScript(newBinary, currentExe, version, gwURL, nodeID), "upgrade_worker.sh"
}

// buildWindowsScript generates a Windows batch script that handles the full
// upgrade lifecycle: confirm-connect → wait → backup → replace → start.
// Key safety improvement: new binary is verified to connect to Gateway
// BEFORE the old worker is stopped, ensuring zero downtime.
func (e *UpgradeEngine) buildWindowsScript(newBinary, currentExe, version, gwURL, nodeID string) string {
	// Windows paths need cleanup
	backupFile := fmt.Sprintf("%s.bak.v%s", strings.TrimSuffix(currentExe, ".exe"), version)
	newBin := strings.ReplaceAll(newBinary, " ", "")
	// origArgs already contains ALL flags, reuse as-is
	origArgs := strings.Join(os.Args[1:], " ")
	origArgs = strings.ReplaceAll(origArgs, `"`, `\"`)
	// Confirm-connect test uses the same args but with --confirm-connect
	testArgs := origArgs + " --confirm-connect"

	return fmt.Sprintf(`@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo ComputeHub Worker 自动升级 v%s
echo ========================================

:: [1] Verify new binary can connect to Gateway FIRST
echo [1/8] 测试新版本连接能力...
"%s" worker %s
if errorlevel 1 (
    echo [ERROR] 新版本连接验证失败，放弃升级 (不会影响当前运行的 Worker)
    goto abort
)
echo   ✅ 连接验证通过

:: [2] Wait for old Worker to exit
echo [2/8] 等待旧 Worker 退出...
:wait_old
tasklist /fi "IMAGENAME eq computehub.exe" 2>nul | find /i "computehub.exe" >nul
if errorlevel 1 goto upgrade
timeout /t 3 /nobreak >nul
goto wait_old

:upgrade
:: [3] Backup current binary
echo [3/8] 备份旧版...
if exist "%s" del "%s" >nul 2>&1
copy /Y "%s" "%s" >nul

:: [4] Replace with new binary
echo [4/8] 替换二进制...
copy /Y "%s" "%s" >nul
if errorlevel 1 (
    echo [ERROR] 替换失败
    goto rollback
)

:: [5] Start new Worker
echo [5/8] 启动新版 Worker...
start "" "%s" %s

:: [6] Wait for registration
echo [6/8] 等待 Worker 注册...
timeout /t 15 /nobreak >nul

:: [7] Health check
echo [7/8] 健康检查...
for /l %%i in (1,1,5) do (
    curl -sf "%s/api/health" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Worker 健康检查通过
        goto done
    )
    timeout /t 3 /nobreak >nul
)

:: Health check failed — rollback
echo [ERROR] Worker 健康检查失败，执行回滚

:rollback
echo [回滚] 恢复旧版...
copy /Y "%s" "%s" >nul
echo [回滚] 启动旧版 Worker...
start "" "%s" %s
echo ROLLBACK > "%s\computehub_upgrade_failed.txt"
goto done

:abort
echo 升级已放弃，当前 Worker 正常运行中，不受影响

:done
echo [8/8] 清理临时文件...
del "%%~f0" >nul 2>&1
echo ========================================
echo 升级完成!
echo ========================================
endlocal
`,
		version,               // 1
		newBin, testArgs,      // 2,3: confirm-connect test
		backupFile, backupFile,// 4,5
		currentExe, backupFile,// 6,7
		newBin, currentExe,    // 8,9
		currentExe, origArgs,  // 10,11
		gwURL,                 // 12
		backupFile, currentExe,// 13,14
		currentExe, origArgs,  // 15,16
		e.state.config.ReportDir) // 17
}

// buildUnixScript generates a shell script that handles the full upgrade lifecycle
// with health check and automatic rollback.
func (e *UpgradeEngine) buildUnixScript(newBinary, currentExe, version, gwURL, nodeID string) string {
	backupFile := fmt.Sprintf("%s.bak.v%s", currentExe, version)
	// origArgs already contains ALL the Worker args (--gw, --node-id, etc.)
	// DO NOT append extras — they'd duplicate flags
	origArgs := strings.Join(os.Args[1:], " ")
	origArgs = strings.ReplaceAll(origArgs, `"`, `\"`)

	script := fmt.Sprintf(`#!/bin/bash
set -e

UPGRADE_VERSION="%s"
START_TIME=$(date +%%s)

echo "========================================"
echo "ComputeHub Worker 自动升级 v${UPGRADE_VERSION}"
echo "========================================"

# [1] Wait for old Worker to exit
echo "[1/8] 等待旧 Worker 退出..."
MAX_WAIT=120
WAITED=0
while pgrep -f "computehub.*worker" > /dev/null 2>&1; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "[ERROR] 等待超时 (${MAX_WAIT}秒)，强制继续"
        break
    fi
    sleep 3
    WAITED=$((WAITED + 3))
done

# [2] Backup current binary
echo "[2/8] 备份旧版..."
if [ -f "%[2]s" ]; then
    cp "%[2]s" "%[3]s"
    echo "  已备份: %[3]s"
fi

# [3] Replace with new binary
echo "[3/8] 替换二进制..."
cp "%[4]s" "%[5]s"
chmod +x "%[5]s"
echo "  已替换: %[5]s"

# [4] Verify new binary runs
echo "[4/8] 验证新版..."
if ! "%[5]s" version > /dev/null 2>&1; then
    echo "[ERROR] 版本验证失败，执行回滚"
    goto_rollback
fi
echo "  ✅ 版本验证通过"

# [5] Start new Worker (origArgs already contains ALL flags)
echo "[5/8] 启动新版 Worker..."
nohup "%[5]s" %[6]s > /tmp/computehub-worker.log 2>&1 &
NEW_PID=$!
echo "  新Worker PID: ${NEW_PID}"

# [6] Wait for registration
echo "[6/8] 等待 Worker 注册..."
sleep 15

# [7] Health check (Gateway endpoint is /api/health, NOT /api/v1/nodes/xxx/health)
echo "[7/8] 健康检查..."
HEALTH_OK=false
for i in 1 2 3 4 5; do
    if curl -sf "%[7]s/api/health" > /dev/null 2>&1; then
        echo "  ✅ 健康检查通过 (attempt ${i}/5)"
        HEALTH_OK=true
        break
    fi
    echo "  ⏳ 等待健康检查... (attempt ${i}/5)"
    sleep 3
done

if [ "${HEALTH_OK}" = false ]; then
    echo "[ERROR] 健康检查失败，执行回滚"
    goto_rollback
fi

echo ""
echo "[8/8] 升级成功! PID=${NEW_PID}"
echo "========================================"
exit 0

# Rollback function
goto_rollback() {
    echo ""
    echo "========== 执行回滚 =========="
    if [ -f "%[3]s" ]; then
        echo "[回滚] 恢复旧版..."
        cp "%[3]s" "%[2]s"
        chmod +x "%[2]s"
        echo "[回滚] 启动旧版 Worker..."
        nohup "%[2]s" %[6]s > /tmp/computehub-worker.log 2>&1 &
        ELAPSED=$(($(date +%%s) - START_TIME))
        echo "ROLLBACK at +${ELAPSED}s" > "%[8]s/computehub_upgrade_failed.txt"
        echo "  已回滚到旧版 (耗时 ${ELAPSED}s)"
    else
        echo "[ERROR] 备份文件不存在，无法回滚!"
    fi
    echo "========== 回滚完成 =========="
    exit 1
}
`,
		version,            // 1: UPGRADE_VERSION
		currentExe,         // 2: current binary path
		backupFile,         // 3: backup path
		newBinary,          // 4: downloaded new binary
		currentExe,         // 5: currentExe (target of copy, verify, start; same path replaced)
		origArgs,           // 6: full original args with all flags
		gwURL,              // 7: Gateway URL for health check
		e.state.config.ReportDir, // 8: report dir for fail marker
	)
	return script
}

// ═══════════════════════════════════════════
// 5. 平台独立执行
// ═══════════════════════════════════════════



// runWindowsDetached executes the upgrade script via schtasks, ensuring it
// runs completely outside the Worker process tree. The batch script handles
// wait → backup → replace → restart → cleanup.
func (e *UpgradeEngine) runWindowsDetached(scriptPath, newBinary string) error {
	// Use schtasks for truly independent execution
	schedule := fmt.Sprintf(
		`schtasks /create /sc once /tn "ComputeHubUpgrade" /tr "cmd /c \"%s\"" /st 00:00 /f`+
			` & schtasks /run /tn "ComputeHubUpgrade"`+
			` & schtasks /delete /tn "ComputeHubUpgrade" /f`,
		scriptPath,
	)

	e.log("🚀 调度schtasks升级: %s", scriptPath)
	cmd := exec.Command("cmd", "/c", schedule)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("调度schtasks失败: %w", err)
	}

	// Clean up temp upgrade file after 3 seconds (schtasks grabs it)
	go func() {
		time.Sleep(3 * time.Second)
		os.Remove(scriptPath)
	}()

	return nil
}

// ═══════════════════════════════════════════
// 6. 回滚
// ═══════════════════════════════════════════

// PerformRollback restores the most recent backup and restarts the Worker.
func (e *UpgradeEngine) PerformRollback() (string, error) {
	backups := e.ListBackups()
	if len(backups) == 0 {
		return "", fmt.Errorf("没有可用的备份版本")
	}

	latestBackup := filepath.Join(e.backupDir, backups[0])
	currentExe, err := os.Executable()
	if err != nil || currentExe == "" {
		currentExe = binaryNameForPlatform()
	}

	e.log("🔄 执行回滚: %s → %s", backups[0], currentExe)

	// Backup current version first (just in case)
	oldBackup := filepath.Join(e.backupDir, fmt.Sprintf("computehub-v%s", extractVersion(currentExe)))
	if runtime.GOOS == "windows" {
		oldBackup += ".exe"
	}
	copyFile(currentExe, oldBackup)

	// Replace
	if err := copyFile(latestBackup, currentExe); err != nil {
		return "", fmt.Errorf("回滚替换失败: %w", err)
	}
	if runtime.GOOS != "windows" {
		os.Chmod(currentExe, 0755)
	}

	// Verify
	cmd := exec.Command(currentExe, "version")
	if out, err := cmd.Output(); err != nil {
		return "", fmt.Errorf("回滚后版本验证失败: %w", err)
	} else {
		e.log("✅ 回滚后版本: %s", strings.TrimSpace(string(out)))
	}

	e.log("🔄 重启Worker (回滚后)...")

	// Restart
	e.state.unregister()
	time.Sleep(500 * time.Millisecond)

	args := os.Args[1:]
	attr := &os.ProcAttr{
		Files: []*os.File{os.Stdin, os.Stdout, os.Stderr},
	}
	proc, err := os.StartProcess(currentExe, append([]string{currentExe}, args...), attr)
	if err != nil {
		return "", fmt.Errorf("回滚后启动失败: %w", err)
	}
	e.log("✅ 回滚完成, 新PID=%d", proc.Pid)
	os.Exit(0)

	return "rollback started", nil
}

// ═══════════════════════════════════════════
// 7. 健康验证
// ═══════════════════════════════════════════

// VerifyNewWorker pings the Gateway to confirm the new Worker registered.
// Returns nil if healthy within timeout.
func (e *UpgradeEngine) VerifyNewWorker(timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	url := fmt.Sprintf("%s/api/v1/nodes/%s", e.state.config.GatewayURL, e.state.nodeID)

	for time.Now().Before(deadline) {
		// Use short timeout probes
		probeClient := &http.Client{Timeout: 5 * time.Second}
		resp, err := probeClient.Get(url)
		if err == nil {
			resp.Body.Close()
			if resp.StatusCode == 200 {
				e.log("✅ 新Worker已注册到Gateway")
				return nil
			}
		}

		time.Sleep(3 * time.Second)
	}

	return fmt.Errorf("超时 %v — 新Worker未注册到Gateway", timeout)
}

// ═══════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════

// binaryNameForPlatform returns the expected binary filename for this platform.
func binaryNameForPlatform() string {
	if runtime.GOOS == "windows" {
		return "computehub.exe"
	}
	return "computehub"
}

// extractVersion extracts version from a path like ".../computehub-v1.2.3" or ".../computehub.bak.1.2.3".
func extractVersion(path string) string {
	base := filepath.Base(path)
	base = strings.TrimSuffix(base, ".exe")

	// Try "computehub-vX.Y.Z"
	if idx := strings.Index(base, "-v"); idx >= 0 {
		candidate := base[idx+2:]
		if looksLikeVersion(candidate) {
			return candidate
		}
	}

	// Try "computehub.bak.X.Y.Z"
	if idx := strings.Index(base, ".bak."); idx >= 0 {
		candidate := base[idx+5:]
		if looksLikeVersion(candidate) {
			return candidate
		}
	}

	return "unknown"
}

// looksLikeVersion checks if a string looks like a semver (contains digits and dots).
func looksLikeVersion(s string) bool {
	for _, c := range s {
		if (c >= '0' && c <= '9') || c == '.' {
			continue
		}
		return false
	}
	return len(s) > 0
}

// compareVersions compares two binary names by extracted version, returning
// >0 if a > b, <0 if a < b, 0 if equal.
func compareVersions(aName, bName string) int {
	a := extractVersion(aName)
	b := extractVersion(bName)
	if a == b {
		return 0
	}
	if a == "unknown" {
		return -1
	}
	if b == "unknown" {
		return 1
	}
	// Simple split comparison
	aparts := strings.Split(a, ".")
	bparts := strings.Split(b, ".")
	maxLen := len(aparts)
	if len(bparts) > maxLen {
		maxLen = len(bparts)
	}
	for i := 0; i < maxLen; i++ {
		var av, bv int
		if i < len(aparts) {
			fmt.Sscanf(aparts[i], "%d", &av)
		}
		if i < len(bparts) {
			fmt.Sscanf(bparts[i], "%d", &bv)
		}
		if av > bv {
			return 1
		}
		if av < bv {
			return -1
		}
	}
	return 0
}

// copyFile copies src to dst (cross-device safe, uses Read/Write).
func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	// Ensure destination directory exists
	os.MkdirAll(filepath.Dir(dst), 0755)

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	written, err := io.Copy(out, in)
	if err != nil {
		return err
	}

	// Copy permissions (Unix)
	if runtime.GOOS != "windows" {
		if fi, err := os.Stat(src); err == nil {
			os.Chmod(dst, fi.Mode())
		}
	}

	if err := out.Sync(); err != nil {
		return err
	}

	_ = written // used for verification if needed
	return nil
}

// log prints upgrade engine messages.
func (e *UpgradeEngine) log(format string, args ...interface{}) {
	t := time.Now().Format("15:04:05")
	fmt.Printf("\033[2m[%s] [Engine]\033[0m "+format+"\n", append([]interface{}{t}, args...)...)
}
