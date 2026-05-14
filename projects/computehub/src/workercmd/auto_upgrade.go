// Auto-upgrade system for ComputeHub Worker.
// Periodically checks Gateway for new versions, downloads,
// replaces itself, and restarts with zero manual intervention.

package workercmd

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"time"

	"github.com/computehub/opc/src/version"
)

// UpgradeResponse matches the Gateway's UpgradeCheckResponse
type UpgradeResponse struct {
	CurrentVersion  string `json:"current_version"`
	LatestVersion   string `json:"latest_version"`
	DownloadURL     string `json:"download_url"`
	UpdateAvailable bool   `json:"update_available"`
	BinarySize      int64  `json:"binary_size,omitempty"`
}

// workerExecutable returns the current binary's filename.
func workerExecutable() string {
	os := runtime.GOOS
	arch := runtime.GOARCH
	if os == "windows" {
		if arch == "arm64" {
			return "computehub-worker-win-arm64.exe"
		}
		return "computehub-worker-win-amd64.exe"
	}
	if arch == "arm64" {
		return "computehub-worker-linux-arm64"
	}
	return "computehub-worker-linux-amd64"
}

// checkUpgrade pings the Gateway to see if a new version is available.
func (s *WorkerState) checkUpgrade() (*UpgradeResponse, error) {
	gw := s.config.GatewayURL
	nodeID := s.nodeID
	curVer := version.Short() // e.g. "0.7.1"

	platform := fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH)
	url := fmt.Sprintf("%s/api/v1/upgrade/check?current_version=%s&node_id=%s&platform=%s", gw, curVer, nodeID, platform)
	resp, err := s.client.Get(url)
	if err != nil {
		return nil, fmt.Errorf("连接失败: %w", err)
	}
	defer resp.Body.Close()

	var wrapper struct {
		Success bool            `json:"success"`
		Data    json.RawMessage `json:"data"`
		Error   string          `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&wrapper); err != nil {
		return nil, fmt.Errorf("JSON 解析失败: %w", err)
	}
	if !wrapper.Success {
		return nil, fmt.Errorf("API 错误: %s", wrapper.Error)
	}

	var upgrade UpgradeResponse
	if err := json.Unmarshal(wrapper.Data, &upgrade); err != nil {
		return nil, fmt.Errorf("数据解析失败: %w", err)
	}

	return &upgrade, nil
}

// performUpgrade downloads the latest binary and replaces itself.
func (s *WorkerState) performUpgrade(resp *UpgradeResponse) error {
	fmt.Printf("\n %s🚀 检测到新版本: %s → %s%s\n",
		yellow(bold("")), version.Short(), resp.LatestVersion, reset())
	fmt.Printf("   下载: %s%s%s\n", dim(""), resp.DownloadURL, reset())

	// 1. Verify binary filename matches this platform
	expectedBinary := workerExecutable()
	expectedFile := fmt.Sprintf(".%s.upgrade", expectedBinary)
	if !strings.Contains(resp.DownloadURL, expectedBinary) {
		// URL 里的文件名不匹配当前平台 — 可能是 deploy 目录缺少该平台的二进制
		return fmt.Errorf("平台不匹配: 期望 %s, 但 Gateway 返回 %s (deploy 目录可能缺少该平台二进制)",
			expectedBinary, resp.DownloadURL)
	}

	// 2. Download new binary
	gw := s.config.GatewayURL
	dlURL := gw + resp.DownloadURL
	tmpFile := expectedFile

	out, err := os.Create(tmpFile)
	if err != nil {
		return fmt.Errorf("创建临时文件失败: %w", err)
	}

	httpResp, err := s.client.Get(dlURL)
	if err != nil {
		out.Close()
		os.Remove(tmpFile)
		return fmt.Errorf("下载失败: %w", err)
	}
	defer httpResp.Body.Close()

	written, err := io.Copy(out, httpResp.Body)
	out.Close()
	if err != nil {
		os.Remove(tmpFile)
		return fmt.Errorf("下载写入失败: %w", err)
	}
	fmt.Printf("   下载完成: %.1f MB\n", float64(written)/1024/1024)

	// 2. Verify size matches (non-fatal warning)
	if resp.BinarySize > 0 && written != resp.BinarySize {
		fmt.Printf("   %s⚠️ 文件大小不匹配 (期望: %d, 实际: %d)%s\n",
			yellow(""), resp.BinarySize, written, reset())
	}

	// 3. Make executable (Unix)
	if runtime.GOOS != "windows" {
		os.Chmod(tmpFile, 0755)
	}

	// 4. Replace current binary
	currentExe, err := os.Executable()
	if err != nil {
		currentExe = workerExecutable()
	}

	backupFile := fmt.Sprintf("%s.bak.%s", currentExe, version.Short())

	if runtime.GOOS == "windows" {
		// Windows: running .exe is locked, can't rename/overwrite it directly.
		// Strategy: write a batch script that waits for us to exit, then
		// copies the new binary over the old one and restarts.
		batchFile := "upgrade.bat"
		// 批处理：等待本进程退出 → 拷贝新版覆盖旧版 → 启动新版 → 清理
		batchContent := fmt.Sprintf(`@echo off
chcp 65001 >nul
echo 🔄 ComputeHub Worker 自动升级中...
echo   等待旧进程退出...
:wait
ping 127.0.0.1 -n 2 >nul
if exist "%s" (
	tasklist /fi "PID eq %d" 2>nul | find "%d" >nul
	if not errorlevel 1 goto wait
)
echo   旧进程已退出，正在替换二进制...
copy /Y "%s" "%s" >nul
echo   正在启动新版本...
start "" "%s" %s
echo ✅ 新版 Worker 已启动
del "%%~f0"
`, tmpFile, os.Getpid(), os.Getpid(), tmpFile, currentExe, currentExe, strings.Join(os.Args[1:], " "))

		if err := os.WriteFile(batchFile, []byte(batchContent), 0644); err != nil {
			os.Remove(tmpFile)
			return fmt.Errorf("创建升级脚本失败: %w", err)
		}
		fmt.Printf("   %s📝 升级脚本已创建: %s%s\n", dim(""), batchFile, reset())

		// 启动批处理（隐藏窗口）
		cmd := exec.Command("cmd", "/c", "start", "/min", batchFile)
		if err := cmd.Start(); err != nil {
			os.Remove(batchFile)
			os.Remove(tmpFile)
			return fmt.Errorf("启动升级脚本失败: %w", err)
		}
		fmt.Printf("   %s✅ 升级脚本已启动，本进程即将退出%s\n", green(""), reset())
		time.Sleep(500 * time.Millisecond)

		s.unregister()
		fmt.Printf("\n %s🔄 正在重启新版 Worker (%s)...%s\n",
			green(bold("")), resp.LatestVersion, reset())
		os.Exit(0)
	} else {
		if err := os.Rename(currentExe, backupFile); err != nil {
			if err := os.Rename(tmpFile, currentExe); err != nil {
				os.Remove(tmpFile)
				return fmt.Errorf("替换二进制失败: %w", err)
			}
			fmt.Printf("   %s✅ 已更新%s\n", dim(""), reset())
		} else {
			if err := os.Rename(tmpFile, currentExe); err != nil {
				os.Rename(backupFile, currentExe)
				os.Remove(tmpFile)
				return fmt.Errorf("替换失败，已恢复: %w", err)
			}
			fmt.Printf("   %s✅ 备份: %s%s\n", dim(""), backupFile, reset())
		}
	}

	// 5. Unregister from Gateway
	s.unregister()
	fmt.Printf("\n %s🔄 正在重启新版 Worker (%s)...%s\n",
		green(bold("")), resp.LatestVersion, reset())

	time.Sleep(500 * time.Millisecond)

	// 6. Restart: exec the new binary with the same arguments
	args := os.Args[1:]

	if runtime.GOOS == "windows" {
		// Windows: start new process and exit
		attr := &os.ProcAttr{
			Files: []*os.File{os.Stdin, os.Stdout, os.Stderr},
		}
		proc, err := os.StartProcess(currentExe, append([]string{currentExe}, args...), attr)
		if err != nil {
			return fmt.Errorf("启动新版失败: %w", err)
		}
		fmt.Printf("   %s✅ 新版 Worker 已启动 (PID=%d)%s\n", green(""), proc.Pid, reset())
		os.Exit(0)
	}

	// Unix: start new process and exit (old worker's main loop will restart anyway)
	attr := &os.ProcAttr{
		Files: []*os.File{os.Stdin, os.Stdout, os.Stderr},
	}
	proc, err := os.StartProcess(currentExe, append([]string{currentExe}, args...), attr)
	if err != nil {
		return fmt.Errorf("启动新版失败: %w", err)
	}
	fmt.Printf("   %s✅ 新版 Worker 已启动 (PID=%d)%s\n", green(""), proc.Pid, reset())
	os.Exit(0)
	return nil
}

// upgradeLoop 定期检查更新（启动后运行在 goroutine 中）
func (s *WorkerState) upgradeLoop() {
	// 启动后等待 10 秒再做第一次检查（让注册完成）
	time.Sleep(10 * time.Second)

	for {
		resp, err := s.checkUpgrade()
		if err != nil {
			time.Sleep(5 * time.Minute)
			continue
		}

		if resp != nil && resp.UpdateAvailable && resp.DownloadURL != "" {
			fmt.Printf("\n %s🔄 自动更新: %s → %s%s\n",
				yellow(bold("")), version.Short(), resp.LatestVersion, reset())

			if err := s.performUpgrade(resp); err != nil {
				fmt.Printf(" %s❌ 自动更新失败: %v%s\n", red(bold("")), err, reset())
			}
			// 如果更新成功，performUpgrade 会退出进程
		}

		time.Sleep(5 * time.Minute)
	}
}

// copyFile copies src to dst with the same permissions
func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	if err != nil {
		return err
	}
	return out.Sync()
}
