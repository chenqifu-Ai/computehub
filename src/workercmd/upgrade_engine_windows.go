//go:build windows

package workercmd

import "fmt"

// runUnixDetached should never be called on Windows.
// ScheduleIndependentUpgrade checks runtime.GOOS first.
func (e *UpgradeEngine) runUnixDetached(scriptPath string) error {
	return fmt.Errorf("runUnixDetached called on Windows - this is a bug")
}
