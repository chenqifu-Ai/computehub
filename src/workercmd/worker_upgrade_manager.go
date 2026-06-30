// ComputeHub Worker Intelligent Upgrade Manager — Phase 2
//
// The upgrade manager owns upgrade POLICY and STRATEGY.
// The UpgradeEngine owns upgrade EXECUTION (download, script, rollback, verify).
//
// Architecture:
//   UpgradeManager (policy + strategy)
//     └── UpgradeEngine (execution + safety + platform abstraction)
//           ├── DownloadWithChecksum    — download + SHA256
//           ├── ScheduleIndependentUpgrade — detached script execution
//           ├── PerformRollback         — backup restore + restart
//           ├── VerifyNewWorker         — health check after upgrade
//           ├── CleanupOldVersions      — disk space management
//           └── BackupCurrent           — pre-upgrade snapshot

package workercmd

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/computehub/opc/src/agent"
	"github.com/computehub/opc/src/executil"
	"github.com/computehub/opc/src/version"
)

// ═══════════════════════════════════════════
// UpgradeCache — 本地版本缓存
// ═══════════════════════════════════════════

type UpgradeCache struct {
	LastCheckTime     time.Time `json:"last_check_time"`
	CachedVersion     string    `json:"cached_version"`
	UpgradePending    bool      `json:"upgrade_pending"`
	LastUpgradeTime   time.Time `json:"last_upgrade_time"`
	LastUpgradeResult string    `json:"last_upgrade_result"` // "success" | "failed" | "skipped" | "rollback"
	LastUpgradeError  string    `json:"last_upgrade_error"`
	UpgradeCount      int       `json:"upgrade_count"`
	RollbackCount     int       `json:"rollback_count"`
}

func getCachePath(nodeID string) string {
	homeDir := getWorkerHomeDir()
	return homeDir + "/.computehub/upgrade_cache_" + nodeID + ".json"
}

func (m *UpgradeManager) loadCache() {
	cachePath := getCachePath(m.state.nodeID)
	data, err := os.ReadFile(cachePath)
	if err != nil {
		m.cache = &UpgradeCache{CachedVersion: version.Short()}
		return
	}
	if err := json.Unmarshal(data, &m.cache); err != nil {
		m.cache = &UpgradeCache{CachedVersion: version.Short()}
		return
	}
	if m.cache.CachedVersion == "" {
		m.cache.CachedVersion = version.Short()
		return
	}
	// FIX: If cache version differs from current binary, the last upgrade
	// didn't write back the cache (or we're on a freshly restarted process).
	// Always sync CachedVersion to the actual binary version to prevent
	// "stuck upgrade loop" where cache says 1.3.27 but binary is 1.3.28.
	if m.cache.CachedVersion != version.Short() {
		m.cache.CachedVersion = version.Short()
		m.saveCache()
	}
}

func (m *UpgradeManager) saveCache() {
	cachePath := getCachePath(m.state.nodeID)
	os.MkdirAll(filepath.Dir(cachePath), 0755)
	data, _ := json.MarshalIndent(m.cache, "", "  ")
	os.WriteFile(cachePath, data, 0644)
}

// ═══════════════════════════════════════════
// 升级策略
// ═══════════════════════════════════════════

type UpgradeStrategy string

const (
	UpgradeAuto      UpgradeStrategy = "auto"      // detect & upgrade immediately
	UpgradeScheduled UpgradeStrategy = "scheduled" // only upgrade in time window
	UpgradeManual    UpgradeStrategy = "manual"    // cache only, wait for instruction
	UpgradeRolling   UpgradeStrategy = "rolling"   // cluster rolling upgrade (Gateway orchestrated)
)

// UpgradeStrategyInfo returns the strategy descriptions.
func UpgradeStrategyInfo() string {
	return `升级策略说明:
  auto      — 自动升级（默认）检测到新版立即升级
  scheduled — 定时升级    只在凌晨调度窗口内升级（避免影响任务）
  manual    — 手动升级    只缓存不执行，等管理员/Agent 指令
  rolling   — 滚动升级    逐节点升级（需要集群支持）
`
}

// ═══════════════════════════════════════════
// UpgradeManager — 策略层
// ═══════════════════════════════════════════

type UpgradeManager struct {
	state          *WorkerState
	client         *http.Client
	cache          *UpgradeCache
	strategy       UpgradeStrategy
	windowStartHour int
	windowEndHour   int
	engine         *UpgradeEngine
	executor       *UpgradeExecutor // Phase 3: test-register executor

	// forceSkipVersion — set after a failed upgrade so we don't retry the
	// same version forever. Cleared when a new version is detected.
	forceSkipVersion string
}

func parseStrategy(s string) UpgradeStrategy {
	switch strings.ToLower(s) {
	case "auto", "":
		return UpgradeAuto
	case "scheduled":
		return UpgradeScheduled
	case "manual":
		return UpgradeManual
	case "rolling":
		return UpgradeRolling
	default:
		return UpgradeAuto
	}
}

// NewUpgradeManager creates an UpgradeManager with the UpgradeEngine ready.
func NewUpgradeManager(state *WorkerState) *UpgradeManager {
	strategyStr := os.Getenv("COMPUTEHUB_UPGRADE_STRATEGY")
	if strategyStr == "" {
		strategyStr = "auto"
	}

	// Create engine first
	engine := NewUpgradeEngine(state)

	m := &UpgradeManager{
		state:            state,
		client:           &http.Client{Timeout: 20 * time.Second}, // 20s — API调用不该超过20秒
		strategy:         parseStrategy(strategyStr),
		windowStartHour:  2, // default 2-4 AM
		windowEndHour:    4,
		engine:           engine,
		executor:         NewUpgradeExecutor(state), // Phase 3: test-register executor
	}
	m.loadCache()
	m.log("已初始化: 策略=%s 引擎=%s", m.strategy, "UpgradeEngine")
	if m.strategy == UpgradeScheduled {
		m.log("调度窗口: %02d:00 - %02d:00", m.windowStartHour, m.windowEndHour)
	}

	return m
}

// ═══════════════════════════════════════════
// RunOnce — 单次升级循环
// ═══════════════════════════════════════════

// RunOnce executes one upgrade check → condition → download → execute cycle.
// Called by upgradeLoop() every 30 minutes.
//
// Returns nil on success (no upgrade needed, or upgrade executed and process exited).
// Returns error if conditions aren't met (caller should try fallback).
func (m *UpgradeManager) RunOnce() error {
	needsUpgrade, newVer, oldVer := m.CheckForUpgrade()
	if !needsUpgrade {
		m.cache.LastCheckTime = time.Now()
		m.saveCache()
		return nil
	}

	// Skip if this version already failed
	if newVer == m.forceSkipVersion {
		return nil
	}

	// New version detected — clear skip flag from old version
	if m.forceSkipVersion != "" {
		m.log("清空跳过标记 (旧版本 %s 有新版本 %s)", m.forceSkipVersion, newVer)
		m.forceSkipVersion = ""
	}

	// Strategy check
	switch m.strategy {
	case UpgradeManual:
		m.log("⏸️  策略=manual, 跳过 %s → %s (已缓存)", oldVer, newVer)
		m.saveCache()
		return nil

	case UpgradeScheduled:
		now := time.Now()
		hour := now.Hour()
		if hour < m.windowStartHour || hour >= m.windowEndHour {
			m.log("⏰ 策略=scheduled, 当前 %02d:00 不在窗口 (%02d:00-%02d:00)", hour, m.windowStartHour, m.windowEndHour)
			m.saveCache()
			return nil
		}

	case UpgradeRolling:
		m.log("🔄 策略=rolling, 当前节点独立升级")
	}

	// Conditions check
	if err := m.CheckUpgradeConditions(); err != nil {
		m.saveCache()
		return fmt.Errorf("条件不满足: %w", err)
	}

	// ── Phase 3: test-register executor ──
	m.log("🔄 触发升级: %s → %s (test-register模式)", oldVer, newVer)

	// NOTE: cache is NOT updated here.
	// executor.Execute() calls os.Exit(0) on success — cache will be rewritten
	// on the fresh process start (loadCache → CachedVersion = version.Short()).
	// If executor fails, cache must stay at old version so next loop retries.

	// Cleanup old versions (async, non-blocking)
	go m.engine.CleanupOldVersions()

	// The executor handles everything:
	//   - download + verify binary
	//   - spawn child (--test-register) from staging
	//   - TCP IPC: wait for child "ready"
	//   - backup old binary
	//   - unregister + exit(0)
	//   → child replaces binary + re-registers + enters worker loop
	//
	// On success: this function does NOT return (process exits via os.Exit(0)).
	// On failure: returns error, caller retries later.
	if err := m.executor.Execute(newVer); err != nil {
		m.log("❌ test-register升级失败: %v", err)
		m.forceSkipVersion = newVer
		return fmt.Errorf("test-register升级失败: %w", err)
	}

	// Unreachable — executor calls os.Exit(0) on success
	return nil
}

// ═══════════════════════════════════════════
// 版本检查
// ═══════════════════════════════════════════

// CheckForUpgrade queries Gateway for available version.
func (m *UpgradeManager) CheckForUpgrade() (needsUpgrade bool, newVersion, oldVersion string) {
	url := fmt.Sprintf("%s/api/v1/upgrade/check?current_version=%s&node_id=%s&platform=%s/%s",
		m.state.config.GatewayURL,
		m.cache.CachedVersion,
		m.state.nodeID,
		runtime.GOOS,
		runtime.GOARCH,
	)

	resp, err := m.client.Get(url)
	if err != nil {
		m.log("⚠️  检查连接失败: %v", err)
		return false, "", m.cache.CachedVersion
	}
	defer resp.Body.Close()

	var wrapper struct {
		Success bool            `json:"success"`
		Data    json.RawMessage `json:"data"`
		Error   string          `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&wrapper); err != nil {
		m.log("⚠️  JSON解析失败: %v", err)
		return false, "", m.cache.CachedVersion
	}
	if !wrapper.Success {
		m.log("⚠️  API错误: %s", wrapper.Error)
		return false, "", m.cache.CachedVersion
	}

	var respData struct {
		CurrentVersion  string `json:"current_version"`
		LatestVersion   string `json:"latest_version"`
		UpdateAvailable bool   `json:"update_available"`
	}
	if err := json.Unmarshal(wrapper.Data, &respData); err != nil {
		m.log("⚠️  数据解析失败: %v", err)
		return false, "", m.cache.CachedVersion
	}

	m.cache.LastCheckTime = time.Now()
	m.saveCache()

	if !respData.UpdateAvailable {
		// Version matches gateway latest — cache is already up to date
		return false, respData.LatestVersion, m.cache.CachedVersion
	}

	return true, respData.LatestVersion, m.cache.CachedVersion
}

// ═══════════════════════════════════════════
// 升级条件检查
// ═══════════════════════════════════════════

func (m *UpgradeManager) CheckUpgradeConditions() error {
	// 1. Active tasks
	m.state.mu.Lock()
	runningCount := len(m.state.runningTasks)
	m.state.mu.Unlock()
	if runningCount > 0 {
		return fmt.Errorf("有 %d 个任务正在运行", runningCount)
	}

	// 2. Disk space (need ~20MB: download + backup + headroom)
	requiredSpace := int64(20 * 1024 * 1024)
	freeSpace := getFreeDiskSpace(m.engine.downloadDir)
	if freeSpace < requiredSpace {
		return fmt.Errorf("磁盘空间不足: 需 %.1fMB, 仅 %.1fMB",
			float64(requiredSpace)/1024/1024,
			float64(freeSpace)/1024/1024)
	}

	// 3. Rate limit: max 1 upgrade per 5 minutes
	if time.Since(m.cache.LastUpgradeTime) < 5*time.Minute {
		return fmt.Errorf("冷却中 (上次升级 %s 前)", time.Since(m.cache.LastUpgradeTime).Round(time.Second))
	}

	return nil
}

// ═══════════════════════════════════════════
// 下载 (委托给 Engine)
// ═══════════════════════════════════════════

// DownloadNewBinary downloads the latest binary via engine (with SHA256).
func (m *UpgradeManager) DownloadNewBinary() (string, error) {
	needsUpgrade, newVersion, _ := m.CheckForUpgrade()
	if !needsUpgrade {
		return "", fmt.Errorf("没有可用的新版本")
	}
	return m.engine.DownloadWithChecksum(newVersion)
}

// ═══════════════════════════════════════════
// 完整升级流程
// ═══════════════════════════════════════════

// PerformUpgrade executes the full upgrade flow via engine.
// If force=true, skips condition checks.
func (m *UpgradeManager) PerformUpgrade(force bool) (string, error) {
	if !force {
		if err := m.CheckUpgradeConditions(); err != nil {
			return "", fmt.Errorf("升级条件不满足: %s", err)
		}
	}

	needsUpgrade, newVer, oldVer := m.CheckForUpgrade()
	if !needsUpgrade && !force {
		return fmt.Sprintf("✅ 已是最新版本: %s", m.cache.CachedVersion), nil
	}
	if !needsUpgrade && force {
		// force=true: 用实际 binary 版本重新检查（绕开缓存偏差）
		savedVer := m.cache.CachedVersion
		m.cache.CachedVersion = version.Short()
		needsUpgrade, newVer, oldVer = m.CheckForUpgrade()
		m.cache.CachedVersion = savedVer
		if !needsUpgrade {
			return fmt.Sprintf("✅ 已是最新版本: %s", version.Short()), nil
		}
	}

	newBinary, err := m.engine.DownloadWithChecksum(newVer)
	if err != nil {
		return "", fmt.Errorf("下载失败: %w", err)
	}

	// Backup
	m.engine.BackupCurrent(version.Short())

	// Schedule upgrade (spawns detached process that replaces binary + restarts)
	if err := m.engine.ScheduleIndependentUpgrade(newBinary, newVer); err != nil {
		m.cache.LastUpgradeResult = "failed"
		m.cache.LastUpgradeError = err.Error()
		m.saveCache()
		return "", fmt.Errorf("调度升级失败: %w", err)
	}

	// Cache update AFTER successful schedule (not before download — download already passed)
	m.cache.CachedVersion = newVer
	m.cache.LastUpgradeTime = time.Now()
	m.cache.LastUpgradeResult = "success"
	m.cache.UpgradeCount++
	m.saveCache()

	m.engine.CleanupOldVersions()

	return fmt.Sprintf("✅ 升级已调度: %s → %s\n进程退出，升级脚本将接管替换/验证/重启", oldVer, newVer), nil
}

// ═══════════════════════════════════════════
// 回滚 (委托给 Engine)
// ═══════════════════════════════════════════

// PerformRollback restores the most recent backup and restarts the Worker.
func (m *UpgradeManager) PerformRollback() (string, error) {
	m.cache.LastUpgradeResult = "rollback"
	m.cache.RollbackCount++
	m.saveCache()

	return m.engine.PerformRollback()
}

// ═══════════════════════════════════════════
// 状态查询
// ═══════════════════════════════════════════

func (m *UpgradeManager) GetUpgradeStatus() string {
	needsUpgrade, newVer, oldVer := m.CheckForUpgrade()

	var b strings.Builder
	b.WriteString(fmt.Sprintf("当前版本: %s\n", version.Short()))
	b.WriteString(fmt.Sprintf("缓存版本: %s\n", m.cache.CachedVersion))
	b.WriteString(fmt.Sprintf("Gateway最新: %s\n", newVer))

	if needsUpgrade {
		b.WriteString(fmt.Sprintf("🔄 有可用升级: %s → %s\n", oldVer, newVer))
	} else {
		b.WriteString(fmt.Sprintf("✅ 已是最新版本\n"))
	}

	b.WriteString(fmt.Sprintf("升级策略: %s", m.strategy))
	if m.strategy == UpgradeScheduled {
		b.WriteString(fmt.Sprintf(" (窗口 %02d:00-%02d:00)", m.windowStartHour, m.windowEndHour))
	}
	b.WriteString("\n")

	// Active tasks
	m.state.mu.Lock()
	runningCount := len(m.state.runningTasks)
	m.state.mu.Unlock()
	b.WriteString(fmt.Sprintf("活跃任务: %d\n", runningCount))

	// Disk space
	freeSpace := getFreeDiskSpace(m.engine.downloadDir)
	b.WriteString(fmt.Sprintf("可用磁盘: %.1fMB\n", float64(freeSpace)/1024/1024))

	// Engine info
	b.WriteString("\n升级引擎: UpgradeEngine v2\n")
	b.WriteString(fmt.Sprintf("  备份目录: %s\n", m.engine.backupDir))

	// Backups
	backups := m.engine.ListBackups()
	if len(backups) > 0 {
		b.WriteString(fmt.Sprintf("  可用备份 (%d 个):\n", len(backups)))
		for i, bk := range backups {
			if i >= 5 {
				b.WriteString(fmt.Sprintf("    ... 还有 %d 个\n", len(backups)-5))
				break
			}
			b.WriteString(fmt.Sprintf("    📦 %s\n", bk))
		}
	} else {
		b.WriteString("  可用备份: (无)\n")
	}

	// Cache info
	b.WriteString(fmt.Sprintf("\n升级缓存:\n"))
	b.WriteString(fmt.Sprintf("  上次检查: %s\n", m.cache.LastCheckTime.Format("2006-01-02 15:04:05")))
	b.WriteString(fmt.Sprintf("  上次升级: %s (%s)\n",
		m.cache.LastUpgradeTime.Format("2006-01-02 15:04:05"),
		m.cache.LastUpgradeResult))
	if m.cache.LastUpgradeError != "" {
		b.WriteString(fmt.Sprintf("  错误信息: %s\n", m.cache.LastUpgradeError))
	}
	b.WriteString(fmt.Sprintf("  历史升级: %d 次 (回滚 %d 次)\n", m.cache.UpgradeCount, m.cache.RollbackCount))
	b.WriteString(fmt.Sprintf("  跳过版本: %s\n", m.forceSkipVersion))

	// Cached binaries
	entries, _ := os.ReadDir(m.engine.downloadDir)
	count := 0
	for _, e := range entries {
		if si, err := e.Info(); err == nil && si.Size() > 5*1024*1024 {
			count++
		}
	}
	b.WriteString(fmt.Sprintf("  下载缓存: %d 个\n", count))

	return b.String()
}

// ═══════════════════════════════════════════
// Agent 工具注册
// ═══════════════════════════════════════════

func (m *UpgradeManager) RegisterAgentTools(tr *agent.ToolRegistry) {
	// Tool 1: check_and_upgrade
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "check_and_upgrade",
			Description: "检查新版本并在条件满足时自动升级。force=true 跳过条件检查。",
			Parameters: []agent.Param{
				{Name: "force", Type: "bool", Required: false, Description: "强制升级"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			force := false
			if f, ok := args["force"].(bool); ok {
				force = f
			}
			m.log("收到升级请求 (force=%v)", force)

			if !force {
				needsUpgrade, _, _ := m.CheckForUpgrade()
				if !needsUpgrade {
					return fmt.Sprintf("✅ 已是最新版本: %s", m.cache.CachedVersion), nil
				}
			}

			result, err := m.PerformUpgrade(force)
			if err != nil {
				return fmt.Sprintf("❌ 升级失败: %s", err), err
			}
			return result, nil
		},
	})

	// Tool 2: get_upgrade_status
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "get_upgrade_status",
			Description: "查看详细升级状态: 当前/最新版本、策略、缓存、备份、历史。",
			Parameters:  []agent.Param{},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			return m.GetUpgradeStatus(), nil
		},
	})

	// Tool 3: list_downloaded_versions
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "list_downloaded_versions",
			Description: "列出已下载到本地的 Worker 版本。",
			Parameters:  []agent.Param{},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			entries, err := os.ReadDir(m.engine.downloadDir)
			if err != nil {
				return "未找到下载目录", nil
			}
			var b strings.Builder
			b.WriteString(fmt.Sprintf("已下载的版本 (%d 个):\n\n", len(entries)))
			for _, e := range entries {
				if si, err := e.Info(); err == nil && si.Size() > 5*1024*1024 {
					b.WriteString(fmt.Sprintf("  %s  (%.1f MB)\n", e.Name(), float64(si.Size())/1024/1024))
				}
			}
			if b.Len() <= 40 {
				b.WriteString("  (无)")
			}
			return b.String(), nil
		},
	})

	// Tool 4: get_upgrade_policy
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "get_upgrade_policy",
			Description: "查看当前升级策略、调度窗口、备份设置。",
			Parameters:  []agent.Param{},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			var b strings.Builder
			b.WriteString("当前升级策略:\n")
			b.WriteString(fmt.Sprintf("  策略: %s\n", m.strategy))
			if m.strategy == UpgradeScheduled {
				b.WriteString(fmt.Sprintf("  调度窗口: %02d:00 - %02d:00\n", m.windowStartHour, m.windowEndHour))
			}
			b.WriteString(fmt.Sprintf("  保留备份: %d 个版本\n", m.engine.keepVersions))
			b.WriteString(fmt.Sprintf("  下载目录: %s\n", m.engine.downloadDir))
			b.WriteString(fmt.Sprintf("  备份目录: %s\n", m.engine.backupDir))
			b.WriteString(fmt.Sprintf("\n%s", UpgradeStrategyInfo()))
			return b.String(), nil
		},
	})

	// Tool 5: set_upgrade_strategy
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "set_upgrade_strategy",
			Description: "设置升级策略: auto/scheduled/manual/rolling。可选设置调度窗口。",
			Parameters: []agent.Param{
				{Name: "strategy", Type: "string", Required: true, Description: "auto/scheduled/manual/rolling"},
				{Name: "window_start", Type: "int", Required: false, Description: "调度窗口开始小时 (0-23)"},
				{Name: "window_end", Type: "int", Required: false, Description: "调度窗口结束小时 (0-23)"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			strategyStr, _ := args["strategy"].(string)
			if strategyStr == "" {
				return "请指定策略: auto/scheduled/manual/rolling", nil
			}

			newStrategy := parseStrategy(strategyStr)
			m.strategy = newStrategy
			if ws, ok := args["window_start"].(float64); ok {
				m.windowStartHour = int(ws) % 24
			}
			if we, ok := args["window_end"].(float64); ok {
				m.windowEndHour = int(we) % 24
			}

			m.cache.LastUpgradeResult = "strategy_changed"
			m.saveCache()

			result := fmt.Sprintf("✅ 已更新为: %s\n", m.strategy)
			if m.strategy == UpgradeScheduled {
				result += fmt.Sprintf("窗口: %02d:00-%02d:00\n", m.windowStartHour, m.windowEndHour)
			}
			result += "\n注意: 策略变更仅当前会话生效。持久化需设置 COMPUTEHUB_UPGRADE_STRATEGY 环境变量"
			return result, nil
		},
	})

	// Tool 6: rollback — 回滚到上一个备份版本
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "rollback",
			Description: "回滚 Worker 到上一个备份版本。列出所有可用备份，回滚到最新的一个。",
			Parameters:  []agent.Param{},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			backups := m.engine.ListBackups()
			if len(backups) == 0 {
				return "❌ 没有可用备份版本", nil
			}

			msg := fmt.Sprintf("可用备份 (%d 个):\n", len(backups))
			for i, bk := range backups {
				if i >= 5 {
					msg += fmt.Sprintf("  ... 还有 %d 个\n", len(backups)-5)
					break
				}
				msg += fmt.Sprintf("  %d. %s\n", i+1, bk)
			}
			msg += fmt.Sprintf("\n🔄 正在回滚到: %s\n", backups[0])
			msg += "Worker 将重启以应用回滚..."

			result, err := m.PerformRollback()
			if err != nil {
				return fmt.Sprintf("❌ 回滚失败: %s", err), err
			}
			return msg + "\n" + result, nil
		},
	})

	// Tool 7: list_backups — 列出所有备份版本
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "list_backups",
			Description: "列出所有可用的备份版本（用于回滚）。",
			Parameters:  []agent.Param{},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			backups := m.engine.ListBackups()
			if len(backups) == 0 {
				return "没有可用的备份版本。\n提示: 每次升级前会自动创建备份。", nil
			}
			var b strings.Builder
			b.WriteString(fmt.Sprintf("可用备份版本 (%d 个):\n\n", len(backups)))
			for i, bk := range backups {
				info, _ := os.Stat(m.engine.backupDir + "/" + bk)
				size := ""
				if info != nil {
					size = fmt.Sprintf(" (%.1fMB)", float64(info.Size())/1024/1024)
				}
				b.WriteString(fmt.Sprintf("  %d. %s%s\n", i+1, bk, size))
			}
			b.WriteString(fmt.Sprintf("\n备份目录: %s", m.engine.backupDir))
			b.WriteString("\n\n使用 rollback 工具回滚到最新版本。")
			return b.String(), nil
		},
	})

	// Tool 8: cleanup_cache — 清理旧下载缓存
	tr.Register(&agent.ToolEntry{
		Tool: agent.Tool{
			Name:        "cleanup_cache",
			Description: "清理旧的下载缓存和备份文件，仅保留最近的 N 个版本。",
			Parameters: []agent.Param{
				{Name: "keep", Type: "int", Required: false, Description: "保留的版本数 (默认 3)"},
			},
		},
		Execute: func(ctx context.Context, args map[string]interface{}) (string, error) {
			if k, ok := args["keep"].(float64); ok {
				m.engine.keepVersions = int(k)
			}
			removed := m.engine.CleanupOldVersions()
			if len(removed) == 0 {
				return "✅ 无需清理", nil
			}
			var b strings.Builder
			b.WriteString(fmt.Sprintf("🧹 已清理 %d 个旧版本:\n", len(removed)))
			for _, r := range removed {
				b.WriteString(fmt.Sprintf("  - %s\n", r))
			}
			b.WriteString(fmt.Sprintf("\n保留版本数: %d", m.engine.keepVersions))
			return b.String(), nil
		},
	})
}

// ═══════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════

func getFreeDiskSpace(path string) int64 {
	if runtime.GOOS == "windows" {
		return getFreeDiskSpaceWindows(path)
	}
	cmd := executil.SafeCommand("df", "-B1", path)
	out, err := cmd.Output()
	if err == nil {
		lines := strings.Split(strings.TrimSpace(string(out)), "\n")
		if len(lines) >= 2 {
			fields := strings.Fields(lines[len(lines)-1])
			if len(fields) >= 4 {
				var avail int64
				fmt.Sscanf(fields[3], "%d", &avail)
				return avail
			}
		}
	}
	return 10 * 1024 * 1024 * 1024
}

func getFreeDiskSpaceWindows(path string) int64 {
	// Use wmic to query free space
	cmd := exec.Command("wmic", "logicaldisk", "where", "DeviceID='"+path[:2]+"'", "get", "FreeSpace")
	out, err := cmd.Output()
	if err != nil {
		return 10 * 1024 * 1024 * 1024
	}
	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || line == "FreeSpace" {
			continue
		}
		var free int64
		if _, err := fmt.Sscanf(line, "%d", &free); err == nil && free > 0 {
			return free
		}
	}
	return 10 * 1024 * 1024 * 1024
}

func (m *UpgradeManager) log(format string, args ...interface{}) {
	t := time.Now().Format("15:04:05")
	fmt.Printf("\033[2m[%s] [Upgrade]\033[0m "+format+"\n", append([]interface{}{t}, args...)...)
}