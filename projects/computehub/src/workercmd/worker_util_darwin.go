//go:build darwin
// +build darwin

package workercmd

import (
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
)

func runCommand(cmd string) *exec.Cmd {
	if _, err := exec.LookPath("bash"); err == nil {
		return exec.Command("bash", "-c", cmd)
	}
	return exec.Command("/bin/sh", "-c", cmd)
}

func killProcess(p *os.Process) {
	if p != nil {
		p.Signal(syscall.SIGTERM)
	}
}

func detectMemoryGB() float64 {
	// sysctl hw.memsize returns physical memory in bytes
	cmd := exec.Command("sysctl", "-n", "hw.memsize")
	out, err := cmd.Output()
	if err != nil {
		return 16
	}
	bytes, err := strconv.ParseFloat(strings.TrimSpace(string(out)), 64)
	if err != nil {
		return 16
	}
	return bytes / 1024 / 1024 / 1024
}

func getCPULoad() float64 {
	// sysctl vm.loadavg returns { 1.23 0.67 0.34 }
	cmd := exec.Command("sysctl", "-n", "vm.loadavg")
	out, err := cmd.Output()
	if err != nil {
		return 0
	}
	cleaned := strings.Trim(string(out), "{} \n\r")
	parts := strings.Fields(cleaned)
	if len(parts) >= 1 {
		load, err := strconv.ParseFloat(parts[0], 64)
		if err != nil {
			return 0
		}
		return load
	}
	return 0
}

func detectGPUType() (string, error) {
	// Check for Apple Silicon GPU first
	cmd := exec.Command("sysctl", "-n", "machdep.cpu.brand_string")
	out, err := cmd.Output()
	if err == nil {
		brand := strings.TrimSpace(string(out))
		if strings.Contains(brand, "Apple") {
			return "Apple Silicon GPU", nil
		}
	}
	// For Intel Macs, try system_profiler
	cmd = exec.Command("system_profiler", "SPDisplaysDataType")
	out, err = cmd.Output()
	if err != nil {
		return "", fmt.Errorf("no GPU detected")
	}
	for _, line := range strings.Split(string(out), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "Chipset Model:") || strings.HasPrefix(line, "Vendor:") {
			return strings.TrimSpace(strings.SplitN(line, ":", 2)[1]), nil
		}
	}
	return "", fmt.Errorf("no GPU found")
}

func countGPUs() int {
	return 1
}

func (s *WorkerState) collectNvidiaSMI() GPUStats {
	return GPUStats{Count: 0}
}
