// Fix for findDeployDir() — version.txt mismatch causing infinite upgrade loop
//
// The bug: findDeployDir() looks for deploy/ relative to binary location.
// When binary is at /home/computehub/computehub, it finds /home/computehub/deploy/
// (old deployment leftover, version.txt = 1.2.2) instead of
// /home/computehub/OPC/deploy/ (version.txt = 1.2.3).
//
// Fix: walk UP from binary location looking for .git to find project root,
// then use that as anchor for deploy/ directory.

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	srcPath := "/data/data/com.termux/files/home/OPC/src/gateway/gateway.go"

	content, err := os.ReadFile(srcPath)
	if err != nil {
		fmt.Printf("Read error: %v\n", err)
		os.Exit(1)
	}

	oldFunc := `// findDeployDir finds the deploy directory relative to the binary location.
// It supports both flat (deploy/) and versioned (deploy/<version>/) layouts.
func findDeployDir() string {
	// Determine where the running binary lives — that's the most reliable anchor
	exe, _ := os.Executable()
	exeDir := ""
	if exe != "" {
		if idx := strings.LastIndex(exe, "/"); idx >= 0 {
			exeDir = exe[:idx]
		}
	}

	// Search versioned directory first (binary may live in deploy/0.7.4/linux-arm64/)
	versionCandidates := []string{
		"deploy/0.7.7",
		"deploy/0.7.6",
		"deploy/0.7.5",
		"deploy/0.7.4",
	}
	for _, c := range versionCandidates {
		// Try relative to binary directory (e.g. exe=/deploy/0.7.4/linux-arm64/gw → ../../deploy/0.7.4)
		if exeDir != "" {
			// Binary is in a platform subdirectory: ../.. = version dir
			// Binary is in deploy root: .. = parent dir (project root)
			// Try both relative paths
			for _, rel := range []string{"./" + c, "../" + c, "../../" + c} {
				candidate := exeDir + "/" + rel
				if _, err := os.Stat(candidate); err == nil {
					return candidate
				}
			}
			// Also try abs path from exeDir parent
			candidate := exeDir + "/" + c
			if _, err := os.Stat(candidate); err == nil {
				return candidate
			}
		}
		// Try relative to CWD
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}

	// Fall back to flat deploy/ directory
	flatCandidates := []string{"deploy"}
	for _, c := range flatCandidates {
		if exeDir != "" {
			for _, rel := range []string{"./" + c, "../" + c, "../../" + c} {
				candidate := exeDir + "/" + rel
				if _, err := os.Stat(candidate); err == nil {
					return candidate
				}
			}
			candidate := exeDir + "/" + c
			if _, err := os.Stat(candidate); err == nil {
				return candidate
			}
		}
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}
	return "deploy"
}`

	newFunc := `// findDeployDir finds the deploy directory relative to the binary location.
// It supports both flat (deploy/) and versioned (deploy/<version>/) layouts.
//
// Critical fix (2026-06-01): When the binary lives outside the project root
// (e.g. /home/computehub/computehub while the project is /home/computehub/OPC/),
// walking up from exeDir finds a stale deploy/ at the wrong level.
// Solution: walk up looking for .git to find the project root, then use that.
func findDeployDir() string {
	// Determine where the running binary lives — that's the most reliable anchor
	exe, _ := os.Executable()
	exeDir := ""
	if exe != "" {
		if idx := strings.LastIndex(exe, "/"); idx >= 0 {
			exeDir = exe[:idx]
		}
	}

	// Strategy 1: Walk up from exeDir to find project root via .git directory.
	// This ensures we use the CORRECT deploy/ even when binary is outside the project.
	if exeDir != "" {
		dir := exeDir
		for {
			gitPath := filepath.Join(dir, ".git")
			if fi, err := os.Stat(gitPath); err == nil && fi.IsDir() {
				// Found project root at dir/.git/
				candidate := filepath.Join(dir, "deploy")
				if _, err := os.Stat(candidate); err == nil {
					return candidate
				}
				break
			}
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}

	// Strategy 2: Search versioned directory first (binary may live in deploy/0.7.4/linux-arm64/)
	versionCandidates := []string{
		"deploy/0.7.7",
		"deploy/0.7.6",
		"deploy/0.7.5",
		"deploy/0.7.4",
	}
	for _, c := range versionCandidates {
		// Try relative to binary directory (e.g. exe=/deploy/0.7.4/linux-arm64/gw → ../../deploy/0.7.4)
		if exeDir != "" {
			// Binary is in a platform subdirectory: ../.. = version dir
			// Binary is in deploy root: .. = parent dir (project root)
			// Try both relative paths
			for _, rel := range []string{"./" + c, "../" + c, "../../" + c} {
				candidate := exeDir + "/" + rel
				if _, err := os.Stat(candidate); err == nil {
					return candidate
				}
			}
			// Also try abs path from exeDir parent
			candidate := exeDir + "/" + c
			if _, err := os.Stat(candidate); err == nil {
				return candidate
			}
		}
		// Try relative to CWD
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}

	// Fall back to flat deploy/ directory
	flatCandidates := []string{"deploy"}
	for _, c := range flatCandidates {
		if exeDir != "" {
			for _, rel := range []string{"./" + c, "../" + c, "../../" + c} {
				candidate := exeDir + "/" + rel
				if _, err := os.Stat(candidate); err == nil {
					return candidate
				}
			}
			candidate := exeDir + "/" + c
			if _, err := os.Stat(candidate); err == nil {
				return candidate
			}
		}
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}
	return "deploy"
}`

	newContent := strings.Replace(string(content), oldFunc, newFunc, 1)
	if newContent == string(content) {
		fmt.Println("⚠️  Old function text not found — check exact match")
		os.Exit(1)
	}

	err = os.WriteFile(srcPath, []byte(newContent), 0644)
	if err != nil {
		fmt.Printf("Write error: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("✅ findDeployDir() patched successfully")
	fmt.Println("   Added .git walk-up strategy to find correct project root")
	fmt.Println("   Binary at /home/computehub/computehub will now find /home/computehub/OPC/deploy/")
}
