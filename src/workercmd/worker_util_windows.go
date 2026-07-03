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

func runCommand(cmdStr string) *exec.Cmd {
	// Windows: use powershell -Command directly instead of cmd.exe /c
	// This avoids "Access is denied" when cmd.exe cannot be forked
	// Also ensures UTF-8 output encoding
	escaped := strings.ReplaceAll(cmdStr, `"`, `"`)
	psCmd := fmt.Sprintf(`[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; %s`, escaped)
	return exec.Command("powershell", "-Command", psCmd)
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

// ── GPU 检测（nvidia-smi → WMI 回退） ──

// detectGPUType 检测 GPU 型号，优先 nvidia-smi，回退到 WMI
func detectGPUType() (string, error) {
	// 1st try: nvidia-smi（NVIDIA 卡）
	cmd := exec.Command("nvidia-smi", "--query-gpu=name", "--format=csv,noheader")
	output, err := cmd.Output()
	if err == nil {
		lines := strings.Split(strings.TrimSpace(string(output)), "\n")
		if len(lines) > 0 && strings.TrimSpace(lines[0]) != "" {
			return strings.TrimSpace(lines[0]), nil
		}
	}

	// 2nd try: WMI — 适用于摩尔线程、AMD、Intel 等非 NVIDIA GPU
	gpuName, err := detectGPUThroughWMI()
	if err == nil && gpuName != "" {
		return gpuName, nil
	}

	return "", fmt.Errorf("no GPU detected via nvidia-smi or WMI")
}

// detectGPUThroughWMI 通过 Windows WMI 查询第一块独立 GPU
func detectGPUThroughWMI() (string, error) {
	// PowerShell: 获取第一个非 Microsoft 基本显卡的 GPU 名称
	psCmd := `Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notmatch 'Microsoft Basic Display' } | Select-Object -First 1 -ExpandProperty Name`
	cmd := exec.Command("powershell", "-Command", psCmd)
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}
	name := strings.TrimSpace(string(output))
	if name == "" {
		return "", fmt.Errorf("no dedicated GPU found via WMI")
	}
	return name, nil
}

// countGPUs 统计 GPU 数量，优先 nvidia-smi，回退到 WMI
func countGPUs() int {
	// 1st try: nvidia-smi
	cmd := exec.Command("nvidia-smi", "-L")
	output, err := cmd.Output()
	if err == nil {
		count := 0
		for _, line := range strings.Split(strings.TrimSpace(string(output)), "\n") {
			if strings.TrimSpace(line) != "" {
				count++
			}
		}
		if count > 0 {
			return count
		}
	}

	// 2nd try: WMI — 统计独立 GPU 数
	psCmd := `@(Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notmatch 'Microsoft Basic Display' }).Count`
	cmd2 := exec.Command("powershell", "-Command", psCmd)
	out2, err2 := cmd2.Output()
	if err2 != nil {
		return 0
	}
	count, _ := strconv.Atoi(strings.TrimSpace(string(out2)))
	return count
}

// isNVIDIAGPU 判断是否为 NVIDIA GPU
func isNVIDIAGPU() bool {
	cmd := exec.Command("nvidia-smi", "--query-gpu=name", "--format=csv,noheader")
	if err := cmd.Run(); err != nil {
		return false
	}
	return true
}

// collectNvidiaSMI 采集 GPU 状态（温度/利用率/显存）
// 对 NVIDIA 卡：通过 nvidia-smi 获取完整数据
// 对非 NVIDIA 卡：通过 WMI 获取可用数据（利用率/温度可能不可用）
func (s *WorkerState) collectNvidiaSMI() GPUStats {
	var stats GPUStats

	// Try nvidia-smi first
	if isNVIDIAGPU() {
		cmd := exec.Command("nvidia-smi",
			"--query-gpu=index,utilization.gpu,temperature.gpu,memory.used,memory.total",
			"--format=csv,noheader,nounits")
		output, err := cmd.Output()
		if err == nil {
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
	}

	// Fallback: WMI — 摩尔线程/AMD/Intel 显卡，只取显存信息
	psCmd := `Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notmatch 'Microsoft Basic Display' } | Select-Object Name,AdapterRAM`
	cmd2 := exec.Command("powershell", "-Command", psCmd)
	output2, err2 := cmd2.Output()
	if err2 != nil {
		return stats
	}

	lines := strings.Split(strings.TrimSpace(string(output2)), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.Contains(line, "Name") || strings.Contains(line, "AdapterRAM") || strings.Contains(line, "----") {
			continue
		}
		// Parse WMI output: "Moore Threads S3000  17179869184"
		fields := strings.Fields(line)
		if len(fields) >= 2 {
			// Last field should be the RAM value in bytes
			ramBytes, err := strconv.ParseInt(fields[len(fields)-1], 10, 64)
			if err == nil && ramBytes > 0 {
				stats.Count++
				stats.MemoryTotalGB += float64(ramBytes) / 1024 / 1024 / 1024
			}
		}
	}
	if stats.Count == 0 {
		// If WMI parsing failed, try simpler approach: just get count and name
		stats.Count = countGPUs()
		// Rough estimate if we know it's a GPU machine
		if stats.Count > 0 {
			stats.MemoryTotalGB = 16.0 // conservative default for Moore Threads S3000
		}
	}
	return stats
}
