//go:build linux

package gateway

import (
	"fmt"
	"os"
	"syscall"
)

func readCPUPercent() float64 {
	data, err := os.ReadFile("/proc/stat")
	if err != nil {
		return 0
	}
	var user, nice, system, idle, iowait, irq, softirq, steal float64
	if _, err := fmt.Sscanf(string(data[0:300]), "cpu  %f %f %f %f %f %f %f %f",
		&user, &nice, &system, &idle, &iowait, &irq, &softirq, &steal); err != nil {
		return 0
	}
	total := user + nice + system + idle + iowait + irq + softirq + steal
	if total == 0 {
		return 0
	}
	idleTotal := idle + iowait
	return (1 - idleTotal/total) * 100
}

func readMemPercent() float64 {
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 0
	}
	var total, available float64
	if _, err := fmt.Sscanf(string(data), "MemTotal:       %f kB\nMemAvailable:  %f kB", &total, &available); err != nil {
		return 0
	}
	if total == 0 {
		return 0
	}
	return (1 - available/total) * 100
}

func readLoad1m() float64 {
	data, err := os.ReadFile("/proc/loadavg")
	if err != nil {
		return 0
	}
	var load1m float64
	if _, err := fmt.Sscanf(string(data), "%f", &load1m); err != nil {
		return 0
	}
	return load1m
}

func readDiskPercent() float64 {
	var stat syscall.Statfs_t
	if err := syscall.Statfs("/", &stat); err != nil {
		return 0
	}
	total := float64(stat.Blocks) * float64(stat.Bsize)
	available := float64(stat.Bavail) * float64(stat.Bsize)
	if total == 0 {
		return 0
	}
	return (1 - available/total) * 100
}