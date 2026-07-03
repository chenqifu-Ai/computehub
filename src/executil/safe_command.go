// Package executil provides safe wrappers around os/exec for systems where
// os/exec.LookPath (faccessat2) is blocked by seccomp (Android/Termux → SIGSYS).
//
// The fix: pre-resolve binary paths via os.Stat (uses fstatat/statx, which are
// allowed by seccomp) and pass absolute paths to exec.Command, so lookPath is
// never called.
//
// Usage:
//
//	cmd := executil.SafeCommand("df", "-B1", "/data")
//	out, _ := cmd.Output()
package executil

import (
	"os"
	"os/exec"
	"path/filepath"
)

// known paths to search for binaries, ordered by priority.
// On Termux, binaries live under /data/data/com.termux/files/usr/bin/.
// On regular Linux, /usr/bin/ and /bin/ are standard.
var knownPrefixes = []string{
	"/data/data/com.termux/files/usr/bin/", // Termux/Android
	"/system/bin/",                          // Android system
	"/system/xbin/",                         // Android system (root)
	"/usr/bin/",
	"/bin/",
	"/usr/local/bin/",
}

// SafeCommand creates an exec.Cmd resolving binary paths via os.Stat
// to bypass the faccessat2 syscall that crashes on Termux (SIGSYS).
//
// If name already contains a path separator (/), it's passed through
// directly (exec.Command skips lookPath for those).
func SafeCommand(name string, args ...string) *exec.Cmd {
	// If name already has a path separator, exec.Command will skip lookPath.
	if filepath.Base(name) != name {
		return exec.Command(name, args...)
	}

	// Try known paths via os.Stat (safe syscall) before falling through to lookPath.
	for _, prefix := range knownPrefixes {
		full := prefix + name
		if fi, err := os.Stat(full); err == nil && !fi.IsDir() {
			return exec.Command(full, args...)
		}
	}

	// Fallback: let os/exec handle it (works fine on non-Android systems)
	return exec.Command(name, args...)
}

// SafeLookPath resolves a binary path without using faccessat2.
// Falls back to name if not found in known paths.
func SafeLookPath(name string) string {
	if filepath.Base(name) != name {
		return name
	}
	for _, prefix := range knownPrefixes {
		full := prefix + name
		if fi, err := os.Stat(full); err == nil && !fi.IsDir() {
			return full
		}
	}
	return name
}
