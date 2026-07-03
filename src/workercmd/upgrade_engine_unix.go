//go:build !windows

package workercmd

import (
	"fmt"
	"os/exec"
	"syscall"
)

// runUnixDetached executes a shell script in a new process group, completely
// independent of the Worker process. The Worker can exit(0) immediately after
// calling this and the upgrade script will continue running.
func (e *UpgradeEngine) runUnixDetached(scriptPath string) error {
	cmd := exec.Command("/bin/bash", scriptPath)
	cmd.Stdout = nil
	cmd.Stderr = nil
	cmd.Stdin = nil
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setpgid: true, // new process group — survives parent exit
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("启动升级脚本失败: %w", err)
	}

	e.log("🚀 升级脚本已独立执行 (PID=%d, 进程组已分离)", cmd.Process.Pid)
	return nil
}
