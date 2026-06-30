// Auto-upgrade system for ComputeHub Worker.
// Periodically checks Gateway for new versions, downloads,
// replaces itself, and restarts with zero manual intervention.
//
// Phase 2: UpgradeManager + UpgradeEngine are the primary path.
// This file provides the fallback (兜底) check-only path.
// The actual download+replace+restart logic has moved to:
//   - upgrade_engine.go (execution)
//   - worker_upgrade_manager.go (policy)

package workercmd

import (
	"fmt"
	"time"
)

// upgradeLoop — Worker 升级主循环
//
// Phase 2+: 优先使用 UpgradeManager → UpgradeEngine 做智能升级
//   (条件检查 + 缓存 + SHA256 + 独立脚本 + 回滚)
//
// 兜底路径: 仅当 UpgradeManager 不可用或失败时使用 fallback check
//
// 检查间隔: 30 分钟
func (s *WorkerState) upgradeLoop() {
	// 启动后等 10 秒再第一次检查（让注册完成）
	time.Sleep(10 * time.Second)

	for {
		// ── Phase 2: UpgradeManager (策略引擎) ──
		if s.um != nil {
			if err := s.um.RunOnce(); err != nil {
				fmt.Printf(" %s[Upgrade] ⚠️ UpgradeManager: %v%s\n",
					dim(""), err, reset())
				// RunOnce 返回 error（条件不满足 / 下载失败）→ 继续循环等待
				// RunOnce 执行升级 → exit(0), 不会走到这里
			}
			// 正常返回 → 继续循环
		} else {
			// 无 UpgradeManager → 兜底日志（不应发生）
			fmt.Printf(" %s[Upgrade] ⚠️ UpgradeManager 未初始化%s\n", yellow(""), reset())
		}

		// 30 分钟间隔
		time.Sleep(5 * time.Minute)
	}
}