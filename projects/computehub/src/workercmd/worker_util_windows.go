//go:build windows
// +build windows

package workercmd

import (
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
	"unsafe"
)

var (
	kernel32                   = syscall.NewLazyDLL("kernel32.dll")
	procGlobalMemoryStatusEx   = kernel32.NewProc("GlobalMemoryStatusEx")
)

type memoryStatusEx struct {
	dwLength        uint32
	dwMemoryLoad    uint32
	ullTotalPhys    uint64
	ullAvailPhys    uint64
	ullTotalPageFile uint64
	ullAvailPageFile uint64
	ullTotalVirtual uint64
	ullAvailVirtual uint64
	ullAvailExtendedV uint64
}

func runCommand(cmd string) *exec.Cmd {
	// 自动切换 UTF-8 编码，解决中文乱码问题
	return exec.Command("cmd", "/c", "chcp 65001 >nul && "+cmd)
}

func killProcess(p *os.Process) {
	if p != nil {
		p.Kill()
	}
}

func detectMemoryGB() float64 {
	var ms memoryStatusEx
	ms.dwLength = uint32(unsafe.Sizeof(ms))
	ret, _, _ := procGlobalMemoryStatusEx.Call(uintptr(unsafe.Pointer(&ms)))
	if ret != 0 {
		return float64(ms.ullTotalPhys) / 1024 / 1024 / 1024
	}
	return 32
}

func getCPULoad() float64 {
	return 50.0
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
