//go:build linux
// +build linux

package workercmd

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"syscall"
)

func runCommand(cmdStr string) *exec.Cmd {
	// Linux platform always uses sh -c.
	// Skip exec.LookPath("sh") because it calls faccessat2 (syscall 439)
	// which is not supported in proot/chroot environments and causes SIGSYS.
	// /bin/sh is guaranteed to exist on any POSIX Linux system.
	return exec.Command("/bin/sh", "-c", cmdStr)
}

func killProcess(p *os.Process) {
	if p != nil {
		p.Signal(syscall.SIGTERM)
	}
}

func detectMemoryGB() float64 {
	data, _ := os.ReadFile("/proc/meminfo")
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "MemTotal:") {
			parts := strings.Fields(line)
			if len(parts) >= 2 {
				kb, _ := strconv.ParseFloat(parts[1], 64)
				return kb / 1024 / 1024
			}
		}
	}
	return 32
}

func getCPULoad() float64 {
	data, _ := os.ReadFile("/proc/loadavg")
	parts := strings.Fields(string(data))
	if len(parts) >= 1 {
		load, _ := strconv.ParseFloat(parts[0], 64)
		return load / float64(runtime.NumCPU()) * 100
	}
	return 0
}

func detectGPUType() (string, error) {
	cmd := exec.Command("nvidia-smi", "--query-gpu=name", "--format=csv,noheader")
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}
	lines := strings.Split(strings.TrimSpace(string(output)), "\n")
	if len(lines) > 0 {
		return strings.TrimSpace(lines[0]), nil
	}
	return "", fmt.Errorf("no GPU found")
}

func countGPUs() int {
	cmd := exec.Command("nvidia-smi", "-L")
	output, err := cmd.Output()
	if err != nil {
		return 0
	}
	count := 0
	for _, line := range strings.Split(strings.TrimSpace(string(output)), "\n") {
		if strings.TrimSpace(line) != "" {
			count++
		}
	}
	return count
}

func (s *WorkerState) collectNvidiaSMI() GPUStats {
	var stats GPUStats
	cmd := exec.Command("nvidia-smi",
		"--query-gpu=index,utilization.gpu,temperature.gpu,memory.used,memory.total",
		"--format=csv,noheader,nounits")
	output, err := cmd.Output()
	if err != nil {
		return stats
	}
	lines := strings.Split(strings.TrimSpace(string(output)), "\n")
	for _, line := range lines {
		parts := strings.Split(line, ",")
		if len(parts) < 5 {
			continue
		}
		stats.Count++
		util, _ := strconv.ParseFloat(strings.TrimSpace(parts[1]), 64)
		temp, _ := strconv.ParseFloat(strings.TrimSpace(parts[2]), 64)
		memUsed, _ := strconv.ParseFloat(strings.TrimSpace(parts[3]), 64)
		memTotal, _ := strconv.ParseFloat(strings.TrimSpace(parts[4]), 64)
		stats.Utilization += util
		stats.Temperature += temp
		stats.MemoryUsedGB += memUsed / 1024
		stats.MemoryTotalGB += memTotal / 1024
	}
	if stats.Count > 0 {
		stats.Utilization /= float64(stats.Count)
		stats.Temperature /= float64(stats.Count)
	}
	return stats
}
